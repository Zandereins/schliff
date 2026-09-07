"""Empirical ReDoS gate: no compiled scoring pattern may scale super-linearly.

This is the test that would have found the 2026-07-30 audit's findings on its own.
Static shape-triage did not: "any unbounded quantifier on a character class" flagged 47
of the 102 patterns in `scoring/patterns/*` and isolated neither of the two that mattered,
because the shape that actually blew up has no nesting and no overlapping alternation —
just an unbounded run before a required literal.

Method: warm each pattern, then time `.search()` against a family of pathological
filler alphabets at two sizes one doubling apart. On the RAW scale linear patterns
come in near 2.0x and the measured defects at 3.9x-4.1x — margins too close to
separate reliably on a loaded runner.

The ratio is therefore CALIBRATED: divided by the ratio of a known-linear scan of
the same input, measured in the same process, so runner speed divides out. On that
scale healthy patterns measure ~1.05 (max 1.08) and the defect class 2.4-2.8, and
the threshold is 1.5x — see `_MAX_RATIO`. An absolute floor still applies, so a
loaded CI runner cannot flake it while the 4.0x class is still caught with margin.

Known limit, stated rather than glossed: this gate reaches exactly as far as its filler
alphabet. That is not hypothetical — `manifest._FM` was quadratic on a frontmatter-shaped
input at 3.95x per doubling while every generic filler came in at 1.85x, below the
absolute floor, so the gate shipped blind to a live defect for one commit. The two
`frontmatter_*` fillers close that specific shape; a shape nobody has thought of yet
still stays invisible. The `_MIN_ABS_SECONDS` floor has the same character: it suppresses
noise, and it would also suppress a quadratic with a very small constant at this size.

The lesson generalises: when a defect is found by hand, add the filler that would have
found it. The alphabet is the gate.

Cost: ~10-25s. That is the price of the only gate here that does not depend on a
heuristic being right. Its deterministic companion is `test_patterns_are_bounded.py`.
See docs/specs/2026-07-30-redos-audit-fixes.md (D6).
"""
import importlib
import re
import sys
import time

import pytest

# Every module that compiles a regex applied to untrusted content — instruction files,
# eval suites, or foreign directory trees. The list is deliberately WIDER than "the
# scoring dimensions": the first draft of this gate covered 11 modules and 138 patterns
# while the audit harness that actually found the defects covered 25 and 224, and a gate
# narrower than the harness it replaces is not a regression guard. Expanding it to the
# list below found 0 additional super-linear patterns, so the coverage is free.
_PATTERN_MODULES = [
    # pattern data
    "scoring.patterns.base",
    "scoring.patterns.skill_md",
    "scoring.patterns.system_prompt",
    # skill.md-family dimensions
    "scoring.structure",
    "scoring.triggers",
    "scoring.quality",
    "scoring.edges",
    "scoring.efficiency",
    "scoring.composability",
    "scoring.clarity",
    "scoring.security",
    "scoring.operational_coverage",
    "scoring.runtime",
    # system_prompt dimensions
    "scoring.structure_prompt",
    "scoring.output_contract",
    "scoring.completeness",
    "scoring.coherence",
    # engine plumbing that also compiles content-facing patterns
    "scoring.formats",
    "scoring.composite",
    "scoring.diff",
    "scoring.guards",
    "scoring.registry",
    "shared",
    "nlp",
    # consumers that read foreign trees / foreign files
    "manifest",
    "doctor",
    "verify",
    "drift",
    "sync",
    "text_gradient",
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
    # Frontmatter-shaped. Added when the blind spot documented below turned out to hide a
    # live quadratic: `manifest._FM` opens with `^---\s*\n`, so only an input that STARTS
    # with the delimiter reaches its lazy body scan. None of the fillers above do.
    "frontmatter_unterminated": lambda n: "---" + "\n" * (n - 3),
    "frontmatter_open": lambda n: "---\n" + "\n" * (n - 4),
}

