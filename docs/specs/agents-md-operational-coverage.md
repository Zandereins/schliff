# Spec — AGENTS.md `operational_coverage` scoring dimension

- **Status:** Design approved (council-optimized). Spec/design only — **no engine code in this document's scope.**
- **Date:** 2026-06-26
- **Parent spec:** [`agents-md-scoring-profile.md`](agents-md-scoring-profile.md) — this dimension is its designated "Fast-follow."
- **Council record:** 14-agent ultracode (prototype → 6 expert lenses → refute-by-default verify → chairman), output at `tasks/wu5zxbmt8.output`.
- **Build posture:** the engine is a freeze-candidate; implementation is a **separate, explicitly-gated step**. Re-baselining the corpus moves live AGENTS.md scores.

---

## 1. Goal

Add a deterministic `operational_coverage` (opcov) dimension to the `agents.md` headline that measures **whether an AGENTS.md actually equips a coding agent to operate the repo** — runnable setup/build/test commands plus code-style, PR/commit, and gotcha guidance — and demote `efficiency`, which is a **gameable proxy** for that value.

Success = the validated misrank is corrected without introducing new ones, the new scorer cannot be cheaply gamed above a genuine operational doc, and determinism/byte-identity for other formats is preserved.

## 2. Context & evidence (the validated trigger)

The current `agents.md` headline is `0.5·structure + 0.5·efficiency`. `efficiency` rewards fenced-code **density**, not command **value**, and ignores inline-backtick commands. Verified on the real engine:

| Doc (controlled, length/structure-matched) | operational value | old composite |
|---|---|---|
| `D_fence_gaming` — `echo`/`ls`/`pwd` junk in ```bash fences | worthless | **92.5 / A** |
| `B_operational` — real `pnpm install/build/test`, fenced | high | 88.0 / A |
| `E_inline_useful` — same real commands, inline backticks | high | **70.0 / C** |
| `A_hollow` — polished prose, no commands | none | 60.0 |
| `C_gaming` — bare headings | none | 53.5 |

Corpus (30 real files): inline-command-rich docs cluster low; real-pair inversion `JanDeDobbeleer/copilot-ralph` (35 commands) `64.0/C` **<** `deanthecoder/MasterG33k` (1 command, an AgentPrimer context-dump, no build/test) `83.0/B`.

Both parent-spec gates are met: an empty-doc gaming repro **and** a corpus-validated misrank.

## 3. Why `v0` was reworked (council finding)

The first design (`v0`) credited a category only when its **heading** matched a synonym *and* contained a non-junk command. A prototype of `v0` on the real engine showed it does **not** eliminate gaming — it **relocates** it, and it **floors genuine docs**:

- **Gaming relocates, not dies:** `git status`×3 → composite **91.2/A**; `npm install`×3 + platitudes → **91.8/A**; bare inline `npm`/`make`/`pytest` → opcov **100** — all **above** the genuine `B_operational` (88.2). English prose classifies as commands: `go to the dashboard`, `make dinner`, `python the snake`.
- **Genuine docs floored:** `PNNL-CIM-Graph` (10 real code-style rules, no command) → opcov **0**; `kudu` (real `npm test` under a "Before Committing" heading) → **25**.

Root cause: **heading-gating re-measures `structure` inside the operational dimension.** A byte-identical command flips opcov ±20 purely by renaming its heading. The fix is to **drive credit from the command itself** and make headings a booster, **bundled with** command-hardening so decoupling does not amplify gaming.

The architecture (a new deterministic scorer + the `0.4 / 0.4 / 0.2` profile) is **unchanged and approved**. The detection internals are reworked below.

## 4. The optimized design

### 4.1 Categories & weights (provisional, N=30, no ground-truth labels)

Binary per-category credit; `score = sum of credited weights`, integer, `0–100`.

| Category | Weight | Credit type |
|---|---|---|
| setup / install | 20 | command |
| build / run | 20 | command |
| test / lint | 20 | command |
| code-style / conventions | 15 | directive |
| gotchas / pitfalls | 15 | directive |
| PR / commit rules | 10 | directive |

Graded/partial credit is **rejected** (cosmetic at N=30 with no labels). The only graded element is the diversity rule (§4.2.4).

### 4.2 Command credit — family classification + hardening

A category is **command-credited** from any real command of that family appearing **anywhere in the doc**; heading-synonym match is a **fallback booster, never a gate**. Command families:

- **setup** ← `install` / `ci` / `sync` / `add` / `cp .env*` / `*migrate`
- **build** ← `build` / `compile` / `run build` / `cargo build` / `tsc` / `vite` / `make`
- **test** ← `test` / `run test` / `pytest` / `vitest` / `jest` / `ruff` / `eslint` / `mypy` / `prettier` / `typecheck`

Decoupling ships **only bundled** with all of the following hardening (neither lands alone):

1. **Two-tier verb set.**
   - *Strict tier* (unambiguous tool names): `npm pnpm yarn bun pip uv poetry cargo pytest vitest jest ruff eslint mypy tsc docker kubectl gradle mvn dotnet` — may credit with a subcommand/operand.
   - *Guarded tier* (English homonyms): `go make just node python ruby swift task biome git gh` — credit **only** with a recognized subcommand, flag, or path token. Kills `go to the dashboard`, `make dinner`.
2. **Read-only / inspection verbs are junk-equivalent** (never credit): `git status|log|diff|show|branch`, `docker ps`, `npm ls`, and any first-arg `version|help|--version|--help|-v|-h`. Kills the `git status`×3 = opcov 100 hole. (`git commit|rebase|squash` survive only as a **PR-directive** signal, not a command.) The original junk-filter (`echo ls pwd cd true cat whoami date clear`) remains.
3. **Inline spans must be command-shaped** (not merely "has an argument" — refuted on the engine: `go to the dashboard` has args). Require a leading `$`/`#` prompt, **or** a verb followed by a flag (`-x`/`--x`), a subcommand, or a path token (`./`, `/`). **Bare single-token inline rejected** — kills name-dropping `` `npm` ``.
4. **Command diversity:** dedupe identical command lines doc-wide; require **≥2 distinct real commands** before crediting all three command categories. Kills heading-multiplication (`git status`×3 / `npm install`×3).
5. **Negation guard** (bound to #1): skip a command token whose sentence carries `do not` / `don't` / `never` / `avoid`. Latent in `v0` (masked by heading-gating); load-bearing once gating is removed.
6. **Conservative recall** (low risk): credit script delegation (`./script.sh`, `bash|sh <script>`); expand verbs with `nix zig mix dart flutter pdm gleam`; soften heading *boosters* to inflected forms (`\bcheck`, `\bbuild`, `\bsetup`, `validate|validation`) to catch e.g. `MacroGraph` "Checking your code".

Fenced-block scanning is restricted to shell-family languages (`'' bash sh shell console zsh fish ps1 powershell …`) so ```typescript / ```go / ```text samples are not miscredited as commands.

### 4.3 Directive credit — tightened

- **Narrow `NORMATIVE`.** Drop universal soft cues (`use value ask note important communicate document`). Require an imperative-verb-plus-concrete-object **or** an inline-code token, **and ≥2 distinct cues**. Closes the verified `A_hollow`=30 platitude over-credit ("We communicate via carrier pigeon" must not credit).
- **Content-driven `code_style` fallback (rescues PNNL).** Credit `code_style` when a section has **≥2 normative rules and ≥1 concrete code token** (inline identifier / file-extension / tool-name), independent of heading. **CONDITIONAL:** must be empirically verified at build time against the real `PNNL-CIM-Graph` file to credit it **without** re-crediting `A_hollow`, before the implementation claims it as the fix.

### 4.4 Rejected / deferred

- **Graded credit** — rejected (cosmetic at N=30).
- **A new `compute_composite` "worthlessness gate"** (cap headline when distinct-command-count ≤1 and directive=platitude-only) — **deferred, not a v1 requirement.** `compute_composite` is a pure weighted sum (`guards.py` is unwired/frozen); a gate is new scored-path infrastructure on a freeze-candidate. It is also **unnecessary once §4.2 hardening lands**: with opcov ≈ 0 for gamers, the residual `0.4·structure + 0.2·efficiency` floor (~51) sits **below** `B_operational` (88), so gamers stay under genuine docs. Spec it as an **evidence-gated fallback**: re-run the red-team after hardening; escalate to a composite gate *only if* a gamer still beats `B_operational`, and then as a separate, explicitly-gated engine change.

## 5. Integration — exactly four edits (verified against `registry.py` / `shared.py` 2026-06-26)

Byte-identity for `skill.md` / `claude.md` / `cursorrules` / `system_prompt` is mandatory. opcov is registered for `agents.md` **only**, so it does not run for other formats.

1. **New `scoring/operational_coverage.py`** — `score_operational_coverage(skill_path: str) -> dict` returning `{"score": int >= 0, "details": dict}`, matching the existing scorer signature pattern.
2. **`shared._SCORER_MAP`** — add `"operational_coverage": ("scoring.operational_coverage", "score_operational_coverage")`.
3. **`registry.SCORER_REGISTRY["agents.md"]`** — change from `list(_INSTRUCTION_FILE_SCORERS)` to its **own literal** `[*_INSTRUCTION_FILE_SCORERS, "operational_coverage"]` (do not append to the shared `_INSTRUCTION_FILE_SCORERS` — that would leak opcov into the other instruction formats).
4. **`registry.WEIGHT_PROFILES["agents.md"]`** — `{"structure": 0.5, "efficiency": 0.5}` → `{"structure": 0.4, "operational_coverage": 0.4, "efficiency": 0.2}`.

**Do NOT touch `HEADLINE_EXCLUDED["agents.md"]`.** opcov was never in it; the canonical headline basis = `WEIGHT_PROFILES` keys − `HEADLINE_EXCLUDED`, so adding opcov to the weight profile folds it into the headline automatically. (The earlier "remove from `HEADLINE_EXCLUDED`" framing was a wrong fifth edit.)

**Nice-to-have (follow-up, not blocking):**
- Add `"operational_coverage"` to `shared.VALID_DIMENSIONS` so `--weights operational_coverage=…` is not rejected.
- A `text_gradient` opcov gradient generator for `/auto` and `/analyze`, weighted at agents.md's `0.4` (not the `0.10` skill.md fallback) — otherwise the co-dominant headline dim gives no fix advice.
- Commit the 30-doc per-category table as a fixture so any future weight/synonym change is regression-visible.

## 6. Re-baseline & golden test (R5)

**Sequencing is mandatory:** land hardening **and** decoupling together → re-run the full 30-file corpus → re-baseline R5 **once**. Re-baselining on the un-hardened scorer and again after hardening would bake recall misses in as "truth."

**Rewrite** `test_agents_md_profile.py` (do not "update the golden"):
- Replace the 50/50 assertion with the 3-dim profile; assert `score == 0.4·structure + 0.4·operational_coverage + 0.2·efficiency` and `measured == total == 3`.
- Re-derive mean / median / max (prototype: `underway` = 97.0) / band-counts on the **hardened** scorer.
- **Drop `meltano` from the S-boundary test** (now ≈ 91.0 / A); assert `underway == 97.0 / S` only.
- **Anti-gaming fixtures (post-hardening):** `opcov(D_junk)=0`, `opcov(C_bare)=0`, `composite(E)>composite(D)`, and `opcov(git-status-farm)` low, `opcov(inline-name-drop)=0`, `opcov(prose-verbs)` low.
- **Recall fixtures:** `PNNL-CIM-Graph` credits `code_style`; `kudu` credits `test`.

## 7. Deterministic invariants (assert in the scorer's tests)

- Integer-summed; **order-independent**; no time / random / env / network reads.
- `opcov(raw) == opcov(normalized_content)`.
- Pure stdlib, no new dependencies.

## 8. Decisions (Franz, council-recommended defaults adopted)

1. **English-only scope — accepted.** Directive heading/keyword lists are English; 2/30 corpus docs (CJK: `cxblovedd`, `VCnoC`) floor to opcov 0. Documented as English-scoped for v1 rather than starting keyword whack-a-mole.
2. **Provisional weights — accepted.** The 60/40 command/directive split and 20/20/20/15/10/15 are unfalsifiable at N=30 with no labels. Ship explicitly labeled provisional, with the per-category table committed (§5 nice-to-have).
3. **PNNL rescue is conditional** on the §4.3 build-time verification being green before it is asserted as the fix.

## 9. Out of scope (v1)

Command-syntax validation (rejected "approach B"); LLM-judge (rejected "approach C" — breaks determinism); command execution; any new `compute_composite` worthlessness gate (documented as an evidence-gated fallback only, §4.4).

## 10. Open follow-ups (post-landing, build only on a validated trigger)

Per-language verb-registry expansion, non-English directive support, and graded credit are deferred until a corpus or real-user signal justifies them — same measure-first discipline that gated this dimension.

## 11. Addendum — 2026-07-03 adversarial review (75-agent, 5 lenses + refute-by-default verify)

A post-implementation multi-agent review confirmed 22 findings + 4 critic findings against the first committed scorer. All were fixed on the branch, with regression tests, and the corpus was re-baselined once more (mean 60.53 → 61.06, median 61.40, bands A1/B4/C8/D11/E5/F1; max unchanged `underway` 91.0/A, no S).

**Fixed (behavioral):**

- **ReDoS (critical):** the heading regex tail `\s+(.*\S)\s*$` was quadratic on whitespace-only heading lines (measured 2.2 s at 20 KB, extrapolating to minutes at `MAX_SKILL_SIZE`) — the same vulnerability class as the project's earlier content-regex fix. Replaced with a linear pattern (`[ \t]+(\S.*)$`, trim in code); a warm timing test pins it.
- **Fence desync:** the fence regex only matched bare ` ```lang ` openers, so CommonMark info-string openers (` ```bash title="x" `) and 4+-backtick fences inverted the parser state for the remainder of the document (flooring genuine docs / scanning prose as shell). Now matches the engine-wide convention: any ` ``` `-prefixed line toggles.
- **Directive homonym hole (the §4.3 platitude class, relocated):** the prose-facing tool-name concreteness signal included the _GUARDED English homonyms, so "You must always **make** sure … before you **go** further … the **task** owner" farmed all 40 directive points (opcov 40 for a zero-content doc). The prose signal now excludes guarded homonyms; inside backticks the full set still counts.
- **Recall (the §3 "genuine docs floored" class):** `pytest -v [paths]` (first-flag read-only check inverted from the spec's first-arg rule; `-v` on a verb-intrinsic tool is verbose, not version), `python -m pytest` / `python3 -m pip install` / `python manage.py migrate` (interpreter delegation), `./gradlew build` / `./mvnw install` (runner wrapper scripts shadowed by the script-delegation branch), `docker build` / `docker compose build` (§4.2.1 strict tier — was entirely absent), `npx playwright test` / `bunx vitest` / `pnpm exec vitest` / `uv pip install` (exec-delegation), `cp .env*` and `*migrate`/`db:migrate` (§4.2 setup family — was unimplemented), `make -j4` (flag qualifies per §4.2.1), inline `$ pytest` (the §4.2.3 prompt signal was stripped before classification could see it).
- **Negation guard (§4.2.5):** now sentence-scoped as specced (was line-scoped: "Never commit to main. Run `pnpm test`." lost the credit); `instead of` removed (not in the spec's cue list; "use X instead of Y" recommends X); positive idioms `don't forget/skip` no longer suppress.
- **Spec-side corrections adopted into the implementation:** `git add`/`git init` no longer credit setup (git/gh removed from the guarded command tier — §4.2.2 confines git to junk/PR-directive roles); `tsc` moved to the build family (§4.2 lists it under build); bare guarded operand tightened to exactly one token (kills `` `make tests pass` ``).
- **Integration:** `operational_coverage` added to the CLI dimension display (terminal_art), the Action's PR-comment dimOrder (action.yml), and the leaderboard's accepted optional dimensions (submit.py).

**Deliberate deviations from this spec (implementation wins, spec adjusted here):**

- §4.2.2 read-only rule refined: `--version`/`--help` as first arg is junk; short `-v`/`-h` only when they are the *only* argument, and `-v` on a verb-intrinsic tool (pytest/ruff/…) stays creditable (verbose). The spec's literal first-arg `-v` rule floors real verbose test runs.
- §4.2/§4.2.6 command heading-*booster* is **not implemented**: command credit is fully command-driven; MacroGraph and kudu credit via commands alone. A heading path would re-introduce heading sensitivity for no measured recall gain.
- §4.3 "imperative-verb-plus-concrete-object" alternative is **not implemented**: prose-only concreteness re-opens the platitude hole the same section closes; the code-token arm plus the content fallback carries the PNNL rescue.
- `kubectl` never credits (no setup/build/test family exists for deployment verbs); it remains a directive concreteness signal only.

**§4.4 escalation decision (red-team re-run, REQUIRED by this spec): documented acceptance.** The re-run after all fixes kills every worthless-text gamer (junk fences 54.0/D, platitude farm opcov 0, keyword-stuffers below genuine docs). One vector remains: a *plausible fabrication* — three syntactically valid but invented commands (`npm install` / `npm run build` / `npm test`) plus three concise directive sections with real-looking tokens reaches 97.0/S. This is **accepted, not escalated**: such a document is textually indistinguishable from a genuine minimal AGENTS.md (identical text would be a *correct* AGENTS.md for most Node repos), so no deterministic text scorer can separate them without executing commands (out of scope, §9) — and the deferred worthlessness gate (distinct-command-count ≤ 1) would not fire on it either. The anti-gaming guarantee is therefore scoped precisely: **worthless text cannot outrank operational text; plausible lies about a repo remain out of reach of static scoring.** Pinned as a documented-limit test (`test_known_limit_plausible_fabrication_scores_high`).
