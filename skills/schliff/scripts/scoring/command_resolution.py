"""Dangling-command check: does the repo actually provide the commands an
AGENTS.md tells an agent to run?

Reuses ``operational_coverage._extract_commands`` (the fence/negation/inline
extractor — DRY, single source of truth) and adds a repo-aware resolution layer.
This module does NOT score and NEVER touches ``score_operational_coverage`` or any
golden — it is a separate, additive check.

Spec: docs/specs/2026-07-19-command-resolution.md.

Conservative by design: a command is reported ``dangling`` ONLY when absence is
provable (the manifest exists and the target/script/path is definitively missing).
Anything unprovable is ``unknown``, never ``dangling`` — a false dangling claim
burns the whole artifact.

Deterministic + stdlib-only: no clock / entropy / network. Same (text, repo) → same result.
"""
from __future__ import annotations

import json
import os
import re

from scoring.operational_coverage import _extract_commands, _is_path

_MAKEFILE_NAMES = ("Makefile", "makefile", "GNUmakefile")
# A Makefile target line `name:` — but NOT a variable assignment (`name :=`,
# `name =`). The negative lookahead `(?!=)` rejects `:=`; assignments with a
# space (`NAME = v`) have no colon so never match.
_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-/]*)[ \t]*:(?!=)")
# `include foo.mk` / `-include foo.mk`. A target defined in an included makefile
# is still real — not following includes caused a false `make start` dangling on
# authgear (start lives in makefiles/common.mk). We follow static relative
# includes and fall back to `unknown` on any include we cannot resolve.
_INCLUDE_RE = re.compile(r"^[ \t]*-?include[ \t]+(.+?)[ \t]*$")
# Leading `VAR=value` env-assignments precede the real command
# (`BASE_PATH=/x npm run build`) — skip them so the value is not read as a path.
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=")
# Only treat a path as a runnable script when an interpreter runs it or it is an
# explicit `./` executable — NOT when it is an argument to a linter/tool
# (`npx eslint "components/ui/button.tsx"` is an example arg, not a repo artifact).
_INTERPRETERS = frozenset({
    "bash", "sh", "zsh", "dash", "python", "python3", "node", "ruby", "perl",
})

# Package-manager subcommands that are NOT user scripts. Used only for the
# pnpm/yarn/bun shorthand (`pnpm <x>`), where an unknown word maps to a script.
_PM_BUILTINS = frozenset({
    "install", "i", "ci", "add", "remove", "rm", "update", "up", "upgrade",
    "outdated", "audit", "publish", "link", "unlink", "exec", "dlx", "dedupe",
    "why", "list", "ls", "view", "info", "config", "cache", "init", "create",
    "import", "prune", "store", "patch", "fetch", "rebuild", "run", "help",
})
# npm maps only these bare lifecycle words to package.json scripts.
_NPM_LIFECYCLE = frozenset({"test", "start", "stop", "restart"})


def _find_makefile(repo_root: str) -> str | None:
    for name in _MAKEFILE_NAMES:
        p = os.path.join(repo_root, name)
        if os.path.isfile(p):
            return p
    return None