_N = 2000                 # base size; the comparison runs at 2*_N
# Calibrated scale, not raw. Measured, with the DEFECT CLASS this gate exists for
# — `[\w/]+:`, `[a-z]+@`, `a*b` on an all-`a` input, the module docstring's
# 3.9x-4.1x shapes — not with a strawman:
#
#     healthy (rm -r+)        calibrated  1.05 median, 1.08 max
#     defective ([\w/]+:)     calibrated  2.82 median, 2.40 MIN
#
# A first version of this threshold was 2.0, chosen against `a*a*b`. That pattern
# is CUBIC (raw ~7.6 against the real class's ~3.9), so it flattered the margin:
# review measured a real defective sample at 1.96, a false negative on an idle
# machine. 1.5 sits between the classes with 39% headroom below and 60% above,
# and leans toward the healthy side on purpose — for a security gate, crying wolf
# once beats letting one defect through.
#
# Raising this is NOT how to fix a flake: past ~2.4 it stops separating the
# classes at all.
_MAX_RATIO = 1.5
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
        # No try/except: a module that stops importing must fail this gate loudly, not
        # silently shrink its coverage.
        mod = importlib.import_module(mod_name)
        short = mod_name.rsplit(".", 1)[-1]
        for attr in dir(mod):
            if attr.startswith("__"):
                continue
            walk(getattr(mod, attr), f"{short}.{attr}")
    return found


_PATTERNS = _collect_patterns()


def test_the_calibrator_does_not_blind_the_whole_gate():
    """A None calibrator ratio makes every parametrized case pass vacuously.

    `_ratio` returns None when the calibrator cannot be timed, and that verdict
    is cached per input pair — so one bad measurement blinds all 224 cases for
    the rest of the session, with nothing red to show for it. On a runner with a
    coarse perf_counter this is not hypothetical.
    """
    make = _FILLERS["word"]
    ratio = _calibrator_ratio(make(_N), make(_N * 2), reps=2)
    assert ratio is not None, "the calibrator could not be timed; every case would pass vacuously"
    lo, hi = _CALIBRATOR_BAND
    assert lo < ratio < hi, (
        f"calibrator ratio {ratio:.2f} is implausible for a linear scan — "
        "the division would distort every pattern's result"
    )


def test_the_gate_actually_sees_the_patterns():
    """A gate that collects nothing passes vacuously — and one that collects less than it
    used to has quietly stopped guarding part of the engine. 224 unique compiled patterns
    were reachable across `_PATTERN_MODULES` when this was written."""
    assert len(_PATTERNS) > 200, (
        f"only collected {len(_PATTERNS)} patterns; the audit harness saw 224 across "
        f"these modules. A shrinking count means the walker or an import broke."
    )


def _best_of(rx, text, reps=2):
    """Minimum of `reps` timings. Min, not mean: scheduler noise only ever ADDS time,
    so the minimum is the estimate closest to the true cost."""
    best = float("inf")
    for _ in range(reps):
        start = time.perf_counter()
        rx.search(text)
        best = min(best, time.perf_counter() - start)
    return best


# Calibrator: linear by construction — a literal that never matches, so it scans
# the whole input once and nothing else. Measured in the SAME process on the SAME
# text, so runner speed divides out of the comparison.
_CALIBRATOR = re.compile(r"zzz-this-literal-is-not-present")

# The calibrator's own ratio depends only on the two input strings, not on the
# pattern under test, so measuring it per pattern multiplied the suite's runtime
# by ~4 for no extra information. Keyed on lengths and first bytes: the fillers
# are generated, so that identifies the pair without holding megabytes.
_CALIBRATOR_CACHE: dict = {}

# A linear scan on doubled input measures ~2.0 (idle 1.8-1.9). Outside this band
# the divisor would distort every pattern, so a measurement outside it is taken
# again (bounded, see `_calibrator_ratio`) and the plausibility test asserts it.
_CALIBRATOR_BAND = (0.5, 5.0)
_CALIBRATOR_RETRIES = 3


