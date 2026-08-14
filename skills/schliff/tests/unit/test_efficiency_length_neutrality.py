"""Efficiency must measure density, not length.

`signal_count` is capped on every term — its maximum is 95 — while the denominator
`total_words` is unbounded. Two files with the SAME signal therefore score differently
purely because one is longer, and 182 of 349 real files (52%) cannot reach 95 at any
quality.

Measured discriminator against the "long files are simply worse" hypothesis: across 349
files the median of structure/clarity/composability RISES with length (68 → 74) while
efficiency falls (70 → 42). Only this dimension punishes length.

Spec: docs/specs/2026-08-13-structural-signal-detection.md (section B)
"""
import pytest

from scoring.efficiency import score_efficiency

HEAD = """---
name: length-probe
description: A probe skill used to verify that efficiency measures density and not length.
---

# length-probe

Use when verifying scoring behaviour. Do not use for anything else.

## Commands

"""

# Distinct documented commands — the signal source. Capped at 20 by design.
COMMANDS = "\n".join(
    f"- `probe sub{i} <arg>` — subcommand {i} does one specific thing worth documenting"
    for i in range(24)
)

# Filler prose carrying no signal: pure denominator. Each paragraph must be DISTINCT —
# repeating one verbatim is padding, which the scorer correctly counts as noise, and
# would measure that behaviour instead of the length effect under test.
_NOUNS = ["pipeline", "registry", "manifest", "adapter", "boundary", "contract",
          "artifact", "revision", "namespace", "checkpoint", "threshold", "invariant"]
_VERBS = ["records", "resolves", "captures", "describes", "governs", "annotates"]


def _prose(index: int, sentences: int) -> str:
    """One paragraph on ONE line, so paragraph count fixes the line count.

    Word count must be the only variable: `total_lines <= 300` carries a separate,
    deliberate conciseness bonus that is not under test here. Growing the number of
    paragraphs would move both at once and measure that bonus instead.
    """
    noun, verb = _NOUNS[index % len(_NOUNS)], _VERBS[index % len(_VERBS)]
    body = " ".join(
        f"In stage {index}.{s} the {noun} {verb} how downstream consumers read "
        f"revision {s} of that chapter during review number {index}."
        for s in range(sentences)
    )
    return f"\nSection {index}: {body}\n"


def _probe(tmp_path, sentences: int, name: str, paragraphs: int = 40) -> str:
    path = tmp_path / name
    body = "".join(_prose(i, sentences) for i in range(paragraphs))
    path.write_text(HEAD + COMMANDS + body, encoding="utf-8")
    return str(path)


def test_same_signal_same_score_regardless_of_length(tmp_path):
    """Two files with identical signal must not diverge on word count alone."""
    short = _probe(tmp_path, 2, "short.md")     # ~1700 words, 40 paragraphs
    long = _probe(tmp_path, 6, "long.md")       # ~4000 words, 40 paragraphs

    s, l = score_efficiency(short), score_efficiency(long)
    assert s["details"]["signal_count"] == l["details"]["signal_count"], (
        "fixture broken: the two probes must carry identical signal"
    )
    assert l["details"]["total_words"] > 2 * s["details"]["total_words"], (
        "fixture broken: the long probe must be substantially longer"
    )
    assert s["score"] == l["score"], (
        f"same signal, different length: short={s['score']} long={l['score']} "
        f"({s['details']['total_words']} vs {l['details']['total_words']} words)"
    )


def test_a_dense_long_file_is_not_treated_as_bloat(tmp_path):
    """A file at the signal cap must not trip the bloat penalty on length alone.

    Asserts the structural property, not a score: 40 is the floor of the scoring curve,
    so anything below it means a penalty fired, and density >= 3 is the threshold the
    formula itself uses to call a file dense. A file emitting the most signal the
    formula can represent must clear both.
    """
    path = _probe(tmp_path, 4, "dense.md")      # ~2900 words, signal at the cap
    result = score_efficiency(path)
    details = result["details"]
    assert details["density"] >= 3, (
        f"density={details['density']} at signal_count={details['signal_count']} "
        f"over {details['total_words']} words — signal is capped, the denominator is not"
    )
    assert result["score"] > 40, (
        f"score={result['score']} is below the curve floor, so the bloat penalty fired "
        f"on a file that is at the signal cap"
    )


@pytest.mark.parametrize("sentences", [0, 1, 3, 6, 12])
def test_padding_never_raises_the_score(tmp_path, sentences):
    """Capping the denominator must not turn padding into a way to gain points."""
    baseline = score_efficiency(_probe(tmp_path, 0, "base.md"))["score"]
    padded = score_efficiency(_probe(tmp_path, sentences, f"pad{sentences}.md"))["score"]
    assert padded <= baseline, (
        f"{sentences} filler sentences per paragraph raised the score {baseline} → {padded}"
    )
