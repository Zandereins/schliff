"""Tests for evolve.sanitize — secret redaction."""
from evolve.sanitize import contains_secrets, redact_exception, redact_secrets


class TestRedactSecrets:
    def test_anthropic_key(self):
        text = "key: sk-ant-api03-abcdefghijklmnopqrstuvwxyz"
        result = redact_secrets(text)
        assert "sk-ant-" not in result
        assert "[REDACTED:anthropic-key]" in result

    def test_openai_key(self):
        text = "key: sk-abcdefghijklmnopqrstuvwxyz1234567890"
        result = redact_secrets(text)
        assert "sk-abc" not in result
        assert "[REDACTED" in result

    def test_aws_key(self):
        text = "aws_key=AKIAIOSFODNN7EXAMPLE"
        result = redact_secrets(text)
        assert "AKIA" not in result

    def test_postgres_url(self):
        text = "db: postgres://user:pass@host:5432/db"
        result = redact_secrets(text)
        assert "postgres://" not in result
        assert "[REDACTED:postgres-url]" in result

    def test_github_token(self):
        text = "token: ghp_ABCDEFghijklmnopqrstuvwxyz1234567890"
        result = redact_secrets(text)
        assert "ghp_" not in result

    def test_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload"
        result = redact_secrets(text)
        assert "eyJ" not in result

    def test_private_key(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        result = redact_secrets(text)
        assert "PRIVATE KEY" not in result

    def test_no_secrets_unchanged(self):
        text = "This is a normal instruction file with no secrets."
        assert redact_secrets(text) == text

    def test_multiple_secrets(self):
        text = "key1: sk-ant-api03-abc123def456ghi789 key2: AKIAIOSFODNN7EXAMPLE"
        result = redact_secrets(text)
        assert "sk-ant-" not in result
        assert "AKIA" not in result

    def test_slack_token(self):
        text = "token: xoxb-123456789-abcdefghij"
        result = redact_secrets(text)
        assert "xoxb-" not in result

class TestContainsSecretsBasic:
    def test_detects_secret(self):
        found = contains_secrets("key: sk-ant-api03-abcdefghijklmnopqrst")
        assert len(found) > 0

    def test_no_secrets(self):
        found = contains_secrets("just normal text")
        assert found == []


class TestRedactAdditionalPatterns:
    def test_mongodb_url(self):
        text = "db: mongodb://user:pass@host:27017/mydb"
        result = redact_secrets(text)
        assert "mongodb://" not in result
        assert "[REDACTED:mongodb-url]" in result

    def test_mongodb_srv_url(self):
        text = "db: mongodb+srv://user:pass@cluster.mongodb.net/db"
        result = redact_secrets(text)
        assert "mongodb+srv://" not in result
        assert "[REDACTED:mongodb-url]" in result

    def test_redis_url(self):
        text = "cache: redis://user:pass@host:6379/0"
        result = redact_secrets(text)
        assert "redis://" not in result
        assert "[REDACTED:redis-url]" in result

    def test_mysql_url(self):
        text = "db: mysql://user:pass@host:3306/mydb"
        result = redact_secrets(text)
        assert "mysql://" not in result
        assert "[REDACTED:mysql-url]" in result

    def test_github_oauth_token(self):
        text = "token: gho_ABCDEFghijklmnopqrstuvwxyz1234567890"
        result = redact_secrets(text)
        assert "gho_" not in result
        assert "[REDACTED:github-oauth]" in result

    def test_gitlab_token(self):
        text = "token: glpat-abcdefghijklmnopqrstuv"
        result = redact_secrets(text)
        assert "glpat-" not in result
        assert "[REDACTED:gitlab-token]" in result

    def test_private_key_without_rsa(self):
        text = "-----BEGIN PRIVATE KEY-----\nMIIE..."
        result = redact_secrets(text)
        assert "PRIVATE KEY" not in result

    def test_empty_string(self):
        assert redact_secrets("") == ""

    def test_very_long_input_performance(self):
        """Verify redaction doesn't hang on large inputs."""
        import time
        large = "normal text " * 10000
        start = time.time()
        redact_secrets(large)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Redaction took {elapsed:.1f}s on 120KB input"


class TestContainsSecrets:
    def test_detects_secret(self):
        found = contains_secrets("key: sk-ant-api03-abcdefghijklmnopqrst")
        assert len(found) > 0

    def test_no_secrets(self):
        found = contains_secrets("just normal text")
        assert found == []

    def test_returns_specific_pattern_names(self):
        found = contains_secrets("key: sk-ant-api03-abcdefghijklmnopqrst also postgres://user:pass@host/db")
        assert "[REDACTED:anthropic-key]" in found
        assert "[REDACTED:postgres-url]" in found

    def test_empty_string(self):
        assert contains_secrets("") == []


class TestRedactException:
    def test_redacts_exception_message(self):
        exc = ValueError("API failed with key sk-ant-api03-secretkeyhere123456")
        result = redact_exception(exc)
        assert "sk-ant-" not in result
        assert "REDACTED" in result
