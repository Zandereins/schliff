"""Redaction gaps in `evolve/sanitize.py` (F4, ADR 0013).

Redaction has the opposite error cost to detection: a false positive here is
harmless, a false negative sends a credential to a model provider. So this set
may be aggressive where `scoring/credentials.py` must be precise.
"""
import pytest

from evolve.sanitize import redact_secrets


class TestGitHubTokenCoverage:
    """The shipped patterns bound at exactly 36 and cover only ghp_ and gho_."""

    # Bare prose, deliberately: an assignment like `token: <value>` is caught by
    # the generic name=value rule at sanitize.py:41 whatever the prefix, so it
    # would pass without any vendor pattern at all and prove nothing.
    @pytest.mark.parametrize("prefix", ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"])
    def test_every_github_prefix_is_redacted(self, prefix):
        token = prefix + "9dK2mNqR7vT4wX1zB6cF8gH3jL5pQ"

        assert token not in redact_secrets(f"Authenticate with {token} and retry.")

    def test_a_token_shorter_than_36_is_still_redacted(self):
        token = "ghp_" + "9dK2mNqR7vT4wX1zB6cF"  # 20 chars after the prefix

        assert token not in redact_secrets(f"Authenticate with {token} and retry.")


class TestOdbcPassword:
    def test_odbc_pwd_spelling_is_redacted(self):
        secret = "Sup3rSecretValue12345"

        out = redact_secrets(f"DRIVER={{ODBC}};Pwd={secret};")

        assert secret not in out

    def test_the_conventional_pwd_working_directory_survives(self):
        # All-caps PWD is the shell's working-directory variable, not a secret.
        text = "Run the build from $PWD before deploying."

        assert redact_secrets(text) == text
