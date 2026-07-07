"""Shields.io endpoint badge for any public GitHub repo's AGENTS.md.

GET /api/badge?repo=owner/name

Fetches the repo's AGENTS.md at HEAD from raw.githubusercontent.com, scores it
with the engine's agents.md profile, and returns shields endpoint-schema JSON:

    ![AGENTS.md quality](https://img.shields.io/endpoint?url=https://<host>/api/badge%3Frepo=owner/name)

Every response is HTTP 200 with a badge payload (shields renders errors as a
grey badge, not a broken image). Security posture:
- SSRF: the fetch target is a FIXED host (raw.githubusercontent.com) with a
  path built only from strictly-validated owner/name segments; redirects are
  not followed.
- Compute: same input cap as /api/score (MAX_SKILL_CHARS) before scoring.
- Amplification: aggressive CDN caching (s-maxage) so shields/camo traffic is
  absorbed by the edge, not by GitHub or this function.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Same sys.path bootstrap as score.py: the scoring submodules import each other
# via `from scoring.x import ...`, which requires scripts/ on sys.path.
import skills.schliff.scripts as _schliff_scripts  # noqa: E402

_SCRIPTS_DIR = list(_schliff_scripts.__path__)[0]
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# GitHub constraints: owner <= 39 chars, repo <= 100 chars; conservative charset.
# The negative lookahead rejects "." / ".." (path-segment tricks); the host is
# fixed either way, this just keeps the built URL canonical.
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"^(?!\.{1,2}$)[A-Za-z0-9._-]{1,100}$")

MAX_SKILL_CHARS = 32 * 1024  # keep in lockstep with score.py
FETCH_TIMEOUT = 10  # seconds
# Read cap for the upstream fetch (bounds memory before the char cap applies).
MAX_FETCH_BYTES = 512 * 1024

# Cache hard: badge scores only move when the target repo edits its AGENTS.md.
# s-maxage lets Vercel's edge absorb shields/camo refetches; SWR keeps badges
# instant while revalidating in the background.
CACHE_CONTROL = "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800"
# Fallback badges (fetch errors, no AGENTS.md yet, invalid input) must not be
# pinned in the edge cache for a day: a transient GitHub 5xx would freeze
# "unavailable", and a user who just added their AGENTS.md would stare at
# "no AGENTS.md" — the onboarding moment. Only real scores cache long.
CACHE_CONTROL_FALLBACK = "public, max-age=60, s-maxage=300"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _badge(message: str, color: str, label: str = "AGENTS.md") -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def _color(score: float) -> str:
    if score >= 75:
        return "brightgreen"
    if score >= 50:
        return "yellow"
    return "red"


def _fetch_agents_md(owner: str, repo: str):
    """Return (content, None) or (None, badge-dict) on any fetch problem.

    SSRF containment: the scheme+host are a fixed literal, and the two
    caller-validated path segments are additionally percent-encoded with
    safe='' so no character can act as a path separator, query, fragment,
    or authority delimiter — the request provably cannot leave
    raw.githubusercontent.com or escape the /{owner}/{repo}/HEAD/AGENTS.md
    shape.
    """
    owner_q = urllib.parse.quote(owner, safe="")
    repo_q = urllib.parse.quote(repo, safe="")
    url = f"https://raw.githubusercontent.com/{owner_q}/{repo_q}/HEAD/AGENTS.md"
    req = urllib.request.Request(url, headers={"User-Agent": "schliff-badge/1.0"})
    try:
        with _OPENER.open(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(MAX_FETCH_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, _badge("no AGENTS.md", "lightgrey")
        return None, _badge("unavailable", "lightgrey")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, _badge("unavailable", "lightgrey")
    if len(raw) > MAX_FETCH_BYTES:
        return None, _badge("file too large", "lightgrey")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, _badge("not utf-8", "lightgrey")
    if len(content) > MAX_SKILL_CHARS:
        return None, _badge("file too large", "lightgrey")
    if not content.strip():
        return None, _badge("empty", "lightgrey")
    return content, None


def _score(content: str) -> dict:
    from terminal_art import score_to_grade

    from scoring.composite import compute_composite
    from shared import build_scores

    tmp_dir = tempfile.mkdtemp()
    skill_path = os.path.join(tmp_dir, "skill.md")
    try:
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)
        scores = build_scores(skill_path, eval_suite=None, include_runtime=False, fmt="agents.md")
        composite = compute_composite(scores, fmt="agents.md")
        score = composite["score"]
        grade = score_to_grade(score)
        return _badge(f"{score:g} · {grade}", _color(score), label="AGENTS.md quality")
    finally:
        # rmtree, not unlink+rmdir: if the file write itself failed (e.g.
        # ENOSPC), unlink would raise and leak the mkdtemp dir on a warm
        # instance's persistent /tmp.
        shutil.rmtree(tmp_dir, ignore_errors=True)


class handler(BaseHTTPRequestHandler):
    def _send(self, body: dict, cache_control: str = CACHE_CONTROL_FALLBACK):
        # Always 200: shields renders the payload; non-200 shows a broken badge.
        payload = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", cache_control)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        qs = parse_qs(urlparse(self.path).query)
        repo_param = (qs.get("repo") or [""])[0]
        parts = repo_param.split("/")
        if len(parts) != 2 or not _OWNER_RE.match(parts[0]) or not _REPO_RE.match(parts[1]):
            self._send(_badge("invalid repo", "lightgrey"))
            return
        owner, repo = parts
        content, err = _fetch_agents_md(owner, repo)
        if err is not None:
            self._send(err)
            return
        try:
            self._send(_score(content), cache_control=CACHE_CONTROL)
        except Exception:
            self._send(_badge("scoring error", "lightgrey"))
