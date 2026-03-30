"""Schliff — Format Detection and Content Normalization

Detect the format of a project instruction file and normalize non-SKILL.md
content to SKILL.md shape so the existing scoring engine can process it
without any scorer changes.
"""
from __future__ import annotations

import re
from pathlib import Path

# Supported format identifiers
FORMAT_SKILL_MD = "skill.md"
FORMAT_CLAUDE_MD = "claude.md"
FORMAT_CURSORRULES = "cursorrules"
FORMAT_AGENTS_MD = "agents.md"
FORMAT_SYSTEM_PROMPT = "system_prompt"
FORMAT_UNKNOWN = "unknown"

_BASENAME_MAP: dict[str, str] = {
    "skill.md": FORMAT_SKILL_MD,
    "claude.md": FORMAT_CLAUDE_MD,
    ".cursorrules": FORMAT_CURSORRULES,
    "agents.md": FORMAT_AGENTS_MD,
}

_RE_H1 = re.compile(r"^#\s+(.+)", re.MULTILINE)
_RE_ROLE_DEFINITION = re.compile(
    r"(?i)(you are|your role is|act as|you're a|as a \w+ assistant|your purpose)"
)


def detect_format(filename: str, content: str | None = None) -> str:
    """Return the format identifier for a project instruction file.

    Matches by basename (case-insensitive) first. If the filename doesn't
    match a known format, falls back to content heuristics for system_prompt
    detection.

    Returns one of:
    "skill.md", "claude.md", "cursorrules", "agents.md", "system_prompt", "unknown".
    """
    basename = Path(filename).name.lower()
    fmt = _BASENAME_MAP.get(basename, FORMAT_UNKNOWN)

    # Filename-based formats always take priority
    if fmt != FORMAT_UNKNOWN:
        return fmt

    # Extension-based detection for system prompts
    ext = Path(filename).suffix.lower()
    if ext in (".prompt", ".system"):
        return FORMAT_SYSTEM_PROMPT

    # Content heuristic: .txt files with role-definition patterns and no YAML frontmatter
    # If content was not passed, try reading it from the file for .txt heuristic
    if ext == ".txt":
        if content is None:
            try:
                content = Path(filename).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return FORMAT_UNKNOWN
        has_yaml_frontmatter = content.startswith("---")
        if not has_yaml_frontmatter and _RE_ROLE_DEFINITION.search(content):
            return FORMAT_SYSTEM_PROMPT

    return FORMAT_UNKNOWN


def normalize_content(content: str, fmt: str) -> str:
    """Normalize non-SKILL.md content to SKILL.md shape.

    If the content already has YAML frontmatter (starts with "---") or
    fmt is "skill.md", return content unchanged. Otherwise wrap the content
    in synthetic YAML frontmatter so the scoring engine can process it.
    """
    if fmt == FORMAT_SKILL_MD:
        return content
    # Only treat as existing frontmatter if properly closed (--- ... ---)
    if content.startswith("---"):
        end = content.find("---", 3)
        if end >= 4:
            return content

    name = _extract_name(content)
    desc = _extract_description(content, name)

    header = f"---\nname: {_yaml_safe(name)}\ndescription: {_yaml_safe(desc)}\n---\n\n"
    return header + content


def _yaml_safe(value: str) -> str:
    """Escape a value for safe YAML scalar embedding."""
    if any(c in value for c in (':', '#', '{', '}', '[', ']', ',', '&', '*',
                                 '?', '|', '>', '!', "'", '"', '\n', '\r',
                                 '%', '@', '`')):
        escaped = (value.replace('\\', '\\\\').replace('"', '\\"')
                   .replace('\n', '\\n').replace('\r', '\\r'))
        return f'"{escaped}"'
    return value


def _extract_name(content: str) -> str:
    """Extract a name from the first H1 heading or first significant line."""
    match = _RE_H1.search(content)
    if match:
        return match.group(1).strip()

    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            # Truncate long lines to keep frontmatter readable
            return stripped[:80]

    return "Untitled"


def _extract_description(content: str, name: str) -> str:
    """Extract a description from the first paragraph after any heading."""
    lines = content.splitlines()
    has_heading = bool(_RE_H1.search(content))
    past_heading = False
    paragraph: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            past_heading = True
            continue
        if past_heading or not has_heading:
            if stripped:
                paragraph.append(stripped)
            elif paragraph:
                break  # end of first paragraph

    desc = " ".join(paragraph).strip()
    if not desc:
        desc = name
    # Truncate to keep frontmatter compact
    return desc[:200]


# ---------------------------------------------------------------------------
# Token Budget Estimation
# ---------------------------------------------------------------------------

def estimate_tokens(content: str) -> int:
    """Estimate token count using len(content) // 4 heuristic.

    This is a rough approximation — real tokenizers vary by model,
    but len//4 is a widely-used stdlib-only estimate.
    """
    return len(content) // 4


FORMAT_TOKEN_BUDGETS: dict[str, int] = {
    "skill.md": 1000,
    "claude.md": 2000,
    "cursorrules": 500,
    "agents.md": 3000,
    "system_prompt": 1500,
    "unknown": 1500,
}


def check_token_budget(content: str, fmt: str) -> dict:
    """Check if content is within the recommended token budget for its format.

    Returns dict with:
    - tokens: int — estimated token count
    - budget: int — recommended budget for this format
    - within_budget: bool — True if tokens <= budget
    - ratio: float — tokens / budget (1.0 = exactly at budget)
    - severity: str — "ok" | "warning" | "over"
      - ok: within budget
      - warning: 80-100% of budget
      - over: exceeds budget
    """
    tokens = estimate_tokens(content)
    budget = FORMAT_TOKEN_BUDGETS.get(fmt, FORMAT_TOKEN_BUDGETS["unknown"])
    ratio = tokens / budget if budget else 0.0
    within_budget = tokens <= budget

    if ratio > 1.0:
        severity = "over"
    elif ratio > 0.8:
        severity = "warning"
    else:
        severity = "ok"

    return {
        "tokens": tokens,
        "budget": budget,
        "within_budget": severity != "over",
        "ratio": ratio,
        "severity": severity,
    }
