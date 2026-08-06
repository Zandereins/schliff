"""Deterministic credential detection.

Score-neutral and gate-effective (ADR 0011): this module never contributes to a
score. It is deliberately NOT a scoring dimension and must never be added to
``scoring.security._CATEGORIES`` — for ``system_prompt`` that dimension is
always-on and weighted, so a category there would move a published composite.

A finding carries the vendor and the line, never the matched value (ADR 0014).
"""
from __future__ import annotations

import re

# (vendor, pattern). Each requires the vendor prefix AND the exact shape that
# vendor issues, so a placeholder cannot satisfy it (ADR 0012).
_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    # `sk-` is Anthropic's prefix too; the lookahead keeps one token from
    # producing two findings and keeps the vendor label honest.
    ("openai_api_key", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"\bAIza[A-Za-z0-9_-]{31,}")),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    ),
)


# Words a real credential does not contain but a documentation placeholder does.
# Matching one is decisive: precision is worth more than recall here, because a
# false positive turns a third party's green build red (ADR 0012).
_PLACEHOLDER_MARKERS = (
    "example", "replace", "your", "here", "placeholder", "sample",
    "dummy", "todo", "fixme", "changeme", "insert", "redacted", "notreal",
)

# Four or more identical characters in a row — `sk-ant-xxxxxxxx`, `AKIA0000…`.
_REPEATED_RUN = re.compile(r"(.)\1{3,}")


def _is_placeholder(value: str) -> bool:
    """True when the token announces itself as a stand-in rather than a secret."""
    lowered = value.lower()
    if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
        return True
    return bool(_REPEATED_RUN.search(value))


def scan_credentials(content: str) -> list[dict]:
    """Return one finding per structurally valid vendor token in ``content``.

    Each finding is ``{"vendor": str, "line": int}`` with 1-based line numbers.
    The matched value is deliberately absent — see ADR 0014.
    """
    findings: list[dict] = []
    for vendor, pattern in _PATTERNS:
        for match in pattern.finditer(content):
            if _is_placeholder(match.group(0)):
                continue
            findings.append({
                "vendor": vendor,
                "line": content.count("\n", 0, match.start()) + 1,
            })
    return findings
