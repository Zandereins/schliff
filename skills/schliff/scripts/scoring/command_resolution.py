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
# A rule whose target name is variable- or pattern-expanded (`$(TARGETS):`,
# `%.o: %.c`, `$(BIN)/foo:`) defines targets we cannot enumerate statically. If a
# Makefile contains ANY such rule its target set is incomplete, so absence of a
# queried target is unprovable -> the caller must not claim dangling. Matches a
# non-recipe (not tab-indented) line whose left-hand side before a `:` (not `:=`)
# contains `$` or `%`. Assignments (`VAR := $(X)`) are excluded by the `(?!=)`.
_MAKE_DYNAMIC_TARGET_RE = re.compile(r"^(?![\t#])[^:#]*[$%][^:#]*:(?!=)")
# `include foo.mk` / `-include foo.mk`. A target defined in an included makefile
# is still real — not following includes caused a false `make start` dangling on
# authgear (start lives in makefiles/common.mk). We follow static relative
# includes and fall back to `unknown` on any include we cannot resolve.
# The capture is greedy-to-end and stripped in Python. A lazy `(.+?)[ \t]*$`
# backtracks quadratically on a long whitespace run (measured: 15.7s on one
# 800KB line, vs 0.25ms here) — an attacker-authored Makefile is untrusted input
# in CI, so the ReDoS shape must not survive. Verified byte-identical on every
# include form (`include a.mk`, `  -include a.mk b.mk  `, tabs, `includefoo`).
_INCLUDE_RE = re.compile(r"^[ \t]*-?include[ \t]+(.*)")
# Hard bounds for parsing untrusted build files. `_make_targets` follows includes;
# without a visited-set the depth cap alone allowed N**5 fan-out (measured 15.0s
# at N=12 through the real CLI). Budgets bound work even when the graph is legal.
_MAX_INCLUDE_FILES = 64
_MAX_MAKEFILE_BYTES = 1_048_576
_MAX_PKG_JSON_BYTES = 2_097_152
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


def _make_targets(makefile: str, repo_root: str) -> tuple[set[str], bool]:
    """Return (defined targets, unresolved_include). ``unresolved_include`` is
    True when the makefile pulls in an include we cannot statically follow
    (variable/glob path, missing file, escaping path, or an exhausted budget) —
    in that case a target we did not find may still exist, so the caller must not
    claim dangling.

    Iterative worklist with a realpath visited-set: every Makefile is parsed at
    most once, so include diamonds and cycles cost O(files), not O(N**depth).
    Includes are contained to ``repo_root`` — before this, `include ../../etc/x`
    was opened, giving attacker-authored build files a read primitive outside the
    checkout.
    """
    targets: set[str] = set()
    unresolved = False
    try:
        root = os.path.realpath(repo_root)
        queue = [os.path.realpath(makefile)]
    except OSError:
        return set(), True
    visited: set[str] = set()
    while queue:
        path = queue.pop()
        if path in visited:
            continue
        if len(visited) >= _MAX_INCLUDE_FILES:
            return targets, True
        visited.add(path)
        try:
            if os.path.getsize(path) > _MAX_MAKEFILE_BYTES:
                unresolved = True
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            unresolved = True
            continue
        for line in lines:
            m = _MAKE_TARGET_RE.match(line)
            if m:
                targets.add(m.group(1).lower())
            elif _MAKE_DYNAMIC_TARGET_RE.match(line):
                # Variable/pattern target: the target set is not fully knowable.
                unresolved = True
            inc = _INCLUDE_RE.match(line)
            if not inc:
                continue
            for part in inc.group(1).strip().split():
                if "$" in part or "*" in part or "?" in part:
                    unresolved = True
                    continue
                try:
                    inc_path = os.path.realpath(
                        os.path.normpath(os.path.join(os.path.dirname(path), part))
                    )
                    contained = os.path.commonpath([root, inc_path]) == root
                except (OSError, ValueError):
                    unresolved = True
                    continue
                if not contained:
                    # Never open it: an escaping include is unprovable *and* a
                    # read primitive. realpath first, so symlinks cannot escape.
                    unresolved = True
                elif os.path.isfile(inc_path):
                    if inc_path not in visited:
                        queue.append(inc_path)
                else:
                    unresolved = True
    return targets, unresolved


