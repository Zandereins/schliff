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

# Files that describe how often the collector must run.
_SITES = [
    "docs/specs/2026-08-11-plugin-channel-experiment.md",
    ".github/workflows/collect-traffic.yml",
    "scripts/collect-traffic.sh",
]

# Phrasings that STATE a required spacing. Deliberately narrow: "a rolling
# 14-day window" is a property of GitHub's API and an input to the rule, not the
# rule, and must keep its number.
_STATES_A_CADENCE = re.compile(
    r"(?:at least\s+)?once every\s+\w+\s+days"
    r"|run(?:s|ning)?\s+(?:it\s+)?(?:at least\s+)?every\s+\w+\s+days"
    r"|\bgo\s+\w+\s+days\s+without\s+a\s+run"
    r"|\b\w+-day rule\b"
    r"|floor is one run every\s+\w+\s+days",
    re.IGNORECASE,
)


def _read(rel):
    with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def test_the_cadence_rule_is_stated_exactly_once():
    hits = []
    for rel in _SITES:
        for m in _STATES_A_CADENCE.finditer(_read(rel)):
            line = _read(rel)[: m.start()].count("\n") + 1
            hits.append(f"{rel}:{line}: {m.group(0)!r}")
    assert len(hits) == 1, (
        "the cadence rule must be stated once and referenced elsewhere; found "
        f"{len(hits)} statements:\n  " + "\n  ".join(hits)
    )


def test_the_one_statement_is_the_canonical_anchor():
    spec = _read(_SITES[0])
    assert '<a id="the-cadence-rule"></a>' in spec, "the anchor other sites link to is gone"
    m = _STATES_A_CADENCE.search(spec)
    assert m, "the canonical statement itself disappeared"
    anchor_at = spec.index('<a id="the-cadence-rule"></a>')
    assert anchor_at < m.start() < anchor_at + 1200, (
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
