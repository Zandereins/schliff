"""Unit tests for deterministic credential detection (ADR 0011-0016).

The detector is score-neutral and gate-effective: it never changes a score, and
a finding never carries the matched value — only the vendor and the line.
"""
import time

import pytest

from scoring.credentials import _PATTERNS, scan_credentials


class TestFindingPayload:
    """A finding carries vendor + line, and nothing else (ADR 0014)."""

    def test_reports_aws_key_with_vendor_and_line(self):
        content = (
            "# Setup\n"
            "\n"
            "Export your key:\n"
            "\n"
            "```bash\n"
            "export AWS_ACCESS_KEY_ID=AKIA3XZQ7RBN2WKPLMTV\n"
            "```\n"
        )

        findings = scan_credentials(content)

        assert len(findings) == 1
        assert findings[0]["vendor"] == "aws_access_key"
        assert findings[0]["line"] == 6

    def test_reports_anthropic_key(self):
        content = "Set ANTHROPIC_API_KEY=sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWx in your env.\n"

        findings = scan_credentials(content)

        assert len(findings) == 1
        assert findings[0]["vendor"] == "anthropic_api_key"

    def test_finding_never_carries_the_matched_value(self):
        secret = "sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWx"

        findings = scan_credentials(f"key: {secret}\n")

        assert findings, "expected a finding to assert against"
        rendered = repr(findings)
        assert secret not in rendered
        assert "AbCdEfGh" not in rendered, "no fragment of the value may survive"


class TestVendorCoverage:
    """Each supported vendor is recognised by its own issued shape."""

    @pytest.mark.parametrize("vendor,token", [
        ("github_token", "ghp_9dK2mNqR7vT4wX1zB6cF8gH3jL5pQ"),
        ("github_token", "gho_9dK2mNqR7vT4wX1zB6cF8gH3jL5pQ"),
        ("github_token", "ghs_9dK2mNqR7vT4wX1zB6cF8gH3jL5pQ"),
        ("slack_token", "xoxb-2417-9821-A9dK2mNqR7vT4wX1zB6c"),
        ("google_api_key", "AIzaSyD3kL9mN2pQ7rT4vW8xZ1bC6fG5hJ0"),
        ("openai_api_key", "sk-proj-Nx7Qm2Kd9dK2mNqR7vT4wX1zB6cF8gH3"),
        (
            "jwt",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0"
            ".dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        ),
    ])
    def test_vendor_token_is_detected(self, vendor, token):
        findings = scan_credentials(f"credential: {token}\n")

        assert [f["vendor"] for f in findings] == [vendor]


class TestPlaceholdersNeverFire:
    """The discriminator is the value, not the location (ADR 0012).

    A false positive here turns somebody else's green build red, so a shape that
    announces itself as a placeholder must never produce a finding.
    """

    @pytest.mark.parametrize("placeholder", [
        "sk-ant-REPLACE_ME_WITH_YOUR_KEY",
        "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx",
        "sk-ant-YOUR_API_KEY_GOES_HERE_1",
        "sk-ant-api03-EXAMPLE_KEY_NOT_REAL",
        "AKIAIOSFODNN7EXAMPLE",
    ])
    def test_placeholder_produces_no_finding(self, placeholder):
        assert scan_credentials(f"ANTHROPIC_API_KEY={placeholder}\n") == []


class TestReDoSBound:
    """ADR 0013: first-party patterns prove ReDoS safety by timing, not by the
    `validate_regex_complexity` heuristic (which guards eval-suite regexes and
    false-positives on a pattern schliff already ships).

    These patterns run over untrusted file content, so a catastrophic one is a
    denial of service on any CI that gates with schliff.
    """

    # Long runs of each pattern's own alphabet, plus near-miss prefixes: the
    # shapes that make a backtracking engine explore the most.
    PATHOLOGICAL = (
        "AKIA" + "A" * 20000,
        "sk-ant-" + "a" * 20000,
        "sk-" + "a" * 20000,
        "ghp_" + "a" * 20000,
        "xoxb-" + "a-" * 10000,
        "AIza" + "a" * 20000,
        "eyJ" + "a" * 20000,
        "eyJ" + ("a" * 100 + ".") * 200,
        ("AKIA" + "sk-ant-" + "ghp_") * 2000,
    )

    # Generous: a catastrophic pattern does not take 1s, it takes minutes. The
    # margin is what keeps this from flaking on a loaded CI runner.
    BUDGET_SECONDS = 1.0

    @pytest.mark.parametrize("payload", PATHOLOGICAL)
    def test_every_pattern_completes_within_budget(self, payload):
        for vendor, pattern in _PATTERNS:
            started = time.perf_counter()
            pattern.findall(payload)
            elapsed = time.perf_counter() - started
            assert elapsed < self.BUDGET_SECONDS, (
                f"{vendor} took {elapsed:.3f}s on a {len(payload)}-char payload"
            )

    def test_full_scan_completes_within_budget(self):
        payload = "\n".join(self.PATHOLOGICAL)

        started = time.perf_counter()
        scan_credentials(payload)
        elapsed = time.perf_counter() - started

        assert elapsed < self.BUDGET_SECONDS, f"scan took {elapsed:.3f}s"
