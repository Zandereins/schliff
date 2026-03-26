"""Score security dimension of a skill file.

Deductive scoring: starts at 100, subtracts penalties for each security
anti-pattern found. Implements three false-positive mitigation mechanisms:
code-block exclusion, meta-discourse detection, and negation-aware matching.
"""
from __future__ import annotations

import re

from shared import read_skill_safe
from scoring.patterns import (
    _RE_SEC_PROMPT_INJECTION,
    _RE_SEC_INSTRUCTION_OVERRIDE,
    _RE_SEC_DATA_EXFIL,
    _RE_SEC_ENV_LEAK,
    _RE_SEC_DANGEROUS_CMD,
    _RE_SEC_BASE64_CMD,
    _RE_SEC_ZERO_WIDTH,
    _RE_SEC_HEX_ESCAPE,
    _RE_SEC_OVERPERMISSION,
    _RE_SEC_BOUNDARY_VIOLATION,
    _RE_CODE_BLOCK_REGION,
)

# ---------------------------------------------------------------------------
# Pattern categories: (category_name, penalty_per_match, [compiled_patterns])
# ---------------------------------------------------------------------------
_CATEGORIES: list[tuple[str, int, list[re.Pattern]]] = [
    ("injection", 25, [_RE_SEC_PROMPT_INJECTION, _RE_SEC_INSTRUCTION_OVERRIDE]),
    ("exfil", 25, [_RE_SEC_DATA_EXFIL, _RE_SEC_ENV_LEAK]),
    ("dangerous_cmd", 20, [_RE_SEC_DANGEROUS_CMD]),
    ("obfuscation", 15, [_RE_SEC_BASE64_CMD, _RE_SEC_ZERO_WIDTH, _RE_SEC_HEX_ESCAPE]),
    ("overpermission", 15, [_RE_SEC_OVERPERMISSION]),
    ("boundaries", 10, [_RE_SEC_BOUNDARY_VIOLATION]),
]

# Categories where meta-discourse reduction applies.
# All categories except obfuscation get the discount for security-domain skills.
# Obfuscation (zero-width chars, base64 pipe-to-shell) is inherently suspicious
# and never discounted — even in educational content.
_META_DISCOUNTABLE = {"injection", "exfil", "dangerous_cmd", "overpermission", "boundaries"}

# Categories where negation-aware exclusion applies.
# Obfuscation is never negation-excluded (same logic as code-block exemption).
# injection and exfil are never negation-excluded — "never curl evil.com --data"
# could be an attacker using negation as a smokescreen.
_NEGATION_ELIGIBLE = {"dangerous_cmd", "overpermission", "boundaries"}

# Lookback window for negation detection (characters before match)
_NEGATION_LOOKBACK_CHARS = 30

# ---------------------------------------------------------------------------
# Meta-discourse detection keywords
# ---------------------------------------------------------------------------
_META_DESC_KEYWORDS = re.compile(
    r"(?i)\b(security|vulnerability|vulnerabilities|pentest|penetration\s+test|"
    r"CVE|OWASP|exploit|threat|malware)\b"
)
_META_NAME_KEYWORDS = re.compile(
    r"(?i)(security|vuln|shield|guard|sentinel)"
)

