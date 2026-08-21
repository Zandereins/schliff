"""Every caller must resolve the format and pass it to BOTH halves.

compute_gradients uses `fmt` to decide which fixes apply; compute_composite uses
it to decide which dimensions count. A caller that passes it to neither scored an
AGENTS.md without operational_coverage — its heaviest dimension at weight 0.4 —
and the composite counted the gap as zero: 27.0 where build_scores gives 39.0.

The advice was wrong in the same breath: `text_gradient.py AGENTS.md` told the
user to add YAML frontmatter and to create an eval-suite.json worth 25 points,
neither of which exists for that format.
"""
import importlib.util
import os
import subprocess
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, _SCRIPTS)
sys.path.insert(0, os.path.join(_SCRIPTS, "scoring"))

import text_gradient  # noqa: E402

BARE_AGENTS = "# Proj\n\nA tool.\n\n## Overview\n\nIt reads.\n\nTODO: fix this later\n"
SKILL_ONLY_ISSUES = {"no_frontmatter", "missing_name", "missing_description",
                     "no_trigger_eval_suite", "no_eval_suite_test_cases"}


def _load(name, filename):
    """Import a script whose filename is not a valid module name."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SCRIPTS, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def agents_md(tmp_path):
    p = tmp_path / "AGENTS.md"
    p.write_text(BARE_AGENTS, encoding="utf-8")
    return str(p)


def test_dashboard_scores_the_dimensions_the_format_actually_has(agents_md):
    dashboard = _load("dashboard_mod", "dashboard.py")
    data = dashboard.generate_dashboard(agents_md)
    assert "operational_coverage" in data["dimensions"], (
        "dashboard scores an AGENTS.md without its heaviest dimension"
    )
    assert not (set(g["issue"] for g in data["top_gradients"]) & SKILL_ONLY_ISSUES), (
        "dashboard shows SKILL-only advice for an AGENTS.md"
    )


def test_dashboard_composite_uses_the_format_profile(agents_md):
    """The other half. Passing fmt to build_scores but not to compute_composite
    leaves the dimensions right and the headline number wrong, which reads as a
    low score rather than a bug — so `dimensions` alone cannot pin this."""
    import score_skill as scorer

    from shared import build_scores

    dashboard = _load("dashboard_mod2", "dashboard.py")
    reported = dashboard.generate_dashboard(agents_md)["composite_score"]

    scores = build_scores(agents_md, None, include_runtime=False, fmt="agents.md")
    expected = scorer.compute_composite(scores, fmt="agents.md")["score"]
    wrong = scorer.compute_composite(scores)["score"]
    assert expected != wrong, "fixture no longer distinguishes the two profiles"
    assert reported == pytest.approx(expected, abs=0.05), (
        f"dashboard reports {reported}; the agents.md profile gives {expected}"
    )


def test_auto_improve_scores_the_dimensions_the_format_actually_has(agents_md):
    auto = _load("auto_improve_mod", "auto-improve.py")
    result = auto._score_skill(agents_md)
    assert "operational_coverage" in result["dimensions"], (
        "the improvement loop optimises against a composite missing weight 0.4"
    )


def test_text_gradient_cli_gives_format_appropriate_advice(agents_md):
    """The module's own CLI had no --format flag at all."""
    out = subprocess.run(
        [sys.executable, os.path.join(_SCRIPTS, "text_gradient.py"), agents_md, "--json"],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr[-500:]
    import json
    gradients = json.loads(out.stdout)["gradients"]
    issues = {g["issue"] for g in gradients}
    assert not (issues & SKILL_ONLY_ISSUES), (
        f"SKILL-only advice on an AGENTS.md: {sorted(issues & SKILL_ONLY_ISSUES)}"
    )
    assert any(g["dimension"] == "operational_coverage" for g in gradients)


def test_text_gradient_cli_accepts_an_explicit_format(agents_md):
    out = subprocess.run(
        [sys.executable, os.path.join(_SCRIPTS, "text_gradient.py"),
         agents_md, "--json", "--format", "agents.md"],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr[-500:]


def test_incomplete_score_dict_would_understate_the_composite(agents_md):
    """Pins WHY the fix is build_scores rather than just passing fmt along.

    Passing the format to compute_composite while still hand-listing dimensions
    leaves the missing one counted as zero, which looks like a low score rather
    than a bug.
    """
    import score_skill as scorer

    from shared import build_scores

    hand_listed = {
        "structure": scorer.score_structure(agents_md),
        "efficiency": scorer.score_efficiency(agents_md),
    }
    partial = scorer.compute_composite(hand_listed, fmt="agents.md")["score"]
    full = scorer.compute_composite(
        build_scores(agents_md, None, include_runtime=False, fmt="agents.md"),
        fmt="agents.md",
    )["score"]
    assert partial < full, "fixture no longer demonstrates the gap"

def test_dry_run_scores_under_the_same_format_as_the_baseline(tmp_path):
    """--dry-run writes a sibling temp file, and its NAME decided the format.

    `AGENTS.md` becomes `AGENTS.dryrun.tmp`, which detect_format calls "unknown",
    so the candidate was scored with skill.md weights while the baseline used
    agents.md. Measured on one file: 35.0 vs 23.4 — every keep/discard verdict
    inverted, a +4.0 improvement reported as -11.3.
    """
    auto = _load("auto_improve_fmt", "auto-improve.py")
    for name in ("AGENTS.md", "SKILL.md", "CLAUDE.md"):
        p = tmp_path / name
        p.write_text(BARE_AGENTS, encoding="utf-8")
        baseline = auto._score_skill(str(p))["composite"]
        candidate = auto._score_content(BARE_AGENTS, str(p))["composite"]
        assert candidate == pytest.approx(baseline, abs=0.05), (
            f"{name}: dry-run scores {candidate} against a baseline of {baseline}"
        )


@pytest.mark.parametrize("name,fmt", [
    ("CLAUDE.md", "claude.md"),
    ("AGENTS.md", "agents.md"),
    (".cursorrules", "cursorrules"),
])
def test_no_frontmatter_is_not_advised_where_scoring_synthesises_it(tmp_path, name, fmt):
    """build_scores normalizes every format except skill.md, so the frontmatter
    is already credited and a patch for it is worth exactly 0.0 — which
    auto-improve keeps, because its gate is `>= 0`. A CLAUDE.md came back with an
    invented `---\nname: …\n---` block for no gain."""
    p = tmp_path / name
    p.write_text("# cm\n\nRun `make build` to build.\n", encoding="utf-8")
    issues = {
        g["issue"]
        for g in text_gradient.compute_gradients(str(p), None, include_clarity=True, fmt=fmt)
    }
    assert not (issues & {"no_frontmatter", "missing_name", "missing_description"}), (
        f"{fmt}: advises adding frontmatter that scoring already synthesises"
    )


def test_skill_md_still_gets_the_frontmatter_advice(tmp_path):
    """The counter-case: skill.md is NOT normalized, so there the gradient is real."""
    p = tmp_path / "SKILL.md"
    p.write_text("# s\n\nRun `make build` to build.\n", encoding="utf-8")
    issues = {
        g["issue"]
        for g in text_gradient.compute_gradients(str(p), None, include_clarity=True, fmt="skill.md")
    }
    assert "no_frontmatter" in issues


def test_no_clarity_does_not_zero_a_headline_dimension(tmp_path):
    """The composite uses a full denominator, so a popped dimension counts as
    ZERO rather than being renormalized away. On system_prompt clarity weighs
    0.15, and the opt-out turned 51.4 into 36.4."""
    from scoring.registry import get_weights

    dashboard = _load("dashboard_clarity", "dashboard.py")
    p = tmp_path / "sys.prompt"
    p.write_text(
        "You are a helpful assistant.\n\nAlways cite sources.\n"
        "Never invent a citation.\n\nReturn JSON with a `result` key.\n",
        encoding="utf-8",
    )
    weight = get_weights("system_prompt").get("clarity")
    assert weight and weight > 0.05, "fixture assumes clarity is a headline dim here"

    full = dashboard.generate_dashboard(str(p))["composite_score"]
    opted_out = dashboard.generate_dashboard(str(p), include_clarity=False)["composite_score"]
    assert opted_out == pytest.approx(full, abs=0.05), (
        f"--no-clarity dropped a 0.15-weight dimension to zero: {full} -> {opted_out}"
    )


def test_format_flag_rejects_a_typo():
    """Without `choices`, `--format agentsmd` exited 0 and printed SKILL-only
    advice, with no signal the flag had been ignored."""
    out = subprocess.run(
        [sys.executable, os.path.join(_SCRIPTS, "text_gradient.py"),
         "x.md", "--format", "agentsmd"],
        capture_output=True, text=True, timeout=60,
    )
    assert out.returncode != 0
    assert "invalid choice" in out.stderr
