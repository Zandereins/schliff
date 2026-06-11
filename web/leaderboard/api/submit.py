"""Community leaderboard submission endpoint.

TRUST MODEL: submissions are UNVERIFIED and community-supplied. The scores in a
submission are whatever the client POSTed — this endpoint does NOT re-run the
scoring engine, so a caller can claim any (valid-range) score. Every stored
entry is therefore tagged `"verified": false`, and consumers must treat the
leaderboard as untrusted, self-reported data, not as an authoritative ranking.

STORAGE & RATE LIMITING are backend-dependent (see the DATA_DIR / KV notes below):
when Upstash/Vercel-KV env vars are present, submissions are durable (Redis) and a
KV-backed per-IP rate limit is enforced in-function; absent, storage is per-instance
ephemeral /tmp and cross-request limiting must come from the Vercel Firewall
(dashboard / `vercel firewall` CLI / REST API) — see the deploy-side runbook.
"""

import contextlib
import fcntl
import hashlib
import json
import os
import sys
import tempfile
import unicodedata
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

MAX_BODY_BYTES = 64 * 1024  # 64 KB

VALID_GRADES = {"S", "A", "B", "C", "D"}
VALID_FORMATS = {"SKILL.md", ".cursorrules", "CLAUDE.md", "AGENTS.md"}
# The 7 headline dimensions emitted by the engine/playground are REQUIRED.
REQUIRED_DIMENSIONS = {
    "structure", "triggers", "quality", "edges", "efficiency",
    "composability", "clarity",
}
# `security` is a separate opt-in signal: accepted if present, never required.
OPTIONAL_DIMENSIONS = {"security"}
# Full set of recognized keys; any key outside this is rejected.
VALID_DIMENSIONS = REQUIRED_DIMENSIONS | OPTIONAL_DIMENSIONS

# Storage is per-instance, ephemeral /tmp seeded from the bundled data file.
# Within a warm instance, concurrent POSTs are serialized by an flock'd lock file
# and writes are atomic (os.replace), so no entry is lost to a read-modify-write
# race or torn read (issue #51 / tmp-01). DURABILITY across cold starts is a
# separate, deferred concern: the chosen path is Upstash Redis (= Vercel KV, $0),
# per docs/specs/schliff-registry-platform.md — gated on real leaderboard traffic.
# Until then the leaderboard is demo-grade by design.
DATA_DIR = "/tmp/schliff-leaderboard"
DATA_PATH = os.path.join(DATA_DIR, "submissions.json")
LOCK_PATH = os.path.join(DATA_DIR, ".lock")

# Seed data path (bundled with deployment, read-only)
SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "submissions.json")

# Control characters that could cause visual spoofing
_CONTROL_CHARS = set(range(0x00, 0x20)) - {0x0A, 0x0D, 0x09}  # allow \n \r \t
_BIDI_CHARS = {0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
# Zero-width / invisible characters. Visually undetectable, so they let an
# attacker create homograph entries that pass validation but compare unequal in
# the (repo_url, skill_name) dedup key — e.g. "my-skill" vs "my​skill" —
# polluting the leaderboard with duplicate-looking rows. Reject them outright.
_INVISIBLE_CHARS = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x061C}

# --- scoring-model epoch -----------------------------------------------------
# v8.0 introduced the full-denominator composite (PR #41/#42): a breaking scale
# change. A v8+ composite is capped at the skill's coverage and is NOT comparable
# to a v7-and-earlier renormalized composite, so the two must never share a
# ranking. Each entry is stamped with its epoch (derived from the submitted
# schliff version); query.py ranks within a single epoch. Keep this helper in
# sync with the copy in query.py (serverless functions are independent files).
CURRENT_SCORE_MODEL = 2  # full-denominator (schliff >= 8.0)


def _score_model_for(version: str) -> int:
    """Map a schliff version string to its scoring-model epoch (2 = full-denominator
    for >=8.0, 1 = legacy renormalized for earlier). Unparseable -> 1 (conservative:
    an unknown version never pollutes the current-scale ranking)."""
    try:
        major = int(str(version).lstrip("vV").split(".")[0])
    except (ValueError, AttributeError, IndexError):
        return 1
    return 2 if major >= 8 else 1


def _has_unsafe_chars(s: str) -> bool:
    """Reject strings with control, bidi-override, or invisible characters."""
    return any(
        ord(c) in _CONTROL_CHARS or ord(c) in _BIDI_CHARS or ord(c) in _INVISIBLE_CHARS
        for c in s
    )


