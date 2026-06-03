"""Schliff scoring API endpoint for the web playground.

Accepts skill markdown content via POST, runs the schliff scoring engine,
and returns the full score result as JSON.

Rate limiting is NOT possible in this stateless serverless function (no shared
state survives between invocations / cold starts). Cross-request rate limiting
must be configured at the Vercel Firewall level (dashboard / `vercel firewall`
CLI / REST API) — see web/leaderboard/vercel.json comment and the deploy docs.
This handler only enforces a hard per-request input cap to bound the compute
cost of a single scoring run.
"""

import json
import os
import re
import sys
import tempfile
from http.server import BaseHTTPRequestHandler

# schliff's scoring submodules import each other via a sys.path-relative pattern
# (`from scoring.x import ...`) that requires the package's scripts/ directory to
# be ON sys.path. The schliff CLI sets this up at startup (see cli.py's sys.path
# hack); this serverless function bypasses the CLI, so without the same bootstrap
# every scoring call fails with `ModuleNotFoundError: No module named 'scoring'`
# once running against the pip-installed package (an editable install masks it
# locally). Replicate the bootstrap once, at cold start.
import skills.schliff.scripts as _schliff_scripts  # noqa: E402

_SCRIPTS_DIR = list(_schliff_scripts.__path__)[0]
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Hard cap on the raw request body (bounds bytes read off the socket).
MAX_CONTENT_SIZE = 500 * 1024  # 500 KB
# Hard cap on the actual skill text handed to the scoring engine. This is the
# real compute-cost bound: the engine's work scales with this string's length,
# so it must be enforced on the decoded value, not just the (spoofable)
# Content-Length header.
MAX_SKILL_CHARS = 256 * 1024  # 256 KB of text

# Only alphanumeric, hyphens, underscores, dots — no path separators
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+\.md$")

# CORS: `*` is intentional and acceptable here. This is a stateless, read-only
# scorer that uses no cookies, no Authorization header, and no credentials, so
# there is no cross-origin session to steal — the same-origin policy protects
# nothing that this endpoint exposes. `*` lets third-party tools call the public
# scorer directly. Abuse is bounded by the input caps above and by the Vercel
# Firewall rate limit (configured out-of-repo; see module docstring).
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def _run_scoring(content: str, filename: str) -> dict:
    """Write content to a temp file, run schliff scoring, return result dict."""
    from skills.schliff.scripts.scoring.composite import compute_composite
    from skills.schliff.scripts.shared import build_scores
    from skills.schliff.scripts.terminal_art import score_to_grade

    tmp_dir = tempfile.mkdtemp()
    # Use only the basename to prevent path traversal
    safe_name = os.path.basename(filename)
    skill_path = os.path.join(tmp_dir, safe_name)

    try:
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)

        scores = build_scores(skill_path, eval_suite=None, include_runtime=False)
        composite = compute_composite(scores)

        grade = score_to_grade(composite["score"])

        return {
            "composite_score": composite["score"],
            "grade": grade,
            "dimensions": {dim: scores[dim]["score"] for dim in scores},
            "warnings": composite.get("warnings", []),
            "measured_dimensions": composite.get("measured_dimensions", 0),
            "total_dimensions": composite.get("total_dimensions", 0),
        }
    finally:
        try:
            os.unlink(skill_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict):
        self.send_response(status)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self):
        """Return API info for browser visitors."""
        self._send_json(200, {
            "service": "schliff-playground",
            "usage": "POST /api/score with {\"content\": \"...\", \"filename\": \"SKILL.md\"}",
            "max_size_kb": MAX_CONTENT_SIZE // 1024,
        })

    def do_POST(self):
        """Score a skill file and return the result."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._send_json(400, {"error": "Invalid Content-Length header"})
            return

        if content_length > MAX_CONTENT_SIZE:
            self._send_json(413, {
                "error": "Content too large",
                "detail": f"Maximum size is {MAX_CONTENT_SIZE // 1024} KB",
            })
            return

        if content_length == 0:
            self._send_json(400, {"error": "Empty request body"})
            return

        # Read at most MAX_CONTENT_SIZE bytes regardless of the declared
        # Content-Length, so a lying header cannot make us buffer more.
        read_len = min(content_length, MAX_CONTENT_SIZE)
        try:
            raw_body = self.rfile.read(read_len)
            body = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json(400, {"error": "Invalid JSON", "detail": str(exc)})
            return

        if not isinstance(body, dict):
            self._send_json(400, {"error": "Request body must be a JSON object"})
            return

        content = body.get("content")
        filename = body.get("filename", "SKILL.md")

        if not content or not isinstance(content, str):
            self._send_json(400, {"error": "Missing or invalid 'content' field"})
            return

        # Hard cap the text actually scored. This is the compute-cost bound;
        # the byte-level Content-Length check above is not sufficient because a
        # JSON-escaped or multibyte payload can decode to far more characters.
        if len(content) > MAX_SKILL_CHARS:
            self._send_json(413, {
                "error": "Content too large",
                "detail": f"'content' must be at most {MAX_SKILL_CHARS // 1024} KB of text",
            })
            return

        if not isinstance(filename, str) or not _SAFE_FILENAME_RE.match(filename):
            self._send_json(400, {
                "error": "Invalid filename",
                "detail": "Must match [a-zA-Z0-9_-]+.md (no path separators)",
            })
            return

        try:
            result = _run_scoring(content, filename)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {
                "error": "Scoring failed",
                "detail": type(exc).__name__,
            })
