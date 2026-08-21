"""A documented command appears in three shapes; the detector saw one.

Measured over 184 installed SKILL.md files before the fix: 10 top-level bullets
credited, 8 table rows and 2 indented sub-bullets scoring nothing.

The widening is not free. Crediting table rows without a filter admitted 9
non-commands against 2 real ones — precision 2/11, against 39/39 for the
original pattern. In a list the `—` asserts that what follows explains what
precedes; in a table the `|` is only structure, so the row shape alone credits
any two-column code reference.
"""
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, _SCRIPTS)
sys.path.insert(0, os.path.join(_SCRIPTS, "scoring"))

from scoring.patterns.base import find_documented_commands  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("- `npm run build` — build the bundle", ["npm run build"]),
    ("1. `pytest -q` — run the unit tests quietly", ["pytest -q"]),
    ("  - `uv sync --frozen` — install the pinned environment", ["uv sync --frozen"]),
    ("\t* `git status` — show the working tree state", ["git status"]),
    ("| `gh pr list` | List the open pull requests |", ["gh pr list"]),
    ("  | `docker compose up` | Start the local stack |", ["docker compose up"]),
])
def test_all_documented_shapes_are_credited(text, expected):
    assert find_documented_commands(text) == expected


@pytest.mark.parametrize("text", [
    # Every one of these was a real false positive in the field, admitted by the
    # table shape before the command/code filter existed.
    "| `dynamic = 'force-dynamic'` | Opt the route out of caching |",
    "| `revalidate = N` | Revalidate every N seconds |",
    "| `app.ontoolresult = fn` | Handle a tool result |",
    "| `new App(info, caps, {autoResize: true})` | Construct the app |",
])
def test_code_fragments_in_tables_are_not_commands(text):
    assert find_documented_commands(text) == []


@pytest.mark.parametrize("command_line,expected", [
    # `=` alone must not disqualify: these are real command text.
    ("- `docker run -e FOO=bar image` — run with an env var set", ["docker run -e FOO=bar image"]),
    ("- `gh pr list --limit=50` — list with an explicit limit", ["gh pr list --limit=50"]),
])
def test_equals_inside_a_command_is_not_an_assignment(command_line, expected):
    assert find_documented_commands(command_line) == expected


def test_list_marker_alone_on_a_line_credits_nothing():
    """`\\s` after the marker would cross the newline and credit the next line."""
    assert find_documented_commands("1.\n`npm run build` — build the bundle") == []


def test_no_production_caller_reaches_past_the_contract():
    """A fourth shape added later must not leave a consumer behind.

    An earlier version of this test grepped exactly one hardcoded path
    (efficiency.py), so a NEW module importing the raw pattern — the failure it
    exists to prevent — would have passed it. It now walks the whole scripts
    tree. Tests may still probe the patterns directly; the contract binds
    production callers, which is a distinction __all__ cannot express.
    """
    import pathlib

    offenders = []
    for path in pathlib.Path(_SCRIPTS).rglob("*.py"):
        if "test" in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "_RE_DOCUMENTED_COMMAND" in text and path.name != "base.py":
            offenders.append(str(path.relative_to(_SCRIPTS)))
    assert not offenders, (
        "these reach past find_documented_commands: " + ", ".join(offenders)
    )

    efficiency = pathlib.Path(_SCRIPTS, "scoring", "efficiency.py").read_text(encoding="utf-8")
    assert "find_documented_commands" in efficiency, "the known consumer stopped using it"

@pytest.mark.parametrize("text", [
    # Branch 2 of _RE_NOT_A_COMMAND was unreachable: _CMD only ever yields a head
    # followed by whitespace, so a `(` could never sit where the branch required
    # it, and these were all credited as commands.
    "| `app (x, y)` | Construct the app with two args |",
    "| `foo.bar (x)` | Call the thing with one arg |",
    "- `run (a, b)` — call the function with two args",
])
def test_call_expressions_are_not_commands(text):
    assert find_documented_commands(text) == []


@pytest.mark.parametrize("text,expected", [
    # The table shape accepted ANY non-empty cell while the list shape required
    # 10+ characters, so `| x |` counted where `— x` did not.
    ("| `git add` | x |", []),
    ("| `git add` | stages the given paths |", ["git add"]),
    ("- `git add` — x", []),
])
def test_table_needs_a_real_explanation_like_the_list_form(text, expected):
    assert find_documented_commands(text) == expected