def _validate(body):
    required = ["skill_name", "repo_url", "format", "composite", "grade", "dimensions", "version"]
    for field in required:
        if field not in body:
            return f"missing required field: {field}"

    skill_name = body["skill_name"]
    if not isinstance(skill_name, str) or not (1 <= len(skill_name) <= 200):
        return "skill_name must be a string between 1 and 200 characters"
    if _has_unsafe_chars(skill_name):
        return "skill_name contains invalid characters"

    repo_url = body["repo_url"]
    if not isinstance(repo_url, str):
        return "repo_url must be a valid GitHub repository URL"
    parsed_url = urlparse(repo_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "github.com":
        return "repo_url must be a valid GitHub repository URL"
    if len(parsed_url.path.strip("/").split("/")) < 2:
        return "repo_url must point to a specific repository"

    fmt = body["format"]
    if fmt not in VALID_FORMATS:
        return f"format must be one of: {', '.join(sorted(VALID_FORMATS))}"

    composite = body["composite"]
    if isinstance(composite, bool) or not isinstance(composite, (int, float)) or not (0 <= composite <= 100):
        return "composite must be a number between 0 and 100"

    grade = body["grade"]
    if grade not in VALID_GRADES:
        return f"grade must be one of: {', '.join(sorted(VALID_GRADES))}"

    dimensions = body["dimensions"]
    if not isinstance(dimensions, dict):
        return "dimensions must be an object"
    keys = set(dimensions.keys())
    missing = REQUIRED_DIMENSIONS - keys
    if missing:
        return f"dimensions is missing required keys: {', '.join(sorted(missing))}"
    unknown = keys - VALID_DIMENSIONS
    if unknown:
        return f"dimensions has unknown keys: {', '.join(sorted(unknown))}"
    for key, val in dimensions.items():
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not (0 <= val <= 100):
            return f"dimensions.{key} must be a number between 0 and 100"

    version = body["version"]
    if not isinstance(version, str) or not (1 <= len(version) <= 50):
        return "version must be a string between 1 and 50 characters"

    return None


def _load_submissions():
    """Load submissions from /tmp, seeding from bundled data if needed."""
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    # Seed from bundled data on first cold start
    if os.path.exists(SEED_PATH):
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    return []


def _save_submissions(entries):
    """Atomically persist submissions: write a sibling temp file, fsync it, then
    os.replace() into place so a concurrent reader never observes a torn file.
    Callers mutate under _exclusive_lock() to also prevent lost updates."""
    os.makedirs(DATA_DIR, exist_ok=True)
    data = json.dumps(entries, indent=2, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix=".submissions.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, DATA_PATH)
    except BaseException:
        # Never leave a partial temp file behind on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


@contextlib.contextmanager
def _exclusive_lock():
    """Serialize the submissions read-modify-write within a warm instance.

    /tmp is per-instance, so an OS advisory lock (flock) on a sibling lock file is
    enough to stop two concurrent POSTs from last-write-wins clobbering each other
    (issue #51 / tmp-01). Cross-instance durability is out of scope here — see the
    storage note above."""
    os.makedirs(DATA_DIR, exist_ok=True)
    lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


# --- durable storage + rate-limit via Upstash Redis REST (issues #51/#52) -------
# Active ONLY when the Upstash/Vercel-KV env vars are present. Absent -> every
# helper below is bypassed and the /tmp path above runs unchanged, so merging this
# is safe before the store is provisioned (`vercel install upstash`). stdlib-only.
# KEEP THE SHARED HELPERS (_kv_config/_kv_command/_dedup_field/_client_ip/
# _kv_rate_limited) BYTE-IDENTICAL to the copy in query.py — Vercel bundles each
# function independently, so the two files cannot share a module (test enforces it).
# The submit-only helpers/constants below (caps, _kv_upsert) live here only.
SUBMISSIONS_KEY = "schliff:submissions"

# Durable storage no longer self-heals on cold start, so dos-02 (coordinated
# IP-rotation pollution) must be bounded explicitly (issue #51 follow-up):
MAX_SUBMISSIONS = 10000        # hard cap on distinct entries (memory/cost/pollution)
GLOBAL_SUBMIT_LIMIT = 500      # global writes per window, IP-rotation-proof
GLOBAL_SUBMIT_WINDOW = 3600    # seconds (1 hour)


class LeaderboardFullError(Exception):
    """The durable store holds MAX_SUBMISSIONS distinct entries and the incoming
    submission is a brand-new identity. Updates to existing entries still pass."""


def _kv_config():
    """(url, token) for the Upstash REST API, or None when not configured."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    return (url.rstrip("/"), token) if url and token else None


def _kv_command(cfg, *args):
    """Run one Redis command via the Upstash REST API and return its `result`.
    Raises on transport / HTTP / Redis-level error."""
    url, token = cfg
    data = json.dumps([str(a) for a in args]).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError(f"KV error: {payload['error']}")
    return payload.get("result") if isinstance(payload, dict) else payload


def _dedup_field(repo_url, skill_name):
    """Stable hash of the (repo_url, skill_name) identity — the submissions-hash
    field and the dedup key. Inputs are NFKC-normalized + invalid-char-rejected
    upstream, so this is a 1:1 identity."""
    return hashlib.sha256(f"{repo_url}\n{skill_name}".encode("utf-8")).hexdigest()


def _client_ip(handler):
    """Best-effort client IP from Vercel's forwarding headers."""
    fwd = handler.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return handler.headers.get("x-real-ip", "") or "unknown"


def _kv_rate_limited(cfg, key, limit, window):
    """Fixed-window per-key limiter (INCR + EXPIRE on first hit). Returns True to
    block. Fail-open: any KV error -> not limited (never break a request because the
    limiter is unreachable)."""
    try:
        count = _kv_command(cfg, "INCR", key)
        if count == 1:
            _kv_command(cfg, "EXPIRE", key, window)
        return count > limit
    except Exception as exc:
        print(f"Rate-limit check skipped (KV error): {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def _kv_upsert(cfg, entry):
    """Atomic insert-or-update of one entry in the submissions hash. Returns True if
    an existing entry was updated, False if newly inserted. One HSET = no
    read-modify-write race, durable across cold starts (issue #51)."""
    field = _dedup_field(entry["repo_url"], entry["skill_name"])
    # Bound growth: once the store is full, refuse brand-new identities but keep
    # accepting updates to existing rows. (HEXISTS->HLEN->HSET; the tiny TOCTOU
    # window is acceptable for a DoS bound, not a precise invariant.)
    if _kv_command(cfg, "HEXISTS", SUBMISSIONS_KEY, field) == 0:
        if (_kv_command(cfg, "HLEN", SUBMISSIONS_KEY) or 0) >= MAX_SUBMISSIONS:
            raise LeaderboardFullError
    result = _kv_command(cfg, "HSET", SUBMISSIONS_KEY, field,
                         json.dumps(entry, ensure_ascii=False))
    # HSET returns the count of NEW fields: 1 = inserted, 0 = updated existing.
    return result == 0


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        # CORS handled by vercel.json — no duplicate headers
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        # CORS handled by vercel.json
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length < 0 or content_length > MAX_BODY_BYTES:
                self._send_json(413, {"error": "request body too large"})
                return
            # Never read more than the cap even if Content-Length lies.
            raw = self.rfile.read(min(content_length, MAX_BODY_BYTES))
            body = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, {"error": "invalid JSON body"})
            return

        if not isinstance(body, dict):
            self._send_json(400, {"error": "request body must be a JSON object"})
            return

        # Canonicalize text fields (NFKC) so compatibility homographs collapse to
        # one form before validation, dedup, and storage. Combined with the
        # invisible-char rejection in _validate, this keeps the dedup key stable.
        for _field in ("skill_name", "repo_url"):
            if isinstance(body.get(_field), str):
                body[_field] = unicodedata.normalize("NFKC", body[_field])

        error = _validate(body)
        if error:
            self._send_json(400, {"error": error})
            return

        entry = {
            "skill_name": body["skill_name"],
            "repo_url": body["repo_url"],
            "format": body["format"],
            "composite": float(body["composite"]),
            "grade": body["grade"],
            "dimensions": {k: float(v) for k, v in body["dimensions"].items()},
            "version": body["version"],
            # Scoring-model epoch derived from the submitted version, so this
            # entry only ever ranks against same-scale composites.
            "score_model": _score_model_for(body["version"]),
            "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            # Client-supplied, not re-scored by the server. Always false for
            # POSTed entries so consumers can distinguish self-reported scores
            # from any future server-verified ones.
            "verified": False,
        }

        cfg = _kv_config()
        if cfg:
            ip = _client_ip(self)
            # Per-IP cap (defense in depth behind the firewall's 10/60s) AND a
            # global cap that an IP-rotating attacker cannot bypass (dos-02).
            if (_kv_rate_limited(cfg, f"rl:submit:{ip}", 20, 60)
                    or _kv_rate_limited(cfg, "rl:submit:global",
                                        GLOBAL_SUBMIT_LIMIT, GLOBAL_SUBMIT_WINDOW)):
                self._send_json(429, {"error": "rate limit exceeded"})
                return

        try:
            if cfg:
                # Durable, atomic upsert — no read-modify-write, no cold-start loss.
                updated = _kv_upsert(cfg, entry)
            else:
                # /tmp fallback (demo-grade). Hold the lock across load->dedup->save
                # so two concurrent POSTs cannot last-write-wins clobber each other.
                with _exclusive_lock():
                    entries = _load_submissions()

                    # Dedup: update existing entry if repo_url + skill_name match.
                    key_repo = entry["repo_url"]
                    key_skill = entry["skill_name"]
                    updated = False
                    for i, existing in enumerate(entries):
                        if existing.get("repo_url") == key_repo and existing.get("skill_name") == key_skill:
                            entries[i] = entry
                            updated = True
                            break
                    if not updated:
                        entries.append(entry)

                    _save_submissions(entries)
        except LeaderboardFullError:
            self._send_json(429, {"error": "leaderboard is full"})
            return
        except Exception as exc:
            print(f"Storage error: {type(exc).__name__}: {exc}", file=sys.stderr)
            self._send_json(500, {"error": "internal storage error"})
            return

        self._send_json(200, {"ok": True, "updated": updated, "verified": False,
                              "score_model": entry["score_model"]})
