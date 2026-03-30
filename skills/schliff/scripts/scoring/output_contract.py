"""Scorer — Output Contract.

Phase 1b: evaluates whether the system prompt defines clear
output expectations (format, structure, constraints on responses).
"""
from __future__ import annotations

import re

from shared import read_skill_safe

# ---------------------------------------------------------------------------
# Pattern imports — primary source is patterns.system_prompt (built in
# parallel). If it doesn't exist yet, fall back to inline definitions.
# ---------------------------------------------------------------------------
try:
    from scoring.patterns.system_prompt import (
        _RE_SP_CODE_BLOCK_REGION,
        _RE_SP_ERROR_RESPONSE,
        _RE_SP_EXAMPLE_OUTPUT,
        _RE_SP_FORBIDDEN_CONTENT,
        _RE_SP_FORMAT_SPEC,
        _RE_SP_LENGTH_CONSTRAINT,
        _RE_SP_REQUIRED_FIELDS,
        _RE_SP_RESPONSE_STRUCTURE,
        _RE_SP_SCHEMA_DEF,
        _RE_SP_TONE_VOICE,
        _RE_SP_VALIDATION_INSTRUCTION,
    )
except ImportError:
    # Inline fallback — mirrors the spec exactly.
    _RE_SP_FORMAT_SPEC = re.compile(
        r"(?i)(respond (in|with|as)|format (as|your)|output (as|in|format)"
        r"|return (JSON|XML|YAML|markdown|plain text|HTML|CSV))"
    )
    _RE_SP_LENGTH_CONSTRAINT = re.compile(
        r"(?i)(max(imum)?\s+\d+\s+(words?|tokens?|sentences?|characters?"
        r"|paragraphs?|lines?)"
        r"|keep.{0,20}(short|brief|concise|under \d+)"
        r"|limit.{0,20}(to \d+|length))"
    )
    _RE_SP_TONE_VOICE = re.compile(
        r"(?i)(tone:|voice:|style:|speak (as|like)|write (in|with) a"
        r"|formal|informal|professional|friendly|technical|casual|authoritative)"
    )
    _RE_SP_SCHEMA_DEF = re.compile(
        r'(?i)("type":\s*"|fields?:|properties:|required:|schema:)'
    )
    _RE_SP_REQUIRED_FIELDS = re.compile(
        r"(?i)(must include|required fields?"
        r"|always include|every response (must|should) (have|contain|include))"
    )
    _RE_SP_FORBIDDEN_CONTENT = re.compile(
        r"(?i)(never (include|mention|output|say|generate|reveal)"
        r"|do not (include|mention|output|reveal|disclose)"
        r"|forbidden:|prohibited:|exclude:)"
    )
    _RE_SP_RESPONSE_STRUCTURE = re.compile(
        r"(?i)(first[,.]|then[,.]|finally[,.]|step \d"
        r"|begin (with|by)|end (with|by)|start (with|by)"
        r"|your response should (start|begin|end))"
    )
    _RE_SP_ERROR_RESPONSE = re.compile(
        r"(?i)(if .{0,40}(error|fail|unknown|unclear|can'?t|unable)"
        r"|when .{0,30}(error|fail)"
        r"|error (response|format|message)|on (error|failure))"
    )
    _RE_SP_VALIDATION_INSTRUCTION = re.compile(
        r"(?i)(verify|validate|check|ensure|confirm)"
        r".{0,30}(before (respond|return|output)|your (response|output|answer))"
    )
    _RE_SP_EXAMPLE_OUTPUT = re.compile(
        r"(?i)(example (output|response)|sample (output|response)"
        r"|here'?s what .{0,20}(look|should)|expected (output|response))"
    )
    _RE_SP_CODE_BLOCK_REGION = re.compile(r"```[\s\S]*?```")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Regex for detecting JSON-like skeletons (2+ distinct quoted keys)
_RE_JSON_SKELETON = re.compile(r'\{[^}]{5,500}\}')
_RE_JSON_KEY = re.compile(r'"(\w+)"\s*:')

# Extended length constraint: catches "Maximum response size: 2000 tokens" etc.
_RE_LENGTH_EXTENDED = re.compile(
    r"(?i)(max(imum)?\s+.{0,30}\d+\s*(words?|tokens?|sentences?|characters?"
    r"|paragraphs?|lines?)"
    r"|\d+\s*(words?|tokens?|sentences?|characters?|paragraphs?|lines?)\s*(max|limit|cap))"
)