def _paired_scans(rx, small: str, large: str, target_seconds: float = _MIN_ABS_SECONDS,
                  windows: int = 3) -> tuple:
    """Seconds per scan for `small` and `large`, measured in interleaved windows.

    A single `re.search` of the calibrator costs ~0.8 microseconds — three orders
    of magnitude under `_MIN_ABS_SECONDS`, the floor this file applies to every
    other measurement because below it noise dominates. So each timing is a
    window of `n` scans, `n` grown until a window clears the floor.

    Two defences, both measured on CI before they existed. The first version
    took ONE window per size and returned as soon as it cleared the floor — which
    a scheduler stall does by itself, so a stall in the accepted window became
    the divisor for every pattern (calibrator read 7.29 once and, back-computed,
    0.19 once, on a linear scan). Now each size is the FASTEST of `windows`
    windows, for the same reason `_best_of` takes a minimum: a stall only ever
    adds time; and `n` is accepted only once the fastest small window clears the
    floor, so a stall cannot make an undersized window look long enough either.

    Second, the small and large windows are INTERLEAVED (small, large, small,
    large, ...) rather than all-small then all-large, so contention that lasts
    longer than one window — the kind a minimum cannot remove — weighs on both
    sides of the ratio alike instead of on one.
    """
    n = 64
    while True:
        best_small = best_large = float("inf")
        for _ in range(windows):
            for text, which in ((small, "small"), (large, "large")):
                start = time.perf_counter()
                for _ in range(n):
                    rx.search(text)
                elapsed = time.perf_counter() - start
                if which == "small":
                    best_small = min(best_small, elapsed)
                else:
                    best_large = min(best_large, elapsed)
        if best_small >= target_seconds or n >= 1_000_000:
            return best_small / n, best_large / n
        n *= 8


def _calibrator_ratio(small: str, large: str, reps: int):
    key = (len(small), len(large), small[:8], large[:8])
    if key not in _CALIBRATOR_CACHE:
        ratio = None
        for _ in range(_CALIBRATOR_RETRIES):
            c_small, c_large = _paired_scans(_CALIBRATOR, small, large)
            ratio = c_large / c_small if c_small > 0 and c_large > 0 else None
            if ratio is not None and _CALIBRATOR_BAND[0] < ratio < _CALIBRATOR_BAND[1]:
                break
        # Cached even when still implausible after the retries: a None here
        # would pass every case vacuously, and the plausibility test reads the
        # same value and fails loudly instead.
        _CALIBRATOR_CACHE[key] = ratio
    return _CALIBRATOR_CACHE[key]


def _ratio(rx, make, n, reps):
    """Growth of `rx` relative to a known-linear scan of the same input.

    The raw t_large/t_small ratio was the original gate, and it flaked: measured
    over 50 runs of one healthy pattern, 8% of stage-1 samples crossed 3.0, and a
    CI runner produced 3.09/3.03 on a pattern that is linear (idle median 2.07).
    A loaded runner does not just add time, it widens the spread, and taking the
    minimum of several timings does not help when every timing is affected.

    Dividing by the calibrator's own ratio removes the shared component. Measured
    over the same fillers: linear 2.07 raw -> 1.15 calibrated (max 1.21), while a
    genuinely quadratic `a*a*b` goes 7.45 raw -> 4.73 calibrated (min ~4.7). The
    margin widens from a factor of 1.25 against the old threshold to 3.9.

    Returns (calibrated, t_small, t_large, calibrator): every failure message
    prints the last three too, because a red that shows only the calibrated
    number cannot be attributed to the pattern or to the divisor — ten of the
    thirteen red CI attempts this gate produced in 08/09-2026 were of that kind.
    """
    small, large = make(n), make(n * 2)
    t_small = _best_of(rx, small, reps)
    t_large = _best_of(rx, large, reps)
    if t_large < _MIN_ABS_SECONDS or t_small <= 0:
        return None, t_small, t_large, None

    calibrator_ratio = _calibrator_ratio(small, large, reps)
    if calibrator_ratio is None:
        return None, t_small, t_large, None

    return (t_large / t_small) / calibrator_ratio, t_small, t_large, calibrator_ratio


