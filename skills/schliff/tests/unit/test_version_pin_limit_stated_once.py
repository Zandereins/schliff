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

The FIRST version of this guard listed six file paths and skipped missing ones.
It was defeated three ways, each demonstrated: pasting the whole argument into a
file not on the list, renaming a listed file, and writing it into a test
docstring — the very place two of the four original homes sat. A guard that
gives false assurance is worse than none, because the spec then tells future
editors it will catch them. It now enumerates from `git ls-files`, so a new file
is covered the moment it is tracked, and it reads the test file's docstrings.

WHAT IT STILL CANNOT DO: it keys on the concrete EVIDENCE — an address form, a
function name, a version literal — not on the shape of the argument. Someone who
restates the reasoning with fresh examples defeats it. It catches copy-paste,
which is the case that actually happened four times.
"""
import ast
import os
import subprocess

import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

_HOME = "docs/specs/2026-08-13-structural-signal-detection.md"
_GUARD = "skills/schliff/tests/unit/test_version_pin_limit_stated_once.py"

# The file whose ASSERTIONS legitimately name two of these literals: they are
# test data for the honest-pin guards, one per error direction, not a
# restatement of the argument. Its docstrings are still checked — that is where
# two of the four original homes were.
_ASSERTS = "skills/schliff/tests/unit/test_composability_structural_signals.py"

# Evidence carried by copy-paste. Split by whether it may also appear as test
# data, so the first group can be required to sit in exactly one place.
_PROSE_ONLY = [
    "inet_aton",              # the shape rule cannot be completed
    "0000100.1.2.3",          # ...demonstrated by this address
    "git clone git@10.0.0.5",  # the wordlist misses this (the example, not a real clone line)
    "admin@192.168.1.1",      # ...and this
]
_ALSO_TEST_DATA = [
    "v8@10.2.154.26",  # the honest pin the shape rule drops
    "ruff@0.4.2",      # the honest pin the wordlist drops
]


def _tracked(*globs):
    out = subprocess.run(
        ["git", "ls-files", *globs],
        cwd=_REPO, capture_output=True, text=True, check=True,
    ).stdout.split()
    return [p for p in out if p not in (_GUARD,)]


def _read(rel):
    with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _sites_containing(needle, allow=()):
    hits = []
    for rel in _tracked("*.md", "*.py"):
        if rel in allow:
            continue
        if needle in _read(rel):
            hits.append(rel)
    return hits


@pytest.mark.parametrize("needle", _PROSE_ONLY)
def test_prose_evidence_appears_in_exactly_one_file(needle):
    sites = _sites_containing(needle)
    assert sites == [_HOME], (
        f"{needle!r} is in {sites}, expected only {_HOME!r}.\n"
        f"The argument has one home; other sites name the limit and link to it. "
        f"Restating the evidence is how it drifted four times."
    )


@pytest.mark.parametrize("needle", _ALSO_TEST_DATA)
def test_test_data_evidence_is_in_the_home_and_at_most_the_assertions(needle):
    sites = _sites_containing(needle, allow=(_ASSERTS,))
    assert sites == [_HOME], (
        f"{needle!r} is in {sites}, expected only {_HOME!r} (plus assertions in "
        f"{_ASSERTS}). It is evidence for the argument, not a phrase to repeat."
    )


@pytest.mark.parametrize("needle", _PROSE_ONLY + _ALSO_TEST_DATA)
def test_the_assertions_file_does_not_restate_the_argument_in_prose(needle):
    """Two of the four original homes were docstrings in this very file.

    Excluding it wholesale would leave the place the drift actually sat
    unguarded, so only its executable lines get the exemption.
    """
    tree = ast.parse(_read(_ASSERTS))
    prose = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            doc = ast.get_docstring(node)
            if doc:
                prose.append(doc)
    offenders = [d.splitlines()[0][:60] for d in prose if needle in d]
    assert not offenders, (
        f"{needle!r} appears in a docstring of {_ASSERTS}: {offenders}.\n"
        f"Assertions may name it; prose may not — restate nothing, link instead."
    )


def test_the_home_actually_carries_the_argument():
    """A pointer to a document without the finding is worse than no pointer.

    Round 10 found exactly that: the test docstring sent the reader to the spec
    for history the spec did not have.
    """
    home = _read(_HOME)
    missing = [n for n in _PROSE_ONLY + _ALSO_TEST_DATA if n not in home]
    assert not missing, (
        f"the spec amendment is the stated home of this argument but does not "
        f"contain: {missing}"
    )


def test_every_pointer_names_a_target_that_exists():
    """The linking sites name a file and a heading. Both have to be there."""
    anchor = "Amendment 2026-08-25"
    assert f"## {anchor}" in _read(_HOME), f"{_HOME} has no '## {anchor}' heading"

    for rel in ("skills/schliff/scripts/scoring/patterns/skill_md.py",
                "CHANGELOG.md", _ASSERTS):
        text = _read(rel)
        assert anchor in text, f"{rel} no longer points at the argument's home"
        # The path must survive a plain grep. An earlier version of the pattern
        # comment wrapped it across a line break, so `grep <filename>` found
        # nothing at the one site whose only job is to point at the home.
        assert os.path.basename(_HOME) in text, (
            f"{rel} names the anchor but no greppable path to {_HOME} — check "
            f"whether a line break splits the filename"
        )
