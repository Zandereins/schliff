#!/usr/bin/env python3
"""Schliff — Shared Utilities

Centralized constants, file I/O, and common helpers.
Single source of truth — imported by all scoring and analysis modules.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

# Allowlist of hosts permitted for --url fetching
_URL_ALLOWED_HOSTS = frozenset({
    "github.com",
    "raw.githubusercontent.com",
    "gitlab.com",
    "bitbucket.org",
})

# Maximum skill file size (1 MB) to prevent DoS via large inputs
MAX_SKILL_SIZE = 1_000_000

# Maximum entries in the file cache to prevent unbounded memory growth
MAX_CACHE_ENTRIES = 500

# Module-level file cache to avoid redundant reads within a single invocation
_file_cache: dict[str, str] = {}

# Known scoring dimensions for validation
VALID_DIMENSIONS = {
    "structure", "triggers", "quality", "edges",
    "efficiency", "composability", "clarity", "runtime",
    "security", "operational_coverage",
}

# Directories to skip during discovery (common non-source dirs).
# Shared by sync.py, doctor.py, skill_mesh.py, and any future tree walkers.
#
# `site-packages`, `.cache` and `.vercel` were added 2026-08-13: an installed copy of a
# skill is not an installed skill. Measured in this repo, `schliff doctor .` reported
# three vendored copies of the same SKILL.md — two under site-packages, one in a uv
# cache archive at `.vercel/python/cache/uv/archive-v0/…` where neither `.venv` nor
# `site-packages` appears in the path. See
# docs/specs/2026-08-13-doctor-counts-vendored-skills.md.
EXCLUDED_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".tox", "dist", "build", ".eggs",
    "site-packages", ".cache", ".vercel",
})

# --- Regex for description extraction ---
_RE_DESC_BLOCK = re.compile(
    r"^description:\s*[>|]-?\s*\n((?:[ \t]+.+\n)*)", re.MULTILINE
)
_RE_DESC_INLINE = re.compile(r'^description:\s*"?(.+?)"?\s*$', re.MULTILINE)

# Regex complexity validation patterns (used by validate_regex_complexity)
_RE_NESTED_QUANT = re.compile(r'[+*]\)?[+*?{]')
_RE_OVERLAP_QUANT = re.compile(r'\((?!\?:)[^)]*\|[^)]*\)[+*]{1,2}')
_RE_GROUP_INNER_QUANT = re.compile(r'\([^)]*[.][*+][^)]*\)[+*?{]')


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter (---...---) from skill content."""
    # A leading UTF-8 BOM (U+FEFF) is an invisible encoding artifact. Without
    # stripping it, the bare startswith("---") check fails and the frontmatter
    # leaks into the body, perturbing body-sensitive dimensions (composability,
    # efficiency) and breaking BOM-invariant scoring. Mirrors the same fix in
    # security._extract_frontmatter and structure.py.
    content = content.lstrip("﻿")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end >= 4:
            return content[end + 3:].lstrip("\n")
    return content


def invalidate_cache(skill_path: str) -> None:
    """Invalidate the file cache for a given skill path."""
    key = str(Path(skill_path).resolve())
    _file_cache.pop(key, None)


def read_skill_safe(skill_path: str) -> str:
    """Read a skill file with size limit enforcement and caching.

    Reads first, then checks size (avoids TOCTOU race condition).
    Symlinks are resolved (via Path.resolve) and the real target is validated
    to be a regular file. Skill files are commonly symlinked by dotfile
    managers (stow/chezmoi), ``claude --worktree`` setups, and shared
    ``~/.claude/skills`` layouts, so they are followed rather than rejected;
    the resolved target must still be an existing, non-directory regular file.
    """
    raw = Path(skill_path)
    p = raw.resolve()
    key = str(p)
    if key in _file_cache:
        return _file_cache[key]
    if not p.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")
    if p.is_dir():
        raise ValueError(f"Skill path is a directory, not a file: {skill_path}")
    if not p.is_file():
        raise ValueError(f"Skill path is not a regular file: {skill_path}")
    content = p.read_text(encoding="utf-8", errors="replace")
    # Strip ALL leading UTF-8 BOMs (U+FEFF) once, at the read boundary, so no
    # downstream scorer ever sees one. A leading BOM is an invisible encoding
    # artifact; left in place it defeats every `startswith("---")` frontmatter
    # check (structure, composability, efficiency, security-domain), making the
    # same file score differently with/without a BOM — a determinism break. We
    # lstrip rather than strip a single char so a (degenerate) multi-BOM prefix
    # collapses to body too, and any residual U+FEFF is genuinely mid-content
    # where the obfuscation detector still flags it. Root-cause fix; per-scorer
    # strips remain as defense for direct callers.
    content = content.lstrip("﻿")
    if len(content) > MAX_SKILL_SIZE:
        raise ValueError(
            f"file too large: {len(content):,} bytes "
            f"exceeds the {MAX_SKILL_SIZE:,} byte limit"
        )
    if len(_file_cache) >= MAX_CACHE_ENTRIES:
        _file_cache.pop(next(iter(_file_cache)))
    _file_cache[key] = content
    return content


