# Spec: Command Resolution Hotfix (post-review hardening)

**Status:** implemented — PR open, not yet merged
**Branch:** `fix/command-resolution-hotfix`
**Date:** 2026-07-21
**Supersedes decisions in:** `2026-07-19-command-resolution.md` §"Technical decisions"
(the `_find_line` post-hoc line scan is retired here — see Fix 4).

## Outcome (verified 2026-07-21)

All 6 fixes shipped in `command_resolution.py` (Fixes 1–5) + `operational_coverage.py`
(Fix 4 extractor widening). Fix 6 was a no-op (already shipped). 11 new tests, all
red-first then green. **Full suite 1392 → 1403 green; golden opcov/profile 28
byte-identical (hard gate held); ruff clean; CLI dogfood gate 0 dangling.**

**Field verification (the load-bearing evidence)** — OLD (main `2387838`) vs NEW over
the sweep corpus (**140 repos / 170 instruction files / 0 crashes**): OLD = 17
danglings, NEW = 4. **All 13 demotions are WORKSPACE-justified** (1× Chainlit
pnpm-workspace, 12× kmarkussen workspaces-key); zero accidental demotions via
cd/budget/threading, so no real dangling was masked outside genuine workspace repos
(the deliberate false-positive-safe posture). The 4 remaining are unchanged: 3 TRUE
(cervellone `npm run install-all`; SuperClaude `make dev`, `test:coverage` — stale
docs) + 1 deferred prose-FALSE (SuperClaude `npm run build`, "inside pm/" — the
out-of-scope fast-follow). The memory's "~8 FALSE" estimate was per-repo; the true
instance count is 13, same class.

## Goal

Harden the v8.6.1 dangling-command check (`scripts/scoring/command_resolution.py`)
against the defects surfaced by a large adversarial review + council + field sweep
(2026-07-21) — **without** a redesign and **without** touching golden scores. The
single load-bearing outcome is: eliminate the one **real** false-positive class the
field sweep found, and close the two council-CATASTROPHIC availability defects.

## Context / why now

Review pipeline (single source of truth: memory `project_command_resolution_review.md`):

- **60-agent adversarial review → 12 reproduced defect classes**, all 14/14 red
  against the real engine.
- **hydra deep (82% HIGH, 2 REJECT / 4 CONCERN)** verdict: *BLOCK a broader
  distribution push; ship a cheap-wins hotfix (days, no redesign); the allowlist
  invert is a corpus-validated fast-follow, not a release blocker.*
- **Field sweep over 135 real repos (177 instruction files, 0 crashes)** corrected
  the council's priority ordering — see below.

### The field-sweep finding (drives the priority order)

17 dangling claims across 135 real repos → **~8 FALSE, ~9 TRUE** (each verified
against source). **None of the ~8 real FALSE positives is one of the 12 fixture
classes.** grouped-make / `--if-present` / quoted / `sinclude` / mixed-case fired
**zero** times as a real FALSE. The real FALSE positives are all the **same deeper
class**:

> `npm/pnpm run <script>` where the script lives in a **workspace child / subdir**
> and the directory context sits in a table column or "inside X/" prose (no `cd`).
> The engine only checks the **root** manifest — it knows nothing about workspaces.

So the fixtures are real defects but **not** the field FP source. The engine-level
fix for this class outranks the five cheap edge fixes in real-world relevance.

### Δ found during verify (refute-by-default)

Council fix #1 was "`fail-on-dangling` default → `false` (opt-in)". Verified against
the shipped code: `action.yml:29` already has `default: 'false'`, introduced opt-in
in **#118 (4ba6c2c)**. **Fix #1 is a no-op** — already satisfied. But the PR comment
renders the dangling table **independently of the gate** (`action.yml:287-304`), so
FALSE danglings no longer fail CI yet remain **visible** in every consumer PR
comment. The only lever that closes this at the root is the engine fix (Fix 1
below), not `action.yml`.

## Requirements (unchanged invariants)

1. **Additive, zero scoring impact.** MUST NOT change `score_operational_coverage`,
   dimension weights, or any golden score. `_extract_commands` may gain a widened
   return contract (Fix 4) **only if** the corpus goldens stay byte-identical
   (gated by the golden test after the change).
2. **Conservative / false-positive-safe.** A command is `dangling` ONLY when absence
   is provable. Every new rule here **demotes** `dangling → unknown`; it never
   creates a new `dangling` and never downgrades a `resolved`.
3. **Deterministic + stdlib-only.** No clock/entropy/network. Same file+repo → same
   result.
4. **Field-tested, not fixture-tested.** Every new FP fix is verified against the
   real repo that motivates it and pinned as a repo-named regression test; the TRUE
   repos are pinned as "stays-dangling" tests so the new rule masks no real defect.

## Fixes (priority order = real-world relevance, not council numbering)

### Fix 1 — Workspace-aware demotion (the real FP source) — [core]

In `_resolve_one`, immediately before the terminal `return "dangling"` in the
package-manager block (`command_resolution.py:324`): if the script is not in the
**root** `package.json` scripts **and** the repo declares workspaces, return
`unknown` instead of `dangling`.

"Repo declares workspaces" =

- root `package.json` has a `workspaces` key (array, or `{ "packages": [...] }`), **or**
- `pnpm-workspace.yaml` / `pnpm-workspace.yml` exists in the repo root.

