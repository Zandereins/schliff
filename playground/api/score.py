"""Schliff scoring API endpoint for the web playground.

Accepts skill markdown content via POST, runs the schliff scoring engine,
and returns the full score result as JSON.

Rate limiting: handled by Vercel WAF in production — not implemented here.
"""

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler

MAX_CONTENT_SIZE = 500 * 1024  # 500 KB

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def _score_to_grade(score: float) -> str:
    if score >= 95:
        return "S"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 65:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _run_scoring(content: str, filename: str) -> dict:
    """Write content to a temp file, run schliff scoring, return result dict."""
    # Import at function level to optimize cold starts
    from skills.schliff.scripts.shared import build_scores
    from skills.schliff.scripts.scoring.composite import compute_composite

    tmp_dir = tempfile.mkdtemp()
    skill_path = os.path.join(tmp_dir, filename)

    try:
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)

        scores = build_scores(skill_path, eval_suite=None, include_runtime=False)
        composite = compute_composite(scores)

        grade = _score_to_grade(composite["score"])

        return {
            "composite_score": composite["score"],
            "grade": grade,
            "dimensions": {dim: scores[dim]["score"] for dim in scores},
            "warnings": composite.get("warnings", []),
            "measured_dimensions": composite.get("measured_dimensions", 0),
            "total_dimensions": composite.get("total_dimensions", 0),
        }
    finally:
        # Clean up temp file and directory
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

    def do_POST(self):
        """Score a skill file and return the result."""
        # Read and validate content length
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_CONTENT_SIZE:
            self._send_json(413, {
                "error": "Content too large",
                "detail": f"Maximum size is {MAX_CONTENT_SIZE // 1024} KB",
            })
            return

        if content_length == 0:
            self._send_json(400, {"error": "Empty request body"})
            return

        # Parse JSON body
        try:
            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json(400, {"error": "Invalid JSON", "detail": str(exc)})
            return

        content = body.get("content")
        filename = body.get("filename", "SKILL.md")

        if not content or not isinstance(content, str):
            self._send_json(400, {"error": "Missing or invalid 'content' field"})
            return

        if not filename.endswith(".md"):
            self._send_json(400, {"error": "Filename must end with .md"})
            return

        # Run scoring
        try:
            result = _run_scoring(content, filename)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {
                "error": "Scoring failed",
                "detail": str(exc),
            })
