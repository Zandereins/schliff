"""Regression tests for the ten findings of the 2026-08-07 code review.

Each test was confirmed red against the branch before the corresponding fix.
The theme of the review was a gate that fails in both directions: it fired on
published example tokens, and it stayed silent when it could not read the file.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

import verify as verify_mod
from eval_split import split_eval_suite
from evolve.sanitize import redact_secrets
from scoring.credentials import scan_credentials

CLI_PATH = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "cli.py")
LIVE_KEY = "AKIAZ3F7Q2W9B1N4K6XD"

JWT_IO_SAMPLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


class TestNoFalsePositiveOnPublishedTokens:
    """Finding 3. A JWT's shape says nothing about whether it is secret: the
    jwt.io sample and a Supabase `anon` key are public by design and appear in
    real instruction files. A gate with no opt-out cannot fire on them."""

    def test_jwt_io_sample_is_not_a_finding(self):
        assert scan_credentials(f"Example token: {JWT_IO_SAMPLE}\n") == []

    def test_supabase_anon_key_is_not_a_finding(self):
        anon = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJpc3MiOiJzdXBhYmFzZSIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzAwMDAwMDAwfQ"
            ".7mQqM4vRtY2wX9zB6cF8gH3jL5pQaScDeFgHiJkLmNo"
        )
        assert scan_credentials(f"SUPABASE_ANON_KEY={anon}\n") == []

    def test_a_real_vendor_key_still_fires(self):
        assert scan_credentials(f"key {LIVE_KEY}\n") != []


class TestScanIsLinear:
    """Finding 10. The scan runs on attacker-controlled content in CI."""

    def test_many_findings_do_not_take_quadratic_time(self):
        payload = "\n".join(f"AKIA3XZQ7RBN2WKPLMT{chr(65 + i % 26)}" for i in range(20000))

        started = time.perf_counter()
        findings = scan_credentials(payload)
        elapsed = time.perf_counter() - started

        assert len(findings) == 20000
        # Measured at 2.8s before the fix on this input; linear lands far under.
        assert elapsed < 1.0, f"{len(payload)} bytes took {elapsed:.2f}s"

    def test_line_numbers_stay_correct_after_the_rewrite(self):
        content = "a\nb\nc\n" + f"key {LIVE_KEY}\n" + "d\n" + f"key {LIVE_KEY}\n"

        assert [f["line"] for f in scan_credentials(content)] == [4, 6]


class TestVerifyCannotFailOpen:
    """Finding 1. `read_skill_safe` raising must never read as 'no credentials'."""

    def test_oversize_skill_does_not_pass_the_gate(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: x\ndescription: d\n---\n\n# x\n\n"
            f"AWS key: {LIVE_KEY}\n" + ("filler line\n" * 140000),
            encoding="utf-8",
        )

        verdict = verify_mod.run_verify(
            str(skill), min_score=0.0, history_path=str(tmp_path / "h.jsonl")
        )

        assert verdict["exit_code"] != 0, (
            "a file that cannot be scanned must not pass the credential gate"
        )


class TestVerifyMessagePairsVendorWithLine:
    """Finding 7. Sending an operator to the wrong line risks rotating the
    wrong credential."""

    def test_two_vendors_are_reported_as_pairs(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: x\ndescription: d\n---\n"
            f"AWS {LIVE_KEY}\n"
            "filler\n"
            "ANT sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWx\n",
            encoding="utf-8",
        )

        verdict = verify_mod.run_verify(
            str(skill), min_score=0.0, history_path=str(tmp_path / "h.jsonl")
        )
        message = verdict["message"]

        assert "aws_access_key at line 5" in message
        assert "anthropic_api_key at line 7" in message


class TestScoreFailsClosedOnAnUnreadableFile:
    """The cli.py half of finding 2 did NOT reproduce: `score` already exits 1
    with an error and emits no JSON, so no consumer can read an empty
    `credentials` list as an all-clear. Pinned here so a later refactor that
    makes `score` emit JSON on a failed read has to confront this."""

    def test_oversize_file_emits_no_json_at_all(self, tmp_path):
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: x\ndescription: d\n---\n\n# x\n\n"
            f"AWS key: {LIVE_KEY}\n" + ("filler line\n" * 140000),
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, CLI_PATH, "score", str(skill), "--json"],
            capture_output=True, text=True, timeout=120,
        )

        assert result.returncode == 1
        assert result.stdout.strip() == ""
        assert "could not read" in result.stderr


class TestSplitKeepsUnlabelledCases:
    """Finding 4. One `split` label must not delete the other 43 cases."""

    def test_partial_labelling_keeps_the_rest_on_the_train_side(self):
        suite = {
            "triggers": [{"prompt": f"p{i}"} for i in range(43)]
            + [{"prompt": "held", "split": "test"}]
        }

        train, val, leaked = split_eval_suite(suite)

        assert len(train["triggers"]) == 43, "unlabelled cases must not vanish"
        assert [c["prompt"] for c in val["triggers"]] == []
        assert leaked is True, "an empty val side holds nothing out"

    def test_explicit_labels_still_partition(self):
        suite = {"triggers": [{"prompt": "a", "split": "train"},
                              {"prompt": "b", "split": "val"}]}

        train, val, leaked = split_eval_suite(suite)

        assert [c["prompt"] for c in train["triggers"]] == ["a"]
        assert [c["prompt"] for c in val["triggers"]] == ["b"]
        assert leaked is False


class TestLeakFlagIsHonest:
    """Finding 6. `holdout_leaked` False must mean something was held out."""

    @pytest.mark.parametrize("suite", [
        {"triggers": []},
        {"name": "no populations at all"},
        {},
    ])
    def test_a_suite_that_holds_nothing_out_is_flagged(self, suite):
        assert split_eval_suite(suite)[2] is True


class TestPwdRedactionDoesNotEatShell:
    """Finding 9. Over-redaction destroys the prompt it is protecting."""

    def test_lowercase_shell_assignment_survives(self):
        text = "export pwd=/Users/franz/projects/schliff/build"

        assert redact_secrets(text) == text

    def test_odbc_pwd_is_still_redacted(self):
        secret = "Sup3rSecretValue12345"

        assert secret not in redact_secrets(f"DRIVER={{ODBC}};Pwd={secret};")
