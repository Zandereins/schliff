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
    ])
    def test_vendor_token_is_detected(self, vendor, token):
        findings = scan_credentials(f"credential: {token}\n")

        assert [f["vendor"] for f in findings] == [vendor]

    def test_jwts_are_deliberately_not_detected(self):
        """A JWT's shape does not say whether it is secret.

        The jwt.io sample and Supabase's `anon` key are public by design and
        appear in real instruction files; nothing structural separates them
        from a service key. Under a hard-fail gate with no opt-out, an
        undecidable class must not fire. Redaction keeps its JWT pattern,
        where a false positive costs nothing.
        """
        jwt = (
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0"
            ".dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        )

        assert scan_credentials(f"credential: {jwt}\n") == []


class TestPlaceholdersNeverFire:
    """A token that names itself a stand-in produces no finding (ADR 0020).

    Marker words are all that is left of the placeholder test, and they are the
    only part that never cost a real key: `example`, `your`, `replace` and the
    rest do not occur in issued credentials.
    """

    @pytest.mark.parametrize("placeholder", [
        "sk-ant-REPLACE_ME_WITH_YOUR_KEY",
        "sk-ant-YOUR_API_KEY_GOES_HERE_1",
        "sk-ant-api03-EXAMPLE_KEY_NOT_REAL",
        "AKIAIOSFODNN7EXAMPLE",
    ])
    def test_placeholder_produces_no_finding(self, placeholder):
        assert scan_credentials(f"ANTHROPIC_API_KEY={placeholder}\n") == []


class TestTheAcceptedFalsePositives:
    """The price of dropping the repeated-run heuristic, pinned so it is a
    decision on record rather than a surprise (ADR 0020).

    `sk-ant-xxxxxxxx` is documentation and now produces a finding, because the
    same rule that suppressed it also suppressed `AKIA0000TUVWXY3BCDEF`, which
    is a legal AWS key. Under ADR 0019 this costs a line of output; before it,
    the reverse error cost an unseen credential.
    """

    def test_a_repeated_character_placeholder_now_fires(self):
        assert scan_credentials("ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx\n") != []

    def test_and_the_real_key_it_used_to_hide_fires_too(self):
        assert [f["vendor"] for f in scan_credentials("AKIA0000TUVWXY3BCDEF\n")] == [
            "aws_access_key"
        ]


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
