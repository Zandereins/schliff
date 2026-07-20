# Spec: Command Resolution (dangling-command check)

**Status:** done + merge-ready (branch `feat/command-resolution`, not yet merged)
**Merge-prep:** `check-commands` documented in README CLI table; CI dogfood gate
added (test.yml runs it against schliff's own AGENTS.md — 0 dangling, exit 0),
making schliff its own first adopter. `just`/`cargo`/`uv` resolvers deliberately
dropped (cargo/uv are builtins with no dangling potential; just recipes exist in
maintained repos — more resolvers ≠ more findings in credible repos).
**Branch:** `feat/command-resolution`
**Date:** 2026-07-19

## Outcome

Shipped `scripts/scoring/command_resolution.py` + `schliff check-commands` CLI + 6
tests. Verified: golden opcov/profile scores byte-identical (69 tests unchanged),
full suite 1358 → 1364 green, ruff clean. E2E on a mini-repo correctly flags
`make test` (no target) and `npm run coverage` (no script) as dangling with line
numbers, exits 1. Learned: `_extract_commands` returns `(family, lowercased_cmd)`,
so resolution is case-insensitive by necessity — which also serves the
false-positive-safety goal.

## Goal

Given an `AGENTS.md` (or `CLAUDE.md`) **and its surrounding repository**, statically
verify that every setup/build/test command the file tells an agent to run actually
resolves to something that exists in the repo. Report **dangling** commands — a
command the instructions promise but the repo does not provide — as a deterministic,
`found-with-schliff` defect.

This is the "your AGENTS.md line N says `run X`; X does not exist on a clean
checkout" artifact: self-authenticating (needs no account reputation), deterministic
(same inputs → same verdict), and honestly attributable to schliff because schliff's
own command extractor is what surfaces it.

## Context / why now

- Distribution is the bottleneck, not the engine (verified repeatedly). The single
  channel with traction has been a reproduced, self-authenticating technical defect
  delivered peer-to-peer, not a broadcast (see 13-agent strategy panel, 2026-07-19).
- schliff already extracts + classifies commands from instruction files
  (`operational_coverage._extract_commands`), but does **zero** filesystem
  resolution — it scores a file in isolation. This feature adds the repo-aware layer.

## Live hardening (2026-07-19, ~70 real repos)

Ran the check across ~70 real AGENTS.md/CLAUDE.md via code-search before merge.
Six false-positive classes surfaced on real data (none caught by synthetic
fixtures) — all fixed in this module (opcov untouched), each pinned by a
regression test named after the repo that produced it:

1. **env-assign prefix** — `BASE_PATH=/x npm run build` read the env value as a path (gentelella).
2. **quoted tool argument** — `npx eslint "a/b.tsx"` is an example arg, not a repo artifact (ViewComfy).
3. **inline comment** — `npm run lint # run eslint` leaked the comment into resolution (group-income).
4. **Makefile `include`** — `make start` lives in `makefiles/common.mk`; not following includes = false dangling (authgear). Now follows static relative includes; unresolvable include ⇒ `unknown`.
5. **workspace flag** — `npm run x -w pkg` resolves in a sub-package ⇒ `unknown`.
6. **placeholder** — `npm run *`, `make deploy-<env>` are doc placeholders ⇒ `unknown` (cache-cleaner).

Plus dedup (same command listed twice → reported once).

**Method caveat (load-bearing):** the `path` resolver needs the *full* repo. The
code-search sweep built a mini-repo (manifests only), which produced a false
`./test` dangling on semgrep (the path exists as a symlink not fetched). make/npm
findings are manifest-only and trustworthy from a mini-repo; **path findings
require a full clone.** After hardening: 5/5 reported dangling verified real
(100% precision) — conformal `npm run dev`, group-income `npm run lint`,
pebble-navi `npm run debug`, fizzbuzz `npm run evals`, Orvion `make test`.

## Requirements

1. **Additive, zero scoring impact.** MUST NOT modify `score_operational_coverage`,
   the dimension weights, or any golden score. `_extract_commands` is *reused*
   (imported), not changed. Corpus goldens stay byte-identical.
2. **Reuse, don't reimplement** the extractor (fence/negation/inline handling lives
   in one place — DRY).
3. **Conservative / false-positive-safe.** Report a command as `dangling` ONLY when
   resolution is unambiguous:
   - `make <target>` → a `Makefile`/`makefile` exists AND `<target>` is not a defined target.
   - `npm run <script>`, bare npm lifecycle words, and `pnpm run <script>` →
     `package.json` exists AND `<script>` is not in its `scripts`. **These are the
     only dangling-capable package-manager forms** (amended 2026-07-20): they are
     the ones whose manager hard-errors on a missing script (`npm error Missing
     script`, `ERR_PNPM_NO_SCRIPT`). Every `yarn` form falls back to
     `node_modules/.bin` (`yarn tsc` runs the typescript binary, and the binary
     name need not match the package name), and `bun` resolves scripts, then
     files, then binaries — for those, absence from `scripts` proves nothing, so
     they are `unknown`. The original wording claimed `pnpm <script>` / `yarn
     <script>` were dangling-capable; that was verified false and produced live
     false positives.
   - explicit path/script reference (e.g. `./scripts/foo.sh`, `bash tools/x.sh`) → the path does not exist on disk.
   Everything else → `unknown` (NOT a defect). A false dangling claim burns the
   whole artifact, so silence beats a marginal call (ReDoS-report discipline).
4. **Deterministic + stdlib-only.** No clock/entropy/network. Same file+repo → same result.
5. **CLI entrypoint** `schliff check-commands <file> [--repo DIR] [--json]`, exit
   nonzero iff ≥1 dangling command (CI-gate-able, like `verify`). `--repo` defaults
   to the file's directory.

## Technical decisions

- New module `scripts/scoring/command_resolution.py`. Pure functions:
  `resolve_commands(text, repo_root) -> list[CommandResult]` where each result is
  `{command, family, status: resolved|dangling|unknown, evidence}`.
- Resolvers are pure parsers over `Makefile` targets and `package.json` `scripts`;
  path check via `os.path.exists` relative to `repo_root`. Missing manifest ⇒
  `unknown`, never `dangling` (can't prove absence without the manifest).
- Line numbers for the report are recovered by a post-hoc scan for the command's
  literal text (the extractor stays `(family, command)`-shaped; we don't widen its
  contract and risk its callers/goldens).
- CLI `cmd_check_commands` mirrors `cmd_verify`'s exit-code + `--json` conventions.

## Non-goals

- Not a security scanner (that's `security.py`; note its fenced-block FP-hole, out of scope here).
- Not executing anything — pure static resolution.
- Not scoring — this is a separate check, not a dimension.

## Open questions

- Extend resolvers to `just`/`cargo`/`task` targets? Deferred until a real target repo needs it (YAGNI).