def _pkg_scripts(package_json: str) -> set[str] | None:
    # RecursionError is a RuntimeError, NOT a ValueError, so it used to escape
    # this handler: a ~20KB deeply-nested package.json crashed the whole check.
    # Size alone does not bound it (the payload is tiny), hence both guards.
    try:
        if os.path.getsize(package_json) > _MAX_PKG_JSON_BYTES:
            return None
        with open(package_json, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError):
        return None
    if not isinstance(data, dict):
        return None
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return set()
    return {str(k).lower() for k in scripts}


_PNPM_WORKSPACE_NAMES = ("pnpm-workspace.yaml", "pnpm-workspace.yml")


def _repo_has_workspaces(repo_root: str) -> bool:
    """True when the repo declares a workspace/monorepo layout, so a `<pm> run
    <script>` may legitimately live in a child package the root manifest does not
    list. The field sweep (135 real repos) found this is the ONLY real source of
    false danglings: the engine checks only the root manifest.

    Signals: a ``pnpm-workspace.yaml``/``.yml`` (pnpm), or a truthy ``workspaces``
    key in the root ``package.json`` (npm/yarn/bun — an array, or a
    ``{"packages": [...]}`` object). An empty/false value is not a workspace.
    """
    for name in _PNPM_WORKSPACE_NAMES:
        if os.path.isfile(os.path.join(repo_root, name)):
            return True
    package_json = os.path.join(repo_root, "package.json")
    try:
        if os.path.getsize(package_json) > _MAX_PKG_JSON_BYTES:
            return False
        with open(package_json, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError):
        return False
    return isinstance(data, dict) and bool(data.get("workspaces"))


def _dequote(tok: str) -> str:
    """Strip matching surrounding quotes: `npm run "build"` names the `build`
    script, not a literal `"build"`."""
    return tok.strip("'\"")


def _pm_script(verb: str, args: list[str]) -> str | None:
    """The package.json script a `<pm> ...` invocation runs, or None if not a
    script invocation (or too ambiguous to claim)."""
    if verb not in ("npm", "pnpm", "yarn", "bun"):
        return None
    if args and args[0] == "run":
        # The script is the first NON-FLAG token after `run`; `pnpm run -r build`
        # and `pnpm run --silent build` used to read the flag as the script name
        # and report `script '-r' is not defined`.
        for a in args[1:]:
            if not a.startswith("-"):
                return _dequote(a)
        return None
    if not args or args[0].startswith("-"):
        return None
    first = _dequote(args[0])
    if verb == "npm":
        return first if first in _NPM_LIFECYCLE else None
    # pnpm / yarn / bun: an unknown (non-builtin) word MAY run the matching
    # script — but yarn/bun also fall back to a node_modules/.bin binary, so
    # absence is not provable here. See `_pm_absence_provable`.
    return first if first not in _PM_BUILTINS else None


def _pm_absence_provable(verb: str, args: list[str]) -> bool:
    """True only for invocation forms where a missing script is a *hard error*,
    so 'not in package.json' proves the command is broken.

    `npm run X` (npm error Missing script) and `pnpm run X` (ERR_PNPM_NO_SCRIPT)
    qualify. Every yarn form falls back to `node_modules/.bin` (`yarn tsc` runs
    the typescript binary), and bun resolves scripts, then files, then binaries —
    for those, absence from `scripts` proves nothing. The bare pnpm/yarn/bun
    shorthand has the same fallback, so it is unprovable too.
    """
    # `--if-present` makes a missing script exit 0 (npm/pnpm/yarn all honor it),
    # so absence is not an error -> not provable.
    if "--if-present" in args:
        return False
    if args and args[0] == "run":
        return verb in ("npm", "pnpm")
    # bare lifecycle word: only npm maps these to scripts with a hard error.
    return verb == "npm"


def _clean_tokens(cmd: str) -> list[str]:
    """Split a command and strip inline comments + leading env-assignments so the
    real verb/args surface (`BASE_PATH=/x npm run build # note` -> [npm, run, build])."""
    toks = cmd.split()
    for j, t in enumerate(toks):
        if t.startswith("#"):  # inline comment starts here
            toks = toks[:j]
            break
    # Subshell punctuation clings to the tokens after segment splitting:
    # `(cd pkg && npm run build)` yields a segment whose last token is `build)`,
    # which resolved as a script literally named "build)". Strip the grouping
    # characters so the real name surfaces.
    toks = [t.strip("()") for t in toks]
    toks = [t for t in toks if t]
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