def extract_description(content: str) -> str:
    """Extract the description field from YAML frontmatter.

    Handles inline, block scalar (> and |) formats.
    """
    match = _RE_DESC_BLOCK.search(content)
    if match:
        return match.group(1).strip()
    match = _RE_DESC_INLINE.search(content)
    if match:
        return match.group(1).strip()
    return ""


def estimate_token_cost(skill_path: str) -> int:
    """Estimate token cost when this skill is loaded into context.

    Counts words in SKILL.md + all files in references/ directory.
    Uses 1.3 tokens/word approximation (standard for English text with code).
    Returns estimated token count.
    """
    total_words = 0

    # Read SKILL.md content
    try:
        content = read_skill_safe(skill_path)
        total_words += len(content.split())
    except (FileNotFoundError, ValueError):
        return 0

    # Check for references/ directory alongside SKILL.md
    refs_dir = Path(skill_path).parent / "references"
    if refs_dir.is_dir() and not refs_dir.is_symlink():
        for ref_file in sorted(refs_dir.glob("*.md")):
            if ref_file.is_symlink():
                continue
            try:
                ref_content = ref_file.read_text(encoding="utf-8", errors="replace")
                if len(ref_content) <= MAX_SKILL_SIZE:
                    total_words += len(ref_content.split())
            except (OSError, PermissionError):
                continue

    return round(total_words * 1.3)


def skill_payload_digest(skill_path: str) -> str:
    """Identity of an installed skill: everything a doctor row is derived from.

    That is SKILL.md, its ``references/*.md``, and ``eval-suite.json`` — the file
    list ``estimate_token_cost`` charges for, plus the one ``load_eval_suite``
    reads. The suite is fetched through that loader rather than re-discovered, so
    the two cannot drift; the references walk mirrors the cost walk, guard for
    guard.

    Scope, stated exactly: this covers what the SCORE and the COST are derived
    from. The ``Issues`` column can still differ between two copies with the same
    digest — ``structure``'s dangling-reference lint resolves declared paths like
    ``scripts/run.py`` against the skill directory and its plugin/git ancestors,
    which are outside this domain. Measured over the 20 real duplicate groups: 0
    divergences today, and the lint does not score. A digest whose domain is smaller than the quantities it indexes is not
    a simpler key, it is a wrong one; that was got wrong once per quantity, and
    both mistakes are recorded with their measurements in docs/specs/2026-08-13-doctor-counts-vendored-skills.md,
    "Amendment 2026-08-26". Not restated here.

    Returns an empty string when SKILL.md cannot be read, so an unreadable skill
    never collapses onto another.
    """
    path = Path(skill_path)
    digest = hashlib.sha256()

    def _absorb(label: str, text: str) -> None:
        # Length-prefixed: without a separator, a file named `b.md` holding "X"
        # and a file `a.md` holding "Xb.md" hash the same, so two unrelated
        # skills would collapse and one would vanish from the report as a copy
        # of the other.
        blob = text.encode("utf-8")
        digest.update(f"{label}:{len(blob)}\0".encode("utf-8"))
        digest.update(blob)

    # read_skill_safe, not read_text: it strips the BOM, so the same skill saved
    # with and without one is one install rather than two.
    try:
        _absorb("SKILL.md", read_skill_safe(str(path)))
    except (OSError, PermissionError, FileNotFoundError, ValueError):
        return ""

    # Same traversal, same guards as estimate_token_cost: sorted for a stable
    # digest, symlinks skipped, oversized files ignored rather than hashed.
    refs_dir = path.parent / "references"
    if refs_dir.is_dir() and not refs_dir.is_symlink():
        for ref_file in sorted(refs_dir.glob("*.md")):
            if ref_file.is_symlink():
                continue
            try:
                ref_content = ref_file.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue
            if len(ref_content) <= MAX_SKILL_SIZE:
                _absorb(f"references/{ref_file.name}", ref_content)

    # Ask load_eval_suite itself rather than re-deriving its file discovery. The
    # first attempt copied the symlink guard from estimate_token_cost, but
    # load_eval_suite has no such guard — it follows the link. A stow/chezmoi
    # layout, where eval-suite.json is symlinked, was therefore scored but not
    # hashed, and the 4-of-7 and 7-of-7 copies collapsed again. Calling the real
    # loader makes the domains identical by construction, and keeps them
    # identical if its discovery ever changes.
    suite = load_eval_suite(str(path))
    if suite is not None:
        _absorb("eval-suite.json", json.dumps(suite, sort_keys=True, default=str))

    return digest.hexdigest()


