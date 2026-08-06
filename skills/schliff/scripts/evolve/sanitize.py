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
    # All five GitHub token classes, variable length. The previous pair bound at
    # exactly 36 and covered only ghp_/gho_, so a shorter token or a ghu_/ghs_/ghr_
    # one survived unless the surrounding text happened to trip the generic
    # assignment catcher below. Redaction may over-reach; a miss here reaches a
    # model provider (ADR 0013).
    (re.compile(r'gho_[a-zA-Z0-9]{20,}'), '[REDACTED:github-oauth]'),
    (re.compile(r'gh[pusr]_[a-zA-Z0-9]{20,}'), '[REDACTED:github-token]'),
    (re.compile(r'glpat-[a-zA-Z0-9_-]{20,}'), '[REDACTED:gitlab-token]'),
    (re.compile(r'xox[bporas]-[a-zA-Z0-9-]+'), '[REDACTED:slack-token]'),
    (re.compile(r'Bearer\s+[a-zA-Z0-9._-]{20,}'), '[REDACTED:bearer-token]'),
    (re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'), '[REDACTED:private-key]'),
    (re.compile(r'AIza[a-zA-Z0-9_-]{35}'), '[REDACTED:google-api-key]'),
    # ODBC abbreviates Password as Pwd. The lookbehind keeps the conventional
    # all-caps $PWD working-directory variable intact, per SkillOpt staging.py.
    (re.compile(r'(?<![A-Za-z0-9])(Pwd|pwd)\s*=\s*[^\s;"\']{8,}'), r'\1=[REDACTED:db-pass]'),
    (re.compile(r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'), '[REDACTED:jwt]'),
    # Generic assignment catcher — keep last so vendor-specific patterns win.
    # Matches keyword-bearing identifiers (e.g. AWS_SECRET_ACCESS_KEY, db_password,
    # client_secret) followed by a := assignment and a high-entropy value.
    #
    # The identifier prefix is bounded ({0,40}) so a long alphanumeric run that
    # never completes a match cannot drive catastrophic backtracking (ReDoS); the
    # value is length-capped ({16,200}) for the same reason. Group 1 captures the
    # name + separator + optional OPENING quote so the replacement preserves them
    # (no unbalanced quote) and redacts only the secret value. The bare "key"
    # alternative is deliberately excluded so prose like "primary key:", "turkey=",
    # or "monkey:" is not falsely redacted — vendor names use api_key/access_key.
    (re.compile(
        r'(?i)('
        r'\b[a-z0-9_]{0,40}'
        r'(?:client[_-]?secret|secret|password|passwd|api[_-]?key|access[_-]?key|auth[_-]?token|token)'
        r'["\']?'          # optional closing quote on the key (JSON/quoted-key form)
        r'\s*[:=]\s*'
        r'["\']?'          # optional opening quote on the value
        r')'
        r'[a-zA-Z0-9/+=_-]{16,200}'),
     r'\1[REDACTED:credential]'),
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
