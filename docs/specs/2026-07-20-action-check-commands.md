# Spec: `check-commands` in the GitHub Action

**Status:** spec — ready to implement
**Branch:** `feat/action-check-commands-v2` (on top of `fix/check-commands-hardening`)
**Date:** 2026-07-20 (rev. 2026-07-21 after adversarial review)
**Depends on:** `check-commands` hardened in schliff **8.6.1** (the delivery surface
requires the FP/DoS fixes — see `docs/specs/2026-07-19-command-resolution.md` and the
8.6.1 release). The Action MUST pin/require `>= 8.6.1`.
**Related:** `docs/specs/2026-07-19-command-resolution.md` (the engine feature).

## Goal

Surface dangling commands — commands an instruction file tells an agent to run that
do not exist in the repository — inside the pull-request comment the Schliff Action
already posts on consumer repos. This spec covers **only** the delivery surface:
wiring `schliff check-commands` into `action.yml` without weakening its security
posture, breaking existing consumers, or publishing a false claim on a stranger's PR.

## Context / why now

Distribution is schliff's bottleneck (see `project_schliff_state`). The one channel
with traction has been a reproduced, self-authenticating technical defect delivered
peer-to-peer. A dangling command is exactly that: deterministic, checkable in ten
seconds, honestly attributable to schliff. Rendering it in the PR comment turns every
consumer repo into a recurring demonstration of the tool finding a real defect — which
constrains the design: **the comment must post even when a gate fails**, or the
mechanism destroys its own leverage.

## Why 8.6.1 is a hard precondition

An adversarial review + a field sweep of real monorepos found the shipped 8.6.0 engine
emitting **8 false danglings across 3 of 4 real repos** (`pnpm nx`, `bun run dev`,
subshell-paren paths) plus two DoS vectors on attacker-authored build files. Publishing
that on strangers' PRs would invert the strategy — reputational damage where trust is
the goal. All fixed in 8.6.1; this Action gates on that release. See PR #117.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Render as a **section inside the existing** `<!-- schliff-score-comment -->` body | One comment, one marker, one update path; no extra check-run or notification. |
| D2 | Resolve with the engine default — **`--repo` = the instruction file's directory** — not `$GITHUB_WORKSPACE`. Run **only when the file resolves inside the workspace**. | For a repo-root `AGENTS.md` (the default and dominant case) dirname == workspace, so this AGREES with the repo-level intent everywhere it matters. It differs only for a *nested* file, where resolving against the nested manifest is strictly safer than the root one (avoids the monorepo cross-manifest false dangling). Residual: a nested file referencing a *root-relative* path (`./scripts/x.sh` that lives at the repo root) can false-dangle — narrow, documented in Non-goals. This reverses the earlier `$GITHUB_WORKSPACE` pick after the review showed it is both FP-prone on monorepos and untestable via an in-repo fixture. |
| D3 | **Degrade to silence** when the pinned engine lacks the subcommand — via the run+validate path, no separate probe. | `schliff-version` lets consumers pin an older engine; a hard failure would break a published Action. An old engine prints an argparse error to stderr with empty stdout, which the JSON validation already turns into `dangling_count=0`. |
| D4 | Data-gathering step **cannot fail**; the optional gate is a **separate final step, after the comment**. | Preserves D1's leverage: the consumer gets the explanatory comment, then (only if they opted in) the red build. |
| D5 | Transport the result as **base64**, mirroring `result_b64`. | Security-critical, not stylistic — see Security model §2. |
| D6 | New gather step, **not folded into `Run scorer`**. | The scorer step already does scoring, validation, grade mapping and encoding; two failure sources under one exit code produce an unattributable red build. |
| D7 | **Keep** the `fail-on-dangling` input (opt-in, default `false`). | Mirrors the existing `minimum-score` gate — a first-class fail toggle is idiomatic for a CI action, more ergonomic than "read the output, write your own `if` step". The review flagged it as YAGNI vs. the `dangling_count` output; kept because it matches the action's own precedent and the original ask, but the enforcement is a single minimal step (D4). |

## Requirements

1. **Non-breaking for existing consumers.** Any pinned version, or the Action used
   exactly as documented today, sees identical behavior except the added comment
   section. `fail-on-dangling` defaults `false`; no existing build can turn red.
2. **Runs only for AGENTS.md and CLAUDE.md**, gated on `steps.score.outputs.format`
   ∈ {`agents.md`, `claude.md`}. SKILL.md / `.cursorrules` are skill- or editor-local;
   resolving their commands against a repo invites false positives for no benefit.
3. **Executes nothing.** `check-commands` is a static resolver; no consumer command is
   ever run. Must hold for any future resolver in the module.
