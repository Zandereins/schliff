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


def _make_targets(makefile: str) -> set[str]:
    targets: set[str] = set()
    try:
        with open(makefile, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = _MAKE_TARGET_RE.match(line)
                if m:
                    targets.add(m.group(1).lower())
    except OSError:
        return set()
    return targets


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


def _first_path_token(tokens: list[str]) -> str | None:
    for t in tokens:
        if t.startswith("-") or "://" in t or "*" in t:
            continue
        if _is_path(t) and t not in (".", ".."):
            return t
    return None


def _resolve_one(cmd: str, repo_root: str) -> tuple[str, str]:
    tokens = cmd.split()
    if not tokens:
        return "unknown", "empty command"
    verb, args = tokens[0], tokens[1:]

    # 1) make <target>
    if verb == "make":
        targets = [a for a in args if not a.startswith("-") and "=" not in a]
        if not targets:
            return "unknown", "make with no explicit target"
        target = targets[0]
        makefile = _find_makefile(repo_root)
        if makefile is None:
            return "unknown", "no Makefile in repo root"
        if target.lower() in _make_targets(makefile):
            return "resolved", f"make target '{target}' defined in {os.path.basename(makefile)}"
        return "dangling", f"make target '{target}' is not defined in {os.path.basename(makefile)}"

    # 2) package-manager script
    script = _pm_script(verb, args)
    if script is not None:
        package_json = os.path.join(repo_root, "package.json")
        if not os.path.isfile(package_json):
            return "unknown", "no package.json in repo root"
        scripts = _pkg_scripts(package_json)
        if scripts is None:
            return "unknown", "package.json is unparseable"
        if script.lower() in scripts:
            return "resolved", f"npm script '{script}' defined in package.json"
        return "dangling", f"script '{script}' is not defined in package.json scripts"

    # 3) explicit relative path / script reference
    path = _first_path_token(tokens)
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
    for family, cmd in _extract_commands(lines):
        status, evidence = _resolve_one(cmd, repo_root)
        results.append({
            "command": cmd,
            "family": family,
            "status": status,
            "evidence": evidence,
            "line": _find_line(cmd, lines),
        })
    return results