def load_eval_suite(skill_path: str) -> Optional[dict]:
    """Auto-discover and load eval-suite.json from skill directory."""
    skill_dir = Path(skill_path).parent
    auto_path = skill_dir / "eval-suite.json"
    if auto_path.exists():
        try:
            raw = auto_path.read_text(encoding="utf-8")
            if len(raw) > MAX_SKILL_SIZE:
                print(f"Warning: eval-suite.json exceeds {MAX_SKILL_SIZE} bytes, skipping", file=sys.stderr)
                return None
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Warning: malformed eval-suite.json: {e}", file=sys.stderr)
    return None


def build_scores(skill_path: str, eval_suite: Optional[dict] = None,
                  include_runtime: bool = False, fmt: Optional[str] = None,
                  include_security: bool = False) -> dict:
    """Build the standard scoring dict for a skill.

    Centralizes the dimension-scoring calls used by score, badge, and doctor.
    Uses the scorer registry as single source of truth for which dimensions
    to score per format. Supports non-SKILL.md formats (CLAUDE.md, .cursorrules,
    AGENTS.md) by normalizing content to SKILL.md shape before scoring.

    Args:
        eval_suite: Optional eval suite dict for trigger/quality/edge scoring.
        include_runtime: Whether to include the runtime dimension (opt-in).
        fmt: Optional format override. When provided, skips auto-detection.
        include_security: Whether to include the security dimension (opt-in).
    """
    import os
    import tempfile

    from scoring.formats import detect_format, normalize_content
    from scoring.registry import get_scorers, resolve_format

    if fmt is None:
        fmt = detect_format(skill_path)

    # Canonicalize ONCE, then branch only on the canonical name. `fmt` may be a
    # public `--format` alias (`skill`, `system-prompt`, ...), and every branch
    # below used to compare the raw string — so an alias took a different path
    # than its canonical twin. That cost `system-prompt` the security dimension
    # (#168) and sent `skill` through a normalization branch that `skill.md`
    # skips, inventing synthetic frontmatter and inflating a frontmatter-less
    # file by 4.7-5.5 composite points. `detect_format` already returns canonical
    # names, so this is a strict no-op on the detected path — including the
    # playground, which only ever passes detected formats.
    fmt = resolve_format(fmt)

    # System prompts: no normalization, no temp file, dedicated scorer set
    if fmt == "system_prompt":
        scores = {}
        for dim in get_scorers("system_prompt"):
            scores[dim] = _call_scorer(dim, skill_path, None)
        return scores

    tmp_path: Optional[str] = None
    try:
        if fmt != "skill.md":
            content = read_skill_safe(skill_path)
            normalized = normalize_content(content, fmt)
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            )
            tmp.write(normalized)
            tmp.close()
            tmp_path = tmp.name
            skill_path = tmp_path  # scorers now see normalized content

        scorers = get_scorers(fmt)
        scores = {}

        for dim in scorers:
            # Skip opt-in dimensions unless explicitly requested
            if dim == "runtime" and not include_runtime:
                continue
            if dim == "security" and not include_security:
                continue

            scores[dim] = _call_scorer(dim, skill_path, eval_suite)

        return scores
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# Scorer dimension → (module_path, function_name) mapping.
# Module-level to avoid per-call dict reconstruction.
_SCORER_MAP: dict[str, tuple[str, str]] = {
    "structure": ("scoring.structure", "score_structure"),
    "operational_coverage": ("scoring.operational_coverage", "score_operational_coverage"),
    "triggers": ("scoring.triggers", "score_triggers"),
    "quality": ("scoring.quality", "score_quality"),
    "edges": ("scoring.edges", "score_edges"),
    "efficiency": ("scoring.efficiency", "score_efficiency"),
    "composability": ("scoring.composability", "score_composability"),
    "clarity": ("scoring.clarity", "score_clarity"),
    "security": ("scoring.security", "score_security"),
    "runtime": ("scoring.runtime", "score_runtime"),
    "structure_prompt": ("scoring.structure_prompt", "score_structure_prompt"),
    "output_contract": ("scoring.output_contract", "score_output_contract"),
    "completeness": ("scoring.completeness", "score_completeness"),
}

