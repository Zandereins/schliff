"""Tests for wiring the credential detector into schliff's surfaces.

ADR 0011 — score-neutral: the composite is bit-identical with and without a
credential in the file. Still in force.
ADR 0019 — every surface reports and none gates: no finding changes an exit
code anywhere. The risk this file guards is that removing the gate also removes
the finding from sight, which would leave the feature with no purpose at all.
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


class TestVerifyReportsWithoutGating:
    """ADR 0019: `verify` shows the finding and exits on the threshold alone."""

    def test_verify_exits_zero_with_a_credential_present(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("verify", skill, "--min-score", "0")

        assert result.returncode == 0, (
            "a credential no longer fails the build; the classification is "
            "undecidable and the false positive is not fixable by the person it hits"
        )

    def test_verify_still_shows_vendor_and_line(self, tmp_path):
        """The finding must survive the removal of the gate.

        Deleting the gate by deleting the branch would take the only place
        `verify` ever mentions a credential with it, and the feature would exit
        the release silently.
        """
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("verify", skill, "--min-score", "0")
        output = result.stdout + result.stderr

        assert "aws_access_key" in output
        assert "17" in output

    def test_verify_still_fails_on_the_threshold(self, tmp_path):
        """The other gate is untouched — removing one must not remove both."""
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("verify", skill, "--min-score", "100")

        assert result.returncode == 1

    def test_verify_says_nothing_about_credentials_on_a_clean_file(self, tmp_path):
        skill = _write_skill(tmp_path, "Set `AWS_ACCESS_KEY_ID` in your environment.")

        result = _run_cli("verify", skill, "--min-score", "0")

        assert result.returncode == 0, result.stderr
        assert "credential" not in (result.stdout + result.stderr).lower()

    def test_verify_never_echoes_the_value(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("verify", skill, "--min-score", "0")

        assert LIVE_KEY not in result.stdout + result.stderr


class TestReportingSurfaces:
    """ADR 0014: reporting surfaces display the finding and never change their
    exit code. A human running `score` must see it too — the JSON branch is for
    machines, and a leak that only machines can see helps nobody.
    """

    def test_human_score_output_shows_vendor_and_line(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("score", skill)

        assert "aws_access_key" in result.stdout
        assert "17" in result.stdout
        assert LIVE_KEY not in result.stdout

    def test_human_score_still_exits_zero(self, tmp_path):
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("score", skill)

        assert result.returncode == 0, "score reports, it does not gate"

    def test_score_does_not_promise_a_gate_that_no_longer_exists(self, tmp_path):
        """The renderer used to tell the reader that `verify` would fail on this.

        Instructions that outlive the behaviour they describe are the exact
        follow-on damage that dominated the three review passes: the rule was
        changed in one module and its neighbouring sentence was left standing.
        """
        skill = _write_skill(tmp_path, f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        out = _run_cli("score", skill).stdout.lower()

        assert "verify" not in out or "fails" not in out
        assert "--min-score" not in out

    def test_clean_file_says_nothing_about_credentials(self, tmp_path):
        skill = _write_skill(tmp_path, "Set `AWS_ACCESS_KEY_ID` in your environment.")

        result = _run_cli("score", skill)

        assert "credential" not in result.stdout.lower()

    def test_doctor_json_reports_the_finding_without_gating(self, tmp_path):
        _write_skill(tmp_path / "leaky", f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("doctor", "--skill-dirs", str(tmp_path), "--json")

        assert result.returncode == 0, "doctor reports on other people's files"
        report = json.loads(result.stdout)
        entries = [r for r in report["results"] if r.get("credentials")]
        assert len(entries) == 1
        assert entries[0]["credentials"] == [{"vendor": "aws_access_key", "line": 17}]
        assert LIVE_KEY not in result.stdout

    def test_doctor_human_output_flags_the_skill(self, tmp_path):
        _write_skill(tmp_path / "leaky", f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        result = _run_cli("doctor", "--skill-dirs", str(tmp_path))

        assert "credential" in result.stdout.lower()
        assert "aws_access_key" in result.stdout
        assert LIVE_KEY not in result.stdout

    def test_every_human_surface_hedges_the_same_way(self, tmp_path):
        """One wording across surfaces, because one claim is being made.

        `score` and `verify` were changed to say "possible"; `doctor` kept the
        confident noun for a release. It reads other people's files, where an
        unhedged claim is least defensible.
        """
        skill = _write_skill(tmp_path / "leaky", f"Set `AWS_ACCESS_KEY_ID={LIVE_KEY}`.")

        surfaces = {
            "score": _run_cli("score", skill).stdout,
            "verify": _run_cli("verify", skill, "--min-score", "0").stdout,
            "doctor": _run_cli("doctor", "--skill-dirs", str(tmp_path)).stdout,
        }

        for name, out in surfaces.items():
            assert "possible credential" in out.lower(), f"{name} states it as a fact"
