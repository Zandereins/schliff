"""Entry points ask the owners instead of keeping their own copies (#225, #205).

`shared.load_eval_suite` owns reading a sibling eval-suite.json, `detect_format`
owns which format a file is, and `build_scores`/`compute_composite` own which
dimensions count. Each copy below drifted from its owner in a way a user could
see: a non-UTF-8 suite ended the run, a patch reported a delta its gradient did
not, and an AGENTS.md got a composite `schliff score` does not give.
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, _SCRIPTS)

import text_gradient  # noqa: E402

SKILL = (
    "---\nname: demo\ndescription: Demo skill. Use when testing.\n---\n\n"
    "# Demo\n\n## Instructions\n\n1. Run the thing.\n2. Check the output.\n"
)
BARE_AGENTS = "# Proj\n\nA tool.\n\n## Overview\n\nIt reads.\n\nTODO: fix this later\n"


def _load(name, filename):
    """Import a script whose filename is not a valid module name."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(_SCRIPTS, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(script, *args, home):
    env = dict(os.environ, HOME=str(home))
    return subprocess.run(
        [sys.executable, os.path.join(_SCRIPTS, script), *args],
        capture_output=True, text=True, env=env, timeout=60,
    )


@pytest.fixture
def skill_with_binary_suite(tmp_path):
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL, encoding="utf-8")
    # Not UTF-8: a UnicodeDecodeError is a ValueError, not a JSONDecodeError.
    (skill_dir / "eval-suite.json").write_bytes(b'{"skill_name": "\xff\xfe"}')
    return skill_dir / "SKILL.md"


# The owner reads bytes and decodes with replacement, so the suite loads; the
# copies called read_text() and raised before their except clauses could look.
@pytest.mark.parametrize("script,extra", [
    ("score-skill.py", ["--json"]),
    ("text_gradient.py", ["--json"]),
])
def test_a_non_utf8_suite_degrades_instead_of_ending_the_run(
        script, extra, skill_with_binary_suite, tmp_path):
    result = _run(script, str(skill_with_binary_suite), *extra, home=tmp_path)
    assert result.returncode == 0, (
        f"{script} exits {result.returncode} on a non-UTF-8 eval-suite.json:\n"
        f"{result.stdout[-400:]}{result.stderr[-400:]}"
    )
    assert "Traceback" not in result.stderr
    json.loads(result.stdout)


