"""ReDoS regression guard for content-facing scoring regexes.

The public playground scores untrusted input (<=256KB) with the real engine, so an
O(n^2) pattern is a remote CPU-DoS. `_RE_REAL_EXAMPLES` used `input.*output`
(greedy, unbounded) under findall(): a ~200KB single line of "input " pegged the
engine for ~35s. Bounded to `input.{0,200}?output` it is linear. (Audit 2026-06-11.)
"""
import os
import tempfile
import time

from scoring.patterns.skill_md import _RE_REAL_EXAMPLES

# ~200KB single line of "input " — no "output", no newline. Passes the playground's
# size + filename caps; worst case for the greedy form.
_MALICIOUS = "input " * (200 * 1024 // 6)


def test_real_examples_regex_is_linear_not_redos():
    start = time.perf_counter()
    _RE_REAL_EXAMPLES.findall(_MALICIOUS)
    elapsed = time.perf_counter() - start
    # pre-fix ~35s (O(n^2)); bounded fix ~0.05s. 3s is a ~600x guard, CI-slop-safe.
    assert elapsed < 3.0, f"possible ReDoS regression: {elapsed:.2f}s on 200KB single line"


def test_real_examples_regex_still_matches_intended():
    for s in ("see the input then the output", "Example 1:", "e.g. x",
              "for instance", "for example"):
        assert _RE_REAL_EXAMPLES.search(s), s


def test_build_scores_no_redos_end_to_end():
    """The exact playground call path stays fast on the malicious payload."""
    from shared import build_scores
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(_MALICIOUS)
        path = f.name
    try:
        start = time.perf_counter()
        build_scores(path, eval_suite=None, include_runtime=False)
        elapsed = time.perf_counter() - start
        assert elapsed < 8.0, f"possible ReDoS regression in build_scores: {elapsed:.2f}s"
    finally:
        os.unlink(path)