4. **Inherits the `-P` threat model.** Every inline `python3` uses `python3 -P`. The
   workspace is attacker-writable via PR; without `-P`, a planted `json.py` or shadowed
   `skills/` at the repo root executes in the consumer's CI.
5. **Attacker-controlled strings never reach an interpolation sink and never render as
   active markdown.** Command/evidence text comes from the consumer's file. It MUST NOT
   be interpolated into the `github-script` body (base64 only), and MUST be rendered
   inside a code span with backticks stripped, so `[x](url)`, `!`, `|`, and control
   chars cannot produce a link, image, or broken row.
6. **False-positive-safe.** The engine's conservative contract (`dangling` only on
   provable absence, else `unknown`) is inherited from 8.6.1. The Action MUST render
   only `status === 'dangling'` rows — never `unknown`/`resolved`.
7. **Comment posts before enforcement.** With `fail-on-dangling: 'true'` and danglings
   present, the consumer gets the comment first, then the red build.
8. **Degrades to silence, never to a false claim.** Missing subcommand, invalid JSON,
   scorer crash, missing output, empty output, or a fork-PR read-only token ⇒ no
   section and no failure. `dangling_count` is `''` when the check did not run.

## Technical design

### Step ordering in `action.yml`

```
  Set up Python
  Install Schliff scorer
  Run scorer                  (id: score)     + emits `format`, `skill_full`
→ Check dangling commands     (id: dangling)  NEW — never fails
  Check minimum score                         unchanged (position + semantics)
  Comment on PR                               + renders dangling section
→ Enforce dangling gate       (id: gate)      NEW — the only step that can fail here
```

The pre-existing `minimum-score`-suppresses-comment interaction is unchanged and out
of scope (Non-goals).

### New input & output

```yaml
inputs:
  fail-on-dangling:
    description: 'Fail the build when the instruction file references setup/build/test commands that do not resolve in the repo. AGENTS.md / CLAUDE.md only.'
    required: false
    default: 'false'
outputs:
  dangling_count:
    description: "Number of dangling commands found. Empty string when the check did not run (non-AGENTS format, engine older than 8.6.1, or no valid output)."
    value: ${{ steps.dangling.outputs.dangling_count }}
```

### `Run scorer` additions

Two outputs from the already-validated `$RESULT`, using `.get(...)` so a **pre-8.x
engine that omits the key does not KeyError** (verified 2026-07-20: schliff 6.3.0 emits
no `format` key):

```bash
FORMAT=$(echo "$RESULT" | python3 -P -c "import sys,json; print(json.load(sys.stdin).get('format',''))" 2>/dev/null) || true
echo "format=$FORMAT" >> "$GITHUB_OUTPUT"
echo "skill_full=$SKILL_FULL" >> "$GITHUB_OUTPUT"
```

`skill_full` is the already-resolved absolute path, so the new step never re-derives
the default-to-AGENTS.md logic (single source of truth).

### `Check dangling commands` (new step, id: `dangling`)

```yaml
if: steps.score.outputs.format == 'agents.md' || steps.score.outputs.format == 'claude.md'
```

Shell body (all `python3 -P`):

1. **Run** against the **file's own directory** (engine default; D2):
   `schliff check-commands "$SKILL_FULL" --json > out.json 2>/dev/null || true`.
   Exit 1 is the expected "dangling found" signal, so `|| true` (R8/D4). No `--repo`.
   No separate capability probe (D3/finding U): an old engine writes an argparse error
   to stderr and nothing to stdout, which fails validation below → count 0.
2. **Validate** with `python3 -P`: require a JSON object whose `dangling_count` is an
   int and `results` a list. Anything else ⇒ `dangling_count=0`, no `dangling_b64`.
3. **Emit** `dangling_count`, and `dangling_b64` (`base64 -w0` of the raw JSON) **only**
   when `dangling_count > 0`.
4. **Log** a plain-text summary to stdout — the only human surface on `push` events
   (no PR comment there).

### Comment rendering (inside the existing `github-script` step)

Guarded decode — **the empty-string case is the common one** (no danglings, step
skipped, or old engine) and a bare `JSON.parse(Buffer.from('', 'base64'))` throws
`SyntaxError`, which would abort the whole comment step and stop the *existing* score
comment from posting (finding C). So:

```js
const db64 = '${{ steps.dangling.outputs.dangling_b64 }}';
let dangling = [];
if (db64) {
  try {
    dangling = (JSON.parse(Buffer.from(db64, 'base64').toString('utf8')).results || [])
      .filter(r => r.status === 'dangling');
  } catch { dangling = []; }
}
```

