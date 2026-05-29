"""Plumbing tests for the Judge v0 smoke-test harness (scoring/../judge/judge_v0.py).

Does NOT test judge quality (that needs the real API + a key) — only that the
harness loads labels, assembles leave-one-out prompts, votes, computes agreement,
and writes a log, in --mock mode.
"""
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS / "judge"))

import judge_v0  # noqa: E402


def test_build_system_includes_rubric_and_leave_one_out_anchor():
    anchors = [{"label": "PASS", "specimen": "x-skill", "critique": "has a checkable test"}]
    s = judge_v0.build_system("verifiable_success", anchors)
    assert "verifiable_success" in s
    assert "[PASS] x-skill: has a checkable test" in s


def test_dim_rubrics_present():
    assert set(judge_v0.RUBRICS) == {"verifiable_success", "assumption_completeness"}


def test_run_mock_smoke(tmp_path):
    labels = judge_v0.REPO_ROOT / "benchmarks/corpus/v1/phase1-calibration/labels-v0.jsonl"
    out = tmp_path / "results.jsonl"
    rc = judge_v0.run(labels, judge_v0.MODEL_DEFAULT, n=3, temp=0.3, mock=True, out_path=out)
    assert rc == 0

    res = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(res) == 8  # 5 B + 3 C active (3 anchors excluded via status=excluded; see labels-v0.jsonl)
    for r in res:
        assert r["judge"] in ("PASS", "FAIL")
        assert r["human"] in ("PASS", "FAIL")
        assert isinstance(r["agree"], bool)
        assert len(r["prompt_sha"]) == 12
