"""Efficiency must keep charging for length — it is the context-cost proxy.

`doctor` reports "Total context cost" and cites this dimension, so the score must not
be decouplable from word count. A denominator cap at 1500 words was tried and reverted:
it fixed a real defect (signal_count maxes at 95, so 182 of 349 real files could not
reach the top band at any quality) but removed the self-correction that bounds gaming.

Measured on a stuffed probe diluted with neutral prose — `_spread_stuffing_noise`
allows `0.12 * prose_tokens`, so dilution drives noise to zero:

    uncapped   43 -> 66 -> 44 -> 35     length takes the gain back
    capped     43 -> 66 -> 73 -> 68     the gain stays

The 43 -> 66 step is a pre-existing dilution defect that exists either way. What the
cap removed is the correction after it. These tests pin the correction, not the score.

Spec: docs/specs/2026-08-13-structural-signal-detection.md (section B)
"""
from shared import _file_cache
from scoring.efficiency import score_efficiency

HEAD = """---
name: probe
description: A probe skill used to verify that efficiency keeps charging for length.
---

# probe

Use when probing. Do not use for anything else.

## Commands

"""

# A term repeated far beyond natural prose — the stuffing signal.
STUFFED = "\n".join(
    f"- `deploy sub{i} <arg>` — deploy the deploy deploy target {i} for deploy"
    for i in range(14)
)

_WORDS = ["orchestration", "provisioning", "telemetry", "scheduling",
          "routing", "packaging", "validation", "archival"]


def _dilute(paragraphs: int) -> str:
    """Neutral prose that shares no term with the command table above it."""
    return "".join(
        f"\nParagraph {i}: the {_WORDS[i % 8]} layer explains how a reader interprets "
        f"stage {i} without repeating any term from the table above it here.\n"
        for i in range(paragraphs)
    )


def _score(tmp_path, paragraphs: int) -> int:
    path = tmp_path / f"probe_{paragraphs}.md"
    path.write_text(HEAD + STUFFED + _dilute(paragraphs), encoding="utf-8")
    _file_cache.clear()
    return score_efficiency(str(path))["score"]


def test_diluting_stuffing_does_not_pay_off_at_scale(tmp_path):
    """Padding away a stuffing penalty must not leave the file better than it started."""
    baseline = _score(tmp_path, 0)
    padded = _score(tmp_path, 400)
    assert padded <= baseline, (
        f"padding raised the score {baseline} -> {padded}: the stuffing penalty was "
        f"diluted away and the added words were never charged for"
    )


def test_growth_beyond_the_signal_ceiling_still_costs(tmp_path):
    """Two files, same signal, very different length must not score the same.

    A capped denominator made these identical, which is what let padding be free.
    """
    short = _score(tmp_path, 120)
    long = _score(tmp_path, 400)
    assert long < short, (
        f"a file three times longer with the same signal scored {long} vs {short} — "
        f"efficiency is no longer sensitive to length"
    )
