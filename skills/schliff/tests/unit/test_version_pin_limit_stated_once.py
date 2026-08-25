"""The SSH-address limit on `_RE_VERSION_COMPAT` must be argued in one place.

The reasoning had four homes — the pattern comment, the CHANGELOG, and two test
docstrings. Every correction then had to land in all four, and four review rounds
in a row found one out of step: `0x7f.1` was removed from four sites and left in
a fifth; "not the presence of a number" was fixed in a docstring and left in the
CHANGELOG; a stale pattern transcription was replaced in one class of four; a
clause order was corrected in the spec and re-scrambled in the CHANGELOG.

That is the failure #209 fixed for the collector's cadence rule, and this guard
is the same shape: the argument lives in the spec amendment, every other site
names the limit and links to it.

WHAT THIS GUARD CANNOT DO, stated because a guard giving false assurance is
worse than none (the lesson `test_cadence_rule_stated_once.py` records about its
own first version): it keys on the concrete EVIDENCE — an address form, a
command, a version literal — not on the shape of the argument. Someone who
restates the reasoning with fresh examples defeats it. It catches the copy-paste
case, which is the one that actually happened four times.
"""
import os

import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Prose sites that describe the limit. Test files are deliberately absent: an
# assertion naming `v8@10.2.154.26` is a check, not a restatement of the
# argument, and the positive set has to name it for the guard on the shape rule's
# error direction to exist at all.
_SITES = [
    "CHANGELOG.md",
    "README.md",
    "skills/schliff/scripts/scoring/patterns/skill_md.py",
    "skills/schliff/scripts/scoring/composability.py",
    "docs/specs/2026-08-13-structural-signal-detection.md",
    "docs/SCORING.md",
]

# The evidence the argument is built from. Each is a literal a copy-paste would
# carry along; none is a phrasing that can be reworded while keeping the point.
_EVIDENCE = [
    "inet_aton",            # the shape rule cannot be completed
    "0000100.1.2.3",        # ...demonstrated by this address
    "git clone git@",       # the wordlist misses this
    "admin@192.168.1.1",    # ...and this
    "v8@10.2.154.26",       # the shape rule drops this honest pin
    "ruff@0.4.2",           # the wordlist drops this honest pin
]

_HOME = "docs/specs/2026-08-13-structural-signal-detection.md"


def _sites_containing(needle: str):
    found = []
    for rel in _SITES:
        path = os.path.join(_REPO, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            if needle in fh.read():
                found.append(rel)
    return found


@pytest.mark.parametrize("needle", _EVIDENCE)
def test_evidence_appears_in_exactly_one_prose_site(needle):
    sites = _sites_containing(needle)
    assert len(sites) <= 1, (
        f"{needle!r} is stated in {len(sites)} places: {sites}.\n"
        f"The argument has one home ({_HOME}); other sites name the limit and "
        f"link to it. Restating the evidence is how it drifted four times."
    )


def test_the_home_actually_carries_the_argument():
    """A pointer to a document without the finding is worse than no pointer.

    Round 10 found exactly that: the test docstring sent the reader to the spec
    for history the spec did not have.
    """
    with open(os.path.join(_REPO, _HOME), encoding="utf-8") as fh:
        home = fh.read()
    missing = [n for n in _EVIDENCE if n not in home]
    assert not missing, (
        f"the spec amendment is the stated home of this argument but does not "
        f"contain: {missing}"
    )


def test_every_pointer_names_a_section_that_exists():
    """The three linking sites name an anchor. It has to be there."""
    anchor = "Amendment 2026-08-25"
    with open(os.path.join(_REPO, _HOME), encoding="utf-8") as fh:
        assert f"## {anchor}" in fh.read(), f"{_HOME} has no '## {anchor}' heading"

    pointers = [
        "skills/schliff/scripts/scoring/patterns/skill_md.py",
        "CHANGELOG.md",
        "skills/schliff/tests/unit/test_composability_structural_signals.py",
    ]
    for rel in pointers:
        with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
            text = fh.read()
        assert anchor in text, f"{rel} no longer points at the argument's home"