# Extended example pattern: "Example N:" or "Example:" with code block nearby
_RE_EXAMPLE_HEADER = re.compile(r"(?i)(example\s*\d*\s*:|output\s*:)")

# Specific tone adjectives (excludes vague words)
_RE_TONE_SPECIFIC_ADJ = re.compile(
    r"(?i)\b(formal|informal|professional|friendly|technical|casual"
    r"|authoritative|analytical|direct|empathetic|warm|neutral|concise"
    r"|terse|humorous|serious|academic|conversational|playful)\b"
)

# Vague tone words that don't count
_RE_TONE_VAGUE = re.compile(r"(?i)\b(appropriate|suitable|proper|good|nice)\b")

# "Respond in JSON" without field spec — anti-gaming
_RE_JSON_NO_FIELDS = re.compile(
    r"(?i)respond.{0,15}(in|with|as)\s+JSON(?!\s*[\{:])"
)

# Numeric length check
_RE_HAS_NUMBER = re.compile(r"\d+")

# Code block or indented block
_RE_CODE_OR_INDENT = re.compile(r"(^```|^    \S|^\t\S)", re.MULTILINE)


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks from text for prose-only analysis."""
    return _RE_SP_CODE_BLOCK_REGION.sub("", text)


def _count_schema_fields(text: str) -> int:
    """Count distinct field names in JSON-like schema definitions."""
    fields: set[str] = set()
    for skeleton in _RE_JSON_SKELETON.finditer(text):
        for key_match in _RE_JSON_KEY.finditer(skeleton.group()):
            fields.add(key_match.group(1).lower())
    # Also count fields-style definitions
    for m in re.finditer(r'(?i)(?:^|\n)\s*[-*]\s*["`]?(\w+)["`]?\s*:', text):
        fields.add(m.group(1).lower())
    return len(fields)


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def score_output_contract(
    skill_path: str, content: str | None = None, **kw: object,
) -> dict:
    """Score the output contract definition of a system prompt.

    Args:
        skill_path: Path to the system prompt file.
        content: Raw content string (optional, avoids re-reading file).
        **kw: Additional keyword arguments (forward compat).

    Returns:
        dict with keys: score (int 0-100), issues (list[str]),
        details (dict with checks sub-dict).
    """
    # --- Load content ---
    if content is None:
        try:
            content = read_skill_safe(skill_path)
        except (FileNotFoundError, ValueError):
            return {"score": 0, "issues": ["file_not_found"], "details": {"checks": {}}}

    if not content or not content.strip():
        return {"score": 0, "issues": ["empty_content"], "details": {"checks": {}}}

    # Strip code blocks for prose analysis
    prose = _strip_code_blocks(content)
    # Keep original for schema/example detection (they live in code blocks)
    full = content

    score = 0
    issues: list[str] = []
    checks: dict[str, dict] = {}

    # --- 1. Format specification (10 pts) ---
    fmt_match = _RE_SP_FORMAT_SPEC.search(prose)
    if fmt_match:
        # Anti-gaming: "Respond in JSON" without field spec → max 3 pts
        if _RE_JSON_NO_FIELDS.search(prose) and _count_schema_fields(full) == 0:
            checks["format_specification"] = {"found": True, "points": 3, "note": "json_without_fields"}
            score += 3
            issues.append("format_spec_vague: JSON without field specification")
        else:
            checks["format_specification"] = {"found": True, "points": 10}
            score += 10
    else:
        checks["format_specification"] = {"found": False, "points": 0}

    # --- 2. Length/size constraints (10 pts) ---
    len_match = _RE_SP_LENGTH_CONSTRAINT.search(prose)
    if not len_match:
        # Try extended pattern (e.g. "Maximum response size: 2000 tokens")
        len_match = _RE_LENGTH_EXTENDED.search(prose)
    if len_match:
        matched_text = len_match.group(0)
        # Anti-gaming: "keep it short" without number → max 5 pts
        if not _RE_HAS_NUMBER.search(matched_text):
            checks["length_constraint"] = {"found": True, "points": 5, "note": "no_numeric_limit"}
            score += 5
            issues.append("length_constraint_vague: no numeric limit")
        else:
            checks["length_constraint"] = {"found": True, "points": 10}
            score += 10
    else:
        checks["length_constraint"] = {"found": False, "points": 0}

    # --- 3. Tone/voice definition (10 pts) ---
    tone_match = _RE_SP_TONE_VOICE.search(prose)
    if tone_match:
        specific_adjs = set(_RE_TONE_SPECIFIC_ADJ.findall(prose))
        # Remove vague words
        specific_adjs = {a.lower() for a in specific_adjs} - {
            v.lower() for v in _RE_TONE_VAGUE.findall(prose)
        }
        if len(specific_adjs) >= 2:
            checks["tone_voice"] = {"found": True, "points": 10, "adjectives": list(specific_adjs)}
            score += 10
        else:
            checks["tone_voice"] = {"found": True, "points": 5, "note": "needs_2+_specific_adjectives"}
            score += 5
            issues.append("tone_vague: fewer than 2 specific tone adjectives")
    else:
        checks["tone_voice"] = {"found": False, "points": 0}

    # --- 4. Schema definition (10 pts) ---
    # Check both prose and full content (schemas are often in code blocks)
    schema_match = _RE_SP_SCHEMA_DEF.search(full)
    if not schema_match:
        # Also check for JSON skeletons
        skeleton_match = _RE_JSON_SKELETON.search(full)
        if skeleton_match and _RE_JSON_KEY.search(skeleton_match.group()):
            schema_match = skeleton_match
    # Count fields across the entire document (JSON keys in code blocks count)
    field_count = _count_schema_fields(full)
    if schema_match or field_count >= 2:
        if field_count >= 2:
            checks["schema_definition"] = {"found": True, "points": 10, "fields": field_count}
            score += 10
        else:
            checks["schema_definition"] = {"found": True, "points": 5, "note": "single_field_schema"}
            score += 5
            issues.append("schema_trivial: single-field schema")
    else:
        checks["schema_definition"] = {"found": False, "points": 0}

    # --- 5. Required fields (10 pts) ---
    if _RE_SP_REQUIRED_FIELDS.search(prose):
        checks["required_fields"] = {"found": True, "points": 10}
        score += 10
    else:
        checks["required_fields"] = {"found": False, "points": 0}

    # --- 6. Forbidden content (10 pts) ---
    if _RE_SP_FORBIDDEN_CONTENT.search(prose):
        checks["forbidden_content"] = {"found": True, "points": 10}
        score += 10
    else:
        checks["forbidden_content"] = {"found": False, "points": 0}

    # --- 7. Response structure (10 pts) ---
    if _RE_SP_RESPONSE_STRUCTURE.search(prose):
        checks["response_structure"] = {"found": True, "points": 10}
        score += 10
    else:
        checks["response_structure"] = {"found": False, "points": 0}

    # --- 8. Error response format (10 pts) ---
    if _RE_SP_ERROR_RESPONSE.search(prose):
        checks["error_response"] = {"found": True, "points": 10}
        score += 10
    else:
        checks["error_response"] = {"found": False, "points": 0}

    # --- 9. Validation instruction (10 pts) ---
    if _RE_SP_VALIDATION_INSTRUCTION.search(prose):
        checks["validation_instruction"] = {"found": True, "points": 10}
        score += 10
    else:
        checks["validation_instruction"] = {"found": False, "points": 0}

    # --- 10. Example output (10 pts) ---
    # Check for explicit "example output/response" pattern first
    example_match = _RE_SP_EXAMPLE_OUTPUT.search(full)
    # Also check for "Example N:" or "Output:" headers with code blocks nearby
    if not example_match:
        example_match = _RE_EXAMPLE_HEADER.search(full)
    if example_match:
        # Must have code block or indented block within 10 lines
        match_pos = example_match.start()
        text_before = full[:match_pos]
        match_line = text_before.count("\n")
        lines = full.split("\n")
        has_code_nearby = False
        for i in range(match_line, min(match_line + 11, len(lines))):
            if _RE_CODE_OR_INDENT.search(lines[i]):
                has_code_nearby = True
                break
        if has_code_nearby:
            checks["example_output"] = {"found": True, "points": 10}
            score += 10
        else:
            checks["example_output"] = {"found": True, "points": 5, "note": "no_code_block_nearby"}
            score += 5
            issues.append("example_output_no_block: example mentioned but no code block nearby")
    else:
        checks["example_output"] = {"found": False, "points": 0}

    final_score = max(0, min(100, score))
    return {"score": final_score, "issues": issues, "details": {"checks": checks}}
