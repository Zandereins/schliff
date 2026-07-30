# Schliff Scoring System

How Schliff measures skill quality — and what the numbers actually mean.

Schliff is deterministic: the same input always produces the same score. The
headline composite uses the canonical registry weights, and calibration is OFF by
default, so `verify`, `badge`, and the leaderboard are reproducible across machines.

---

## What gets scored

Schliff runs a set of **structural scorers** over an instruction file and (optionally)
its eval suite. These are static-analysis checks — they measure file organization,
keyword coverage, assertion breadth, information density, and so on. They run
instantly and require no LLM invocation.

The **structural score** is the composite renormalized over the dimensions Schliff can
measure deterministically without an eval suite — **structure, efficiency, composability,
and clarity**. It is what the web playground reports. The full 7-dimension composite
additionally folds in **triggers, quality, and edges**, which require an eval suite
(`schliff init`).

A high structural score is a **lint score**, not a guarantee of runtime quality. A
skill with a 99/100 structure can still fail when Claude actually runs it. Two
dimensions exist specifically as separate **signals** that are never folded into the
headline number:

- **security** — an advisory gate (pass/flag at threshold 70).
- **runtime** — opt-in, invokes Claude with eval prompts and checks `response_*`
  assertions against real output.

> The core engine is **stdlib-only** (requires Python >= 3.9). The optional `[evolve]`
> and `[judge]` extras (litellm / anthropic) exist only for the LLM-judge smoke-test
> and are not needed for scoring.

---

## The dimensions and their weights

Schliff supports five formats. The **skill.md family** — `SKILL.md`, `CLAUDE.md`, and
`.cursorrules` — shares one 8-scorer registry and one weight profile. `AGENTS.md` runs
the same 8 scorers **plus `operational_coverage`** and has its own 3-dimension headline
(see below). The **system prompt** format (`system_prompt`) has its own scorer and
weight set.

### skill.md family

Eight scorers run per file. Seven of them form the **headline composite**; `security`
is reported as a separate signal and `runtime` is opt-in (and also a separate signal).

| Dimension | Weight | Role | What it measures |
| --- | --- | --- | --- |
| **structure** | 0.15 | headline | Frontmatter (name, description), headers, examples, progressive disclosure, file length, dead content, referenced-file existence |
| **triggers** | 0.20 | headline | TF-IDF keyword overlap between description and eval prompts, with stemming, synonym expansion, domain-signal detection, negation handling; reports precision and recall |
| **quality** | 0.20 | headline | Eval-suite coverage: assertion-type diversity, feature breadth, descriptions, instruction-assertion coherence |
| **edges** | 0.15 | headline | Edge-case definitions in the eval suite: category diversity, expected behaviors, edge assertions |
| **efficiency** | 0.10 | headline | Information density (signal-to-noise ratio), actionable instructions, real examples, WHY-reasoning, verification commands |
| **composability** | 0.10 | headline | Scope boundaries, global-state assumptions, I/O contracts, handoffs, tool fallbacks, error behavior, idempotency, dependencies, namespace isolation, version notes |
| **clarity** | 0.05 | headline | Contradictions, vague references, ambiguous pronouns, incomplete instructions |
| **security** | 0.05 | **separate signal** | Injection / unsafe-pattern checks. **Excluded** from the skill.md-family headline; reported under `signals.security` with a pass/flag status. |
| **runtime** | n/a | **separate signal** | Actual Claude behavior via `response_*` assertions. **No profile weight**, never in any headline composite. Opt-in. |

The full registry profile lists all eight weights and sums to **1.00**. `security`
(0.05) is in that profile but is **excluded from the headline basis** for this family,
so the seven headline weights sum to **0.95** before normalization. Stage 2 of the
composite (below) renormalizes those seven back to 1.0, so `security` does not contribute
to the headline number unless a caller explicitly re-weights it via `--weights`.

> **Note:** `runtime` carries **no weight in any profile**. Any claim that runtime is a
> "10% weight" dimension is false — it is only ever a separate signal.

### AGENTS.md profile

`AGENTS.md` is project context for a coding agent, not a reusable skill, so its
headline is a 3-dimension operational profile (the eval-gated dimensions — triggers,
quality, edges — are excluded, and the remaining scorers stay separate signals):

| Dimension | Weight | What it measures |
| --- | --- | --- |
| **structure** | 0.40 | Same structural scorer as the skill.md family |
| **operational_coverage** | 0.40 | Whether the doc equips an agent to operate the repo: real setup/build/test commands (junk-, read-only- and prose-hardened command classification) plus code-style / gotcha / PR directive sections with concrete code tokens |
| **efficiency** | 0.20 | Information density — deliberately demoted: fenced-code density is a gameable proxy for operational value |