def _memo(cache: dict, key: str, producer):
    """Per-call memo: repo_root is constant across all commands in one
    ``resolve_commands`` call, so each manifest is parsed at most once instead of
    once per command (the compound-DoS multiplier the council flagged). The cache
    is call-scoped (never process-global) so tests reusing a repo path can't
    cross-contaminate."""
    if key not in cache:
        cache[key] = producer()
    return cache[key]


def _resolve_one(cmd: str, repo_root: str, cache: dict) -> tuple[str, str]:
    tokens = _clean_tokens(cmd)
    if not tokens:
        return "unknown", "empty command"
    verb, args = tokens[0], tokens[1:]

    # 1) make <target>
    if verb == "make":
        # `-C dir` / `-f file` retarget make at a different directory or makefile.
        # The extractor lowercases, so `-C` arrives as `-c`. Without this guard the
        # directory was read as the target: `make -C build test` reported
        # "target 'build' is not defined" — a false dangling on a standard form.
        if any(a in ("-c", "-f") or a.startswith(("-c", "-f", "--directory", "--file", "--makefile")) for a in args):
            return "unknown", "make runs against another directory/makefile (-C/-f)"
        targets = [a for a in args if not a.startswith("-") and "=" not in a]
        if not targets:
            return "unknown", "make with no explicit target"
        target = targets[0]
        if _is_placeholder(target):
            return "unknown", f"'{target}' is a placeholder, not a concrete target"
        makefile = _memo(cache, "makefile", lambda: _find_makefile(repo_root))
        if makefile is None:
            return "unknown", "no Makefile in repo root"
        defined, unresolved_include = _memo(
            cache, "make_targets", lambda: _make_targets(makefile, repo_root)
        )
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
        if any(
            a in ("-w", "-r", "--recursive") or a.startswith(("--workspace", "--filter"))
            for a in args
        ):
            return "unknown", "workspace-scoped script; resolves in a sub-package"
        package_json = os.path.join(repo_root, "package.json")
        if not os.path.isfile(package_json):
            return "unknown", "no package.json in repo root"
        scripts = _memo(cache, "pkg_scripts", lambda: _pkg_scripts(package_json))
        if scripts is None:
            return "unknown", "package.json is unparseable"
        if script.lower() in scripts:
            return "resolved", f"npm script '{script}' defined in package.json"
        # bun resolves scripts, then FILES, then binaries: `bun run index.ts` and
        # bare `bun index.ts` execute the file. Codegen'd targets (`bun run
        # dist/index.js`, built earlier in the same doc) mean a missing file
        # proves nothing either — so bun never yields dangling here.
        if verb == "bun":
            if os.path.exists(os.path.normpath(os.path.join(repo_root, script))):
                return "resolved", f"file '{script}' exists"
            return "unknown", (
                f"'{script}' is neither a package.json script nor a file on a clean "
                "checkout; bun also resolves node_modules binaries"
            )
        if not _pm_absence_provable(verb, args):
            return "unknown", (
                f"script '{script}' is not in package.json scripts; {verb} may fall "
                "back to a node_modules/.bin binary"
            )
        if _memo(cache, "workspaces", lambda: _repo_has_workspaces(repo_root)):
            # Root manifest is not authoritative in a monorepo — the script may
            # live in a workspace child. Absence is unprovable -> unknown, never
            # dangling. (The field sweep's one real false-positive class.)
            return "unknown", (
                f"script '{script}' is not in the root package.json, but the repo "
                "declares workspaces; it may be defined in a workspace package"
            )
        return "dangling", f"script '{script}' is not defined in package.json scripts"

    # 3) explicit interpreter-run script / `./` executable
    path = _script_path(tokens)
    if path is not None:
        full = os.path.normpath(os.path.join(repo_root, path))
        # Only claim on paths that stay inside the repo; escapes are unprovable.
        # realpath (not abspath) resolves symlinks first, so a symlinked path that
        # points outside the checkout escapes here instead of turning os.path.exists
        # into an existence oracle for external files. Matches _make_targets, which
        # already realpaths its include containment.
        try:
            root_real = os.path.realpath(repo_root)
            full_real = os.path.realpath(full)
            contained = os.path.commonpath([root_real, full_real]) == root_real
        except (OSError, ValueError):
            return "unknown", f"path '{path}' is not statically resolvable"
        if not contained:
            return "unknown", f"path '{path}' escapes repo root"
        if os.path.exists(full):
            return "resolved", f"path '{path}' exists"
        return "dangling", f"path '{path}' does not exist on a clean checkout"

    return "unknown", "no resolver for this command"


