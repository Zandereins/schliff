"""Tests for wiring the credential detector into schliff's surfaces.

ADR 0011 — score-neutral: the composite is bit-identical with and without a
credential in the file.
ADR 0014 — gate-effective: `verify` exits non-zero on a finding, independently
of `--min-score`; reporting surfaces display it and never change their exit code.
"""
import json
import subprocess
import sys
from pathlib import Path

CLI_PATH = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "cli.py")

# Structurally valid, and free of any placeholder marker.
LIVE_KEY = "AKIA3XZQ7RBN2WKPLMTV"

SKILL_TEMPLATE = """\
---
name: deploy-helper
description: >
  Deploys the service to staging and production. Use when the user asks to
  deploy, ship, release or roll back. Trigger phrases: "deploy to staging",
  "ship it", "roll back the release". Do NOT use for local dev servers.
---

# deploy-helper

## Commands

- `make deploy` — deploy to staging

## Configuration

{config}

## Edge cases

- Deploy fails mid-rollout: re-run `make deploy`; it is idempotent.
"""


def _run_cli(*args, timeout=60):
    return subprocess.run(
        [sys.executable, CLI_PATH, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _write_skill(tmp_path: Path, config: str) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "SKILL.md"
    p.write_text(SKILL_TEMPLATE.format(config=config), encoding="utf-8")
    return str(p)


class TestScoreJsonCarriesTheFinding:
    """`score --json` is the Action's only data source (ADR 0014)."""

    def test_json_reports_vendor_and_line(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("score", skill, "--json")

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        # Line 17 of the rendered file — verified against the file, not counted
        # by eye. A wrong line number is worse than no finding (ADR 0016).
        assert payload["credentials"] == [{"vendor": "aws_access_key", "line": 17}]

    def test_json_omits_nothing_when_clean(self, tmp_path):
        skill = _write_skill(tmp_path, "Set `AWS_ACCESS_KEY_ID` in your environment.")

        result = _run_cli("score", skill, "--json")

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["credentials"] == []

    def test_finding_never_carries_the_value(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("score", skill, "--json")

        assert LIVE_KEY not in result.stdout, "the matched value leaked into score output"


class TestScoreNeutrality:
    """ADR 0011: the composite is bit-identical with and without a credential.

    This is a guard, not a driver. It fails the day someone folds the detector
    into `security._CATEGORIES` — which is exactly the silent break ADR 0011
    exists to prevent, and it would surface first on `system_prompt`, where the
    security dimension is always-on and weighted.
    """

    def test_composite_is_unchanged_by_a_credential(self, tmp_path):
        clean = _write_skill(tmp_path / "clean", "Set `AWS_ACCESS_KEY_ID` in your environment.")
        dirty = _write_skill(tmp_path / "dirty", f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        clean_payload = json.loads(_run_cli("score", clean, "--json").stdout)
        dirty_payload = json.loads(_run_cli("score", dirty, "--json").stdout)

        assert dirty_payload["credentials"], "fixture must actually contain a credential"
        assert dirty_payload["composite_score"] == clean_payload["composite_score"]
        assert dirty_payload["dimensions"] == clean_payload["dimensions"]


class TestVerifyGate:
    """ADR 0014: `verify` fails on a credential regardless of the threshold."""

    def test_verify_fails_even_with_the_threshold_satisfied(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("verify", skill, "--min-score", "0")

        assert result.returncode != 0, "a credential must fail the gate at any threshold"

    def test_verify_passes_a_clean_file_at_the_same_threshold(self, tmp_path):
        skill = _write_skill(tmp_path, "Set `AWS_ACCESS_KEY_ID` in your environment.")

        result = _run_cli("verify", skill, "--min-score", "0")

        assert result.returncode == 0, result.stderr

    def test_verify_never_echoes_the_value(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("verify", skill, "--min-score", "0")

        assert LIVE_KEY not in result.stdout + result.stderr