@pytest.mark.parametrize("issue", ["excessive_hedging:3", "filler_phrases:4"])
def test_regex_patch_reports_the_delta_of_its_gradient(issue, tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(SKILL, encoding="utf-8")
    gradient = {"dimension": "efficiency", "issue": issue, "delta": 2.75,
                "priority": 1.0, "instruction": "x"}
    patches = [p for p in text_gradient.generate_patches(str(skill), [gradient])
               if p["op"] == "remove_regex"]
    assert patches, "fixture no longer produces a regex patch"
    assert patches[0]["delta"] == 2.75


def test_doctor_composite_uses_the_format_profile(tmp_path):
    from scoring.composite import compute_composite
    from shared import build_scores

    agents = tmp_path / "AGENTS.md"
    agents.write_text(BARE_AGENTS, encoding="utf-8")
    doctor = _load("doctor_mod", "doctor.py")
    reported = doctor._score_single_skill(str(agents))["composite"]

    scores = build_scores(str(agents), None, fmt="agents.md")
    expected = compute_composite(scores, fmt="agents.md")["score"]
    assert expected != compute_composite(scores)["score"], (
        "fixture no longer distinguishes the two profiles")
    assert reported == pytest.approx(expected, abs=0.05)


def test_score_skill_agrees_with_schliff_score_on_agents_md(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(BARE_AGENTS, encoding="utf-8")
    ours = json.loads(_run("score-skill.py", str(agents), "--json", home=tmp_path).stdout)
    theirs = json.loads(_run("cli.py", "score", str(agents), "--json", home=tmp_path).stdout)
    assert "operational_coverage" in ours["dimensions"]
    assert ours["composite_score"] == pytest.approx(theirs["composite_score"], abs=0.05)


def test_an_explicit_non_utf8_suite_is_an_error_not_a_traceback(
        skill_with_binary_suite, tmp_path):
    """An explicit `--eval-suite` the user named should still stop the run, but
    with a message: UnicodeDecodeError is not a JSONDecodeError."""
    suite = skill_with_binary_suite.parent / "eval-suite.json"
    result = _run("text_gradient.py", str(skill_with_binary_suite),
                  "--eval-suite", str(suite), "--json", home=tmp_path)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr, result.stderr[-400:]
    assert "could not read eval-suite" in result.stderr


PROMPT = (
    "You are a helpful assistant.\n\nAlways cite sources.\n"
    "Never invent a citation.\n\nReturn JSON with a `result` key.\n"
)


def test_no_clarity_does_not_zero_a_headline_dimension(tmp_path):
    """The composite uses a full denominator, so a popped dimension counts as
    zero. On system_prompt clarity weighs 0.15, so the opt-out leaves it in."""
    prompt = tmp_path / "bot.prompt"
    prompt.write_text(PROMPT, encoding="utf-8")
    full = json.loads(_run("score-skill.py", str(prompt), "--json", home=tmp_path).stdout)
    opted = json.loads(_run("score-skill.py", str(prompt), "--json", "--no-clarity",
                            home=tmp_path).stdout)
    assert opted["composite_score"] == pytest.approx(full["composite_score"], abs=0.05)


@pytest.mark.parametrize("filename", ["SKILL.md", "CLAUDE.md", ".cursorrules"])
def test_no_clarity_still_drops_clarity_on_the_skill_md_family(filename, tmp_path):
    """Each format in the guard is pinned on its own: dropping one from the
    tuple would silently keep clarity for that format."""
    path = tmp_path / filename
    path.write_text(SKILL, encoding="utf-8")
    opted = json.loads(_run("score-skill.py", str(path), "--json", "--no-clarity",
                            home=tmp_path).stdout)
    assert "clarity" not in opted["dimensions"]


def test_weights_on_a_system_prompt_use_its_own_profile(tmp_path):
    """`--weights` must speak the format's dimensions, and leaving clarity and
    security out of the override must not delete two core 0.15 dimensions."""
    prompt = tmp_path / "bot.prompt"
    prompt.write_text(PROMPT, encoding="utf-8")
    full = json.loads(_run("score-skill.py", str(prompt), "--json", home=tmp_path).stdout)

    # clarity's own registry weight: the composite must not move.
    same = _run("score-skill.py", str(prompt), "--json", "--weights", "clarity=0.15",
                home=tmp_path)
    assert same.returncode == 0, same.stderr[-400:]
    same = json.loads(same.stdout)
    assert same["confidence"]["total"] == full["confidence"]["total"]
    assert same["composite_score"] == pytest.approx(full["composite_score"], abs=0.05)

    # A dimension only this profile has is accepted ...
    own = _run("score-skill.py", str(prompt), "--json", "--weights", "output_contract=1",
               home=tmp_path)
    assert own.returncode == 0, own.stderr[-400:]

    # ... and a skill.md name the profile does not score is rejected, not ignored.
    foreign = _run("score-skill.py", str(prompt), "--json", "--weights", "structure=0.3",
                   home=tmp_path)
    assert foreign.returncode == 1
    assert "unknown dimension 'structure'" in foreign.stderr


def test_text_output_handles_a_dimension_without_issues(tmp_path):
    """operational_coverage returns no `issues` key; the text report read it
    with `[]` and ended with `Error: 'issues'`."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text(BARE_AGENTS, encoding="utf-8")
    result = _run("score-skill.py", str(agents), home=tmp_path)
    assert result.returncode == 0, result.stderr[-400:]
    assert "Issues found" in result.stdout
