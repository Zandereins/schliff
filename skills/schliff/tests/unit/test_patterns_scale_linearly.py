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
import math
import re
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
#     defective, idle, 7 samples each via `_ratio` at n=2000 (2026-09-15):
#         [\w/]+:   2.05-2.28    [a-z]+@   2.15-2.25    a*b   2.12-2.16
#
# A first version of this threshold was 2.0, chosen against `a*a*b`. That pattern
# is CUBIC (raw ~7.6 against the real class's ~3.9), so it flattered the margin:
# review measured a real defective sample at 1.96, a false negative on an idle
# machine. 1.5 sits 43 % above the healthy median and 27 % under the defective
# minimum — nearer the defective side, so a loaded runner reaches it from that
# side first, and the defect-class test below reports exactly that when it
# happens. For a security gate, crying wolf once beats letting one defect
# through.
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
    ratio = _calibrator_ratio(make(_N), make(_N * 2))
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
# pattern under test. Measured at this revision, 47-49 calls per file run reach
# it for 11-12 distinct pairs at ~44 ms each, so the cache saves about 2 s on a
# 5 s file — and costs the session-wide blast radius #233 describes. Keyed on
# lengths and first bytes: the fillers are generated, so that identifies the
# pair without holding megabytes.
_CALIBRATOR_CACHE: dict = {}

# A linear scan on doubled input measures ~2.0 (idle 1.8-1.9; 1.3-3.0 under
# sixteen busy processes). Outside this band the divisor would distort every
# pattern; the plausibility test asserts it for the one pair it measures.
_CALIBRATOR_BAND = (0.5, 5.0)
# Scans per window past which a window is accepted whether or not it cleared the
# floor — the only exit on a clock that never advances. Used by the accept
# check and by the clamp on the next-round estimate; they must agree.
_CALIBRATOR_MAX_SCANS = 1_000_000


