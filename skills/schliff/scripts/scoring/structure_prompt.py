"""Scorer -- Structure (system prompt variant).

Evaluates structural quality of system prompts: role definition, section
organization, instruction hierarchy, length, progressive detail, dead content.

10 checks x 10 points = 0-100 additive scoring.
"""
from __future__ import annotations

import re

from scoring.patterns.base import _RE_CODE_BLOCK_REGION
from scoring.patterns.system_prompt import (
    _RE_SP_CONSTRAINT_BLOCK,
    _RE_SP_DEAD_CONTENT,
    _RE_SP_EXAMPLES,
    _RE_SP_OUTPUT_FORMAT,
    _RE_SP_ROLE_DEFINITION,
    _RE_SP_SECTION_SEPARATOR,
    _RE_SP_TASK_DESCRIPTION,
)
from shared import read_skill_safe


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks so only prose remains."""
    return _RE_CODE_BLOCK_REGION.sub("", text)


def _word_count(text: str) -> int:
    return len(text.split())


def _deduplicate_constraints(matches: list[str]) -> list[str]:
    """Deduplicate constraint matches by normalized 40-char prefix."""
    seen: set[str] = set()
    unique: list[str] = []
    for m in matches:
        # Normalize: lowercase, strip punctuation, collapse whitespace
        norm = re.sub(r"[^\w\s]", "", m.lower()).strip()
        prefix = norm[:40]
        if prefix not in seen:
            seen.add(prefix)
            unique.append(m)
    return unique


def _section_has_content(text: str, match_end: int, min_words: int = 10) -> bool:
    """Check if a section separator has at least min_words of content after it."""
    # Look at text after the match until the next section separator or end
    remaining = text[match_end:]
    # Find the next section separator
    next_sep = _RE_SP_SECTION_SEPARATOR.search(remaining)
    if next_sep:
        section_text = remaining[:next_sep.start()]
    else:
        section_text = remaining
    # Strip code blocks from the section
    section_text = _strip_code_blocks(section_text)
    return _word_count(section_text.strip()) >= min_words


def score_structure_prompt(
    skill_path: str, content: str | None = None
) -> dict:
    """Score the structural quality of a system prompt.

    Args:
        skill_path: Path to the system prompt file.
        content: Raw content string (optional, avoids re-reading file).

    Returns:
        dict with keys: score (int), issues (list[str]), details (dict).
    """
    # --- Load content ---
    if content is None:
        try:
            content = read_skill_safe(skill_path)
        except (FileNotFoundError, ValueError):
            return {"score": 0, "issues": ["file_not_found"], "details": {"checks": {}}}

    if not content or not content.strip():
        return {"score": 0, "issues": ["empty_content"], "details": {"checks": {}}}

    # --- Prepare prose (strip code blocks) ---
    prose = _strip_code_blocks(content)
    prose_stripped = prose.strip()

    if not prose_stripped:
        return {"score": 0, "issues": ["empty_prose"], "details": {"checks": {}}}

    # Detect content that is only empty XML tags (anti-gaming)
    _only_empty_tags = re.sub(r"<\w{1,30}>\s*</\w{1,30}>", "", prose_stripped)
    if not _only_empty_tags.strip():
        return {"score": 0, "issues": ["empty_xml_tags_only"], "details": {"checks": {}}}

    score = 0
    issues: list[str] = []
    checks: dict[str, dict] = {}
    total_words = _word_count(prose_stripped)
    prose_len = len(prose_stripped)

    # -----------------------------------------------------------------------
    # Check 1: Role definition (10 pts)
    # Anti-gaming: generic role without specific domain noun -> only 5 pts
    # -----------------------------------------------------------------------
    role_match = _RE_SP_ROLE_DEFINITION.search(prose)
    if role_match:
        # Check if it's a generic role without a specific domain noun
        match_start = max(0, role_match.start() - 10)
        match_end = min(len(prose), role_match.end() + 80)
        context = prose[match_start:match_end].lower()
        # Generic patterns: "helpful assistant", "a helper", "a good assistant", etc.
        _generic_role = re.compile(
            r"(?i)(helpful\s+assistant|a\s+helper\b|a\s+good\s+assistant"
            r"|a\s+nice\s+assistant|an?\s+assistant\b(?!\s+for\s+\w+))",
        )
        if _generic_role.search(context):
            score += 5
            checks["role_definition"] = {"points": 5, "note": "generic_role"}
            issues.append("generic_role_definition")
        else:
            score += 10
            checks["role_definition"] = {"points": 10}
    else:
        checks["role_definition"] = {"points": 0}
        issues.append("no_role_definition")

    # -----------------------------------------------------------------------
    # Check 2: Task description (10 pts)
    # -----------------------------------------------------------------------
    if _RE_SP_TASK_DESCRIPTION.search(prose):
        score += 10
        checks["task_description"] = {"points": 10}
    else:
        checks["task_description"] = {"points": 0}
        issues.append("no_task_description")

    # -----------------------------------------------------------------------
    # Check 3: Constraint block (10 pts) -- needs 2+ unique matches
    # Filter out vague constraints like "always be nice"
    # -----------------------------------------------------------------------
    constraint_matches = _RE_SP_CONSTRAINT_BLOCK.findall(prose)
    unique_constraints = _deduplicate_constraints(constraint_matches)
    # Filter: "always" or "never" followed by vague adjective is not a real constraint
    _vague_constraint = re.compile(
        r"(?i)^(always\s+(be\s+)?(helpful|nice|good|patient|friendly|courteous|professional"
        r"|polite|thorough|careful|accurate|positive)"
        r"|never\s+(be\s+)?(bad|mean|rude|unhelpful|wrong))$",
    )
    unique_constraints = [c for c in unique_constraints if not _vague_constraint.match(c.strip())]
    if len(unique_constraints) >= 2:
        score += 10
        checks["constraint_block"] = {"points": 10, "unique_count": len(unique_constraints)}
    elif len(unique_constraints) == 1:
        score += 5
        checks["constraint_block"] = {"points": 5, "unique_count": 1}
        issues.append("only_one_constraint")
    else:
        checks["constraint_block"] = {"points": 0, "unique_count": 0}
        issues.append("no_constraints")

    # -----------------------------------------------------------------------
    # Check 4: Output format specification (10 pts)
    # Validate match is about actual format, not vague behavioral instruction
    # -----------------------------------------------------------------------
    fmt_match = _RE_SP_OUTPUT_FORMAT.search(prose)
    if fmt_match:
        # Check the match context for actual format keywords
        ctx_start = fmt_match.start()
        ctx_end = min(len(prose), fmt_match.end() + 60)
        fmt_ctx = prose[ctx_start:ctx_end].lower()
        # False positives: "respond helpfully", "respond in a friendly manner",
        # "respond in complete sentences" -- these are tone, not format
        _vague_respond = re.compile(
            r"respond\s+(helpful|polite|courteous|in\s+(a\s+)?(friendly|professional"
            r"|courteous|complete\s+sentence|kind|helpful))",
        )
        if _vague_respond.search(fmt_ctx):
            checks["output_format"] = {"points": 0, "note": "vague_format"}
            issues.append("no_output_format")
        else:
            score += 10
            checks["output_format"] = {"points": 10}
    else:
        checks["output_format"] = {"points": 0}
        issues.append("no_output_format")

    # -----------------------------------------------------------------------
    # Check 5: Examples present (10 pts)
    # -----------------------------------------------------------------------
    if _RE_SP_EXAMPLES.search(prose):
        score += 10
        checks["examples"] = {"points": 10}
    else:
        checks["examples"] = {"points": 0}
        issues.append("no_examples")

    # -----------------------------------------------------------------------
    # Check 6: Section separators (10 pts) -- 2+ distinct, non-empty sections
    # -----------------------------------------------------------------------
    sep_matches = list(_RE_SP_SECTION_SEPARATOR.finditer(content))  # Use original content for separators
    valid_sections = 0
    for m in sep_matches:
        if _section_has_content(content, m.end()):
            valid_sections += 1
    if valid_sections >= 2:
        score += 10
        checks["section_separators"] = {"points": 10, "valid_sections": valid_sections}
    elif valid_sections == 1:
        score += 5
        checks["section_separators"] = {"points": 5, "valid_sections": 1}
        issues.append("only_one_section")
    else:
        checks["section_separators"] = {"points": 0, "valid_sections": 0}
        issues.append("no_sections")

    # -----------------------------------------------------------------------
    # Check 7: Logical ordering (10 pts)
    # Role/context in first 25%, constraints in middle 50%
    # Only awarded when both role AND constraints are actually present
    # and text is long enough to have meaningful ordering (>50 words)
    # -----------------------------------------------------------------------
    ordering_ok = False
    if role_match and prose_len > 0 and total_words >= 50:
        role_pos = role_match.start() / prose_len
        constraint_first = _RE_SP_CONSTRAINT_BLOCK.search(prose)
        if constraint_first:
            constraint_pos = constraint_first.start() / prose_len
            if role_pos < 0.25 and constraint_pos > 0.25:
                ordering_ok = True
    if ordering_ok:
        score += 10
        checks["logical_ordering"] = {"points": 10}
    else:
        checks["logical_ordering"] = {"points": 0}
        issues.append("poor_logical_ordering")

    # -----------------------------------------------------------------------
    # Check 8: Length appropriateness (10 pts)
    # 50-2000 words = 10, <50 or >2000 = 5
    # -----------------------------------------------------------------------
    if 50 <= total_words <= 2000:
        score += 10
        checks["length"] = {"points": 10, "words": total_words}
    elif total_words > 0:
        score += 5
        checks["length"] = {"points": 5, "words": total_words}
        if total_words < 50:
            issues.append("too_short")
        else:
            issues.append("too_long")
    else:
        checks["length"] = {"points": 0, "words": 0}
        issues.append("no_content")

    # -----------------------------------------------------------------------
    # Check 9: Progressive detail (10 pts)
    # First paragraph <50 words AND at least 1 further section exists
    # -----------------------------------------------------------------------
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose_stripped) if p.strip()]
    if paragraphs and _word_count(paragraphs[0]) < 50 and len(paragraphs) > 1:
        score += 10
        checks["progressive_detail"] = {"points": 10}
    else:
        checks["progressive_detail"] = {"points": 0}
        if paragraphs and _word_count(paragraphs[0]) >= 50:
            issues.append("first_paragraph_too_long")
        if len(paragraphs) <= 1:
            issues.append("single_paragraph")

    # -----------------------------------------------------------------------
    # Check 10: No dead content (10 pts)
    # TODO/FIXME/TBD/placeholder patterns -> 0 matches = 10 pts
    # -----------------------------------------------------------------------
    dead_matches = _RE_SP_DEAD_CONTENT.findall(prose)
    if len(dead_matches) == 0:
        score += 10
        checks["no_dead_content"] = {"points": 10}
    else:
        checks["no_dead_content"] = {"points": 0, "dead_count": len(dead_matches)}
        issues.append(f"dead_content:{len(dead_matches)}")

    # -----------------------------------------------------------------------
    # Keyword stuffing penalty (Global Anti-Gaming Rule #4)
    # If >30% of all signal matches are in a single paragraph, -10%
    # -----------------------------------------------------------------------
    _all_signal_patterns = [
        _RE_SP_ROLE_DEFINITION, _RE_SP_TASK_DESCRIPTION, _RE_SP_CONSTRAINT_BLOCK,
        _RE_SP_OUTPUT_FORMAT, _RE_SP_EXAMPLES,
    ]
    total_signal_matches = sum(len(p.findall(prose)) for p in _all_signal_patterns)
    if total_signal_matches > 0 and paragraphs:
        max_para_matches = 0
        for para in paragraphs:
            para_matches = sum(len(p.findall(para)) for p in _all_signal_patterns)
            max_para_matches = max(max_para_matches, para_matches)
        if total_signal_matches > 0 and max_para_matches / total_signal_matches > 0.30:
            # Check if content is essentially a single paragraph
            if len(paragraphs) <= 1 or max_para_matches == total_signal_matches:
                penalty = int(score * 0.20)  # 20% penalty for single-paragraph stuffing
                score -= penalty
                issues.append("keyword_stuffing")
                checks["keyword_stuffing_penalty"] = {"penalty": penalty}

    # -----------------------------------------------------------------------
    # Clamp final score
    # -----------------------------------------------------------------------
    score = max(0, min(100, score))

    return {"score": score, "issues": issues, "details": {"checks": checks}}
