"""Community leaderboard query endpoint.

TRUST MODEL: entries are UNVERIFIED, community self-reported scores (the submit
endpoint stores client-supplied values without re-scoring). Responses carry a
top-level `"unverified": true` flag and each entry carries `"verified"` so
clients can render an appropriate "community-submitted, not verified" notice.
Read-only; CORS handled in vercel.json.
"""

import hashlib
import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

VALID_GRADES = {"S", "A", "B", "C", "D"}
VALID_FORMATS = {"SKILL.md", ".cursorrules", "CLAUDE.md", "AGENTS.md"}

VALID_SORT_FIELDS = {
    "composite", "structure", "triggers", "quality", "edges",
    "efficiency", "composability", "clarity", "security", "date",
    "delta",
}
# The 7 headline dimensions are the required core; `security` is an optional
# opt-in signal (kept in sync with submit.py's REQUIRED/OPTIONAL split).
REQUIRED_DIMENSIONS = {
    "structure", "triggers", "quality", "edges", "efficiency",
    "composability", "clarity",
}
OPTIONAL_DIMENSIONS = {"security"}
DIMENSION_KEYS = REQUIRED_DIMENSIONS | OPTIONAL_DIMENSIONS

# Match submit.py storage paths
DATA_DIR = "/tmp/schliff-leaderboard"
DATA_PATH = os.path.join(DATA_DIR, "submissions.json")
SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "submissions.json")


def _load_submissions():
    """Load submissions from /tmp, seeding from bundled data if needed."""
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    if os.path.exists(SEED_PATH):
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    return []


# --- scoring-model epoch (keep in sync with submit.py) -----------------------
# v8.0's full-denominator composite (PR #41/#42) is a breaking scale change, so
# v7-and-earlier composites must never co-rank with v8+ ones. Entries are stamped
# with an epoch at submit time; legacy/seed rows predate the field and are
# backfilled here from their version string.
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


def _resolve_score_model(entries, requested):
    """Backfill score_model on every entry, then select the active epoch and keep
    only its entries — so a single ranking never mixes incomparable scales.

    Active epoch = ``requested`` when given, else the latest epoch that has data
    (within-scale and never an empty default view). Returns
    ``(filtered_entries, active_model, models_available_desc)``."""
    for e in entries:
        e.setdefault("score_model", _score_model_for(e.get("version", "")))
    models_available = sorted({e["score_model"] for e in entries}, reverse=True)
    if requested is not None:
        active = requested
    else:
        active = models_available[0] if models_available else CURRENT_SCORE_MODEL
    return [e for e in entries if e.get("score_model") == active], active, models_available


def _sort_key(entry, sort_field):
    if sort_field == "date":
        return entry.get("submitted_at", "")
    if sort_field == "composite":
        return entry.get("composite", 0)
    if sort_field == "delta":
        return entry.get("delta", entry.get("composite", 0))
    return entry.get("dimensions", {}).get(sort_field, 0)


# --- durable storage + rate-limit via Upstash Redis REST (issues #51/#52) -------
# Active ONLY when the Upstash/Vercel-KV env vars are present. Absent -> every
# helper below is bypassed and the /tmp path above runs unchanged, so merging this
# is safe before the store is provisioned (`vercel install upstash`). stdlib-only.
# KEEP THIS BLOCK BYTE-IDENTICAL to the copy in submit.py — Vercel bundles each
# function independently, so the two files cannot share a module (test enforces it).
SUBMISSIONS_KEY = "schliff:submissions"


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


def _canonical_repo_url(repo_url):
    """Canonicalize a GitHub repo URL to its identity form
    ``https://github.com/owner/repo`` (owner+repo lowercased), or return None when it
    is not an https github.com URL with at least an owner and a repo path segment.

    Query string, fragment, and any path beyond owner/repo (a trailing slash,
    ``/tree/main``, ``.git``, ...) are dropped so every spelling of the same repo
    maps to one (repo_url, skill_name) dedup key — otherwise one repo could mint
    unlimited rows. Keep BYTE-IDENTICAL with the copy in query.py."""
    if not isinstance(repo_url, str):
        return None
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        return None
    segments = [s for s in parsed.path.split("/") if s]
    if len(segments) < 2:
        return None
    owner, repo = segments[0].lower(), segments[1].lower()
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None
    return f"https://github.com/{owner}/{repo}"


def _dedup_field(repo_url, skill_name):
    """Stable hash of the (repo_url, skill_name) identity — the submissions-hash
    field and the dedup key. Inputs are NFKC-normalized + invalid-char-rejected
    upstream, so this is a 1:1 identity."""
    return hashlib.sha256(f"{repo_url}\n{skill_name}".encode("utf-8")).hexdigest()


def _client_ip(handler):
    """Best-effort client IP for rate-limit keying. ``x-real-ip`` is set by Vercel's
    trusted proxy and is not client-spoofable, so prefer it. For ``x-forwarded-for``
    the RIGHTMOST hop is the one the trusted proxy appended; the leftmost is
    attacker-controlled — keying the limit on it lets a spoofer both bypass their own
    limit (rotate the left value) and target a victim (spoof the victim's IP to burn
    their bucket)."""
    real = handler.headers.get("x-real-ip", "").strip()
    if real:
        return real
    fwd = handler.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[-1].strip() or "unknown"
    return "unknown"


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


