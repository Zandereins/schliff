"""Deterministic safety/gating guards for the LLM-judge layer.

STATUS: staged for the v8.1 judge harness — NOT yet wired into any live scoring
path. The judge is frozen (see judge/judge_v0.py); these helpers are designed to be
consulted by it when it resumes, NOT by the shipping deterministic linter /
`schliff score`. Their only current caller is the test suite. "default-on" below
describes the intended behavior inside the judge harness once wired, not behavior
on any user-facing score today.

These are NOT scored dimensions and carry no weight in the composite. They are
cheap, deterministic helpers:

- ``detect_destructive_commands`` — raises a human-review FLAG when an unguarded
  destructive/irreversible system command appears (e.g. ``echo b > /proc/sysrq-trigger``,
  grub ``mem=`` edits, ``rm -rf /``). Default-on within the judge harness (once wired)
  — unlike the opt-in ``security`` score, which also code-block-excludes such commands as "examples".
  That exclusion is exactly why the highest-blast-radius Phase-0 failure
  (skill 09 ``algorithms``) would be silently missed on a default run. A flag,
  not a penalty — asymmetric toward safety (a false flag costs one human glance).

- ``judge_floor`` — the GATING INVARIANT. The judge runs only on artifacts above
  a linter-completeness floor; below it (stubs, frontmatter-less dumps) the
  deterministic linter already scores ~0, so the judge must not be run and must
  not fabricate semantic findings (Phase-0 skills 08 stub, 10 dump;
  failure-mode-first doctrine, Husain/Shankar).

- ``detect_mixed_script`` — flags mixed/non-Latin scripts in the trigger surface
  (name / description / headers) that create retrieval ambiguity in an
  English-keyed system (Phase-0 skill 10, tri-script Thai/Chinese/English).

Provenance: ``docs/research/2026-04-28-skill-failure-modes.md`` → End Consolidation
→ "Deterministic (not LLM)". Human-ratified Phase-0 result, 2026-05-22.
"""
from __future__ import annotations

import re
import unicodedata

from shared import read_skill_safe

_READ_ERRORS = (FileNotFoundError, ValueError, PermissionError, OSError, RuntimeError)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _split_frontmatter(content: str) -> tuple[str | None, str]:
    """Return (frontmatter_without_delimiters, body). frontmatter is None if absent."""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[3:end], content[end + 4:]
    return None, content


def _line_at(content: str, pos: int) -> str:
    """Return the full line containing character position ``pos``."""
    start = content.rfind("\n", 0, pos) + 1
    end = content.find("\n", pos)
    return content[start:] if end == -1 else content[start:end]


# ---------------------------------------------------------------------------
# 1. Destructive-command detector (default-on → human-review flag)
# ---------------------------------------------------------------------------

# High-precision patterns for IRREVERSIBLE / system-mutating commands. Tuned for
# precision (this is a flag, but noise erodes trust); the two corpus anchors are
# `echo b > /proc/sysrq-trigger` (unsynced reboot) and grub `mem=` (boot footgun).
_DESTRUCTIVE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("sysrq_trigger", re.compile(r">\s*/proc/sysrq-trigger")),
    ("rm_rf", re.compile(r"\brm\s+-(?=[a-z]*r)(?=[a-z]*f)[a-z]+", re.I)),
    ("dd_to_device", re.compile(r"\bdd\b[^\n]*\bof=\s*/dev/")),
    ("mkfs", re.compile(r"\bmkfs(\.\w+)?\b")),
    ("fork_bomb", re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:")),
    ("chmod_777", re.compile(r"\bchmod\s+(-R\s+)?0?777\b")),
    ("grub_mem", re.compile(r"\bmem=\d+[KMG]?\b")),
    ("write_system_path", re.compile(r">\s*/(etc|boot)/")),
    ("disk_tool", re.compile(r"\b(wipefs|fdisk|parted)\b")),
    ("recursive_chown_system", re.compile(r"\bchown\s+-R\b[^\n]*\s/(etc|usr|var|boot)\b")),
]

# A destructive command is "guarded" if a negation/warning sits on its line or
# the line immediately above (warnings commonly precede a code fence).
_GUARD_RE = re.compile(
    r"(?i)\b(never|don'?t|do\s+not|avoid|must\s+not|should\s+not|warning|danger(ous)?|"
    r"caution|careful|irreversible|destroys?|wipes?|do\s+NOT)\b"
)


def _is_guarded(content: str, match_start: int) -> bool:
    """True if a negation/warning sits on the match line or on the single
    immediately-preceding content line (blank lines and ``` fence markers are
    skipped — warnings commonly sit just above a code fence, not on the command
    line itself).

    The window is intentionally ONE content line, not a rolling multi-line
    window: a guard must directly precede the command it covers, so a single
    unrelated warning cannot mask every destructive command below it."""
    line_start = content.rfind("\n", 0, match_start) + 1
    preceding = content[:line_start].rstrip("\n").split("\n") if line_start else []
    window_lines: list[str] = []
    for ln in reversed(preceding):
        stripped = ln.strip()
        if not stripped or stripped.startswith("```"):
            continue
        window_lines.append(ln)
        break
    window_lines.append(_line_at(content, match_start))
    return bool(_GUARD_RE.search(" ".join(window_lines)))


