"""Regression guards for the playground/leaderboard JSON parse robustness (PG-1).

Deeply-nested JSON makes json.loads raise RecursionError, which is NOT a subclass
of ValueError/JSONDecodeError, so it escaped the parse `except` and surfaced as a
Vercel 500 instead of a clean 400. Both internet-facing parse sites must catch it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_SCORE_PY = _ROOT / "playground" / "api" / "score.py"
_SUBMIT_PY = _ROOT / "web" / "leaderboard" / "api" / "submit.py"


def test_json_loads_deep_nesting_raises_recursionerror_not_valueerror():
    # Root-cause pin: confirms the broadened except is actually needed.
    with pytest.raises(RecursionError):
        json.loads("[" * 50000)
    # And that it is NOT already caught by the narrow tuple.
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
