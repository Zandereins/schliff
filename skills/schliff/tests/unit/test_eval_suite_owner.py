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
