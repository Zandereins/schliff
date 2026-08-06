"""The loop derives edits from `train` and judges them on `val` (ADR 0015).

When the two sides are not disjoint the run must say so, because a delta from a
non-disjoint comparison is not evidence of anything.
"""
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("auto_improve", SCRIPTS / "auto-improve.py")
auto_improve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auto_improve)

SKILL = """\
---
name: deploy-helper
description: Deploys the service. Use when asked to deploy or ship.
---

# deploy-helper

Run `make deploy`.
"""


def _suite(labelled: bool):
    def case(name, split):
        c = {"prompt": name, "should_trigger": True}
        if labelled:
            c["split"] = split
        return c
    return {"triggers": [case("a", "train"), case("b", "val")]}


def _write(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text(SKILL, encoding="utf-8")
    (tmp_path / "eval-suite.json").write_text("{}", encoding="utf-8")
    return str(p)


def test_summary_reports_a_clean_split(tmp_path, monkeypatch):
    skill = _write(tmp_path)
    monkeypatch.setattr(auto_improve, "load_eval_suite", lambda _p: _suite(labelled=True))

    summary = auto_improve.run_auto_improve(skill, max_iterations=1, dry_run=True)

    assert summary["holdout_leaked"] is False


def test_summary_flags_an_unlabelled_suite(tmp_path, monkeypatch):
    skill = _write(tmp_path)
    monkeypatch.setattr(auto_improve, "load_eval_suite", lambda _p: _suite(labelled=False))

    summary = auto_improve.run_auto_improve(skill, max_iterations=1, dry_run=True)

    assert summary["holdout_leaked"] is True
