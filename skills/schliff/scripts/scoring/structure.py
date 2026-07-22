"""Score structural quality of a skill file.

Checks frontmatter, length, examples, headers, progressive disclosure,
imperative voice, referenced files, and dead content.
"""
import re
from bisect import bisect_right
from pathlib import Path

from scoring.patterns import (
    _RE_CODE_BLOCKS,
    _RE_FRONTMATTER_DESC,
    _RE_FRONTMATTER_NAME,
    _RE_HEADERS,
    _RE_HEDGING,
    _RE_REAL_EXAMPLES,
    _RE_REFS,
    _RE_SECTION_HEADER,
    _RE_TODO,
)
from shared import read_skill_safe, strip_frontmatter

# Progressive-disclosure signal (#10, content-only): the SKILL.md POINTS the reader
# to external detail. Two byte-verifiable forms, unioned by _disclosure_refs:
#  (1) a markdown link to a LOCAL .md file  ](./x.md) / ](references/x.md)  — not http/anchor
#  (2) a references/ path in a link/backtick/see-read-load verb (non-.md resources)
# A bare `scripts/build` build-command mention does NOT count (it is code, not disclosure).
_RE_MD_LINK = re.compile(r"\]\(\s*(?!https?:|#)([\w./-]+\.md)\s*\)", re.I)
_RE_REF_PATH = re.compile(r"(?:\]\(|`|\bsee\s+|\bread\s+|\bload\s+)(references/[\w./-]+)", re.I)


def _disclosure_refs(content: str) -> set:
    """Distinct local-detail pointers declared in the content (see regexes above)."""
    return set(_RE_MD_LINK.findall(content)) | set(_RE_REF_PATH.findall(content))


def _refs_verifiable(skill_dir: Path) -> bool:
    """A reference can only be PROVEN dangling from a real on-disk location. Positive
    evidence of one: a references/ dir, or a .claude-plugin / .git ancestor. A bare
    mkdtemp (playground/badge) or a normalized temp copy (non-skill.md) has none, so
    dangling is unprovable and never claimed — a false dangling burns the artifact
    (the command_resolution doctrine)."""
    if (skill_dir / "references").is_dir():
        return True
    for anc in [skill_dir, *skill_dir.parents]:
        if (anc / ".claude-plugin").is_dir() or (anc / ".git").exists():
            return True
    return False


def _ref_resolves(ref: str, skill_dir: Path) -> bool:
    """A referenced resource path resolves if it exists relative to the skill
    directory (canonical self-contained skill) OR relative to an enclosing
    plugin/repo root. The latter covers the common monorepo/plugin layout where
    skills share a single root-level ``references/`` directory — without it the
    linter false-flags valid references as missing. Only widens resolution, so
    it can never miss a genuinely-absent file.

    Security: a ref is confined to its base directory. Any ``..`` segment is
    rejected outright and every candidate must resolve back inside its base, so a
    crafted ref like ``references/../../../etc/passwd`` cannot turn the linter into
    a filesystem existence oracle when an untrusted SKILL.md is scored locally."""
    if ".." in Path(ref).parts:
        return False

    def _within(base: Path) -> bool:
        try:
            base_r = base.resolve()
            cand = (base_r / ref).resolve()
        except OSError:
            return False
        return cand.is_relative_to(base_r) and cand.exists()

    if _within(skill_dir):
        return True
    for anc in skill_dir.parents:
        if (anc / ".claude-plugin").is_dir() or (anc / ".git").exists():
            if _within(anc):
                return True
    return False


def score_structure(skill_path: str) -> dict:
    """Score structural quality of a skill file.

    Uses inline Python analysis directly — no external bash dependency.
    """
    return _score_structure_inline(skill_path)


