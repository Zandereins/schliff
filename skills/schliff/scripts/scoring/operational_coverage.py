"""operational_coverage (opcov) scorer for AGENTS.md.

Measures whether an AGENTS.md actually equips a coding agent to operate the
repo: runnable setup/build/test commands plus code-style, PR/commit, and
gotcha guidance. Credit is driven by the COMMAND itself (heading is never a
gate), bundled with the §4.2/§4.3 hardening so decoupling does not amplify
gaming.

Spec: docs/specs/agents-md-operational-coverage.md.

Deterministic: pure stdlib (``re``), no clock / entropy / ambient state /
network reads. ``opcov(raw) == opcov(normalized)`` because ``strip_frontmatter``
removes the synthetic header ``normalize_content`` prepends, leaving the body
byte-identical.
"""
from __future__ import annotations

import re

from shared import read_skill_safe, strip_frontmatter

# --------------------------------------------------------------------------- #
# Categories & weights (binary per-category credit; score = sum of credited)
# --------------------------------------------------------------------------- #
_COMMAND_WEIGHTS = {"setup": 20, "build": 20, "test": 20}
_DIRECTIVE_WEIGHTS = {"code_style": 15, "gotchas": 15, "pr": 10}

# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"^([ \t]*)```([A-Za-z0-9_-]*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_INLINE_RE = re.compile(r"`([^`\n]+)`")
_FLAG_RE = re.compile(r"^-{1,2}[A-Za-z]")
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=")
_NEG_RE = re.compile(r"\b(do not|don'?t|dont|never|avoid|instead of)\b", re.IGNORECASE)
_FILE_EXT_RE = re.compile(r"\.(py|ts|tsx|js|jsx|rs|go|rb|java|md|json|sh)\b")

# An inline backtick span only counts toward the directive concreteness signal
# when it is a REAL code token, not prose dressed in cosmetic backticks. A code
# token carries a code-shape character (path/punctuation/operator), a digit,
# camelCase / CONSTANT_CASE, a file extension, or a registered tool name.
# Plain English words/phrases (`x`, `tidy`, `the vibe`) carry none of these and
# are rejected — closing the §4.3 platitude-over-credit hole (cosmetic backticks
# farming all 40 directive points).
_CODE_SHAPE_RE = re.compile(r"[._/:=()\[\]{}<>*|\\@#!+\-]")
_CAMEL_RE = re.compile(r"[a-z][A-Z]")
_CONST_CASE_RE = re.compile(r"\b[A-Z][A-Z0-9_]+\b")
_DIGIT_RE = re.compile(r"\d")
_ALNUM_RUN_RE = re.compile(r"[A-Za-z0-9]+")

_SHELL_LANGS = {
    "", "bash", "sh", "shell", "console", "zsh", "fish", "shellscript",
    "terminal", "shell-session", "ps1", "powershell",
}

# --------------------------------------------------------------------------- #
# Command classification token sets (§4.2 hardening)
# --------------------------------------------------------------------------- #
_JUNK = {
    "echo", "ls", "pwd", "cd", "true", "false", ":", "exit", "cat", "whoami",
    "date", "clear", "sleep", "head", "tail", "sort", "which",
}
_WRAPPERS = {"sudo", "command", "exec", "time", "env", "xargs", "nohup", "then", "do"}

# Verb-intrinsic tools: the tool name IS its family. May stand alone when fenced;
# inline must be command-shaped (bare single-token inline rejected).
_TEST_INTRINSIC = {
    "pytest", "vitest", "jest", "mocha", "tox", "nox", "ruff", "eslint", "mypy",
    "tsc", "prettier", "black", "flake8", "isort", "pyright", "nextest", "pre-commit",
}
_BUILD_INTRINSIC = {"vite", "webpack"}

# Runner verbs (strict tier): consume optional leading run|r then map a family token.
_RUNNER = {
    "npm", "pnpm", "yarn", "bun", "pip", "pip3", "uv", "uvx", "poetry", "pipenv",
    "pdm", "cargo", "dotnet", "gradle", "gradlew", "mvn", "deno", "turbo", "nx",
    "sbt", "nix", "zig", "mix", "dart", "flutter", "gleam",
}

# Guarded tier (English homonyms): credit only with a recognized subcommand/flag/path.
_GUARDED = {
    "go", "make", "just", "node", "python", "python3", "ruby", "swift", "task",
    "biome", "git", "gh", "rake", "bundle", "rails",
}

_SETUP_TOKENS = {
    "install", "i", "ci", "sync", "add", "bootstrap", "init", "setup",
    "restore", "develop", "deps", "get",
}
_BUILD_TOKENS = {
    "build", "compile", "dev", "serve", "start", "watch", "bundle", "dist", "package",
}
_TEST_TOKENS = {
    "test", "tests", "check", "checks", "lint", "lint:fix", "format", "fmt",
    "typecheck", "type-check", "e2e", "coverage", "validate", "verify", "ci",
    "clippy", "nextest", "spec", "specs",
}

