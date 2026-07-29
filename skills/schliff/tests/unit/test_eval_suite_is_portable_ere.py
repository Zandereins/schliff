"""The shipped suite's `pattern` assertions must be POSIX ERE, or CI silently loses them.

`run-eval.sh` evaluates every `test_cases[].assertions[]` of type `pattern` with
`grep -qiE`. That is POSIX ERE. It is not PCRE: `(?i)`, `\\d`, `\\w`, `\\b` and
lookarounds are not ERE constructs, and grep does not report them as errors to this
call site — the invocation is wrapped in `2>/dev/null`, so a rejected pattern is
indistinguishable from a pattern that simply did not match. The assertion just quietly
counts as failed.

This is not hypothetical. On `main`, CI reported 113 of 119 static assertions passing
while the same suite scored 119/119 on a developer machine. Six assertions had never
worked on the platform that gates the branch. Nobody saw it because 6 failures out of
119 is 94%, comfortably above the suite's 80% floor — the threshold was large enough
to hide a whole class of dead assertion. At 13 assertions the same four-per-suite
defect reads 69% and finally goes red.

The second consumer pulls the other way: `runtime-evaluator.py` matches the same values
with Python `re.search` and no `re.I`, so a `(?i)` there is load-bearing rather than
redundant. A pattern that works on both is one that needs no case flag at all —
`[Ff]irst`, not `(?i)first`.

Scope is deliberate. `edge_cases` are not read by the grep path at all, so PCRE syntax
there is not silently dropped and is left alone.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SUITE = Path(__file__).resolve().parents[2] / "eval-suite.json"

# Constructs that are PCRE/Python-only. grep -E does not implement them, and the call
# site swallows the resulting error, so each one is an assertion that can never pass.
_NOT_ERE = [
    (re.compile(r"\(\?"), "inline group flag or lookaround, e.g. (?i) — use [Ff]oo instead"),
    (re.compile(r"\\[dwsSWD]"), r"perl character class, e.g. \d — use [0-9] / [A-Za-z_] instead"),
    (re.compile(r"\\b"), r"\b word boundary — not ERE"),
]


def _patterns() -> list[tuple[str, str]]:
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    return [
        (tc["id"], a["value"])
        for tc in suite.get("test_cases", [])
        for a in tc.get("assertions", [])
        if a.get("type") == "pattern"
    ]


def test_suite_has_pattern_assertions_to_check():
    """Guard the guard: an empty list would make every test below vacuously pass."""
    assert _patterns(), "no `pattern` assertions found — this check would be inert"


@pytest.mark.parametrize("tc_id,value", _patterns(), ids=lambda v: str(v)[:32])
def test_pattern_is_posix_ere(tc_id: str, value: str):
    for rx, why in _NOT_ERE:
        assert not rx.search(value), (
            f"{tc_id} pattern {value!r} uses a {why}. grep -E cannot run it and the "
            f"error is discarded, so the assertion would count as failed on CI while "
            f"passing on a machine whose `grep` is more permissive."
        )


@pytest.mark.parametrize("tc_id,value", _patterns(), ids=lambda v: str(v)[:32])
def test_pattern_compiles(tc_id: str, value: str):
    """A pattern ERE accepts but Python rejects would break the runtime evaluator."""
    try:
        re.compile(value)
    except re.error as e:  # pragma: no cover - only reached on a malformed suite
        pytest.fail(f"{tc_id} pattern {value!r} does not compile: {e}")