# ---------------------------------------------------------------------------
# Negation words for negation-aware matching
# ---------------------------------------------------------------------------
_NEGATION_RE = re.compile(
    r"(?i)\b(never|don't|do not|avoid|must not|should not|shouldn't|"
    r"won't|cannot|can't)\b"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_frontmatter(content: str) -> str:
    """Return raw YAML frontmatter string (without delimiters), or ''."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end >= 4:
            return content[3:end]
    return ""


def _is_security_domain(content: str) -> bool:
    """Detect whether the skill is about security (educational content)."""
    fm = _extract_frontmatter(content)
    if not fm:
        return False

    # Check description field
    desc_match = re.search(r"(?m)^description:.*?(?=^\S|\Z)", fm, re.DOTALL)
    if desc_match and _META_DESC_KEYWORDS.search(desc_match.group()):
        return True

    # Check metadata.domain: security
    if re.search(r"(?m)domain:\s*security", fm, re.IGNORECASE):
        return True

    # Check name field
    name_match = re.search(r"(?m)^name:\s*(.+)", fm)
    if name_match and _META_NAME_KEYWORDS.search(name_match.group(1)):
        return True

    return False


def _find_code_block_ranges(content: str) -> list[tuple[int, int]]:
    """Return list of (start, end) positions for ```...``` code blocks."""
    return [(m.start(), m.end()) for m in _RE_CODE_BLOCK_REGION.finditer(content)]


def _in_code_block(pos: int, ranges: list[tuple[int, int]]) -> bool:
    """Check if a character position falls inside any code block range."""
    return any(start <= pos < end for start, end in ranges)


def _preceded_by_negation(content: str, match_start: int) -> bool:
    """Check if the lookback window before match_start contains a negation word.

    Only considers text on the same line (no newline crossing) to avoid
    matching negation words from unrelated sentences.
    """
    window_start = max(0, match_start - _NEGATION_LOOKBACK_CHARS)
    window = content[window_start:match_start]
    # Don't cross newline boundaries — only look at the current line
    last_newline = window.rfind("\n")
    if last_newline >= 0:
        window = window[last_newline + 1:]
    return bool(_NEGATION_RE.search(window))


def _empty_result(issues: list[str] | None = None, error: str = "") -> dict:
    """Return a zero-score result dict for error cases."""
    return {
        "score": 0,
        "issues": issues or ["security:unreadable"],
        "details": {
            "category_penalties": {},
            "total_penalty": 100,
            "meta_discourse_reduction": 1.0,
            "code_block_excluded": 0,
            "negation_excluded": 0,
            **({"error": error} if error else {}),
        },
    }


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def score_security(skill_path: str) -> dict:
    """Score security dimension of a skill file.

    Deductive scoring: starts at 100, subtracts penalties for each security
    anti-pattern found. Implements three false-positive mitigation mechanisms:
    code-block exclusion, meta-discourse detection, and negation-aware matching.

    Returns:
        {
            "score": int (0-100, clamped),
            "issues": list[str],
            "details": {
                "category_penalties": dict,
                "total_penalty": int,
                "meta_discourse_reduction": float,
                "code_block_excluded": int,
                "negation_excluded": int,
            }
        }
    """
    try:
        content = read_skill_safe(skill_path)
    except (FileNotFoundError, ValueError, PermissionError, OSError, RuntimeError) as e:
        return _empty_result(error=str(e))

    # Meta-discourse detection
    is_security = _is_security_domain(content)
    penalty_multiplier = 0.1 if is_security else 1.0

    # Code block ranges
    cb_ranges = _find_code_block_ranges(content)

    # Scan all categories
    category_penalties: dict[str, float] = {}
    code_block_excluded = 0
    negation_excluded = 0

    for cat_name, penalty_per_match, patterns in _CATEGORIES:
        cat_raw = 0
        for pat in patterns:
            for m in pat.finditer(content):
                match_start = m.start()

                # Code-block exclusion (not for obfuscation)
                if cat_name != "obfuscation" and _in_code_block(match_start, cb_ranges):
                    code_block_excluded += 1
                    continue

                # Negation-aware exclusion (only eligible categories)
                if cat_name in _NEGATION_ELIGIBLE and _preceded_by_negation(content, match_start):
                    negation_excluded += 1
                    continue

                cat_raw += penalty_per_match

        if cat_raw > 0:
            # Apply meta-discourse reduction only to discountable categories
            multiplier = penalty_multiplier if cat_name in _META_DISCOUNTABLE else 1.0
            category_penalties[cat_name] = cat_raw * multiplier

    total_penalty_int = int(round(sum(category_penalties.values())))
    score = max(0, 100 - total_penalty_int)
    issues = [f"security:{cat}" for cat in category_penalties]

    return {
        "score": score,
        "issues": issues,
        "details": {
            "category_penalties": category_penalties,
            "total_penalty": total_penalty_int,
            "meta_discourse_reduction": penalty_multiplier,
            "code_block_excluded": code_block_excluded,
            "negation_excluded": negation_excluded,
        },
    }


def get_composite_cap(security_score: int) -> int | None:
    """Return composite score cap based on security score, or None if no cap."""
    if security_score < 5:
        return 20
    if security_score < 10:
        return 40
    if security_score < 20:
        return 60
    return None