def _load_seed():
    """Bundled, read-only demo rows (data/submissions.json)."""
    if os.path.exists(SEED_PATH):
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    return []


def _kv_load_all(cfg):
    """All submissions from KV, unioned with bundled seed rows not yet resubmitted
    into KV (KV wins on identity conflict). HGETALL over REST returns a flat
    [field, value, field, value, ...] array."""
    raw = _kv_command(cfg, "HGETALL", SUBMISSIONS_KEY)
    if isinstance(raw, list):
        values = raw[1::2]
    elif isinstance(raw, dict):
        values = list(raw.values())
    else:
        values = []

    def _key(e):
        # Canonicalize the repo_url before keying so a legacy non-canonical KV/seed
        # row still dedups against the canonical form submit.py now stores (LB-1).
        # Fall back to the raw value if it is not a canonicalizable github URL, so a
        # malformed row keeps a stable, distinct key instead of collapsing.
        repo = _canonical_repo_url(e.get("repo_url", "")) or e.get("repo_url", "")
        return _dedup_field(repo, e.get("skill_name", ""))

    entries, seen = [], set()
    for v in values:
        try:
            e = json.loads(v)
        except (ValueError, TypeError):
            continue
        entries.append(e)
        seen.add(_key(e))

    for e in _load_seed():
        if _key(e) not in seen:
            entries.append(e)
    return entries


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

    def do_GET(self):
        # Per-IP read rate-limit when KV is configured (issue #52); the firewall's
        # single rule is spent on /api/submit, so this is the cap for /api/query.
        cfg = _kv_config()
        if cfg and _kv_rate_limited(cfg, f"rl:query:{_client_ip(self)}", 100, 60):
            self._send_json(429, {"error": "rate limit exceeded"})
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        def first(key, default=None):
            vals = params.get(key)
            return vals[0] if vals else default

        # --- sort ---
        sort = first("sort", "composite")
        if sort not in VALID_SORT_FIELDS:
            self._send_json(400, {"error": f"invalid sort field: {sort}"})
            return

        # --- limit ---
        try:
            limit = int(first("limit", 50))
            if limit < 1 or limit > 200:
                raise ValueError
        except ValueError:
            self._send_json(400, {"error": "limit must be an integer between 1 and 200"})
            return

        # --- offset ---
        try:
            offset = int(first("offset", 0))
            if offset < 0:
                raise ValueError
        except ValueError:
            self._send_json(400, {"error": "offset must be a non-negative integer"})
            return

        # --- grade filter (validated against allowed set) ---
        grade_raw = first("grade")
        grade_filter = None
        if grade_raw:
            grade_filter = {g.strip() for g in grade_raw.split(",") if g.strip()}
            invalid = grade_filter - VALID_GRADES
            if invalid:
                self._send_json(400, {"error": f"invalid grade(s): {', '.join(sorted(invalid))}"})
                return

        # --- format filter (validated against allowed set) ---
        format_raw = first("format")
        format_filter = None
        if format_raw:
            format_filter = {f.strip() for f in format_raw.split(",") if f.strip()}
            invalid = format_filter - VALID_FORMATS
            if invalid:
                self._send_json(400, {"error": f"invalid format(s): {', '.join(sorted(invalid))}"})
                return

        # --- score_model selection (optional; default = latest epoch present) ---
        sm_raw = first("score_model")
        requested_model = None
        if sm_raw is not None:
            try:
                requested_model = int(sm_raw)
            except ValueError:
                self._send_json(400, {"error": "score_model must be an integer"})
                return

        try:
            entries = _kv_load_all(cfg) if cfg else _load_submissions()
        except Exception as exc:
            print(f"Storage error: {type(exc).__name__}: {exc}", file=sys.stderr)
            self._send_json(500, {"error": "internal storage error"})
            return

        # --- keep a single, comparable scoring-model epoch (no mixed scales) ---
        entries, active_model, models_available = _resolve_score_model(entries, requested_model)

        # --- filter ---
        if grade_filter:
            entries = [e for e in entries if e.get("grade") in grade_filter]
        if format_filter:
            entries = [e for e in entries if e.get("format") in format_filter]

        # --- sort (always descending) ---
        entries.sort(key=lambda e: _sort_key(e, sort), reverse=True)

        total = len(entries)
        page = entries[offset: offset + limit]

        # Ensure every returned entry advertises its verification status, even
        # legacy/seed rows written before the field existed.
        for e in page:
            e.setdefault("verified", False)

        self._send_json(200, {
            "entries": page,
            "total": total,
            "limit": limit,
            "offset": offset,
            # Active scoring-model epoch for this ranking + the epochs that have
            # data, so the client can offer a scale switch. v7-and-earlier (1) and
            # v8+ full-denominator (2) composites are never mixed in one ranking.
            "score_model": active_model,
            "score_models_available": models_available,
            # Leaderboard data is community self-reported and not server-verified.
            "unverified": True,
        })
