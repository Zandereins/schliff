"""Deterministic credential detection.

Score-neutral (ADR 0011) and reported rather than gated (ADR 0019): this module
never contributes to a score and never decides an exit code. It is deliberately
NOT a scoring dimension and must never be added to ``scoring.security._CATEGORIES``
— for ``system_prompt`` that dimension is always-on and weighted, so a category
there would move a published composite.

**What a finding claims:** that a string has the shape of a given vendor's
credential. Not that it is one. Shape does not separate a live key from a
documentation example (ADR 0020), which is why nothing here gates.

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
    # producing two findings and keeps the vendor label honest. Hyphens are
    # allowed inside the body only BEHIND a known key segment (`proj-`,
    # `svcacct-`, `admin-`), which is the form OpenAI has issued since 2024;
    # after a bare `sk-` they matched kebab-case prose such as
    # `sk-production-cluster-namespace` and failed a third party's build
    # (ADR 0020).
    (
        "openai_api_key",
        re.compile(
            r"\bsk-(?!ant-)(?:(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}"
            r"|[A-Za-z0-9_]{20,})"
        ),
    ),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"\bAIza[A-Za-z0-9_-]{31,}")),
    # No JWT pattern. A JWT's shape says nothing about whether it is secret:
    # the jwt.io sample and Supabase's `anon` key are public by design and appear
    # in real instruction files, and no structural test separates them from a
    # service key. The reason outlived the gate that first motivated it: a class
    # nothing can decide is a class this scan stays out of, because a report
    # that fires on every published example token is one people learn to ignore
    # (ADR 0020). Redaction keeps its JWT pattern — there a false positive is
    # free (ADR 0013).
)


# Words a real credential does not contain but a documentation placeholder does.
# These stay: they are the cheapest true signal available, and they silence AWS's
# own published `AKIAIOSFODNN7EXAMPLE`, which appears in real instruction files.
#
# A run of four identical characters used to be treated the same way. It is gone
# (ADR 0020): `AKIA0000TUVWXY3BCDEF` is a legal AWS key, and suppressing real
# keys to catch placeholders spelled with `AAAA` was the wrong trade once the
# finding stopped failing builds (ADR 0019). Recall is the expensive direction
# now.
_PLACEHOLDER_MARKERS = (
    "example", "replace", "your", "here", "placeholder", "sample",
    "dummy", "todo", "fixme", "changeme", "insert", "redacted", "notreal",
)


def _is_placeholder(value: str) -> bool:
    """True when the token announces itself as a stand-in rather than a secret."""
    return any(marker in value.lower() for marker in _PLACEHOLDER_MARKERS)


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
