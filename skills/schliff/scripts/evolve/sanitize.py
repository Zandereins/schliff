"""Secret redaction for lineage output and error messages.

Prevents API keys and credentials from leaking into lineage files,
terminal output, or error messages.
"""
from __future__ import annotations

import re

# Patterns that indicate secrets — compiled for performance
_SECRET_PATTERNS = [
    (re.compile(r'sk-ant-[a-zA-Z0-9_-]{20,}'), '[REDACTED:anthropic-key]'),
    (re.compile(r'sk-[a-zA-Z0-9]{20,}'), '[REDACTED:openai-key]'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), '[REDACTED:aws-key]'),
    (re.compile(r'postgres://[^\s"\']+'), '[REDACTED:postgres-url]'),
    (re.compile(r'mongodb(\+srv)?://[^\s"\']+'), '[REDACTED:mongodb-url]'),
    (re.compile(r'redis://[^\s"\']+'), '[REDACTED:redis-url]'),
    (re.compile(r'mysql://[^\s"\']+'), '[REDACTED:mysql-url]'),
    (re.compile(r'ghp_[a-zA-Z0-9]{36}'), '[REDACTED:github-token]'),
    (re.compile(r'gho_[a-zA-Z0-9]{36}'), '[REDACTED:github-oauth]'),
    (re.compile(r'glpat-[a-zA-Z0-9_-]{20,}'), '[REDACTED:gitlab-token]'),
    (re.compile(r'xox[bporas]-[a-zA-Z0-9-]+'), '[REDACTED:slack-token]'),
    (re.compile(r'Bearer\s+[a-zA-Z0-9._-]{20,}'), '[REDACTED:bearer-token]'),
    (re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'), '[REDACTED:private-key]'),
]


def redact_secrets(text: str) -> str:
    """Redact known secret patterns from text."""
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def contains_secrets(text: str) -> list[str]:
    """Check if text contains secret-like patterns. Returns list of pattern names found."""
    found = []
    for pattern, replacement in _SECRET_PATTERNS:
        if pattern.search(text):
            found.append(replacement)
    return found


def redact_exception(exc: BaseException) -> str:
    """Produce a safe error message from an exception, redacting any secrets."""
    msg = str(exc)
    return redact_secrets(msg)
