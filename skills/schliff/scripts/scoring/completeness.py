"""Scorer — Completeness.

Phase 1b: evaluates whether the system prompt covers all
essential aspects (error handling, edge cases, ambiguity, off-topic,
multi-turn, language, empty input, rate limits, graceful degradation,
and non-obvious examples).
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
        _RE_SP_AMBIGUITY_HANDLING,
        _RE_SP_CODE_BLOCK_REGION,
        _RE_SP_EDGE_CASES,
        _RE_SP_EMPTY_INPUT,
        _RE_SP_ERROR_HANDLING,
        _RE_SP_GRACEFUL_DEGRADE,
        _RE_SP_LANGUAGE_LOCALE,
        _RE_SP_MULTI_TURN,
        _RE_SP_NONOBVIOUS_EXAMPLE,
        _RE_SP_OFF_TOPIC,
        _RE_SP_RATE_LIMIT,
    )
except ImportError:
    # Inline fallback — mirrors the spec exactly.
    _RE_SP_ERROR_HANDLING = re.compile(
        r"(?i)(if .{0,30}(error|fail|invalid|wrong|broken|missing)"
        r"|when .{0,20}(error|fail)"
        r"|error (handling|response|behavior))"
    )
    _RE_SP_EDGE_CASES = re.compile(
        r"(?i)(edge case|corner case|special case|exception"
        r"|unusual (input|case|situation)"
        r"|if (the|an?) (input|request|query) is (empty|blank|missing|malformed))"
    )
    _RE_SP_AMBIGUITY_HANDLING = re.compile(
        r"(?i)(if (unclear|ambiguous|vague|confusing|uncertain)"
        r"|when (you'?re?|the (intent|meaning) is) (unsure|unclear|not sure|uncertain)"
        r"|ask (for|the user for) clarification)"
    )
    _RE_SP_OFF_TOPIC = re.compile(
        r"(?i)(off.?topic|out of scope|unrelated (question|request|topic)"
        r"|not (within|in) (your|the) (scope|domain)"
        r"|if (the user|someone) asks? (about|for) .{0,30}(unrelated|outside))"
    )
    _RE_SP_MULTI_TURN = re.compile(
        r"(?i)(follow.?up|conversation (history|context)"
        r"|previous (message|turn|question)"
        r"|referring (back|to earlier)|maintain context"
        r"|remember (earlier|previous|the))"
    )
    _RE_SP_LANGUAGE_LOCALE = re.compile(
        r"(?i)(language:|respond in \w+"
        r"|if .{0,20}(another|different|foreign) language"
        r"|locale|translation|multilingual|english only)"
    )
    _RE_SP_EMPTY_INPUT = re.compile(
        r"(?i)(empty (input|message|query|request)"
        r"|blank (input|message)|null"
        r"|no (input|message|content) (provided|given|received)"
        r"|if .{0,20}(nothing|empty))"
    )
    _RE_SP_RATE_LIMIT = re.compile(
        r"(?i)(rate limit|too many (requests?|calls?)"
        r"|throttl|quota|if .{0,30}(exceed|limit|cap))"
    )
    _RE_SP_GRACEFUL_DEGRADE = re.compile(
        r"(?i)(graceful(ly)?\s+(fail|degrad|handle)"
        r"|best effort|partial (response|result)"
        r"|if .{0,30}(can'?t fully|unable to complete|partial))"
    )
    _RE_SP_NONOBVIOUS_EXAMPLE = re.compile(
        r"(?i)(example|e\.g\.)"
    )
    _RE_SP_CODE_BLOCK_REGION = re.compile(r"```[\s\S]*?```")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Extended multi-turn: natural phrases the spec patterns miss
_RE_MULTI_TURN_EXT = re.compile(
    r"(?i)(previous (conversation|interaction|exchange|session)s?"
    r"|conversation (exceeds?|length|turns?|limit)"
    r"|summarize (earlier|previous|prior)"
    r"|retain.{0,15}(memory|context|state)"
    r"|each (request|conversation|message) is (independent|separate|stateless))"
)

# Extended graceful degradation: tool failures, retry patterns
_RE_GRACEFUL_DEGRADE_EXT = re.compile(
    r"(?i)(if .{0,30}(tool|function|api|service).{0,20}(fail|error|unavailable)"
    r"|retry.{0,15}(once|again|later)"
    r"|try again.{0,15}(then|before|after)"
    r"|unable to (access|reach|connect|retrieve))"
)

# Context markers for non-obvious examples
_RE_NONOBVIOUS_CONTEXT = re.compile(
    r"(?i)(but|however|edge|special|even (if|when|though)|note that)"
)

# Generic error handling (anti-gaming)
_RE_GENERIC_ERROR = re.compile(
    r"(?i)if.{0,15}error.{0,15}inform.{0,15}user"
)

# "Ask for clarification" without specifying WHEN
_RE_UNCONDITIONAL_CLARIFY = re.compile(
    r"(?i)ask (for|the user for) clarification"
)
_RE_CLARIFY_WITH_CONDITION = re.compile(
    r"(?i)(if|when|whenever).{0,40}(ask (for|the user for) clarification"
    r"|clarif)"
)

# Empty handling must specify response
_RE_EMPTY_WITH_RESPONSE = re.compile(
    r"(?i)(empty|blank|null|nothing).{0,60}(respond|return|reply|output|say|give)"
)


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks from text for prose-only analysis."""
    return _RE_SP_CODE_BLOCK_REGION.sub("", text)