def test_the_gate_still_fires_on_the_real_defect_class():
    """A calibrated threshold is only worth having if it still fires.

    Measured against the shapes this gate exists for — an unbounded run before a
    required literal, the module docstring's 3.9x-4.1x defects — not against a
    strawman. A first version of this test used `a*a*b`, which is CUBIC (raw ~7.6
    vs the real class's ~3.9); it "passed" with room to spare while the threshold
    it validated sat on top of the real class, where review measured a sample at
    1.96 against a 2.0 gate.

    There is no linear arm here on purpose. The first version had one, and it was
    dead code: `a*b` on 600 chars runs in 0.2ms, under _MIN_ABS_SECONDS, so
    `_ratio` returned None every time and the assertion never executed. `a*b` is
    also not linear against an all-`a` input — it is itself a member of the defect
    class. The healthy side is already covered by the 224 parametrized cases.
    """
    make = lambda n: "a" * n                       # noqa: E731
    defects = {
        "[\\w/]+:": re.compile(r"[\w/]+:"),
        "[a-z]+@": re.compile(r"[a-z]+@"),
        "a*b": re.compile(r"a*b"),
    }
    missed = []
    for label, rx in defects.items():
        # 2000, not 600: at 600 two of these three run in under _MIN_ABS_SECONDS
        # and _ratio returns None, so the test would report "unmeasured" for the
        # very patterns it exists to catch. Measured at 2000: 8.4ms, 33ms, 71ms.
        ratio, t_small, t_large, cal = _ratio(rx, make, 2000, reps=3)
        if ratio is None:
            missed.append(f"{label}: fell under the timing floor, unmeasured "
                          f"({t_small * 1000:.2f}ms -> {t_large * 1000:.2f}ms)")
        elif ratio < _MAX_RATIO:
            missed.append(f"{label}: {ratio:.2f}, under the {_MAX_RATIO} threshold "
                          f"(raw {t_large / t_small:.2f} = {t_small * 1000:.1f}ms -> "
                          f"{t_large * 1000:.1f}ms, calibrator {cal:.2f})")
    assert not missed, (
        "the gate would not catch a known-defective pattern:\n  " + "\n  ".join(missed)
    )


@pytest.mark.parametrize("path,rx", _PATTERNS, ids=[p for p, _ in _PATTERNS])
def test_pattern_scales_linearly(path, rx):
    """Two-stage so a loaded runner cannot flake it.

    Stage 1 is a cheap sweep over every filler. Anything it flags is re-measured in
    stage 2 with more repetitions AND at a second doubling, and only counts if BOTH
    doublings are super-linear. A quadratic pattern shows ~4.0x raw at every doubling;
    a scheduling hiccup shows once.

    On the raw scale the healthy margin was 1.3-2.4x against a 3.0x threshold, too
    thin to rest on a single sample — and a CI runner duly produced 3.09x on a
    pattern whose idle median is 2.07x. Calibration widens that: healthy ~1.05
    against a 1.5x threshold. A flaky gate gets disabled, and a disabled gate is
    worse than none.
    """
    offenders = []
    for filler_name, make in _FILLERS.items():
        rx.search(make(200))  # warm
        ratio, t_small, t_large, _ = _ratio(rx, make, _N, reps=2)
        if ratio is None or ratio < _MAX_RATIO:
            continue
        # Stage 2: confirm at two consecutive doublings before failing.
        r1, s1, l1, c1 = _ratio(rx, make, _N, reps=5)
        r2, _, l2, c2 = _ratio(rx, make, _N * 2, reps=5)
        if r1 is None or r1 < _MAX_RATIO or r2 is None or r2 < _MAX_RATIO:
            continue
        offenders.append(
            f"{filler_name}: {s1 * 1000:.1f}ms -> {l1 * 1000:.1f}ms -> {l2 * 1000:.1f}ms "
            f"(calibrated {r1:.2f}x, {r2:.2f}x per doubling; raw {l1 / s1:.2f}x, {l2 / l1:.2f}x; "
            f"calibrator {c1:.2f}, {c2:.2f})"
        )
    assert not offenders, (
        f"{path} scales super-linearly on untrusted input:\n  "
        + "\n  ".join(offenders)
        + "\n\nA ratio near 4.0x per doubling is quadratic. This pattern runs on "
          "content from a public HTTP endpoint and from third-party CI. Bound the "
          "quantifier, and calibrate the bound against the real corpus rather than "
          "guessing it — see docs/specs/2026-07-30-redos-audit-fixes.md"
    )


