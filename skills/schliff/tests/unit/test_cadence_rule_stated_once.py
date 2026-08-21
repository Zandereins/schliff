"""The collector's cadence rule must be stated in exactly one place.

The number lived in eleven sites across three files. Every correction then had
to land in all eleven, and three review rounds in a row found a site that had
been missed — including one where the amendment prose claimed the sweep was
complete. The defect was not the number; it was that it had eleven homes.

This test fails when a second site restates it. Referring to it is fine and is
what every other site now does.
"""
import os
import re

import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Files that describe how often the collector must run. The Makefile belongs
# here: `make help` prints its target descriptions verbatim, so it is the most
# operator-facing statement of the rule — and it was the one site the first
# version of this guard could not see.
_SITES = [
    "docs/specs/2026-08-11-plugin-channel-experiment.md",
    ".github/workflows/collect-traffic.yml",
    "scripts/collect-traffic.sh",
    "Makefile",
]

# Any stated duration: "14 days", "14d", "14-day".
#
# The first version of this guard listed five near-verbatim phrasings and could
# be defeated by rewording. Proven: appending "the floor is 14 days between
# runs." to a guarded file left all its assertions green, so it certified
# "stated exactly once" while a contradicting statement sat in the repo. A guard
# that gives false assurance is worse than none, because the spec now tells
# future editors it will catch them.
_A_DURATION = re.compile(r"\b\d+\s*(?:d\b|days?\b)|\b\d+-day\b", re.IGNORECASE)

# ...unless the surrounding text is talking about GitHub's rolling API window,
# which is a property of the API and the INPUT to the rule, not the rule.
# Collapsing those two is how the wrong number spread in the first place.
_API_WINDOW_CONTEXT = re.compile(
    r"(?:rolling\s+)?\d+[- ]days?\s+window"
    r"|window[^.]{0,40}\b\d+[- ]days?"
    r"|\b\d+\s+days?\s+(?:is|measure)",
    re.IGNORECASE,
)


# ...and only counts where the surrounding text is about how often the COLLECTOR
# RUNS. Without this the guard flagged Gate 1's "21 days", Gate 2's "30 days" and
# the distributor survey's "90 days" — every duration in the document.
_CADENCE_CONTEXT = re.compile(
    r"\brun\b|\bruns\b|\brunning\b|\bcadence\b|\bfloor\b|\bsnapshot\b|\bexpire",
    re.IGNORECASE,
)


def _cadence_statements(text: str):
    out = []
    for m in _A_DURATION.finditer(text):
        context = text[max(0, m.start() - 90):m.end() + 90]
        if _API_WINDOW_CONTEXT.search(context):
            continue
        if not _CADENCE_CONTEXT.search(context):
            continue
        out.append((m.start(), m.group(0)))
    return out


# The Amendments section is the change log: it MUST name the old figure, or it
# documents nothing. Everything before it is the live document, and that is where
# "stated once" has to hold.
_AMENDMENTS_HEADING = "## Amendments"


def _read(rel):
    with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _live_text(rel):
    """The part of a file that states current rules, excluding the change log."""
    text = _read(rel)
    cut = text.find(_AMENDMENTS_HEADING)
    return text if cut == -1 else text[:cut]


def test_the_cadence_rule_is_stated_exactly_once():
    hits = []
    for rel in _SITES:
        text = _live_text(rel)
        for pos, frag in _cadence_statements(text):
            line = text[:pos].count("\n") + 1
            hits.append(f"{rel}:{line}: {frag!r}")
    assert len(hits) == 1, (
        "the cadence rule must be stated once and referenced elsewhere; found "
        f"{len(hits)} statements:\n  " + "\n  ".join(hits)
    )


def test_the_one_statement_is_the_canonical_anchor():
    spec = _live_text(_SITES[0])
    assert '<a id="the-cadence-rule"></a>' in spec, "the anchor other sites link to is gone"
    statements = _cadence_statements(spec)
    assert statements, "the canonical statement itself disappeared"
    anchor_at = spec.index('<a id="the-cadence-rule"></a>')
    pos = statements[0][0]
    assert anchor_at < pos < anchor_at + 1200, (
        "the surviving statement is not the one under the anchor"
    )


@pytest.mark.parametrize("rel", _SITES[1:])
def test_other_sites_refer_rather_than_restate(rel):
    text = _read(rel)
    assert "CADENCE RULE" in text or "cadence rule" in text, (
        f"{rel} neither states nor references the rule — a reader there learns nothing"
    )


def test_the_api_window_keeps_its_own_number():
    """A rolling 14-day window is a fact about GitHub's API, not the cadence.
    Collapsing the two is how the wrong number spread in the first place."""
    spec = _read(_SITES[0])
    assert re.search(r"rolling 14-day window", spec), (
        "the API window fact was removed along with the duplicated cadence numbers"
    )