Rendering — only when `dangling.length`, deduped by `(line, command)`, capped at 10
rows, `command` and `evidence` **both** in code spans with metacharacters neutralized,
and the format label reused (not hardcoded "AGENTS.md" — finding X):

```js
function cell(s) {                       // finding B: unwrapped text is link/image-injectable
  return String(s ?? '')
    .replace(/`/g, '')                   // no code-span break-out
    .replace(/[\r\n]+/g, ' ')
    .replace(/[ -]/g, ' ')
    .replace(/\|/g, '│')            // no row split (defensive; engine never emits '|')
    .slice(0, 120);
}
if (dangling.length) {
  const seen = new Set();
  const rows = dangling.filter(r => {
    const k = `${r.line}:${r.command}`;
    return seen.has(k) ? false : seen.add(k);
  }).slice(0, 10);
  body += `\n### 🔗 Dangling commands (${dangling.length})\n\n`;
  body += `These commands in ${fmtLabel} don't resolve to a make target, npm script, or path in this repo:\n\n`;
  body += `| Line | Command | Why |\n|-----:|:--------|:----|\n`;
  for (const r of rows) body += `| ${r.line ?? '—'} | \`${cell(r.command)}\` | \`${cell(r.evidence)}\` |\n`;
  if (dangling.length > rows.length) body += `\n…and ${dangling.length - rows.length} more.\n`;
}
```

Worked example (real engine output from the mini-repo fixture, not invented):

```
### 🔗 Dangling commands (2)

These commands in AGENTS.md don't resolve to a make target, npm script, or path in this repo:

| Line | Command | Why |
|-----:|:--------|:----|
| 7 | `make test` | `make target 'test' is not defined in Makefile` |
| 8 | `npm run evals` | `script 'evals' is not defined in package.json scripts` |
```

### `Enforce dangling gate` (new final step, id: `gate`)

```yaml
if: inputs.fail-on-dangling == 'true' && steps.dangling.outputs.dangling_count != '' && steps.dangling.outputs.dangling_count != '0'
```

Emits `::error::` with the count and file, then `exit 1`. The `!= ''` guard matters: a
skipped `dangling` step yields `''`, not `'0'` (finding E). It runs *after* the comment
step (R7), so the consumer always gets the explanation before the red build.

## Security model

Four load-bearing properties:

1. **`-P` (PYTHONSAFEPATH) on every inline `python3`.** The workspace is attacker-
   writable via PR; without `-P`, CWD is on `sys.path[0]` and a planted `json.py` /
   shadowed `skills/` executes. Inherited; the new steps are no exception.
2. **Base64 as an injection barrier.** `action.yml:145` interpolates
   `'${{ steps.score.outputs.result_b64 }}'` straight into the `github-script` body —
   safe *only* because base64 is a closed alphabet. Dangling payloads carry attacker-
   authored command strings; interpolating them raw is script injection into a context
   holding a comment-write `GITHUB_TOKEN`. `dangling_b64` inherits this (D5).
3. **Markdown neutralization at render time.** Escaping the transport does not make the
   content safe to *render*. `command`/`evidence` are wrapped in code spans with
   backticks stripped, so `[x](url)`/`!`/`|`/control chars cannot form a link, image,
   or broken row (finding B — the reachable vector is `npm run [pwned](https://evil)`,
   which the engine faithfully echoes into evidence). Not RCE — GitHub sanitizes HTML.
4. **Availability is bounded in the engine, not the Action.** The DoS vectors (include
   fan-out, include-regex backtracking, oversized/nested manifests) are fixed in 8.6.1,
   so the "cannot fail" gather step also cannot hang. A composite `run` step cannot set
   `timeout-minutes`, so this bound MUST live in the engine — which is why 8.6.1 is a
   precondition, not a nice-to-have.

**Fork-PR reality (findings Q/R).** On a PR from a fork, `GITHUB_TOKEN` is read-only,
so the comment step cannot post — this is a pre-existing property of the current
action, not introduced here. The security model must not claim a write capability that
does not exist on forks. Mitigation is *graceful degradation*, not `pull_request_target`
(which would run with a write token in the base-repo context against attacker code — a
worse footgun). On a fork PR the consumer sees the job-log summary (gather step §4)
instead of a comment; `fail-on-dangling` still works. The comment step must not hard-
fail when it cannot post (wrap the create/update in try/catch or `continue-on-error`).

**Pre-existing, out of scope:** the comment step already renders `result.warnings`
unescaped. Engine-generated but can echo file content. Not introduced here; separate
follow-up (Open questions).

## Verification plan

No claim is met until the named command has run and its output is shown. Static review
of `action.yml` does not verify a composite action — the lesson of PR #82, which is why
`action-selftest.yml` exists.