Rationale: with workspaces the script may legitimately live in a child package; the
root manifest is not authoritative, so absence is unprovable → `unknown`. This is
the exact conservative posture the module already takes for `-w`/`--filter`
(`command_resolution.py:295-299`); it just also fires when the workspace context is
declared by the manifest rather than by an explicit flag.

**Scope decision (Franz, 2026-07-21):** *manifest signal only.* The second field
sub-class — directory context in a table column / "inside X/" prose with no `cd`
(SuperClaude_Framework case) — is a fragile heuristic and is **deferred** to a
separate fast-follow with its own field sweep. It is out of scope here.

Empirically fixes Chainlit (`pnpm run dev`, has pnpm workspace) and
kmarkussen/vs-code-work-share-plugin (`npm run compile/watch/dev`, ws=True).
SuperClaude_Framework stays FALSE until the deferred prose fix.

### Fix 2 — DoS input-budget guard + manifest memoization — [council CATASTROPHIC]

At the top of `resolve_commands`, one global budget guard. Caps (field-validated:
observed MAX over 177 files = 56 cmds / 926 lines / 964 line-len → these clip no
real repo):

- lines per doc: **5000**
- bytes per line: **2048**
- distinct commands: **256**

On overflow, every extracted command is reported `unknown` (evidence: input budget
exceeded) **without** calling `_resolve_one` — i.e. no manifest parsing, no
per-command filesystem work. This bounds the compound DoS (a tiny attacker-authored
doc driving ~6h of CI work through the resolver).

Plus **memoize** the manifest parses (`_pkg_scripts`, `_make_targets`,
`_repo_has_workspaces`) via a per-call cache dict threaded into `_resolve_one` — no
process-global state (temp-repo reuse across tests must not cross-contaminate).

### Fix 3 — realpath containment for the interpreter path check — [edge]

`command_resolution.py:331` uses `os.path.abspath` for repo-root containment on the
interpreter-run script path. `abspath` does not resolve symlinks, so a symlinked
path inside the checkout is an existence oracle / weak escape. Use `os.path.realpath`
(matching `_make_targets`, which already realpaths — `command_resolution.py:100`).

### Fix 4 — Retire `_find_line`; thread the real line from `_extract_commands` — [correctness, golden-touching]

`_find_line` (`command_resolution.py:383-389`) recovers the report line by scanning
for a substring match. Three defects:

- **quadratic DoS** — O(distinct-cmds × lines) substring scan.
- **cd-taint puncture** — a command that appears on two lines resolves the line to
  the *first* match, which may not be the tainted one, so the `dangling → unknown`
  cd demotion (`command_resolution.py:410`) can be bypassed.
- **`line` field corruption** — the reported line can point at a prose mention
  rather than the extracted command's real line.

Fix: widen `_extract_commands` to return `(family, norm, lineno)` (additive third
element), and thread the real line through `resolve_commands`. Retires all three
defects at once.

**Scope decision (Franz, 2026-07-21):** *full additive threading* (not the
conservative inline-demote fallback). This reverses the deliberate
`2026-07-19-command-resolution.md:105-107` choice to keep the extractor
`(family, command)`-shaped. That choice is safe to reverse **because** the only
other consumer (`operational_coverage.py:604-607`) uses value-only comprehensions
(`{norm for _fam, norm in cmds}`) — the widened arity changes unpacking, not values.
**Gate:** the golden opcov/profile test MUST stay byte-identical after this change;
if it drifts, the change is wrong.

### Fix 5 — Dequote script token + handle `--if-present` — [edge]

- Dequote the script token in `_pm_script` (`npm run "build"` → `build`) so a quoted
  script name is not read literally.
- `npm run <script> --if-present` is **not** a hard error on a missing script
  (npm exits 0), so it is not dangling → treat as `unknown` in
  `_pm_absence_provable`.

### Fix 6 — `fail-on-dangling` default (already satisfied) — [no-op, document only]

Verified: `action.yml:29` already ships `default: 'false'` (opt-in, #118). No code
change. Documented here so the council checklist is closed against the real code.

## Regression-test plan (field-named, per Franz's field-test rule)

New FP fixes pinned against the real repos that motivate them:

- **FALSE → now `unknown`:** Chainlit/chainlit `pnpm run dev`;
  kmarkussen/vs-code-work-share-plugin `npm run compile|watch|dev`.
- **TRUE → stays `dangling`** (guards against over-demotion): Orsati/cervellone-game
  `npm run install-all` (no workspaces); a non-workspace repo whose `npm run X` is a
  genuine typo must still be caught.

Each new rule gets a synthetic unit test **and** a field-shaped test (mini-repo with
the real manifest shape). Fixtures alone are not field-ready.

## Verification gates (after every step)

- full suite green (baseline to be re-measured on branch before first edit);
- **golden opcov/profile byte-identical** (hard gate for Fix 4);
- `ruff` clean;
- new rules field-verified against the named real repos.

## Non-goals

- No redesign, no allowlist invert (council: corpus-validated fast-follow, separate).
- No prose/table directory-context heuristic (deferred fast-follow — see Fix 1).
- No `action.yml` behavior change (Fix 6 is already shipped).
- No new `dangling` verdicts — this hotfix only demotes and hardens.

## Open questions / fast-follows

- Prose/"inside X/" directory-context demotion (SuperClaude_Framework class) — needs
  its own field sweep before it is safe.
- Allowlist invert — separate corpus-validated change.
