"""operational_coverage must produce fixes, and the fixes must actually work.

The dimension carries the heaviest weight in the agents.md profile — tied with
structure — but had no fix path: a file scoring 0/100 there was advised to add
examples for +2 while 40 composite points sat untouched.

The tests score the CANONICAL EXAMPLE carried by each instruction rather than a
fixture written alongside it. The first version of this change did the latter
and passed while the advice was wrong: it told users to run `make` (the scorer
needs an operand) and to mention `pytest` in prose (the scorer needs a fence or
a flag), and the fixtures happened to use `npm run build` and a fenced block.
Advice and test data must be the same object or they drift apart silently.
"""
import os
import sys

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import text_gradient  # noqa: E402

from scoring.operational_coverage import score_operational_coverage  # noqa: E402
from scoring.registry import get_weights  # noqa: E402

BARE = "# Proj\n\nA tool that does things.\n\n## Overview\n\nIt reads and writes.\n"
CATEGORIES = ["setup", "build", "test", "code_style", "gotchas", "pr"]


def _write(tmp_path, text, name="AGENTS.md"):
    # A unique path per call: the scorer keys on the path, so reusing one file
    # for several variants silently returns the first result. A harness that did
    # this reported commands the base file does not contain.
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def _opcov(path, fmt="agents.md"):
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt=fmt)
    return [g for g in grads if g["dimension"] == "operational_coverage"]


def test_bare_agents_md_gets_a_fix_for_every_category(tmp_path):
    path = _write(tmp_path, BARE)
    assert score_operational_coverage(path)["score"] == 0
    assert {g["issue"] for g in _opcov(path)} == {f"opcov_missing_{c}" for c in CATEGORIES}


def test_opcov_fix_outranks_the_previous_top_suggestion(tmp_path):
    path = _write(tmp_path, BARE)
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md")
    opcov = [g for g in grads if g["dimension"] == "operational_coverage"]
    other = [g for g in grads if g["dimension"] != "operational_coverage"]
    assert opcov
    assert max(g["delta"] for g in opcov) > max((g["delta"] for g in other), default=0.0)


@pytest.mark.parametrize("category", CATEGORIES)
def test_the_example_the_instruction_gives_actually_earns_the_credit(tmp_path, category):
    """Follow the advice verbatim; the score must move.

    This is the test that catches advice the scorer refuses — a bare `make`, an
    inline `pytest`, or two rules that reuse one normative word.
    """
    spec = text_gradient._OPCOV_FIX[category]
    before_path = _write(tmp_path, BARE, "before.md")
    before = score_operational_coverage(before_path)["score"]

    after_path = _write(tmp_path, BARE + "\n" + spec["example"] + "\n", f"after_{category}.md")
    after = score_operational_coverage(after_path)["details"]["categories"]
    assert after[category]["credited"], (
        f"{category}: the example in its own instruction earns no credit — "
        f"{after[category]['reason']}"
    )
    assert score_operational_coverage(after_path)["score"] > before


@pytest.mark.parametrize("category", CATEGORIES)
def test_delta_is_a_floor_and_is_met(tmp_path, category):
    """The promised delta must be achievable, and must not overpromise.

    Directive categories can pay MORE than the table says (code_style has a
    heading-agnostic content fallback, so a gotchas section can satisfy it in
    passing — measured at +20.0 where the table says +6.0). Erring low is the
    safe direction next to "confidence: high"; erring high is not.
    """
    spec = text_gradient._OPCOV_FIX[category]
    before_path = _write(tmp_path, BARE, "fb.md")
    before = score_operational_coverage(before_path)["score"]
    grad = next(g for g in _opcov(before_path) if g["issue"] == f"opcov_missing_{category}")

    after_path = _write(tmp_path, BARE + "\n" + spec["example"] + "\n", f"fa_{category}.md")
    after = score_operational_coverage(after_path)["score"]
    dim_weight = get_weights("agents.md")["operational_coverage"]
    actual = round((after - before) * dim_weight, 1)
    assert actual >= grad["delta"] - 0.05, (
        f"{category}: promised +{grad['delta']}, delivered +{actual} — overpromise"
    )


def test_delta_tracks_the_registry_not_a_copy_of_it(tmp_path):
    """Both weights are read, never copied: the dimension weight from the registry
    and the category weight from the scorer. A copy of either stays green while the
    original moves under it."""
    path = _write(tmp_path, BARE)
    weight = get_weights("agents.md")["operational_coverage"]
    for g in _opcov(path):
        cat = g["issue"].replace("opcov_missing_", "")
        expected = round(text_gradient._OPCOV_WEIGHTS[cat] * weight, 1)
        assert g["delta"] == expected


def test_ranking_uses_the_agents_md_profile(tmp_path):
    """Under skill.md's table operational_coverage falls to the 0.10 default, which
    ranked a 1.5-point TODO fix above a 4.0-point PR section on a real file."""
    text = (
        BARE
        + "\n## Setup\n\n```bash\nnpm install\n```\n"
        + "\n## Build\n\n```bash\nnpm run build\n```\n"
        + "\n## Testing\n\n```bash\npytest -q\n```\n"
        + "\n## Code Style\n\n- Never use `eval`.\n- Always type `foo.py`.\n"
        + "\n## Gotchas\n\n- Never commit `.env`.\n- Always wipe `build/`.\n"
        + "\nTODO: fix this later\n"
    )
    path = _write(tmp_path, text)
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md")
    pr = next(g for g in grads if g["issue"] == "opcov_missing_pr")
    todo = [g for g in grads if g["issue"].startswith("has_todo")]
    if todo:
        assert pr["priority"] > todo[0]["priority"], (
            "a 1.5-point TODO fix outranks a 4.0-point PR section"
        )


def test_no_gradients_when_the_caller_omits_the_format(tmp_path):
    """Detecting the format here was tried and reverted — it desynchronises this
    function from compute_composite, which stays on skill.md weights. Pinned so
    the revert is not undone by accident; the caller gap is tracked separately."""
    path = _write(tmp_path, BARE)
    assert not _opcov(path, fmt=None)


def test_all_fixes_together_reach_full_credit(tmp_path):
    before_path = _write(tmp_path, BARE, "sum_before.md")
    grads = _opcov(before_path)
    assert len(grads) == len(CATEGORIES)
    combined = BARE + "".join(
        "\n" + text_gradient._OPCOV_FIX[g["issue"].replace("opcov_missing_", "")]["example"] + "\n"
        for g in grads
    )
    after_path = _write(tmp_path, combined, "sum_after.md")
    assert score_operational_coverage(after_path)["score"] == 100
    assert not _opcov(after_path)


def test_credited_category_produces_no_gradient(tmp_path):
    path = _write(tmp_path, BARE + "\n" + text_gradient._OPCOV_FIX["test"]["example"] + "\n")
    issues = {g["issue"] for g in _opcov(path)}
    assert "opcov_missing_test" not in issues
    assert "opcov_missing_setup" in issues


def test_no_opcov_gradients_for_skill_md(tmp_path):
    path = _write(tmp_path, BARE, "SKILL.md")
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="skill.md")
    assert not [g for g in grads if g["dimension"] == "operational_coverage"]