**Vehicle: extend `.github/workflows/action-selftest.yml`.** It already runs `uses: ./`
against this repo's own AGENTS.md with `comment-on-pr` on PRs. Add the fixture path to
its `paths:` filter (finding L) so fixture-only changes retrigger it.

**Anti-race (finding D):** only the existing self-test job posts a comment
(`comment-on-pr: true`). Every fixture-based job sets `comment-on-pr: false` and asserts
via **outputs**, never the shared PR comment — otherwise N jobs clobber one marker.

| # | Gate | Evidence / red signal |
|---|------|-----------------------|
| V1 | Suite stays green | `pytest` — baseline on `fix/check-commands-hardening`: **1392 passed**. No regression. |
| V2 | `action.yml` is valid | The selftest run itself is the real syntax gate (no `actionlint`/PyYAML in CI). Locally, `python3 -c "import yaml; yaml.safe_load(open('action.yml'))"` under a Python with PyYAML — NOT `python3 -P` (breaks 3rd-party imports) and NOT relied on in CI (finding N). |
| V3 | Clean repo emits no section | Existing selftest job: own AGENTS.md has 0 dangling → `dangling_count == '0'`, no section, **and the score comment still posts** (asserted — guards finding C). |
| V4 | Dangling detected end-to-end | New job, `comment-on-pr: false`, `skill-path: <fixture>/AGENTS.md` → `dangling_count == '2'`; assert the two commands via the `dangling_count` output + a decode of the step log. |
| V5 | Old engine degrades silently | New job with `schliff-version: '8.5.0'` → the check runs, finds no subcommand, `dangling_count == '0'`, job green (NOT "step skipped" — the step runs; finding M). Probe-free path verified locally: 8.5.0 → argparse exit 2, empty stdout. |
| V6 | Hostile strings don't break rendering | Fixture AGENTS.md with `npm run [pwned](https://evil.example)` (the reachable link-injection vector) and a backtick → rendered body has no anchor/image and no broken row (finding B/O; `\|` is defensive-only since the engine never emits a literal pipe in a command). |
| V7 | Gate fires after the comment | Fixture job, `fail-on-dangling: 'true'`, action step with `continue-on-error: true`; a following step asserts `steps.<action>.outcome == 'failure'` AND the comment was posted first — the `continue-on-error` is on the *step*, so the job can assert the red outcome without dying (resolves finding P). |
| V8 | Non-AGENTS format untouched | Job with `skill-path` = a SKILL.md → `dangling` step skipped (format gate), comment identical to today. |

**Fixture:** commit `skills/schliff/tests/fixtures/dangling-repo/` with `AGENTS.md` +
`Makefile` + `package.json`. Because D2 resolves against the file's directory, the
engine resolves against the fixture dir with no `--repo` and no workspace clobbering —
which is exactly why dirname is the testable choice.

**Merge constraint:** this PR touches `.github/workflows/`, so the maintainer merges it
via the GitHub web UI (token scope).

## Non-goals

- Any change to `score_operational_coverage`, weights, or golden scores. Reporting only.
- GitHub annotations / `$GITHUB_STEP_SUMMARY` (D1 chose one human surface; revisit only
  with evidence the comment is missed).
- The `minimum-score`-suppresses-comment interaction.
- **Nested-file root-relative paths (finding K/#10 residual).** With D2 (dirname), a
  *nested* `packages/api/AGENTS.md` that references a *root-relative* path
  (`./scripts/x.sh` living at the repo root, not under `packages/api/`) can false-
  dangle. Narrow (nested file + root-relative path + explicit `skill-path`), and the
  inverse (`$GITHUB_WORKSPACE`) has the larger, more common monorepo-manifest FP, so
  dirname is chosen. Documented, not fixed here.
- **Partial checkouts (finding J).** Sparse checkouts and uninitialized submodules hide
  files the engine would resolve against. A missing manifest degrades to `unknown`
  (safe), but a path inside an unchecked submodule can false-dangle. The Action assumes
  the default full `actions/checkout`; sparse/submodule is a consumer opt-in and is
  documented as a caveat, not code.
- Extending resolver coverage. Verified 2026-07-20: `./scripts/nope.sh` under a
  "Testing" heading was not reported despite not existing, because the extractor did not
  classify that line into a command family. Coverage is "commands the extractor
  classifies", and docs must not overstate it.

## Open questions

1. **Warnings escaping** — pre-existing unescaped `result.warnings`; separate small PR.
2. **README / Action docs** — the new input, the AGENTS.md/CLAUDE.md-only scope, and the
   fork-PR / partial-checkout caveats need documenting before release.
