"""A documented command list must not score below a bare command dump.

`_RE_ACTIONABLE_LINES` matches English imperative verbs at line start, so a line that
*is* an executable command counts as nothing. Both fixtures therefore measure
`actionable_lines: 1`, and the dump wins on density alone by being shorter — the
efficiency formula divides signal by word count, so explaining your commands costs
points.

The pair differs only in whether the commands are real and documented; sections,
frontmatter and prose scaffolding are identical.

Spec: docs/specs/2026-08-13-structural-signal-detection.md
"""
from pathlib import Path

import pytest

from scoring.efficiency import score_efficiency

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "command-signal"
DESERVES = str(FIXTURES / "deserves.md")
DUMP = str(FIXTURES / "dump.md")


def test_documented_commands_outscore_a_command_dump():
    """The file that documents its commands must rank above the one that dumps them."""
    deserves = score_efficiency(DESERVES)["score"]
    dump = score_efficiency(DUMP)["score"]
    assert deserves > dump, (
        f"documented={deserves} dump={dump} — a bare command dump must not "
        f"outscore a documented command list"
    )


def test_documented_commands_register_as_signal():
    """A documented command line is actionable content and must be counted as such."""
    details = score_efficiency(DESERVES)["details"]
    # deserves.md carries 7 distinct documented commands in its Commands section
    # plus prose; counting only the single prose imperative is the defect.
    assert details["actionable_lines"] >= 7, (
        f"actionable_lines={details['actionable_lines']} — 7 documented commands "
        f"in the Commands section register as nothing"
    )


def test_bare_command_list_contributes_nothing():
    """A command in a list with no explanation beside it is not a signal.

    dump.md's Commands section is seven bare bullets (`ls -la`, `cd /workspace`,
    `pwd -P`, …). Its Workflow section does explain four commands, and those count —
    the detector separates documented from undocumented, not useful from trivial.
    Judging whether `ls -la` is worth documenting is not something a structural
    detector can do, and claiming otherwise would be the same overreach this fix removes.
    """
    from scoring.patterns import _RE_DOCUMENTED_COMMAND, normalize_command

    body = Path(DUMP).read_text(encoding="utf-8")
    commands_section = body.split("## Commands")[1].split("##")[0]
    hits = [
        normalize_command(m.group(1))
        for m in _RE_DOCUMENTED_COMMAND.finditer(commands_section)
    ]
    assert hits == [], f"bare bullets registered as documented commands: {hits}"


@pytest.mark.parametrize("path", [DESERVES, DUMP])
def test_efficiency_stays_in_range(path):
    """Guard the formula's bounds while the signal source changes."""
    score = score_efficiency(path)["score"]
    assert 0 <= score <= 100


@pytest.mark.parametrize(
    "command,expected",
    [
        ("tool score <file>", "tool score"),
        ("tool score SKILL.md", "tool score"),
        ("tool@8.8.2 verify <file>", "tool verify"),
        ("tool doctor --skill-dirs <dir>", "tool doctor"),
        # A scoped package name is the name, not a version pin. Splitting on '@'
        # here produced an empty token ('npx  compile'), collapsing two different
        # packages onto one identity. Found on an installed skill, not a fixture.
        ("npx @vercel/microfrontends compile", "npx @vercel/microfrontends compile"),
        ("npx @scope/other compile", "npx @scope/other compile"),
        # The head is the program, never an argument. A program name carrying an
        # extension matched the file-with-suffix branch and broke out on token 0,
        # returning an empty identity so the whole line was dropped — the exact line
        # shape this detector exists to credit. Found by review; 0 field hits.
        ("run-eval.sh --eval-suite core", "run-eval.sh"),
        ("manage.py migrate", "manage.py migrate"),
        ("score-skill.py SKILL.md --json", "score-skill.py"),
    ],
)
def test_normalize_command_identity(command, expected):
    """A command's identity is its program plus subcommands — not its arguments."""
    from scoring.patterns import normalize_command

    assert normalize_command(command) == expected


def test_aligned_dependency_entry_is_not_a_command():
    """A padded package name in a dependency list is not a documented command.

    Found on a real AGENTS.md in docs/launch/corpus/agents, not on a fixture:
    a dependency table aligns its entries with trailing spaces inside the backticks,
    which reads as "program + argument" unless a real argument is required.
    """
    from scoring.patterns import _RE_DOCUMENTED_COMMAND

    dependency_entry = (
        "* `coverlet.collector     ` : Coverlet is a cross platform code "
        "coverage library for .NET, with support for line and branch coverage."
    )
    assert _RE_DOCUMENTED_COMMAND.search(dependency_entry) is None

    # ...while a real command on the same shape of line still registers.
    real_command = "* `make test` : ExUnit + coveralls JSON."
    assert _RE_DOCUMENTED_COMMAND.search(real_command) is not None


def test_scoped_packages_do_not_collapse():
    """Two different scoped packages must not deduplicate onto each other."""
    from scoring.patterns import normalize_command

    a = normalize_command("npx @vercel/microfrontends compile")
    b = normalize_command("npx @scope/other compile")
    assert a != b, f"both normalized to {a!r}"
