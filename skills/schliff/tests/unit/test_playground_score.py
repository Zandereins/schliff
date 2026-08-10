"""Regression guards for the playground/leaderboard JSON parse robustness (PG-1).

Deeply-nested JSON makes json.loads raise RecursionError on CPython 3.10-3.13.
RecursionError is NOT a subclass of ValueError/JSONDecodeError, so it escaped the
parse `except` and surfaced as a Vercel 500 instead of a clean 400. Both
internet-facing parse sites must catch it.

CPython 3.14 changed the ground under this: its json parser no longer recurses,
so the same input raises JSONDecodeError and 20 000-deep *valid* nesting parses
successfully where it used to be rejected. The guard tuple stays as it is —
half the supported range still needs it — and the tests below assert
containment rather than which exception a given interpreter picks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_SCORE_PY = _ROOT / "playground" / "api" / "score.py"
_SUBMIT_PY = _ROOT / "web" / "leaderboard" / "api" / "submit.py"


# The tuple the production parse sites catch. Named once so the test below
# asserts against the same thing the code does.
_PARSE_GUARD = (json.JSONDecodeError, ValueError, RecursionError)


def test_deep_nesting_cannot_escape_the_parse_guard():
    """Nothing thrown by deeply-nested input may fall outside the guard.

    This used to pin `RecursionError` specifically, which made it a statement
    about CPython rather than about the code under test — and CPython changed:
    3.14's json parser no longer recurses, so the same 50 000-deep input raises
    JSONDecodeError there while 3.10-3.13 raise RecursionError. Both are inside
    the guard, which is the only property that ever mattered.
    """
    try:
        json.loads("[" * 50000)
    except _PARSE_GUARD:
        pass
    except BaseException as exc:  # noqa: BLE001 — the point is to name escapees
        pytest.fail(
            f"{type(exc).__name__} escapes the production except tuple on "
            f"this interpreter"
        )


def test_recursion_error_must_be_named_explicitly():
    """Why the tuple cannot shrink to (ValueError, JSONDecodeError).

    Still load-bearing on every supported interpreter: `requires-python` is
    >=3.10, and on 3.10-3.13 deeply-nested JSON does raise RecursionError.
    Dropping it because 3.14 no longer needs it would break the older half of
    the support range.
    """
    assert not issubclass(RecursionError, (ValueError, json.JSONDecodeError))


def _parse_except_lines(path: Path) -> list[str]:
    return [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if re.search(r"except\s*\(.*JSONDecodeError", ln)
    ]


@pytest.mark.parametrize("path", [_SCORE_PY, _SUBMIT_PY], ids=["playground", "leaderboard"])
def test_json_parse_except_catches_recursionerror(path):
    lines = _parse_except_lines(path)
    assert lines, f"no JSONDecodeError parse-except found in {path.name}"
    for ln in lines:
        assert "RecursionError" in ln, (
            f"{path.name} parse except must catch RecursionError (PG-1): {ln.strip()}"
        )


class TestContentLengthGuard:
    """A negative Content-Length must not turn the byte cap into an unbounded read.

    `read_len = min(content_length, MAX_CONTENT_SIZE)` is -1 when the header is -1, and
    `rfile.read(-1)` reads to EOF — so the declared cap is bypassed entirely. The
    leaderboard's `submit.py` has the `< 0` guard; the playground's `score.py` did not.

    Driven through `do_POST` with an instrumented `rfile`, not asserted against the source
    text: the guard is a behaviour, and this file's other tests read the source only because
    they pin an `except` clause, which has no observable behaviour to drive.
    """

    @staticmethod
    def _handler_class(monkeypatch):
        """Load playground/api/score.py by path.

        `monkeypatch.syspath_prepend`, not a bare `sys.path.insert`: the first version of
        this helper inserted the repo root on EVERY call and never removed it, so a suite
        run left five duplicate entries in a global. This file's sibling conftest isolates
        cwd per test with automatic restore for the same reason — a test that mutates
        process-wide state and does not undo it can change the behaviour of tests that run
        after it.
        """
        import importlib.util
        monkeypatch.syspath_prepend(str(_ROOT))
        spec = importlib.util.spec_from_file_location("_pg_score", _SCORE_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _drive(self, monkeypatch, content_length: str, body: bytes):
        import io
        mod = self._handler_class(monkeypatch)

        class RecordingBytesIO(io.BytesIO):
            def __init__(self, data):
                super().__init__(data)
                self.reads: list = []

            def read(self, n=-1):
                data = super().read(n)
                self.reads.append((n, len(data)))
                return data

        class H(mod.handler):
            def __init__(self):
                self.headers = {"Content-Length": content_length}
                self.rfile = RecordingBytesIO(body)
                self.wfile = io.BytesIO()
                self.status = None

            def send_response(self, status):
                self.status = status

            def send_header(self, *a):
                pass

            def end_headers(self):
                pass

        h = H()
        h.do_POST()
        h.body = json.loads(h.wfile.getvalue().decode("utf-8")) if h.wfile.getvalue() else {}
        return h, mod.MAX_CONTENT_SIZE

    # A body far past the cap, so an unbounded read is unmistakable.
    BODY = json.dumps({"content": "x" * 64, "filename": "SKILL.md"}).encode() + b"\n" + b"P" * (3 * 1024 * 1024)

    def test_negative_content_length_does_not_bypass_the_cap(self, monkeypatch):
        h, cap = self._drive(monkeypatch, "-1", self.BODY)
        requested, returned = h.rfile.reads[0] if h.rfile.reads else (None, 0)
        assert returned <= cap, (
            f"Content-Length: -1 read {returned:,} bytes past the {cap:,}-byte cap "
            f"(rfile.read({requested}) reads to EOF)"
        )

    def test_negative_content_length_is_reported_as_an_invalid_header(self, monkeypatch):
        """Discriminating on the REASON, not just the status.

        Before the guard this already returned 400 — from the truncated-JSON branch, not
        from any Content-Length check. Asserting the status alone would have passed on the
        unfixed code, so it asserts the error string that only the guard produces.
        """
        h, _ = self._drive(monkeypatch, "-1", self.BODY)
        assert h.status == 400, f"expected 400 for an invalid Content-Length, got {h.status}"
        assert h.body.get("error") == "Invalid Content-Length header", (
            f"400 came from the wrong branch: {h.body!r}. A negative Content-Length must be "
            f"rejected as an invalid header, not incidentally as unparseable JSON."
        )

    def test_honest_oversize_still_gets_413(self, monkeypatch):
        h, _ = self._drive(monkeypatch, str(3 * 1024 * 1024), self.BODY)
        assert h.status == 413, f"expected 413 for an honest oversize, got {h.status}"

    def test_lying_small_content_length_still_reads_only_what_it_declared(self, monkeypatch):
        h, _ = self._drive(monkeypatch, "10", self.BODY)
        requested, returned = h.rfile.reads[0]
        assert returned == 10, f"read {returned} bytes for a declared 10"
        assert h.status == 400  # truncated JSON

    def test_zero_content_length_still_rejected_as_an_empty_body(self, monkeypatch):
        """Also discriminating on the reason, for the opposite direction.

        An over-broad guard (`<= 0` instead of `< 0`) keeps every status identical and only
        changes which message an empty body gets — invisible to a status-only assertion.
        Found by mutation, like every other instance of this on the branch.
        """
        h, _ = self._drive(monkeypatch, "0", b"")
        assert h.status == 400
        assert h.body.get("error") == "Empty request body", (
            f"an empty body must keep its own reason, not be absorbed by the "
            f"Content-Length guard: {h.body!r}"
        )