def _count_nonobvious_examples(text: str) -> int:
    """Count examples that appear in edge/error/ambiguity context.

    An example is 'non-obvious' if within 5 lines there's a context
    marker like 'but', 'however', 'edge', 'special', 'even if', etc.
    """
    lines = text.split("\n")
    count = 0
    seen_contexts: set[str] = set()

    for i, line in enumerate(lines):
        if _RE_SP_NONOBVIOUS_EXAMPLE.search(line):
            # Check surrounding 5 lines for context markers
            window_start = max(0, i - 2)
            window_end = min(len(lines), i + 6)
            window = "\n".join(lines[window_start:window_end])
            context_matches = _RE_NONOBVIOUS_CONTEXT.findall(window)
            if context_matches:
                # Deduplicate on normalized context to prevent gaming
                ctx_key = line.strip().lower()[:80]
                if ctx_key not in seen_contexts:
                    seen_contexts.add(ctx_key)
                    count += 1

    # Cap at 3 to prevent gaming with trivially similar examples
    return min(count, 3)


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def score_completeness(
    skill_path: str, content: str | None = None, **kw: object,
) -> dict:
    """Score the completeness of a system prompt.

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

    raw_score = 0
    issues: list[str] = []
    checks: dict[str, dict] = {}

    # --- 1. Error handling (10 pts) ---
    if _RE_SP_ERROR_HANDLING.search(prose):
        # Anti-gaming: generic "if error, inform user" → max 5 pts
        if _RE_GENERIC_ERROR.search(prose) and not re.search(
            r"(?i)(error (code|type|message|response)|specific|status|"
            r"return.{0,20}\{|error.{0,30}(format|schema|json))", prose
        ):
            checks["error_handling"] = {"found": True, "points": 5, "note": "generic_error_handling"}
            raw_score += 5
            issues.append("error_handling_generic: no specific error format")
        else:
            checks["error_handling"] = {"found": True, "points": 10}
            raw_score += 10
    else:
        checks["error_handling"] = {"found": False, "points": 0}

    # --- 2. Edge case coverage (10 pts) ---
    if _RE_SP_EDGE_CASES.search(prose):
        checks["edge_cases"] = {"found": True, "points": 10}
        raw_score += 10
    else:
        checks["edge_cases"] = {"found": False, "points": 0}

    # --- 3. Ambiguity handling (10 pts) ---
    ambiguity_match = _RE_SP_AMBIGUITY_HANDLING.search(prose)
    if ambiguity_match:
        # Anti-gaming: "ask for clarification" without WHEN → 0 pts
        has_unconditional = _RE_UNCONDITIONAL_CLARIFY.search(prose)
        has_conditional = _RE_CLARIFY_WITH_CONDITION.search(prose)
        if has_unconditional and not has_conditional:
            checks["ambiguity_handling"] = {"found": True, "points": 0, "note": "no_when_condition"}
            issues.append("ambiguity_no_condition: 'ask for clarification' without specifying when")
        else:
            checks["ambiguity_handling"] = {"found": True, "points": 10}
            raw_score += 10
    else:
        checks["ambiguity_handling"] = {"found": False, "points": 0}

    # --- 4. Off-topic handling (10 pts) ---
    if _RE_SP_OFF_TOPIC.search(prose):
        checks["off_topic"] = {"found": True, "points": 10}
        raw_score += 10
    else:
        checks["off_topic"] = {"found": False, "points": 0}

    # --- 5. Multi-turn awareness (10 pts) ---
    if _RE_SP_MULTI_TURN.search(prose) or _RE_MULTI_TURN_EXT.search(prose):
        checks["multi_turn"] = {"found": True, "points": 10}
        raw_score += 10
    else:
        checks["multi_turn"] = {"found": False, "points": 0}

    # --- 6. Language/locale handling (10 pts) ---
    if _RE_SP_LANGUAGE_LOCALE.search(prose):
        checks["language_locale"] = {"found": True, "points": 10}
        raw_score += 10
    else:
        checks["language_locale"] = {"found": False, "points": 0}

    # --- 7. Empty/null input handling (10 pts) ---
    empty_match = _RE_SP_EMPTY_INPUT.search(prose)
    if empty_match:
        # Anti-gaming: must specify the response, not just mention empty
        if _RE_EMPTY_WITH_RESPONSE.search(prose):
            checks["empty_input"] = {"found": True, "points": 10}
            raw_score += 10
        else:
            # Check full content too (response format may be in code block)
            if _RE_EMPTY_WITH_RESPONSE.search(content):
                checks["empty_input"] = {"found": True, "points": 10}
                raw_score += 10
            else:
                checks["empty_input"] = {"found": True, "points": 5, "note": "no_response_specified"}
                raw_score += 5
                issues.append("empty_input_no_response: empty handling without specifying response")
    else:
        checks["empty_input"] = {"found": False, "points": 0}

    # --- 8. Rate/limit awareness (5 pts) ---
    if _RE_SP_RATE_LIMIT.search(prose):
        checks["rate_limit"] = {"found": True, "points": 5}
        raw_score += 5
    else:
        checks["rate_limit"] = {"found": False, "points": 0}

    # --- 9. Graceful degradation (10 pts) ---
    if _RE_SP_GRACEFUL_DEGRADE.search(prose) or _RE_GRACEFUL_DEGRADE_EXT.search(prose):
        checks["graceful_degradation"] = {"found": True, "points": 10}
        raw_score += 10
    else:
        checks["graceful_degradation"] = {"found": False, "points": 0}

    # --- 10. Non-obvious examples (15 pts) ---
    nonobvious_count = _count_nonobvious_examples(content)
    if nonobvious_count >= 2:
        checks["nonobvious_examples"] = {"found": True, "points": 15, "count": nonobvious_count}
        raw_score += 15
    elif nonobvious_count == 1:
        checks["nonobvious_examples"] = {"found": True, "points": 7, "count": 1, "note": "only_1_example"}
        raw_score += 7
    else:
        checks["nonobvious_examples"] = {"found": False, "points": 0, "count": 0}

    # Cap at 100 (max theoretical is 105)
    final_score = max(0, min(100, raw_score))
    return {"score": final_score, "issues": issues, "details": {"checks": checks}}
