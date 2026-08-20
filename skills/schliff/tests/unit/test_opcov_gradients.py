"""operational_coverage must produce fixes, and the fixes must actually work.

The dimension carries weight 0.4 in the agents.md profile — tied with structure
— but had no fix path: a file scoring 0/100 there was advised to add examples
for +2 while 40 composite points sat untouched.
"""
import os
import sys

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import text_gradient  # noqa: E402

from scoring.operational_coverage import score_operational_coverage  # noqa: E402

BARE = "# Proj\n\nA tool that does things.\n\n## Overview\n\nIt reads and writes.\n"

FIXES = {
    "setup": "\n## Setup\n\n```bash\nnpm install\n```\n",
    "build": "\n## Build\n\n```bash\nnpm run build\n```\n",
    "test": "\n## Testing\n\n```bash\npytest -q\n```\n",
    "code_style": (
        "\n## Code Style\n\n- Always use `snake_case` for module names.\n"
        "- Never import from `internal/` outside its package.\n"
    ),
    "gotchas": (
        "\n## Gotchas\n\n- Never commit `.env`; the deploy reads it from the vault.\n"
        "- Wipe `build/` before `npm run build` or stale assets ship.\n"
    ),
    "pr": (
        "\n## Pull Requests\n\n- Branch names must use the `feat/` prefix.\n"
        "- Run `pytest -q` before opening a PR.\n"
    ),
}


def _write(tmp_path, text, name="AGENTS.md"):
    # A unique path per call: the scorer keys on the path, so reusing one file
    # for several variants silently returns the first result.
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def _opcov_gradients(path):
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md")
    return [g for g in grads if g["dimension"] == "operational_coverage"]


def test_bare_agents_md_gets_operational_coverage_fixes(tmp_path):
    path = _write(tmp_path, BARE)
    assert score_operational_coverage(path)["score"] == 0
    issues = {g["issue"] for g in _opcov_gradients(path)}
    assert issues == {
        "opcov_missing_setup", "opcov_missing_build", "opcov_missing_test",
        "opcov_missing_code_style", "opcov_missing_gotchas", "opcov_missing_pr",
    }


def test_opcov_fix_outranks_the_previous_top_suggestion(tmp_path):
    path = _write(tmp_path, BARE)
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md")
    opcov = [g for g in grads if g["dimension"] == "operational_coverage"]
    other = [g for g in grads if g["dimension"] != "operational_coverage"]
    assert opcov, "no operational_coverage gradient produced"
    assert max(g["delta"] for g in opcov) > max((g["delta"] for g in other), default=0.0)


@pytest.mark.parametrize("category,expected_delta", [
    ("setup", 8.0), ("build", 8.0), ("test", 8.0),
    ("code_style", 6.0), ("gotchas", 6.0), ("pr", 4.0),
])
def test_applying_the_fix_raises_the_score_by_the_predicted_amount(
    tmp_path, category, expected_delta,
):
    """A suggestion you can follow without the number moving is decoration."""
    before_path = _write(tmp_path, BARE, "before.md")
    before = score_operational_coverage(before_path)["score"]

    grad = next(
        g for g in _opcov_gradients(before_path)
        if g["issue"] == f"opcov_missing_{category}"
    )
    assert grad["delta"] == expected_delta
    assert grad["confidence"] == "high", "the delta is computed, not estimated"

    after_path = _write(tmp_path, BARE + FIXES[category], f"after_{category}.md")
    after = score_operational_coverage(after_path)["score"]
    actual = round((after - before) * 0.4, 1)
    assert actual >= expected_delta - 0.05, (
        f"{category}: predicted +{expected_delta}, actually +{actual}"
    )


def test_credited_category_produces_no_gradient(tmp_path):
    path = _write(tmp_path, BARE + FIXES["test"])
    issues = {g["issue"] for g in _opcov_gradients(path)}
    assert "opcov_missing_test" not in issues
    assert "opcov_missing_setup" in issues


def test_no_opcov_gradients_for_skill_md(tmp_path):
    """The dimension only runs for agents.md; it must not leak into SKILL.md advice."""
    path = _write(tmp_path, BARE, "SKILL.md")
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="skill.md")
    assert not [g for g in grads if g["dimension"] == "operational_coverage"]


def test_all_fixes_together_reach_full_credit(tmp_path):
    """The suggestions are additive: the estimate sums deltas, so applying all
    of them must actually land at 100, not merely at 'better'."""
    before_path = _write(tmp_path, BARE, "sum_before.md")
    grads = _opcov_gradients(before_path)
    assert len(grads) == 6

    combined = BARE + "".join(FIXES[g["issue"].replace("opcov_missing_", "")] for g in grads)
    after_path = _write(tmp_path, combined, "sum_after.md")

    assert score_operational_coverage(after_path)["score"] == 100
    assert sum(g["delta"] for g in grads) == pytest.approx(40.0)
    assert not _opcov_gradients(after_path)