def _score_structure_inline(skill_path: str) -> dict:
    """Score structural quality of a SKILL.md file."""
    score = 0
    issues = []

    try:
        content = read_skill_safe(skill_path)
    except (FileNotFoundError, ValueError):
        return {"score": 0, "issues": ["file_not_found"], "details": {}}

    # Early return for empty or nearly empty skill bodies
    body = strip_frontmatter(content)
    if len(body.strip()) < 10:
        return {"score": 0, "issues": ["empty_skill_body"], "details": {}}

    lines = content.split("\n")

    # Frontmatter
    # Tolerate a leading UTF-8 BOM (U+FEFF) so files saved by Windows/cross-platform
    # editors are not silently denied the frontmatter delimiter match. read_skill_safe
    # decodes with plain "utf-8" and does not strip a BOM, which would otherwise make
    # lines[0].strip() == "﻿---" != "---" and drop up to 30 structure points.
    if lines and lines[0].lstrip("﻿").strip() == "---":
        score += 10
        if _RE_FRONTMATTER_NAME.search(content):
            score += 10
        else:
            issues.append("missing_name")
        if _RE_FRONTMATTER_DESC.search(content):
            score += 10
        else:
            issues.append("missing_description")
    else:
        issues.append("no_frontmatter")

    # Length
    if len(lines) <= 500:
        score += 10
    elif len(lines) <= 700:
        score += 5
        issues.append("long_skill_md")

    # Examples — match the improved bash script logic
    real_examples = len(_RE_REAL_EXAMPLES.findall(content))
    code_block_pairs = len(_RE_CODE_BLOCKS.findall(content)) // 2
    if real_examples >= 2:
        score += 10
    elif real_examples >= 1 or code_block_pairs // 3 >= 2:
        score += 5
        if real_examples == 0:
            issues.append("no_real_examples")
    else:
        issues.append("no_real_examples")

    # Headers — only count non-empty sections (anti-gaming)
    # Precompute newline offsets once so each header's line number is a single
    # bisect instead of an O(n) prefix slice+count (avoids O(headers * file-size)).
    newline_offsets = [m for m, ch in enumerate(content) if ch == "\n"]
    all_headers = list(_RE_HEADERS.finditer(content))
    header_count = 0
    for h_match in all_headers:
        h_line = bisect_right(newline_offsets, h_match.start() - 1)
        # Check next 5 lines for actual content (not blank or another header)
        has_content = False
        for j in range(h_line + 1, min(h_line + 6, len(lines))):
            stripped = lines[j].strip()
            if stripped and not stripped.startswith("#"):
                has_content = True
                break
        if has_content:
            header_count += 1
    if header_count >= 3:
        score += 10
    elif header_count >= 1:
        score += 5

    # Progressive disclosure — credited from CONTENT (the skill links external
    # detail), not from an on-disk references/ dir, so the score is reproducible
    # across contexts (#10). A long skill that points readers to detail files is
    # practicing disclosure in its bytes; a references/ dir it never links is
    # invisible to the reader and earns nothing.
    skill_dir = Path(skill_path).parent
    disclosure = _disclosure_refs(content)
    if len(lines) <= 200 or len(disclosure) >= 2:
        score += 15
    elif len(disclosure) == 1:
        score += 10
        issues.append("thin_progressive_disclosure")
    else:
        score += 5
        issues.append("no_progressive_disclosure")

    # Imperative voice
    hedge_count = len(_RE_HEDGING.findall(content))
    if hedge_count == 0:
        score += 5
    elif hedge_count <= 2:
        score += 3

    # Referenced files — credited from CONTENT (declared refs), never from on-disk
    # existence, so the score is reproducible (#10). Declaration alone cannot be
    # farmed: traversal tokens and ref-stuffing get only the neutral credit.
    refs = set(_RE_REFS.findall(content))
    if not refs:
        # No references declared — neutral score (not rewarded, not penalized)
        score += 5
    elif any(".." in Path(r).parts for r in refs) or len(refs) > 32:
        # Traversal ('..') or excessive ref-stuffing — neutral credit, no on-disk
        # resolution attempted (the linter can never become a filesystem oracle).
        score += 5
        issues.append("malformed_or_excessive_refs")
    else:
        # References declared and well-formed — content credit.
        score += 10
        # Dangling detection is a NON-scoring lint issue, emitted only from a
        # provable on-disk location (never in an isolated/temp context).
        if _refs_verifiable(skill_dir):
            missing = sorted(r for r in refs if not _ref_resolves(r, skill_dir))
            if missing:
                issues.append(f"missing_refs: {missing}")

    # No dead content (TODO/FIXME/placeholder, empty sections)
    todo_count = len(_RE_TODO.findall(content))
    # Check for headers followed by only blank lines or next header
    empty_sections = 0
    for i, line in enumerate(lines):
        if _RE_SECTION_HEADER.match(line):
            # Look at next 5 non-empty lines
            next_content = 0
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].strip() and not lines[j].startswith("#"):
                    next_content += 1
            if next_content == 0:
                empty_sections += 1
    if todo_count == 0 and empty_sections == 0:
        score += 10
    elif todo_count == 0:
        score += 7
        issues.append(f"has_empty_sections:{empty_sections}")
    else:
        issues.append(f"has_todo_or_placeholder_text:{todo_count}")
        if empty_sections > 0:
            issues.append(f"has_empty_sections:{empty_sections}")

    return {"score": max(0, min(100, score)), "issues": issues, "details": {"line_count": len(lines)}}
