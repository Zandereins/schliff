from http.server import BaseHTTPRequestHandler
import json
import os
import fcntl
import traceback
from urllib.parse import urlparse, parse_qs

VALID_SORT_FIELDS = {
    "composite", "structure", "triggers", "quality", "edges",
    "efficiency", "composability", "clarity", "security", "sync", "date",
    "delta",
}
DIMENSION_KEYS = {
    "structure", "triggers", "quality", "edges", "efficiency",
    "composability", "clarity", "security", "sync",
}

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "submissions.json")


def _load_submissions():
    data_path = os.path.realpath(DATA_PATH)
    if not os.path.exists(data_path):
        return []
    with open(data_path, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            content = f.read().strip()
            return json.loads(content) if content else []
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _sort_key(entry, sort_field):
    if sort_field == "date":
        return entry.get("submitted_at", "")
    if sort_field == "composite":
        return entry.get("composite", 0)
    if sort_field == "delta":
        # Sort by improvement delta if present, otherwise by composite
        return entry.get("delta", entry.get("composite", 0))
    # dimension sort
    return entry.get("dimensions", {}).get(sort_field, 0)


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
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

        # --- grade filter ---
        grade_raw = first("grade")
        grade_filter = None
        if grade_raw:
            grade_filter = {g.strip() for g in grade_raw.split(",") if g.strip()}

        # --- format filter ---
        format_raw = first("format")
        format_filter = None
        if format_raw:
            format_filter = {f.strip() for f in format_raw.split(",") if f.strip()}

        try:
            entries = _load_submissions()
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "internal storage error"})
            return

        # --- filter ---
        if grade_filter:
            entries = [e for e in entries if e.get("grade") in grade_filter]
        if format_filter:
            entries = [e for e in entries if e.get("format") in format_filter]

        # --- sort (always descending) ---
        entries.sort(key=lambda e: _sort_key(e, sort), reverse=True)

        total = len(entries)
        page = entries[offset: offset + limit]

        self._send_json(200, {
            "entries": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        })