_GIT_READONLY = {
    "status", "log", "diff", "show", "branch", "remote", "fetch", "blame", "reflog",
}
_INSPECT_FLAGS = {"-v", "-h", "--version", "--help"}
_STOPWORDS = {
    "to", "the", "it", "in", "of", "a", "an", "sure", "at", "your", "this",
    "that", "is", "we", "you", "and", "for", "with", "here",
}

# Tool-name set for the directive concreteness signal.
_ALL_TOOLS = (
    _TEST_INTRINSIC | _BUILD_INTRINSIC | _RUNNER | _GUARDED
    | {"docker", "kubectl", "helm", "podman", "django-admin", "nix-shell"}
)
_TOOL_RE = re.compile(
    r"\b(" + "|".join(sorted((re.escape(t) for t in _ALL_TOOLS), key=len, reverse=True))
    + r")\b"
)

# --------------------------------------------------------------------------- #
# Directive heading synonyms (directive credit needs a heading match, except
# code_style which also has a heading-agnostic content fallback).
# --------------------------------------------------------------------------- #
_DIRECTIVE_HEADING = {
    "code_style": [
        r"\bconvention", r"\bcode[\s-]?style\b", r"\bstyle\b", r"\bguideline",
        r"\bstandard", r"\bnaming\b", r"\bpreference", r"\bformatting\b",
    ],
    "gotchas": [
        r"\bgotcha", r"\bpitfall", r"\bcaveat", r"\bwarning", r"\btroubleshoot",
        r"\bknown issue", r"\bcommon (issue|problem|mistake)", r"\bimportant\b",
    ],
    "pr": [
        r"\bpull request", r"\bpr\b", r"\bcommit", r"\bcontribut",
        r"\bbefore committing", r"\bbranch",
    ],
}
_DIRECTIVE_HEADING_RE = {
    cat: [re.compile(p, re.IGNORECASE) for p in pats]
    for cat, pats in _DIRECTIVE_HEADING.items()
}

