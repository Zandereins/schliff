"""Empirical ReDoS gate: no compiled scoring pattern may scale super-linearly.

This is the test that would have found the 2026-07-30 audit's findings on its own.
Static shape-triage did not: "any unbounded quantifier on a character class" flagged
45 of 102 patterns and isolated neither of the two that mattered, because the shape
that actually blew up has no nesting and no overlapping alternation — just an
unbounded run before a required literal.

Method: warm each pattern, then time `.search()` against a family of pathological
filler alphabets at two sizes one doubling apart. Linear patterns come in near 2.0x;
the measured defects were 3.9x-4.1x. The threshold is 3.0x with an absolute floor, so
a loaded CI runner cannot flake it while the 4.0x class is still caught with margin.

Cost: ~10-25s. That is the price of the only gate here that does not depend on a
heuristic being right. Its deterministic companion is `test_patterns_are_bounded.py`.
See docs/specs/2026-07-30-redos-audit-fixes.md (D6).
"""
import importlib
import re
import time

import pytest

# Every module that compiles patterns applied to untrusted instruction-file content.
_PATTERN_MODULES = [
    "scoring.patterns.base",
    "scoring.patterns.skill_md",
    "scoring.patterns.system_prompt",
    "scoring.output_contract",
    "scoring.structure_prompt",
    "scoring.completeness",
    "scoring.security",
    "scoring.clarity",
    "scoring.composability",
    "scoring.efficiency",
    "scoring.guards",
]

# Filler alphabets. Each one is the worst case for a different quantifier shape:
# a bare word run for `[\w/]+`, a flag run for `[a-z]*`, a digit run for `\d+`, a
# newline run for `\s*` spanning the record separator, and so on.
_FILLERS = {
    "word": lambda n: "a" * n,
    "word_space": lambda n: "a " * (n // 2),
    "word_underscore": lambda n: "a_" * (n // 2),
    "dots": lambda n: "." * n,
    "slashes": lambda n: "/" * n,
    "backticks": lambda n: "`" * n,
    "pipes": lambda n: "|" * n,
    "dashes": lambda n: "-" * n,
    "spaces": lambda n: " " * n,
    "tabs": lambda n: "\t" * n,
    "newlines": lambda n: "\n" * n,
    "digits": lambda n: "1" * n,
    "punct": lambda n: ".,;:" * (n // 4),
    "colon_space": lambda n: ": " * (n // 2),
    "equals": lambda n: "a=b " * (n // 4),
    "rm_flags": lambda n: "rm -" + "r" * (n - 4),
    "run_prefix": lambda n: "Run " + "a" * (n - 4),
    "always_run": lambda n: "always " + "a " * ((n - 7) // 2),
    "never_word": lambda n: "never " + "x" * (n - 6),
    "sudo": lambda n: "sudo " + "a" * (n - 5),
    "curl": lambda n: "curl " + "a" * (n - 5),
    "echo": lambda n: "echo " + "a" * (n - 5),
    "the_file": lambda n: "the file " * (n // 9),
    "urlish": lambda n: "http://a/" * (n // 9),
    "md_link": lambda n: "- [x](y.md) " * (n // 12),
}

_N = 2000                 # base size; the comparison runs at 2*_N
_MAX_RATIO = 3.0          # linear ~2.0, the measured defects were 3.9-4.1
_MIN_ABS_SECONDS = 0.004  # below this, timing noise dominates — ignore the ratio


def _collect_patterns():
    found, seen = [], set()

    def walk(obj, path, depth=0):
        if depth > 3:
            return
        if isinstance(obj, re.Pattern):
            key = (obj.pattern, obj.flags)
            if key not in seen:
                seen.add(key)
                found.append((path, obj))
            return
        if isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]", depth + 1)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}[{k!r}]", depth + 1)

    for mod_name in _PATTERN_MODULES:
        mod = importlib.import_module(mod_name)
        short = mod_name.rsplit(".", 1)[-1]
        for attr in dir(mod):
            if attr.startswith("__"):
                continue
            walk(getattr(mod, attr), f"{short}.{attr}")
    return found


_PATTERNS = _collect_patterns()


def test_the_gate_actually_sees_the_patterns():
    """A gate that collects nothing passes vacuously. The engine had 169 compiled
    patterns at the time of the audit; anything near zero means the walker broke."""
    assert len(_PATTERNS) > 80, f"only collected {len(_PATTERNS)} patterns"


def _best_of(rx, text, reps=2):
    """Minimum of `reps` timings. Min, not mean: scheduler noise only ever ADDS time,
    so the minimum is the estimate closest to the true cost."""
    best = float("inf")
    for _ in range(reps):
        start = time.perf_counter()
        rx.search(text)
        best = min(best, time.perf_counter() - start)
    return best


def _ratio(rx, make, n, reps):
    small, large = make(n), make(n * 2)
    t_small = _best_of(rx, small, reps)
    t_large = _best_of(rx, large, reps)
    if t_large < _MIN_ABS_SECONDS or t_small <= 0:
        return None, t_small, t_large
    return t_large / t_small, t_small, t_large


@pytest.mark.parametrize("path,rx", _PATTERNS, ids=[p for p, _ in _PATTERNS])
def test_pattern_scales_linearly(path, rx):
    """Two-stage so a loaded runner cannot flake it.

    Stage 1 is a cheap sweep over every filler. Anything it flags is re-measured in
    stage 2 with more repetitions AND at a second doubling, and only counts if BOTH
    doublings are super-linear. A quadratic pattern shows ~4.0x at every doubling; a
    scheduling hiccup shows once. Measured margin for the healthy patterns is 1.3-2.4x
    against a 3.0x threshold, which is too thin to rest on a single sample — a flaky
    gate gets disabled, and a disabled gate is worse than none.
    """
    offenders = []
    for filler_name, make in _FILLERS.items():
        rx.search(make(200))  # warm
        ratio, t_small, t_large = _ratio(rx, make, _N, reps=2)
        if ratio is None or ratio < _MAX_RATIO:
            continue
        # Stage 2: confirm at two consecutive doublings before failing.
        r1, s1, l1 = _ratio(rx, make, _N, reps=5)
        r2, _, l2 = _ratio(rx, make, _N * 2, reps=5)
        if r1 is None or r1 < _MAX_RATIO or r2 is None or r2 < _MAX_RATIO:
            continue
        offenders.append(
            f"{filler_name}: {s1 * 1000:.1f}ms -> {l1 * 1000:.1f}ms -> {l2 * 1000:.1f}ms "
            f"(ratios {r1:.2f}x, {r2:.2f}x per doubling)"
        )
    assert not offenders, (
        f"{path} scales super-linearly on untrusted input:\n  "
        + "\n  ".join(offenders)
        + "\n\nA ratio near 4.0x per doubling is quadratic. This pattern runs on "
          "content from a public HTTP endpoint and from third-party CI. Bound the "
          "quantifier, and calibrate the bound against the real corpus rather than "
          "guessing it — see docs/specs/2026-07-30-redos-audit-fixes.md"
    )