def _make_targets(makefile: str, _depth: int = 0) -> tuple[set[str], bool]:
    """Return (defined targets, unresolved_include). ``unresolved_include`` is
    True when the makefile pulls in an include we cannot statically follow
    (variable/glob path, missing file, or too-deep nesting) — in that case a
    target we did not find may still exist, so the caller must not claim dangling.
    """
    targets: set[str] = set()
    unresolved = False
    try:
        with open(makefile, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return set(), True
    for line in lines:
        m = _MAKE_TARGET_RE.match(line)
        if m:
            targets.add(m.group(1).lower())
        inc = _INCLUDE_RE.match(line)
        if inc:
            for part in inc.group(1).split():
                if "$" in part or "*" in part or "?" in part or _depth >= 5:
                    unresolved = True
                    continue
                inc_path = os.path.normpath(os.path.join(os.path.dirname(makefile), part))
                if os.path.isfile(inc_path):
                    sub, sub_unresolved = _make_targets(inc_path, _depth + 1)
                    targets |= sub
                    unresolved = unresolved or sub_unresolved
                else:
                    unresolved = True
    return targets, unresolved


def _pkg_scripts(package_json: str) -> set[str] | None:
    try:
        with open(package_json, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return set()
    return {str(k).lower() for k in scripts}


def _pm_script(verb: str, args: list[str]) -> str | None:
    """The package.json script a `<pm> ...` invocation runs, or None if not a
    script invocation (or too ambiguous to claim)."""
    if verb not in ("npm", "pnpm", "yarn", "bun"):
        return None
    if args and args[0] == "run" and len(args) >= 2:
        return args[1]
    if not args or args[0].startswith("-"):
        return None
    first = args[0]
    if verb == "npm":
        return first if first in _NPM_LIFECYCLE else None
    # pnpm / yarn / bun: an unknown (non-builtin) word runs the matching script.
    return first if first not in _PM_BUILTINS else None


def _clean_tokens(cmd: str) -> list[str]:
    """Split a command and strip inline comments + leading env-assignments so the
    real verb/args surface (`BASE_PATH=/x npm run build # note` -> [npm, run, build])."""
    toks = cmd.split()
    for j, t in enumerate(toks):
        if t.startswith("#"):  # inline comment starts here
            toks = toks[:j]
            break
    k = 0
    while k < len(toks) and _ENV_ASSIGN_RE.match(toks[k]):
        k += 1
    return toks[k:]


def _script_path(tokens: list[str]) -> str | None:
    """A path only counts as a runnable repo artifact when an interpreter runs it
    (`bash scripts/x.sh`) or it is an explicit `./` executable — not when it is a
    tool argument (`npx eslint "a/b.tsx"`) or a bare filename."""
    if not tokens:
        return None
    verb = tokens[0]
    cand: str | None = None
    if verb in _INTERPRETERS and len(tokens) >= 2:
        cand = tokens[1]
    elif verb.startswith("./"):
        cand = verb
    if cand is None:
        return None
    cand = cand.strip("'\"")
    if not _is_path(cand) or "://" in cand or "*" in cand or cand in (".", ".."):
        return None
    return cand


def _is_placeholder(name: str) -> bool:
    """A doc placeholder, not a real target/script name: `npm run *`,
    `make deploy-<env>`, `pnpm $SCRIPT`."""
    return any(c in name for c in "*<>$?") or name in ("...", "…")


def _resolve_one(cmd: str, repo_root: str) -> tuple[str, str]:
    tokens = _clean_tokens(cmd)
    if not tokens:
        return "unknown", "empty command"
    verb, args = tokens[0], tokens[1:]

    # 1) make <target>
    if verb == "make":
        targets = [a for a in args if not a.startswith("-") and "=" not in a]
        if not targets:
            return "unknown", "make with no explicit target"
        target = targets[0]
        if _is_placeholder(target):
            return "unknown", f"'{target}' is a placeholder, not a concrete target"
        makefile = _find_makefile(repo_root)
        if makefile is None:
            return "unknown", "no Makefile in repo root"
        defined, unresolved_include = _make_targets(makefile)
        if target.lower() in defined:
            return "resolved", f"make target '{target}' defined in {os.path.basename(makefile)}"
        if unresolved_include:
            return "unknown", f"make target '{target}' not in {os.path.basename(makefile)}, but it has unresolvable includes"
        return "dangling", f"make target '{target}' is not defined in {os.path.basename(makefile)}"

    # 2) package-manager script
    script = _pm_script(verb, args)
    if script is not None:
        if _is_placeholder(script):
            return "unknown", f"'{script}' is a placeholder, not a concrete script"
        if any(a == "-w" or a.startswith("--workspace") for a in args):
            return "unknown", "workspace-scoped script (-w); resolves in a sub-package"
        package_json = os.path.join(repo_root, "package.json")
        if not os.path.isfile(package_json):
            return "unknown", "no package.json in repo root"
        scripts = _pkg_scripts(package_json)
        if scripts is None:
            return "unknown", "package.json is unparseable"
        if script.lower() in scripts:
            return "resolved", f"npm script '{script}' defined in package.json"
        return "dangling", f"script '{script}' is not defined in package.json scripts"

    # 3) explicit interpreter-run script / `./` executable
    path = _script_path(tokens)
    if path is not None:
        full = os.path.normpath(os.path.join(repo_root, path))
        # Only claim on paths that stay inside the repo; escapes are unprovable.
        if os.path.commonpath([os.path.abspath(repo_root), os.path.abspath(full)]) != os.path.abspath(repo_root):
            return "unknown", f"path '{path}' escapes repo root"
        if os.path.exists(full):
            return "resolved", f"path '{path}' exists"
        return "dangling", f"path '{path}' does not exist on a clean checkout"

    return "unknown", "no resolver for this command"


def _find_line(cmd: str, lines: list[str]) -> int | None:
    toks = [t for t in cmd.lower().split() if t]
    for i, ln in enumerate(lines, 1):
        low = ln.lower()
        if all(t in low for t in toks):
            return i
    return None


def resolve_commands(text: str, repo_root: str) -> list[dict]:
    """Resolve every extracted command against the repo.

    Returns one dict per command: ``{command, family, status, evidence, line}``
    where status is ``resolved`` | ``dangling`` | ``unknown``.
    """
    lines = text.splitlines()
    results: list[dict] = []
    seen: set[str] = set()
    for family, cmd in _extract_commands(lines):
        if cmd in seen:  # same command listed twice — report once
            continue
        seen.add(cmd)
        status, evidence = _resolve_one(cmd, repo_root)
        results.append({
            "command": cmd,
            "family": family,
            "status": status,
            "evidence": evidence,
            "line": _find_line(cmd, lines),
        })
    return results
