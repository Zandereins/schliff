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
    """Raw deltas are compared here, and they are NOT all on one scale.

    opcov deltas are computed against the agents.md profile; structure and
    efficiency deltas are hardcoded literals scaled by skill.md's weights, so on
    an AGENTS.md they understate their own effect (no_real_examples reports 1.5
    and delivers 4.0). The assertion below holds either way — 8.0 beats 4.0 as
    well as 1.5 — but it must not be read as evidence that the scales agree.
    See the mixed-scale issue tracked separately.
    """
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
def test_applying_the_fix_raises_the_composite(tmp_path, category):
    """Measured against the COMPOSITE, which is the number the CLI prints.

    An earlier version of this test compared score_operational_coverage before
    and after and called the delta a floor. That was the wrong quantity: adding
    a section also moves other dimensions. Measured on a saturated file, the
    `pr` fix states +4.0 and the composite gains +3.6, because the added prose
    dilutes efficiency. On a bare file the same fix overshoots instead.

    So the direction is asserted, not the magnitude — the magnitude is what
    `confidence: medium` is admitting to. Do not tighten this into an equality
    without first fixing the delta scale (see the mixed-scale issue).
    """
    from scoring import compute_composite
    from shared import build_scores

    def composite(path):
        return compute_composite(
            build_scores(path, None, include_runtime=True, fmt="agents.md"),
            fmt="agents.md",
        )["score"]

    before_path = _write(tmp_path, BARE, "cb.md")
    after_path = _write(
        tmp_path,
        BARE + "\n" + text_gradient._OPCOV_FIX[category]["example"] + "\n",
        f"ca_{category}.md",
    )
    assert composite(after_path) > composite(before_path), (
        f"{category}: following the advice does not raise the score the CLI shows"
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


def test_a_cheap_auto_patchable_fix_is_not_pushed_out(tmp_path):
    """An earlier version of this test asserted the opposite and pinned a bug.

    It claimed a PR section must outrank a TODO deletion, on the premise that the
    TODO was worth 1.5 and the section 4.0. Both numbers were wrong: structure
    deltas are scaled by skill.md's weights, so the TODO fix is really worth 4.0
    on an AGENTS.md, and the PR section delivers 2.8 rather than 4.0 once the
    added prose dilutes efficiency. The TODO fix is also EFFORT_SIMPLE and
    auto-applicable by generate_patches, where the PR section is manual. Ranking
    it below the section pushed the cheaper, larger, automatic fix out of
    --top N. The correct order is the one this test now asserts.
    """
    # Deliberately sparse: the strong opcov gradients (setup/build/test, the
    # 0.96 ones) must be PRESENT for this to test anything. An earlier fixture
    # satisfied every category, leaving only opcov_missing_pr at 0.48, and the
    # assertion then held with or without the delta rescale — it pinned nothing.
    text = BARE + "\nTODO: fix this later\n"
    path = _write(tmp_path, text)
    grads = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md")
    todo = [g for g in grads if g["issue"].startswith("has_todo")]
    pr = [g for g in grads if g["issue"] == "opcov_missing_pr"]
    # Not guarded with `if`: a guard turns this into a test that passes while
    # pinning nothing, and has_todo emission is exactly what a structure-scorer
    # change would alter.
    assert todo, "fixture no longer produces a has_todo gradient"
    assert pr, "fixture no longer produces an opcov_missing_pr gradient"

    # Stronger than "beats the pr fix": it must outrank EVERY opcov fix, and it
    # must survive the top-5 truncation that suggest and the evolve prompt apply.
    # Before the delta rescale it ranked sixth at 0.60 and the default view
    # contained no applicable patch at all.
    opcov = [g for g in grads if g["dimension"] == "operational_coverage"]
    assert opcov, "fixture no longer produces operational_coverage gradients"
    assert todo[0]["priority"] > max(g["priority"] for g in opcov), (
        "a manual section fix outranks a cheaper auto-applicable one"
    )
    assert text_gradient.generate_patches(path, grads[:5]), (
        "the default top-5 contains no applicable patch"
    )


def test_confidence_is_medium_because_the_composite_effect_varies(tmp_path):
    """The delta is exact for the dimension and approximate for the composite.

    Measured both directions: on a bare file the composite gains +20.0 against a
    stated +8.0 (one example credits several categories), on a saturated file
    +2.8 against +4.0 (added prose dilutes efficiency 95 -> 89). "high" would
    claim a precision that does not exist, and it also inflated priority by 1/0.6.
    """
    path = _write(tmp_path, BARE)
    grads = _opcov(path)
    assert grads
    assert all(g["confidence"] == "medium" for g in grads)


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
