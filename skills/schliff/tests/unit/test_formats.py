"""Tests for scoring/formats.py — format detection and content normalization."""
from __future__ import annotations

from scoring.formats import detect_format, normalize_content


# --- P0: detect_format ---

def test_detect_skill_md():
    assert detect_format("SKILL.md") == "skill.md"


def test_detect_claude_md():
    assert detect_format("CLAUDE.md") == "claude.md"


def test_detect_cursorrules():
    assert detect_format(".cursorrules") == "cursorrules"


def test_detect_agents_md():
    assert detect_format("AGENTS.md") == "agents.md"


def test_detect_unknown():
    assert detect_format("README.md") == "unknown"


# --- P0: normalize_content passthrough ---

def test_normalize_passthrough():
    content = "---\nname: My Skill\ndescription: Does things\n---\n\n# My Skill\n\nBody text."
    result = normalize_content(content, "skill.md")
    assert result == content


# --- normalize_content: non-skill.md formats get synthetic frontmatter ---

def test_normalize_wraps_plain_content():
    content = "# My Tool\n\nThis tool does something useful."
    result = normalize_content(content, "claude.md")
    assert result.startswith("---\n")
    assert "name:" in result
    assert "description:" in result
    assert content in result


def test_normalize_passthrough_if_already_has_frontmatter():
    content = "---\nname: Existing\ndescription: Already wrapped\n---\n\nBody."
    result = normalize_content(content, "cursorrules")
    assert result == content


def test_normalize_no_heading_uses_first_line():
    content = "This is the first significant line.\n\nMore content follows."
    result = normalize_content(content, "agents.md")
    assert result.startswith("---\n")
    assert "name:" in result
    assert content in result


# --- Token-budget alias resolution (audit 2026-07-22) ---

def test_format_alias_resolves_to_correct_token_budget():
    """`--format cursor`/`agents`/`claude`/`skill`/`system-prompt` must map to their
    real budget, not silently fall back to the unknown=1500 default (which flips the
    within_budget verdict on the exact spellings the docs tell users to type)."""
    from scoring.formats import FORMAT_TOKEN_BUDGETS, check_token_budget
    content = "word " * 300
    # Compared against the table rather than restated as literals: what is under test is
    # that the alias resolves, not what each budget happens to be. Restating them made
    # this test fail for an unrelated recalibration of one entry.
    for alias, canonical in (
        ("cursor", "cursorrules"),
        ("cursorrules", "cursorrules"),
        ("agents", "agents.md"),
        ("claude", "claude.md"),
        ("skill", "skill.md"),
        ("system-prompt", "system_prompt"),
    ):
        expected = FORMAT_TOKEN_BUDGETS[canonical]
        assert check_token_budget(content, alias)["budget"] == expected, (
            f"alias {alias!r} did not resolve to {canonical!r}"
        )
        # The original bug was a silent fall-through to the unknown default, so an alias
        # whose real budget differs from that default must not land on it.
        if expected != FORMAT_TOKEN_BUDGETS["unknown"]:
            assert check_token_budget(content, alias)["budget"] != FORMAT_TOKEN_BUDGETS["unknown"]
    # unknown/garbage still falls back safely
    assert check_token_budget(content, "totally-bogus")["budget"] == FORMAT_TOKEN_BUDGETS["unknown"]


# --- Alias and canonical name must score identically (2026-08-04) ---

_NO_FRONTMATTER = """\
# Deploy Helper

Helps deploy things to production safely.

## Usage

Run the deploy command.

## When to Use

Use when deploying a service.
"""


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_skill_alias_scores_identically_to_canonical_name(tmp_path):
    """`--format skill` and `--format skill.md` must agree on a frontmatter-less file.

    `shared.build_scores` branched on a RAW compare (`fmt != "skill.md"`). The public
    `skill` alias failed it, entered the normalization branch its canonical twin skips,
    and was scored as a copy wrapped in synthetic frontmatter that the file does not
    have — inflating it by 4.7-5.5 composite points across the 8 tracked instruction
    files without frontmatter (two of them in the benchmark corpus).

    The fixture deliberately has NO frontmatter: with frontmatter present
    `normalize_content` returns the content unchanged, so the bug is invisible.
    """
    from shared import build_scores
    path = _write(tmp_path, "SKILL.md", _NO_FRONTMATTER)
    assert build_scores(path, None, fmt="skill") == build_scores(path, None, fmt="skill.md")


def test_stating_skill_format_does_not_invent_frontmatter(tmp_path):
    """The structure score must report missing frontmatter, not have it papered over.

    This is the direction the fix converges on, pinned separately from the equality
    above: equality alone would also be satisfied by making BOTH spellings normalize,
    which would hide the defect the structure dimension exists to report.
    """
    from shared import build_scores
    no_fm = _write(tmp_path, "SKILL.md", _NO_FRONTMATTER)
    with_fm = _write(
        tmp_path,
        "WITH.md",
        "---\nname: deploy-helper\ndescription: Use when deploying.\n---\n\n" + _NO_FRONTMATTER,
    )
    stated = build_scores(no_fm, None, fmt="skill")["structure"]["score"]
    assert stated < build_scores(with_fm, None, fmt="skill.md")["structure"]["score"]


def test_every_format_alias_scores_identically_to_its_canonical_name(tmp_path):
    """Generalized over the alias table, so a newly added alias cannot reopen this.

    Two of the four branch sites that compared a raw format string have now been fixed
    one incident at a time (#168 for `system-prompt`, this one for `skill`). Deriving
    the pairs from FORMAT_ALIASES instead of listing them is what makes the next alias
    covered on the day it is added.
    """
    from scoring.registry import FORMAT_ALIASES
    from shared import build_scores
    path = _write(tmp_path, "SKILL.md", _NO_FRONTMATTER)
    for alias, canonical in sorted(FORMAT_ALIASES.items()):
        assert build_scores(path, None, fmt=alias) == build_scores(path, None, fmt=canonical), (
            f"alias {alias!r} scored differently than canonical {canonical!r}"
        )