def _paired_scans(rx, small: str, large: str, target_seconds: float = _MIN_ABS_SECONDS,
                  windows: int = 3) -> tuple:
    """Seconds per scan for `small` and `large`, measured in interleaved windows.

    A single `re.search` of the calibrator costs ~0.8 microseconds — three orders
    of magnitude under `_MIN_ABS_SECONDS`, the floor this file applies to every
    other measurement because below it noise dominates. So each timing is a
    window of `n` scans, `n` grown until a window clears the floor.

    Two defences against the field record in the spec's 2026-09-05/07 amendment
    (docs/specs/2026-07-30-redos-audit-fixes.md). The first version took ONE
    window per size and returned as soon as it cleared the floor — which a
    scheduler stall does by itself, so a stall in the accepted window became the
    divisor for every pattern. Now each size is the FASTEST of `windows` windows,
    for the same reason `_best_of` takes a minimum: a stall only ever adds time;
    and `n` is accepted only once the fastest small window clears the floor, so
    a stall cannot make an undersized window look long enough either.

    Second, the small and large windows are INTERLEAVED (small, large, small,
    large, ...) rather than all-small then all-large. The minimum is still taken
    per side, so the windows are not paired: what interleaving buys is that a
    burst shorter than a round can leave each side a clean window, where the
    sequential order left one side none. Both sides run `n` scans, so a large
    window is about twice as long as a small one and a short burst is that much
    likelier to land in one — sizing the large side to the floor on its own is
    a companion of #233. Interleaving is not a defence against contention that
    covers most of a round: a burst that leaves a side no clean window moves
    the divisor in either order, and that residual is what the plausibility
    band is for.
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
        if best_small >= target_seconds or n >= _CALIBRATOR_MAX_SCANS:
            return best_small / n, best_large / n
        # Size the next round from this one instead of growing blindly: `n *= 8`
        # overshot the 4 ms floor about sixfold (24 ms windows), which is
        # wasted scanning, not a runtime win either way — the calibrator is
        # ~10 % of this file's wall time before and after. The 1.25 margin is
        # for the fastest window of the next round landing a little under the
        # estimate. A clock too coarse to time a 64-scan window returns 0 and
        # would divide by it; that case grows n the old way. A clock that
        # returns a near-zero reading instead would size the next round into
        # the billions before the cap above is consulted, so the estimate is
        # clamped to the cap here.
        if best_small > 0:
            estimate = math.ceil(n * target_seconds / best_small * 1.25)
        else:
            estimate = n * 8
        n = min(_CALIBRATOR_MAX_SCANS, max(n * 2, estimate))


def _calibrator_ratio(small: str, large: str):
    key = (len(small), len(large), small[:8], large[:8])
    if key not in _CALIBRATOR_CACHE:
        c_small, c_large = _paired_scans(_CALIBRATOR, small, large)
        # Cached as measured, plausible or not. The plausibility test reads
        # the `word` pair at (_N, 2*_N) — one of the fifty-two pairs this suite
        # keys — and only that one is asserted; an implausible divisor on any
        # other pair distorts the cases that hit it without a red of its own
        # (too high passes them silently, too low fails them with the divisor
        # printed). A version that failed the calling case instead was tried
        # in review and rejected: under sustained load it turned one bad
        # divisor into a red on every pattern of that pair. The measurement
        # design that would remove the gap — calibrate in the same loop as the
        # pattern, no cache — is #233.
        _CALIBRATOR_CACHE[key] = (
            c_large / c_small if c_small > 0 and c_large > 0 else None
        )
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
    number cannot be attributed to the pattern or to the divisor — eleven of the
    thirteen red CI attempts this gate produced in 08/09-2026 were of that kind.
    """
    small, large = make(n), make(n * 2)
    t_small = _best_of(rx, small, reps)
    t_large = _best_of(rx, large, reps)
    if t_large < _MIN_ABS_SECONDS or t_small <= 0:
        return None, t_small, t_large, None

    calibrator_ratio = _calibrator_ratio(small, large)
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

    ONE reading per pattern, on purpose. The gate flags a pattern only when
    three readings in a row clear the threshold (stage 1, then both stage-2
    doublings), so a single reading under it is a necessary condition for the
    gate to be blind — and this test was the red one in eleven of the thirteen
    attempts the spec amendment counts, at 1.11-1.47. A version that re-measured
    a miss and passed if ANY reading cleared was tried in review and reverted:
    it is green on exactly the runner profiles where the gate lets a defect
    through. Since every red prints the divisor, the CI record can now say
    whether such a reading came from the calibrator (this PR) or from the
    pattern side under load, which is a threshold-margin question — see the
    spec amendment.
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
        r2, s2, l2, c2 = _ratio(rx, make, _N * 2, reps=5)
        if r1 is None or r1 < _MAX_RATIO or r2 is None or r2 < _MAX_RATIO:
            continue
        # The second doubling's raw ratio is l2/s2 — its own fresh small timing,
        # not l1 — so that calibrated == raw / calibrator holds for what is printed.
        offenders.append(
            f"{filler_name}: {s1 * 1000:.1f}ms -> {l1 * 1000:.1f}ms, "
            f"{s2 * 1000:.1f}ms -> {l2 * 1000:.1f}ms "
            f"(calibrated {r1:.2f}x, {r2:.2f}x per doubling; raw {l1 / s1:.2f}x, {l2 / s2:.2f}x; "
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


@pytest.mark.parametrize(
    "target,second", [(100.0, 128), (400.0, 500)], ids=["doubling-floor", "estimate"]
)
def test_the_calibrator_survives_stalled_windows(monkeypatch, target, second):
    """One scheduler stall must not become the divisor for 224 patterns.

    The field record — 13 red attempts in 88, a divisor of 7.29 and one of 0.19
    on a scan that is linear by construction, cached for every pattern of the
    pair — is in the spec's 2026-09-05/07 amendment. This pins the mechanism
    that answers it, on a fully virtual clock so the verdict is exact and the
    same on every runner.

    A probe "pattern" advances the clock by 1.0 per scan of the small text and
    2.0 per scan of the large one — a linear scan, divisor exactly 2.0 — and
    adds a stall the size of the floor inside the first small window and inside
    the last large window of EVERY round of `windows` pairs. Every round,
    because the round the calibrator accepts is the one whose windows become
    the divisor. Two positions, because a stalled small window is what tempts
    "any window clears the floor", and a stalled last large window is what
    "take the last window" would read; a stall on both sides is what a mean or
    a maximum would average in, and only the fastest window per side ignores it.

    An unstalled 64-scan small window measures 64 and is rejected for either
    floor; the stalled one clears it and must not be accepted. The second
    round's size is the documented formula, stated here as its two outcomes:
    at floor 100 the doubling floor wins (128), at floor 400 the estimate does
    (500). The floors divide the work: only floor 100 catches "accept once the
    LARGE window clears the floor" (at 400 the large side rejects round one
    too), and only floor 400 catches a wrong estimate (at 100 the doubling
    floor hides it). The single assertion on `seen` pins the interleaving
    order, both round sizes and the exit; the pair assertion pins the divisor.
    """
    windows = 3
    period = 2 * windows  # windows per round: one small and one large per pair
    clock = {"now": 0.0, "stalls": 0, "window": 0, "last": None}
    monkeypatch.setattr(time, "perf_counter", lambda: clock["now"])
    small, large = "a" * 10, "a" * 20
    seen: list = []

    class Probe:
        def search(self, text):
            # A window boundary is a change of text; windows are counted from
            # that, not from clock readings, so the layout of readings is free.
            if len(text) != clock["last"]:
                if clock["last"] is not None:
                    clock["window"] += 1
                clock["last"] = len(text)
                if clock["window"] % period in (0, period - 1):
                    clock["now"] += target
                    clock["stalls"] += 1
            seen.append(len(text))
            clock["now"] += len(text) / 10

    per_small, per_large = _paired_scans(
        Probe(), small, large, target_seconds=target, windows=windows
    )
    first = 64
    expected = ([10] * first + [20] * first) * windows + ([10] * second + [20] * second) * windows
    assert seen == expected, (
        f"{len(seen)} scans in {clock['window'] + 1} windows, expected "
        f"{len(expected)} in {2 * period}: one round of {first} and one of {second}, "
        "small and large alternating, is what accepting on the FASTEST SMALL window "
        "and sizing the next round from the fastest small window produces"
    )
    assert (per_small, per_large) == (1.0, 2.0), (
        f"the stalled windows reached the divisor: {per_small} -> {per_large} "
        "per scan, where only the fastest window per side gives 1.0 -> 2.0"
    )
    # Two rounds, two stalls each: proves the stalls reached the code under
    # test, so a calibrator reading another clock cannot pass the above vacuously.
    assert clock["stalls"] == 4, f"{clock['stalls']} stalls were injected"