def test_the_calibrator_survives_one_stalled_window(monkeypatch):
    """One scheduler stall must not become the divisor for 224 patterns.

    Measured on CI between 2026-08-25 and 2026-09-05: 13 red attempts of this
    file in 88 (ten on macOS, three on ubuntu, one of those on `main`). Two of
    them printed the divisor — a calibrator of 7.29, and a second doubling
    reported as 4.96x calibrated on a 0.93x raw doubling, i.e. 0.19 — on a
    literal scan that is linear by construction; the other eleven printed one
    calibrated number and are consistent with a divisor of 2.7-3.5. The value is
    cached per input pair, so a single stalled timing window distorted every
    pattern measured against that pair.

    The stall is injected into the clock, not the runner: perf_counter jumps by
    30 ms exactly once, on the end reading of the first large window. Under the
    single-window code that window was accepted as the measurement.
    """
    real = time.perf_counter
    state = {"calls": 0, "stalled": False, "armed": False}
    make = _FILLERS["sudo"]
    small, large = make(_N), make(_N * 2)

    def stalled_clock():
        now = real()
        # Windows alternate small, large; each reads the clock twice. The 4th
        # reading is the end of the first large window. Every reading is
        # counted: the accept rule below is pinned by the count.
        if state["armed"]:
            state["calls"] += 1
            if state["calls"] == 4 and not state["stalled"]:
                state["stalled"] = True
                return now + 0.030
        return now

    monkeypatch.setattr(time, "perf_counter", stalled_clock)
    # A fresh cache, restored on teardown: the parametrized cases share the real
    # one, and a value measured under a patched clock must not leak into it.
    monkeypatch.setattr(sys.modules[__name__], "_CALIBRATOR_CACHE", {})
    state["armed"] = True
    ratio = _calibrator_ratio(small, large, reps=2)
    state["armed"] = False
    # The band below is met by an unstalled calibrator too, so first prove the
    # stall reached the code under test — a refactor that reads another clock
    # would otherwise pass this vacuously.
    assert state["stalled"], "the stall was never injected"
    # The stalled window cleared the floor on its own. Accepting it would have
    # ended the scan at n=64 after one round of three window pairs, i.e. twelve
    # clock readings; requiring the FASTEST small window to clear the floor
    # forces at least a second round at a larger n.
    assert state["calls"] >= 24, (
        f"the scan stopped after {state['calls']} clock readings: an undersized "
        "window was accepted because one stalled window cleared the floor"
    )
    lo, hi = _CALIBRATOR_BAND
    assert ratio is not None and lo < ratio < hi, (
        f"one 30 ms stall moved the calibrator to {ratio:.2f}; a linear scan on "
        "doubled input is ~2.0, and this value would be cached for every pattern"
    )


def test_the_calibrator_interleaves_small_and_large_windows():
    """Contention that outlasts one window cannot be removed by a minimum; it can
    only be made to weigh on both sides of the ratio. That needs the small and
    large windows to alternate, which this pins structurally: a probe pattern
    records which text each scan saw."""
    seen = []

    class Probe:
        def search(self, text):
            seen.append(len(text))

    small, large = "a" * 10, "a" * 20
    _paired_scans(Probe(), small, large, target_seconds=0.0, windows=3)
    # target 0 accepts n=64 at once: three pairs of 64-scan windows.
    assert len(seen) == 6 * 64, len(seen)
    windows = [seen[i * 64] for i in range(6)]
    assert windows == [10, 20, 10, 20, 10, 20], windows
    assert all(seen[i * 64:(i + 1) * 64] == [windows[i]] * 64 for i in range(6))

