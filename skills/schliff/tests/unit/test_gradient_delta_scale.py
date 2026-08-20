"""Delta literals are written on skill.md's weight basis and must be rescaled.

Every hardcoded delta in text_gradient.py is a composite estimate sized against
skill.md's table — `missing_name: 1.5` is 10 dimension points times structure's
0.15 there. Scored as an AGENTS.md the same fix is worth 10 x 0.4, so reporting
1.5 understates it ~2.7x. Measured before the fix: removing a TODO marker
reported +1.5 and moved the composite +4.4.
"""
import os
import sys

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import text_gradient  # noqa: E402

from scoring import compute_composite  # noqa: E402
from scoring.registry import get_weights  # noqa: E402
from shared import build_scores  # noqa: E402

SATURATED = (
    "# Proj\n\nA tool.\n\n## Setup\n\n```bash\nnpm install\n```\n"
    "\n## Build\n\n```bash\nnpm run build\n```\n"
    "\n## Testing\n\n```bash\npytest -q\n```\n"
    "\n## Code Style\n\n- Never use `eval`.\n- Always type `foo.py`.\n"
    "\n## Gotchas\n\n- Never commit `.env`.\n- Always wipe `build/`.\n"
    "\n## Pull Requests\n\n- Branch names must use `feat/`.\n- Always run the suite first.\n"
)


def _write(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def _composite(path, fmt):
    return compute_composite(
        build_scores(path, None, include_runtime=True, fmt=fmt), fmt=fmt
    )["score"]


def test_skill_md_deltas_do_not_move():
    """The current path must be untouched: the factor is exactly 1.0 there."""
    for dim, weight in get_weights("skill.md").items():
        assert text_gradient._scale_delta_to_format(1.5, dim, "skill.md") == 1.5, dim
        assert weight  # the profile is non-empty, so the loop is not vacuous


def test_agents_md_structure_delta_is_rescaled():
    base = get_weights("skill.md")["structure"]
    target = get_weights("agents.md")["structure"]
    assert target != base, "fixture assumes the two profiles differ"
    scaled = text_gradient._scale_delta_to_format(1.5, "structure", "agents.md")
    assert scaled == pytest.approx(round(1.5 * target / base, 2))
    assert scaled > 1.5


def test_a_dimension_absent_from_skill_md_is_not_rescaled():
    """operational_coverage computes its delta against the live profile already;
    scaling it here would apply the weight twice."""
    assert "operational_coverage" not in get_weights("skill.md")
    assert text_gradient._scale_delta_to_format(8.0, "operational_coverage", "agents.md") == 8.0


def test_unknown_format_and_none_are_passthrough():
    assert text_gradient._scale_delta_to_format(2.0, "structure", None) == 2.0
    assert text_gradient._scale_delta_to_format(2.0, "structure", "no-such-format") == 2.0


def test_reported_delta_lands_near_the_real_composite_change(tmp_path):
    """The number the CLI prints must be the right size, not merely positive.

    Tolerance is 25%: the delta is an estimate and removing text also nudges
    efficiency. Before the fix this was off by a factor of 2.9, which no
    tolerance of that kind would forgive.
    """
    with_todo = _write(tmp_path, SATURATED + "\nTODO: fix this later\n", "with.md")
    without = _write(tmp_path, SATURATED, "without.md")
    actual = _composite(without, "agents.md") - _composite(with_todo, "agents.md")

    grads = text_gradient.compute_gradients(
        with_todo, None, include_clarity=True, fmt="agents.md"
    )
    todo = [g for g in grads if g["issue"].startswith("has_todo")]
    assert todo, "fixture no longer produces a has_todo gradient"
    reported = todo[0]["delta"]
    assert abs(reported - actual) <= 0.25 * actual, (
        f"reported +{reported} against a real +{round(actual, 1)}"
    )


def test_range_hint_is_dropped_when_the_number_is_rescaled(tmp_path):
    """A "~2.0-5.0" display hint was written on the skill.md basis; once the
    number beside it is rescaled the hint describes something else."""
    path = _write(tmp_path, "# P\n\nIt is important to note that this does things.\n", "h.md")
    for g in text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md"):
        if "delta_display" in g:
            assert g["delta"] == pytest.approx(
                text_gradient._parse_delta(g["delta_display"]), abs=0.01
            ), f"{g['issue']}: display hint disagrees with the rescaled delta"