# Scorers that accept (skill_path, eval_suite) instead of just (skill_path)
_EVAL_SUITE_SCORERS = frozenset({"triggers", "quality", "edges"})


def _call_scorer(dim: str, skill_path: str, eval_suite) -> dict:
    """Call a single scorer by dimension name.

    Uses lazy imports via importlib (cached in sys.modules after first call).
    """
    import importlib

    if dim not in _SCORER_MAP:
        raise ValueError(f"Unknown scorer dimension: {dim}")

    module_path, func_name = _SCORER_MAP[dim]
    mod = importlib.import_module(module_path)
    func = getattr(mod, func_name)

    if dim in _EVAL_SUITE_SCORERS:
        return func(skill_path, eval_suite)
    elif dim == "runtime":
        return func(skill_path, eval_suite, enabled=False)
    else:
        return func(skill_path)


def validate_regex_complexity(pattern: str, max_length: int = 500) -> tuple[bool, str]:
    """Reject regex patterns with catastrophic backtracking potential.

    Returns (is_safe, reason).
    """
    if len(pattern) > max_length:
        return False, f"pattern too long ({len(pattern)} > {max_length})"

    if _RE_NESTED_QUANT.search(pattern):
        return False, "nested quantifiers detected (potential ReDoS)"
    if _RE_OVERLAP_QUANT.search(pattern):
        return False, "overlapping alternation with quantifier (potential ReDoS)"
    if _RE_GROUP_INNER_QUANT.search(pattern):
        return False, "dot-wildcard quantifier inside repeated group (potential ReDoS)"

    return True, "ok"


