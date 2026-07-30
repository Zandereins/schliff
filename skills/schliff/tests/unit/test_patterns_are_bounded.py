"""Deterministic guard: the patterns bounded by the 2026-07-30 audit stay bounded.

Companion to `test_patterns_scale_linearly.py`, which fuzzes every compiled pattern
empirically. This file is the zero-false-positive half: it pins the exact patterns a
"simplification" is most likely to un-bound, and it pins the BOUNDS themselves against
the corpus measurements they were calibrated from.

Scope note, recorded deliberately. A repo-wide static rule was prototyped and
rejected on measurement: flagging "any unbounded quantifier on a character class"
marked 45 of 102 patterns, and the refinement "…with no required literal prefix,
since a literal limits the number of start positions" still marked 11 — including
`_RE_BACKTICK_REF`, where a leading backtick does limit start positions. A gate whose
allowlist is longer than its findings is the thing it is supposed to prevent, so the
repo-wide sweep is left to the empirical test and this file stays exact.

Why the bounds are load-bearing and not cosmetic: they were calibrated from the
longest run each quantifier actually consumes across 380 real instruction files. Lower
them and real files start scoring differently; remove them and the O(n^2) returns.
See docs/specs/2026-07-30-redos-audit-fixes.md (D1, D6).
"""
import re

import pytest

from scoring.output_contract import _RE_LENGTH_EXTENDED
from scoring.patterns.base import (
    _RE_CONCRETE_CMD,
    _RE_SEC_DANGEROUS_CMD,
    _RE_SPECIFIC_REF,
)
from scoring.patterns.skill_md import _RE_SKILL_AS_OBJECT

# Assert the PRESENCE of each bounded spelling rather than the ABSENCE of any
# unbounded quantifier. The absence form was tried and rejected: it fails
# `_RE_SEC_DANGEROUS_CMD`, whose other alternatives keep `chmod\s+777` and `mkfs\.\w+`
# — literal-prefixed runs that the empirical gate measures as linear, because a
# required literal limits how many start positions the run is reachable from. Asserting
# presence targets the exact regression (someone "simplifying" a bound away) with no
# false positives and no allowlist.
#
# (regex object, name, [sub-expressions that must remain bounded])
BOUNDED_SPELLINGS = [
    (_RE_SPECIFIC_REF, "_RE_SPECIFIC_REF",
     [r"\[\^`\]\{1,\d+\}", r"\[\\w/\]\{1,\d+\}", r"\\w\{1,\d+\}"]),
    (_RE_CONCRETE_CMD, "_RE_CONCRETE_CMD",
     [r"\[\^`\]\{1,\d+\}", r"\[\\w/\.-\]\{1,\d+\}", r"\\w\{1,\d+\}"]),
    # Only the flag runs — the whitespace around them is deliberately unbounded, see
    # TestDangerousCmdWhitespaceIsNotBounded in test_security_field_false_positives.py.
    (_RE_SEC_DANGEROUS_CMD, "_RE_SEC_DANGEROUS_CMD",
     [r"rm\\s\+-\[a-z\]\{0,\d+\}r\[a-z\]\{0,\d+\}f\[a-z\]\{0,\d+\}"]),
    (_RE_LENGTH_EXTENDED, "_RE_LENGTH_EXTENDED",
     [r"\\d\{1,\d+\}"]),
    (_RE_SKILL_AS_OBJECT, "_RE_SKILL_AS_OBJECT",
     [r"\[\\w-\]\{1,\d+\}"]),
]


@pytest.mark.parametrize(
    "rx,name,required", BOUNDED_SPELLINGS, ids=[n for _, n, _ in BOUNDED_SPELLINGS]
)
def test_bounded_quantifiers_are_still_bounded(rx, name, required):
    for expected in required:
        assert re.search(expected, rx.pattern), (
            f"{name} lost its bounded spelling /{expected}/. This pattern runs on "
            f"untrusted content — from a public HTTP endpoint, from third-party CI, or "
            f"from a user-written eval suite — and an unbounded run before a required "
            f"literal is O(n^2). Current pattern:\n  {rx.pattern}\n"
            f"See docs/specs/2026-07-30-redos-audit-fixes.md"
        )


# Longest run measured across 380 real instruction files, per quantifier site. The
# bound must stay comfortably ABOVE these or real files change score.
CORPUS_MAXIMA = {
    "_RE_SPECIFIC_REF word/slash run": (_RE_SPECIFIC_REF, r"\[\\w/\]\{1,(\d+)\}", 58),
    "_RE_CONCRETE_CMD word/slash/dot run": (
        _RE_CONCRETE_CMD, r"\[\\w/\.-\]\{1,(\d+)\}", 118),
    # The suffix after the dot. Widened from 64 to 128 in self-review: 64 carried only
    # 1.28x headroom over the measured 50, which is too thin for a value that moves
    # scores when it is wrong. Verified linear at 128 and 0 corpus differences.
    "_RE_SPECIFIC_REF dot suffix": (_RE_SPECIFIC_REF, r"\\w\{1,(\d+)\}", 50),
    "_RE_CONCRETE_CMD dot suffix": (_RE_CONCRETE_CMD, r"\\w\{1,(\d+)\}", 50),
    "_RE_SKILL_AS_OBJECT word run": (_RE_SKILL_AS_OBJECT, r"\[\\w-\]\{1,(\d+)\}", 19),
}


@pytest.mark.parametrize("label", sorted(CORPUS_MAXIMA))
def test_bound_stays_above_the_measured_corpus_maximum(label):
    rx, extractor, corpus_max = CORPUS_MAXIMA[label]
    m = re.search(extractor, rx.pattern)
    assert m, f"{label}: bounded quantifier not found — was the pattern rewritten?"
    bound = int(m.group(1))
    assert bound > corpus_max, (
        f"{label}: bound {bound} is not above the measured corpus maximum "
        f"{corpus_max}. Tightening below it silently changes real scores — the "
        f"failure mode of a guessed bound. Re-measure before changing this."
    )


def test_backtick_span_bound_covers_the_longest_real_span():
    """The longest backtick span in the corpus is 1151 chars (a canvas-design skill).
    A tighter bound would stop crediting it as a specific reference."""
    for rx, name in ((_RE_SPECIFIC_REF, "_RE_SPECIFIC_REF"),
                     (_RE_CONCRETE_CMD, "_RE_CONCRETE_CMD")):
        m = re.search(r"\[\^`\]\{1,(\d+)\}", rx.pattern)
        assert m, f"{name}: backtick span bound not found"
        assert int(m.group(1)) > 1151, (
            f"{name}: backtick bound {m.group(1)} would truncate the longest real "
            f"span (1151 chars)"
        )