_CD_VERBS = frozenset({"cd", "pushd", "popd"})


def _cd_tainted_lines(lines: list[str]) -> set[int]:
    """1-based line numbers whose commands run in a working directory we cannot
    statically prove.

    The extractor splits on `&&`/`;`/`|` and discards the `cd`, so
    `cd packages/api && npm run lint` reaches resolution as a bare `npm run lint`
    and was resolved against the ROOT manifest — a false dangling on the standard
    monorepo idiom. We do not try to reconstruct the working directory (a design
    that does *resolve* the cd target leaks context across subshells and creates
    fresh false positives); we only mark the affected lines unprovable.

    Inside a shell fence a `cd` persists for the rest of that fence. Outside, it
    only affects its own line. Fence boundaries reset the state.
    """
    tainted: set[int] = set()
    in_fence = False
    fence_tainted = False
    for i, raw in enumerate(lines, 1):
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            fence_tainted = False
            continue
        if in_fence and fence_tainted:
            tainted.add(i)
        line_tainted = False
        for seg in re.split(r"&&|\|\||\||;", raw):
            toks = [t for t in seg.strip().lstrip("$>#").strip().split() if t]
            toks = [t.strip("()") for t in toks]
            toks = [t for t in toks if t]
            if line_tainted:
                tainted.add(i)
            if toks and toks[0].lower() in _CD_VERBS:
                line_tainted = True
                if in_fence:
                    fence_tainted = True
        if line_tainted:
            tainted.add(i)
    return tainted


# Input-budget caps for untrusted docs (the resolver runs on attacker-authored
# AGENTS.md in CI). Field-validated: observed MAX over 177 real instruction files
# = 56 distinct commands / 926 lines / 964 line-length — these clip no real repo.
# On overflow every command degrades to `unknown` with NO per-command resolution
# (no manifest parsing / filesystem walk), bounding the compound DoS the council
# flagged (a ~60-byte doc driving hours of CI work).
_MAX_DOC_LINES = 5000
_MAX_LINE_BYTES = 2048
_MAX_DISTINCT_CMDS = 256

_BUDGET_EVIDENCE = "input exceeds the resolver's budget; not resolved (unknown)"


def resolve_commands(text: str, repo_root: str) -> list[dict]:
    """Resolve every extracted command against the repo.

    Returns one dict per command: ``{command, family, status, evidence, line}``
    where status is ``resolved`` | ``dangling`` | ``unknown``.
    """
    lines = text.splitlines()
    # Budget guard (cheap, pre-resolution): oversized input degrades to all-unknown
    # rather than driving unbounded resolver work.
    over_budget = len(lines) > _MAX_DOC_LINES or any(
        len(ln) > _MAX_LINE_BYTES for ln in lines
    )
    extracted = _extract_commands(lines)
    if not over_budget and len({norm for _f, norm, _l in extracted}) > _MAX_DISTINCT_CMDS:
        over_budget = True

    # Skip the (regex-per-line) cd scan when nothing will be resolved anyway.
    tainted = set() if over_budget else _cd_tainted_lines(lines)
    cache: dict = {}  # per-call manifest memo (see _memo)
    results: list[dict] = []
    seen: set[str] = set()
    # ``_extract_commands`` yields the real 1-based extraction line, so the report
    # line is the actual source line (not a substring guess) and the cd demotion
    # keys on the line the command was truly extracted from.
    for family, cmd, line in extracted:
        if cmd in seen:  # same command listed twice — report once
            continue
        seen.add(cmd)
        if over_budget:
            status, evidence = "unknown", _BUDGET_EVIDENCE
        else:
            status, evidence = _resolve_one(cmd, repo_root, cache)
            # Demote only — a cd context makes absence unprovable, but a target we
            # DID find is still real, so `resolved` is never downgraded.
            if status == "dangling" and line in tainted:
                status = "unknown"
                evidence = "runs after a 'cd'; the working directory is not statically resolvable"
        results.append({
            "command": cmd,
            "family": family,
            "status": status,
            "evidence": evidence,
            "line": line,
        })
    return results