def detect_destructive_commands(skill_path: str) -> dict:
    """Default-on detector: flag unguarded destructive/irreversible commands.

    Unlike ``score_security``, this does NOT code-block-exclude — a cheatsheet that
    lists ``rm -rf /`` as a neutral tip inside a fence is exactly the failure mode.
    Returns ``{flag, matches, unguarded_count, recommendation}``. ``flag`` is True
    iff at least one *unguarded* destructive command is present.
    """
    try:
        content = read_skill_safe(skill_path)
    except _READ_ERRORS as e:
        return {"flag": False, "matches": [], "unguarded_count": 0,
                "recommendation": "", "error": str(e)}

    matches: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for kind, pat in _DESTRUCTIVE_PATTERNS:
        for m in pat.finditer(content):
            key = (kind, m.start())
            if key in seen:
                continue
            seen.add(key)
            matches.append({
                "kind": kind,
                "line": _line_at(content, m.start()).strip()[:120],
                "guarded": _is_guarded(content, m.start()),
            })

    unguarded = [x for x in matches if not x["guarded"]]
    return {
        "flag": bool(unguarded),
        "matches": matches,
        "unguarded_count": len(unguarded),
        "recommendation": (
            "human-review: unguarded destructive/irreversible command(s) present"
            if unguarded else ""
        ),
    }


# ---------------------------------------------------------------------------
# 2. Gating invariant — judge runs only above a linter-completeness floor
# ---------------------------------------------------------------------------

MIN_BODY_WORDS = 30  # below this the artifact is a stub; the linter already scores ~0


def judge_floor(skill_path: str) -> dict:
    """Gating invariant: is the artifact above the linter-completeness floor?

    The LLM-judge must NOT run below the floor — the deterministic linter already
    scores stubs/dumps ~0, and running the judge there fabricates semantic findings.
    Above-floor requires: valid frontmatter with non-empty name + description, and
    a body of at least ``MIN_BODY_WORDS`` words. Returns
    ``{above_floor, reasons, body_words}``; ``reasons`` lists why it failed.
    """
    try:
        content = read_skill_safe(skill_path)
    except _READ_ERRORS as e:
        return {"above_floor": False, "reasons": [f"unreadable: {e}"], "body_words": 0}

    reasons: list[str] = []
    fm, body = _split_frontmatter(content)
    if fm is None:
        reasons.append("no_frontmatter")
    else:
        if not re.search(r"(?m)^name:\s*\S", fm):
            reasons.append("no_name")
        if not re.search(r"(?m)^description:\s*\S", fm):
            reasons.append("no_description")

    body_words = len(body.split())
    if body_words < MIN_BODY_WORDS:
        reasons.append(f"body_too_short({body_words}w<{MIN_BODY_WORDS})")

    return {"above_floor": not reasons, "reasons": reasons, "body_words": body_words}


# ---------------------------------------------------------------------------
# 3. Mixed-script trigger-surface check
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"(?m)^#{1,3}\s+(.+)$")
_CJK_SCRIPTS = ("CJK", "HIRAGANA", "KATAKANA")
_KNOWN_SCRIPTS = ("LATIN", "THAI", "CYRILLIC", "ARABIC", "HEBREW", "DEVANAGARI",
                  "GREEK", "HANGUL") + _CJK_SCRIPTS


def _script_of(ch: str) -> str | None:
    """Classify an alphabetic char into a broad script name, or None."""
    if not ch.isalpha():
        return None
    name = unicodedata.name(ch, "")
    for s in _KNOWN_SCRIPTS:
        if s in name:
            return "CJK" if s in _CJK_SCRIPTS else s
    return "OTHER"


def detect_mixed_script(skill_path: str) -> dict:
    """Flag ≥2 distinct major scripts in the trigger surface (name/description/headers).

    Mixed scripts there fragment retrieval in an English-keyed system (Phase-0
    skill 10: Thai + Chinese + English headers). Returns
    ``{flag, scripts, trigger_surface_scripts}``.
    """
    try:
        content = read_skill_safe(skill_path)
    except _READ_ERRORS as e:
        return {"flag": False, "scripts": {}, "trigger_surface_scripts": [], "error": str(e)}

    fm, body = _split_frontmatter(content)
    surface: list[str] = []
    if fm:
        for key in ("name", "description"):
            mm = re.search(rf"(?m)^{key}:\s*(.+)", fm)
            if mm:
                surface.append(mm.group(1))
    surface.extend(_HEADER_RE.findall(body))

    counts: dict[str, int] = {}
    for ch in " ".join(surface):
        s = _script_of(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1

    # A script "counts" only if it appears ≥2 times (ignore stray accents/symbols).
    major = sorted(s for s, c in counts.items() if c >= 2 and s != "OTHER")
    return {
        "flag": len(major) >= 2,
        "scripts": counts,
        "trigger_surface_scripts": major,
    }


# ---------------------------------------------------------------------------
# Convenience: run all default-on guards
# ---------------------------------------------------------------------------

def run_guards(skill_path: str) -> dict:
    """Run all default-on deterministic guards for one artifact."""
    return {
        "destructive_commands": detect_destructive_commands(skill_path),
        "judge_floor": judge_floor(skill_path),
        "mixed_script": detect_mixed_script(skill_path),
    }
