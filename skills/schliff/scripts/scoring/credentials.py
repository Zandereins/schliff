"""Deterministic credential detection.

Score-neutral and gate-effective (ADR 0011): this module never contributes to a
score. It is deliberately NOT a scoring dimension and must never be added to
``scoring.security._CATEGORIES`` — for ``system_prompt`` that dimension is
always-on and weighted, so a category there would move a published composite.

A finding carries the vendor and the line, never the matched value (ADR 0014).
"""
from __future__ import annotations

import bisect
import re

# (vendor, pattern). Each requires the vendor prefix AND the exact shape that
# vendor issues, so a placeholder cannot satisfy it (ADR 0012).
_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    # `sk-` is Anthropic's prefix too; the lookahead keeps one token from
    # producing two findings and keeps the vendor label honest. No BARE hyphens
    # after the prefix: an earlier `[A-Za-z0-9_-]{20,}` matched kebab-case prose
    # such as `sk-production-cluster-namespace`, which failed a third party's
    # build with no way to suppress it. Real keys are `sk-<alnum>` or one known
    # segment (`proj-`, `svcacct-`, `admin-`) followed by alnum.
    (
        "openai_api_key",
        re.compile(r"\bsk-(?!ant-)(?:proj-|svcacct-|admin-)?[A-Za-z0-9_]{20,}"),
    ),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"\bAIza[A-Za-z0-9_-]{31,}")),
    # No JWT pattern. A JWT's shape says nothing about whether it is secret:
    # the jwt.io sample and Supabase's `anon` key are public by design and appear
    # in real instruction files, and no structural test separates them from a
    # service key. Under a hard-fail gate with no opt-out (ADR 0011), a class we
    # cannot decide is a class we must not fire on. Redaction keeps its JWT
    # pattern — there a false positive is free (ADR 0013).
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
    # Line starts once, then a binary search per finding. Counting newlines per
    # match made the scan quadratic, and the content comes from a file a CI
    # caller does not control: 20k findings in 420 KB took 2.8s that way.
    line_starts = [0]
    line_starts.extend(m.end() for m in re.finditer(r"\n", content))

    findings: list[dict] = []
    for vendor, pattern in _PATTERNS:
        for match in pattern.finditer(content):
            if _is_placeholder(match.group(0)):
                continue
            findings.append({
                "vendor": vendor,
                "line": bisect.bisect_right(line_starts, match.start()),
            })
    return findings