Design, hardening and anti-gaming evidence: `docs/specs/agents-md-operational-coverage.md`.

### system_prompt format

The system-prompt profile uses a different scorer set, and here **security is a core
headline dimension** (weight 0.15) that stays in the composite — only `runtime` is
excluded.

| Dimension | Weight |
| --- | --- |
| structure_prompt | 0.15 |
| output_contract | 0.15 |
| efficiency | 0.15 |
| clarity | 0.15 |
| security | 0.15 |
| composability | 0.10 |
| completeness | 0.15 |

> The exclusion of `security` from the headline is **specific to the skill.md family**
> (`skill.md` / `claude.md` / `cursorrules` / `agents.md`). For `system_prompt`, security
> stays in. Both weight profiles live in `scoring/registry.py`, the single source of truth.

### Format token budgets

Each format carries a recommended token budget (`scoring/formats.py`):

| Format | Budget (tokens) |
| --- | --- |
| skill.md | 2000 |
| claude.md | 2000 |
| cursorrules | 500 |
| agents.md | 3000 |
| system_prompt | 1500 |

---

## Grade scale

Grades come from `terminal_art.score_to_grade` (`_GRADE_THRESHOLDS`):

| Grade | Threshold | Meaning |
| --- | --- | --- |
| **S** | >= 95 | Exceptional — near-perfect on measured dimensions |
| **A** | >= 85 | Strong — minor polish remains |
| **B** | >= 75 | Good — clear improvement paths exist |
| **C** | >= 65 | Adequate — significant gaps in multiple dimensions |
| **D** | >= 50 | Weak — fundamental issues need attention |
| **E** | >= 35 | Poor — most dimensions below acceptable |
| **F** | < 35 | Failing — major structural problems |

Grades apply to the composite score and to each individual dimension.

---

## How the composite is computed (full-denominator model)

This is the part that is most often misunderstood, so read carefully.

Schliff uses a **full-denominator model**. Unmeasured dimensions are **uncredited but
stay in the basis** — they contribute 0 to the score and are *not* removed from the
denominator. The practical consequence: **a skill's score ceiling equals its weight
coverage.** If you can only measure dimensions worth 60% of the headline weight (e.g.
because there is no eval suite yet), the best possible composite is 60.

This is computed in two stages (`scoring/composite.py::compute_composite`):

**Stage 1 — apply weight overrides (raw).** If the caller passes `--weights` (custom)
or opts into calibrated weights, those values overwrite the registry weights *without*
renormalizing yet. (Custom weights also drop the supplementary `clarity`/`security`
dims unless explicitly named.)

**Stage 2 — canonical headline basis (the single normalization point).** Dimensions in
the format's *headline-excluded* set are dropped (for the skill.md family: `security`
and `runtime`; for `system_prompt`: only `runtime`). The remaining weights are
**renormalized to sum to 1.0**. This fixed basis is the same for every entrypoint, so
there is no dual-scale problem.

**Aggregation.** Because the canonical weights already sum to 1.0, the composite is
simply the sum of `score × weight` over the **measured** dimensions:

```
composite = Σ ( score[dim] × canonical_weight[dim] )   for dim in MEASURED
```

There is no separate division step. An unmeasured dimension simply adds 0 — its weight
is *not* redistributed to the others. That is what makes the ceiling equal to coverage.

> **This replaces the old (incorrect) renormalization model.** Earlier docs claimed that
> an unmeasured dimension's weight was *excluded from the denominator and the remaining
> weights renormalized across the measured dims*. That is wrong. Under the true model the
> basis is fixed (renormalized once over the headline dims, before measurement is
> considered), and missing dims are penalized by contributing 0 rather than being
> dropped.

When dimensions are unmeasured, the result carries a warning of the form:

```
Scored M/N dimensions — the score can't exceed COVERAGE% until the rest are
measured. Run /schliff:init to add an eval suite and score: <missing dims>.
```

`weight_coverage` (the fraction of headline weight that was actually measured) and the
measured/total dimension counts are returned alongside the score so consumers know how
trustworthy the number is.

### Worked example

Take a `SKILL.md` with a frontmatter and body but **no eval suite**. Only the
text-based dimensions can be measured; `quality` and `edges` (which need an eval suite)
come back unmeasured.

First, the headline basis is built (security + runtime excluded). The seven raw weights
sum to 0.95, so Stage 2 renormalizes each by dividing by 0.95:

| Dimension | Raw weight | Canonical weight (÷0.95) | Score | Contribution |
| --- | --- | --- | --- | --- |
| structure | 0.15 | 0.1579 | 90 | 14.21 |
| triggers | 0.20 | 0.2105 | 80 | 16.84 |
| quality | 0.20 | 0.2105 | *(unmeasured)* | 0 |
| edges | 0.15 | 0.1579 | *(unmeasured)* | 0 |
| efficiency | 0.10 | 0.1053 | 85 | 8.95 |
| composability | 0.10 | 0.1053 | 70 | 7.37 |
| clarity | 0.05 | 0.0526 | 95 | 5.00 |

Composite = 14.21 + 16.84 + 0 + 0 + 8.95 + 7.37 + 5.00 ≈ **52.4** → grade **D**.

Weight coverage = 0.1579 + 0.2105 + 0.1053 + 0.1053 + 0.0526 = **0.63**, so even with
perfect scores on the five measured dims the ceiling would be **63**. The unmeasured
`quality` and `edges` canonical weights (≈0.37) are *not* redistributed — they drag the
ceiling down on purpose, signalling "add an eval suite." Running `/schliff:init` to
generate one is the fix.

Under the old (wrong) renormalization model this same skill would have renormalized only
across the *measured* dims, scoring `52.4 / 0.63 ≈ 83` → grade **B**, hiding the missing
coverage. The full-denominator model refuses to reward an unmeasured skill.

---

## Calibration (opt-in, off by default)

Schliff can auto-calibrate weights from runtime data (stored at
`~/.schliff/meta/calibrated-weights.json`), but this is **off by default** so that the
headline composite stays deterministic and comparable across machines.

Calibrated weights only apply when **both** of these hold:

1. The environment variable `SCHLIFF_CALIBRATED_WEIGHTS` is set to `1`/`true`/`yes`/`on`.
2. The caller explicitly opts in (`use_calibrated=True`) — only the interactive `score`
   command does this.

Cross-comparison consumers (`verify` CI gate, `badge`, leaderboard) always leave
calibration off, so their decisions never depend on a per-machine env var. When
calibrated weights are in effect the result is stamped `weight_source=calibrated` and a
warning notes that the score is **not comparable** to default-weight scores.

Weight-resolution priority:

1. `--weights` CLI flag (custom, highest)
2. Calibrated weights (only under the opt-in conditions above)
3. Canonical registry defaults (lowest — the reproducible baseline)

---

## Weight override syntax

Override dimension weights via `--weights`:

```bash
python score-skill.py SKILL.md --weights "triggers=0.4,structure=0.3"
```

- Key-value pairs separated by commas.
- Supplementary dims (`clarity`, `security`) are dropped from the basis unless you name
  them explicitly.
- The canonical basis is the single normalization point — the supplied weights are
  renormalized to sum to 1.0 over the resulting headline dims.
- Invalid values cause an immediate error with a clear message.

---

## Anti-gaming

Anti-gaming detection is part of the engine, not a bolt-on. It lives in
`scoring/guards.py` plus per-scorer logic, and it exists so a skill cannot inflate a
dimension by, for example, padding keyword lists, stuffing trivially-passing assertions,
or repeating near-duplicate instructions. Detected gaming patterns are discounted before
they reach the headline.

The full-denominator model is itself an anti-gaming property: because unmeasured
dimensions are uncredited rather than dropped, you cannot raise the composite by simply
omitting the dimensions you would score poorly on.

---

## Security and runtime as separate signals

Both `security` and `runtime` are reported under `signals` (and `security` additionally
under the top-level `security` field), never folded into the skill.md-family headline:

- **security** — scored 0–100, with `status: "pass"` when `score >= 70` (the security
  gate, `SECURITY_GATE = 70`) and `status: "flag"` otherwise. For `system_prompt` this
  same scorer is *also* a core headline dimension (weight 0.15).
- **runtime** — opt-in; runs eval prompts through Claude and reports the pass rate.
  Degrades gracefully (skipped) when the `claude` CLI is unavailable. Has no profile
  weight in any format.

---

## Source-of-truth map

| Concern | File |
| --- | --- |
| Canonical weights, scorer lists, headline-exclusion, aliases | `scoring/registry.py` |
| Composite computation (full-denominator model) | `scoring/composite.py` |
| Grade thresholds, gauges | `terminal_art.py` |
| Format detection, normalization, token budgets | `scoring/formats.py` |
| Anti-gaming guards | `scoring/guards.py` + per-scorer modules |
| Valid dimension names | `shared.py` (`VALID_DIMENSIONS`) |
| Patch-ratio measurement | `measure_patch_ratio.py` |

Version is single-sourced: the CLI reads it via
`importlib.metadata.version("schliff")` (`_resolve_version` in `cli.py`), falling back
to `dev` in a source checkout. Current release: **8.2.0**.