def regex_search_safe(pattern: str, text: str, timeout: int = 2) -> bool:
    """Regex search with timeout to prevent ReDoS from user-supplied patterns.

    Runs the regex in a daemon thread with a timeout. Returns False on
    timeout, invalid pattern (re.error), or no match. This approach is
    thread-safe (unlike SIGALRM which is per-process) and portable across
    all platforms.
    """
    result: list[bool] = [False]
    error: list[Exception | None] = [None]

    def _search() -> None:
        try:
            result[0] = bool(re.search(pattern, text, re.IGNORECASE))
        except re.error as e:
            error[0] = e

    t = threading.Thread(target=_search, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        print(
            f"Warning: regex timed out after {timeout}s on pattern "
            f"'{pattern[:60]}'",
            file=sys.stderr,
        )
        return False
    if error[0] is not None:
        return False
    return result[0]


def load_jsonl_safe(path: str | Path, max_size: int = 10_000_000) -> list[dict]:
    """Safely load a JSONL file with size limit and malformed-line tolerance.

    Reads first, then checks size (avoids TOCTOU race condition).
    Returns a list of parsed JSON objects. Skips malformed lines silently.
    """
    p = Path(path)
    if not p.exists():
        return []
    try:
        raw = p.read_text(encoding="utf-8")
        if len(raw) > max_size:
            return []
        lines = raw.splitlines()
    except OSError:
        return []

    results = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return results


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate scheme and host on every redirect hop to prevent SSRF."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https":
            raise ValueError(f"Redirect to non-HTTPS blocked: {newurl}")
        host = (parsed.hostname or "").lower()
        if host not in _URL_ALLOWED_HOSTS:
            raise ValueError(f"Redirect to disallowed host blocked: {host}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_url_safe(url: str, max_bytes: int = 500_000) -> str:
    """Fetch a URL safely with security restrictions.

    - HTTPS only (no HTTP)
    - Host allowlist: github.com, raw.githubusercontent.com, gitlab.com, bitbucket.org
    - Max response size: 500KB
    - Timeout: 10 seconds
    - Returns content as string
    - Raises ValueError for security violations
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme != "https":
        raise ValueError(
            f"Only HTTPS URLs are allowed (got scheme '{parsed.scheme}'): {url}"
        )

    host = parsed.hostname
    if host is None:
        raise ValueError(f"No hostname in URL: {url}")
    host = host.lower()

    if host not in _URL_ALLOWED_HOSTS:
        raise ValueError(
            f"Host '{host}' is not in the allowed list "
            f"({', '.join(sorted(_URL_ALLOWED_HOSTS))}): {url}"
        )

    # Use a custom opener that re-validates scheme + host on every redirect
    opener = urllib.request.build_opener(_SafeRedirectHandler)
    try:
        with opener.open(url, timeout=10) as response:  # noqa: S310
            # Honour Content-Length if present to avoid reading oversized responses
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    cl_int = int(content_length)
                except ValueError:
                    cl_int = 0  # treat unparseable Content-Length as absent
                if cl_int > max_bytes:
                    raise ValueError(
                        f"Response too large: Content-Length {content_length} "
                        f"exceeds limit of {max_bytes} bytes"
                    )
            data = response.read(max_bytes + 1)
    except urllib.error.URLError as exc:
        # Unwrap redirect-handler security errors for clear messaging
        cause = getattr(exc, "reason", None)
        if isinstance(cause, ValueError):
            raise cause from exc
        raise ValueError(f"Failed to fetch URL: {exc}") from exc

    if len(data) > max_bytes:
        raise ValueError(
            f"Response too large: received more than {max_bytes} bytes from {url}"
        )

    return data.decode("utf-8", errors="replace")


# --- Security: Command validation for autonomous execution ---
_COMMAND_BLOCKLIST_PATTERNS = [
    r'\brm\s+(-[a-zA-Z]*[rRf])', r'\bcurl\b', r'\bwget\b', r'\bnc\b', r'\bncat\b',
    r'\bchmod\b', r'\bchown\b', r'\bdd\b', r'\bmkfs\b', r'\bsudo\b',
    r'`[^`]+`',  # backtick execution
    r'\|\s*(ba)?sh\b', r'\|\s*zsh\b',  # pipe to shell
    r'>\s*/dev/', r'>\s*/etc/', r'>\s*/tmp/',  # write to system dirs
    r'\beval\b', r'\bexec\b',
]
# Shell metacharacter patterns — block command chaining and subshells
_COMMAND_METACHAR_PATTERNS = [
    r';\s*\w',        # semicolon chaining
    r'&&\s*\w',       # AND chaining
    r'\|\|\s*\w',     # OR chaining
    r'\$\(',          # command substitution
    r'\n',            # newline injection
]
_COMMAND_BLOCKLIST_RE = [re.compile(p) for p in _COMMAND_BLOCKLIST_PATTERNS]
_COMMAND_METACHAR_RE = [re.compile(p) for p in _COMMAND_METACHAR_PATTERNS]

_COMMAND_ALLOWLIST_PREFIXES = (
    'python3 ', 'python ', 'bash scripts/', 'node ', 'grep ', 'wc ', 'jq ',
    'cat ', 'head ', 'tail ', 'sort ', 'uniq ', 'diff ', 'git ',
    'sh scripts/',
)


def validate_command_safety(cmd: str) -> tuple[bool, str]:
    """Validate a command is safe to run in autonomous mode.

    Returns (is_safe, reason). Always checks blocklist + metacharacters,
    even for allowlisted prefixes. Allowlist is necessary but not sufficient.

    NOTE: Currently not invoked by any runtime code path. Every
    ``subprocess.run(...)`` call in this codebase uses the list-form with
    hardcoded arguments, so there is no user-supplied command string to
    validate. This function is a reserved guardrail for future features
    that may execute user-supplied commands (e.g., custom eval-suite
    runners, plug-in scorers). Do not delete without adding a replacement
    for those future code paths. See CONTRIBUTING.md.
    """
    cmd_stripped = cmd.strip()
    if not cmd_stripped:
        return False, "empty command"

    # Always check metacharacters first — blocks command chaining regardless of prefix
    for pattern in _COMMAND_METACHAR_RE:
        if pattern.search(cmd_stripped):
            return False, f"blocked metacharacter: {pattern.pattern}"

    # Check if command starts with an allowed prefix
    is_allowlisted = False
    for prefix in _COMMAND_ALLOWLIST_PREFIXES:
        if cmd_stripped.startswith(prefix):
            is_allowlisted = True
            break

    if not is_allowlisted:
        return False, "command does not match any allowed prefix"

    # Block python -c (arbitrary code execution) even though python3 is allowlisted
    if re.match(r'^python3?\s+-[cmu]', cmd_stripped):
        return False, "blocked: python -c/-m/-u (use script path instead)"

    # Check blocklist even for allowlisted commands
    for pattern in _COMMAND_BLOCKLIST_RE:
        pat_str = pattern.pattern
        # Known false positive: \beval\b in "run-eval.sh", \bexec\b in "exec-task.sh"
        if pat_str in (r'\beval\b', r'\bexec\b'):
            # Only skip for file-path patterns (not -c inline code)
            if re.match(r'^(?:python3?|bash)\s+\S+\.(?:py|sh)', cmd_stripped):
                continue
        if pattern.search(cmd_stripped):
            return False, f"blocked pattern: {pat_str}"

    return True, "allowed prefix"