# Tightened NORMATIVE cue set (§4.3): the broad prototype set MINUS universal
# soft cues (use, value, ask, note, important, communicate, document, respect,
# write) so polished platitude prose ("we prefer readability") does not credit.
_NORMATIVE_RE = re.compile(
    r"\b(must|should|shall|never|always|do not|don'?t|avoid|prefer|"
    r"require[ds]?|requires|ensure|make sure|be sure|follow|run|keep|only|"
    r"sort(?:ed)?|format|naming|convention|commit|branch|rebase|squash|merge|"
    r"warning|caution|careful|gotcha|pitfall|wipes?|breaks?|fails?)\b",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Command extraction
# --------------------------------------------------------------------------- #

def _is_path(tok: str) -> bool:
    return ("/" in tok) or tok.startswith("./") or tok.endswith(".sh") or tok in (".", "..")


def _norm(seg: str) -> str:
    return " ".join(seg.lower().split())


def _split_segments(line: str):
    line = re.sub(r"^\s*[\$>#]\s+", "", line)
    return [s for s in re.split(r"&&|\|\||\||;", line) if s.strip()]


def _family_of(tok: str):
    t = tok.lower()
    base = t.split(":", 1)[0]
    for candidate in (t, base):
        if candidate in _SETUP_TOKENS:
            return "setup"
        if candidate in _BUILD_TOKENS:
            return "build"
        if candidate in _TEST_TOKENS:
            return "test"
    return None


def _script_family(name: str):
    n = name.lower()
    if n.startswith(("setup", "install", "bootstrap")):
        return "setup"
    if n.startswith(("build", "compile", "dist")):
        return "build"
    if n.startswith(("test", "check", "lint", "verify", "ci")):
        return "test"
    return None


def _is_readonly(verb: str, nonflag, args) -> bool:
    a0 = nonflag[0] if nonflag else None
    if verb == "git" and a0 in _GIT_READONLY:
        return True
    if verb == "docker" and a0 in {"ps", "images"}:
        return True
    if verb in {"npm", "pnpm", "yarn"} and a0 in {"ls", "list", "outdated", "view"}:
        return True
    if a0 in {"version", "help"}:
        return True
    for a in args:
        if _FLAG_RE.match(a):
            return a in _INSPECT_FLAGS
    return False


def _runner_family(verb: str, nonflag):
    if verb == "nix" and nonflag and nonflag[0] == "develop":
        return "setup"
    consumed_run = False
    a0 = nonflag[0] if nonflag else None
    if a0 in ("run", "r"):
        consumed_run = True
        a0 = nonflag[1] if len(nonflag) > 1 else None
    if a0 is None:
        return None
    fam = _family_of(a0)
    if fam:
        return fam
    # `uv run pytest` / `npm run jest` -> the delegated intrinsic tool's family.
    if a0 in _TEST_INTRINSIC:
        return "test"
    if a0 in _BUILD_INTRINSIC:
        return "build"
    # `npm run <unknown-script>` -> generic build/run
    return "build" if consumed_run else None


def _classify(seg: str, inline: bool):
    """Resolve a single command segment to a family ('setup'|'build'|'test') or None."""
    toks = seg.split()
    had_prompt = False
    i = 0
    while i < len(toks):
        t = toks[i]
        if _ENV_ASSIGN_RE.match(t):
            i += 1
            continue
        if t in ("$", "#", ">"):
            had_prompt = True
            i += 1
            continue
        if t in _WRAPPERS:
            i += 1
            continue
        break
    if i >= len(toks):
        return None

    verb_raw = toks[i]
    args = toks[i + 1:]
    verb = verb_raw.split("/")[-1].lower()

    nonflag = [a for a in args if not _FLAG_RE.match(a)]
    has_flag = any(_FLAG_RE.match(a) for a in args)
    has_path = any(_is_path(a) for a in [verb_raw] + args)
    has_colon = any(":" in a for a in nonflag)

    if verb in _JUNK:
        return None

    # Script delegation (conservative recall).
    if verb_raw.endswith(".sh") or verb_raw.startswith("./"):
        return _script_family(verb)
    if verb in ("bash", "sh", "zsh", "source"):
        for a in args:
            if a.endswith(".sh"):
                return _script_family(a.split("/")[-1])
        return None

    if _is_readonly(verb, nonflag, args):
        return None

    a0 = nonflag[0] if nonflag else None

    # Verb-intrinsic tools.
    if verb in _TEST_INTRINSIC or verb in _BUILD_INTRINSIC:
        fam = "test" if verb in _TEST_INTRINSIC else "build"
        if not inline:
            return fam
        # inline: must be command-shaped (bare single-token inline rejected)
        if had_prompt or has_flag or has_path:
            return fam
        return None

    # Runner verbs (strict tier).
    if verb in _RUNNER:
        return _runner_family(verb, nonflag)
    if verb == "nix-shell":
        return "setup"

    # Guarded tier (English homonyms): credit only on a resolved family token.
    if verb in _GUARDED:
        if a0 is None:
            return None
        fam = _family_of(a0)
        if fam is None:
            return None
        if has_flag or has_path or has_colon:
            return fam
        # bare guarded operand: at most one trailing token, and not English filler
        if len(nonflag) <= 2 and (len(nonflag) < 2 or nonflag[1] not in _STOPWORDS):
            return fam
        return None

    return None


def _extract_commands(lines):
    """Return list of (family, normalized_segment) for real commands, doc-wide."""
    results = []
    in_fence = False
    lang = ""
    for ln in lines:
        fm = _FENCE_RE.match(ln)
        if fm:
            if not in_fence:
                in_fence = True
                lang = fm.group(2).lower()
            else:
                in_fence = False
                lang = ""
            continue
        if in_fence:
            if lang in _SHELL_LANGS and not _NEG_RE.search(ln.lower()):
                for seg in _split_segments(ln):
                    fam = _classify(seg, inline=False)
                    if fam:
                        results.append((fam, _norm(seg)))
            continue
        if _NEG_RE.search(ln.lower()):
            continue
        for span in _INLINE_RE.findall(ln):
            for seg in _split_segments(span):
                fam = _classify(seg, inline=True)
                if fam:
                    results.append((fam, _norm(seg)))
    return results


# --------------------------------------------------------------------------- #
# Sections & directive credit
# --------------------------------------------------------------------------- #

def _sections(lines):
    """Return [(level, title, body_lines)] where each heading owns only its
    IMMEDIATE prose — up to the next heading of ANY level.

    Immediate (not descendant-inclusive) bodies are deliberate for the directive
    gate: a descendant-inclusive parent (e.g. the H1) would otherwise aggregate
    normative cues and code tokens across unrelated child sections and credit a
    platitude doc on borrowed concreteness (the G2 name-drop hole). Command
    extraction is doc-wide and unaffected by this.
    """
    heads = []
    in_fence = False
    for idx, ln in enumerate(lines):
        if _FENCE_RE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        hm = _HEADING_RE.match(ln)
        if hm:
            heads.append((idx, len(hm.group(1)), hm.group(2).strip()))
    out = []
    for i, (idx, level, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(lines)
        out.append((level, title, lines[idx + 1:end]))
    return out


def _has_tool(body: str) -> bool:
    return bool(_TOOL_RE.search(body))


def _is_code_token(span: str) -> bool:
    """True when an inline-backtick span is a real code token, not prose.

    Spec §4.3 concreteness signal = "inline identifier / file-extension /
    tool-name". A bare English word/phrase in cosmetic backticks (``x``,
    ``tidy``, ``the vibe``) is NOT a code token and must not satisfy the gate.
    """
    s = span.strip()
    if not s:
        return False
    # A file extension or a registered tool name is inherently concrete.
    if _FILE_EXT_RE.search(s) or _TOOL_RE.search(s):
        return True
    # Otherwise require a code-shape signal AND a substantive identifier
    # (an alphanumeric run >= 3). This rejects punctuation-only junk —
    # `a:b`, `x.y`, `p/q`, `m=n`, `r-s`, `t|u` — which is prose dressed in
    # cosmetic operators (max alnum run 1), while keeping real tokens such as
    # `db:reset`, `dist/`, `try/except`, `feat:`, `kebab-case`, `Is.Zero`.
    has_shape = bool(
        _is_path(s)
        or _CODE_SHAPE_RE.search(s)
        or _CAMEL_RE.search(s)
        or _CONST_CASE_RE.search(s)
        or _DIGIT_RE.search(s)
    )
    if not has_shape:
        return False
    return max((len(m) for m in _ALNUM_RUN_RE.findall(s)), default=0) >= 3


def _passes_directive_gate(body_lines) -> bool:
    prose = []
    has_code_inline = False
    in_fence = False
    for ln in body_lines:
        if _FENCE_RE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence or _HEADING_RE.match(ln):
            continue
        if not has_code_inline:
            for span in _INLINE_RE.findall(ln):
                if _is_code_token(span):
                    has_code_inline = True
                    break
        s = ln.strip()
        if s:
            prose.append(s)
    if not prose:
        return False
    body = " ".join(prose)
    cues = {m.group(0).lower() for m in _NORMATIVE_RE.finditer(body)}
    if len(cues) < 2:
        return False
    return has_code_inline or bool(_FILE_EXT_RE.search(body)) or _has_tool(body)


def _directive_heading_credit(category, sections) -> bool:
    pats = _DIRECTIVE_HEADING_RE[category]
    for _level, title, body in sections:
        tl = title.lower()
        if any(p.search(tl) for p in pats) and _passes_directive_gate(body):
            return True
    return False


def _content_fallback_code_style(sections) -> bool:
    """Heading-agnostic code_style rescue (§4.3): credit when any section has
    >=2 normative cues and >=1 concrete code token, independent of heading."""
    for _level, _title, body in sections:
        if _passes_directive_gate(body):
            return True
    return False


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def score_operational_coverage(skill_path: str) -> dict:
    try:
        content = strip_frontmatter(read_skill_safe(skill_path))
    except (FileNotFoundError, ValueError):
        return {"score": 0, "details": {"error": "unreadable"}}

    lines = content.split("\n")
    cmds = _extract_commands(lines)
    distinct_norms = {norm for _fam, norm in cmds}
    distinct = len(distinct_norms)
    families = {fam for fam, _norm in cmds}

    # Diversity (§4.2.4): a single distinct command resolves to a single family,
    # so the spec's ">=2 distinct before crediting all three" reduces to crediting
    # exactly the families actually present (1 command -> at most 1 family).
    credited_fams = families if distinct >= 1 else set()

    categories = {}
    for cat in ("setup", "build", "test"):
        cr = cat in credited_fams
        if cr:
            reason = f"real {cat} command resolved"
        elif distinct == 0:
            reason = "no real command (junk/read-only/inline-name-drop only)"
        else:
            reason = "no command of this family"
        categories[cat] = {"credited": cr, "reason": reason}

    sections = _sections(lines)

    code_style = _directive_heading_credit("code_style", sections)
    cs_reason = "heading + normative cues + code token"
    if not code_style:
        code_style = _content_fallback_code_style(sections)
        cs_reason = "content fallback: section with normative cues + code token"
    if not code_style:
        cs_reason = "no section with >=2 normative cues and a concrete code token"
    categories["code_style"] = {"credited": code_style, "reason": cs_reason}

    for cat in ("gotchas", "pr"):
        cr = _directive_heading_credit(cat, sections)
        categories[cat] = {
            "credited": cr,
            "reason": (
                "heading + normative cues + code token" if cr
                else "no matching heading with >=2 cues and a concrete token"
            ),
        }

    score = 0
    for cat, weight in _COMMAND_WEIGHTS.items():
        if categories[cat]["credited"]:
            score += weight
    for cat, weight in _DIRECTIVE_WEIGHTS.items():
        if categories[cat]["credited"]:
            score += weight

    return {
        "score": int(score),
        "details": {
            "categories": categories,
            "distinct_commands": distinct,
            "commands": sorted(distinct_norms),
        },
    }
