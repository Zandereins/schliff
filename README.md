# Schliff

**Your AI instruction files silently degrade — and nothing catches it.** A trigger phrase rots. An edge case slips. Your `SKILL.md` balloons past its token budget. No error, no red test — just an agent that quietly gets worse.

**A deterministic quality scorer for AI instruction files.** Same input, same score — every time, on every machine. Think the [Ruff](https://github.com/astral-sh/ruff) for `SKILL.md`, `CLAUDE.md`, and `AGENTS.md`. It measures the things linters miss, the same way every time, so degradation shows up as a number that drops instead of a bug you chase.

[![PyPI](https://img.shields.io/pypi/v/schliff?color=blue&label=PyPI&v=8.4.0)](https://pypi.org/project/schliff/)
[![Python](https://img.shields.io/pypi/pyversions/schliff)](https://pypi.org/project/schliff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/Zandereins/schliff/actions/workflows/test.yml/badge.svg)](https://github.com/Zandereins/schliff/actions/workflows/test.yml)

Schliff scores the instruction files that drive your AI agents — skills, system prompts, project memory — against an explicit, versioned rubric, so you can gate a release on the number in CI. No LLM judge in the critical path. No network. No randomness. Just a rule engine you can read, pin, and trust.

```bash
pip install schliff
schliff score path/to/SKILL.md
```

```text
schliff v8.4.0

  structure      ████████░░   78/100  good
  triggers       ███████░░░   72/100  good
  quality        ██████░░░░   64/100  fair
  edges          █████░░░░░   55/100  fair
  efficiency     ████████░░   80/100  good
  composability  ███████░░░   70/100  good
  clarity        ██████████  100/100  perfect

  Structural Score  ██████████████░░░░░░  71.2/100  [C]

  Tokens: 740 / 1,000 (ok)
```

No model in the loop produced that number. Run it again on another laptop and you get 71.2 again. That is the whole point.

---

## A real catch

A SKILL.md for [ShieldClaw](docs/case-studies/shieldclaw/) — a real prompt-injection-defense skill, now archived — scored **68.3 [C]** — and Schliff showed exactly why: composability **20/100** (no scope boundaries, no I/O contract, no handoffs), and **3 of 7 dimensions unmeasurable** because there was no eval suite. After adding the missing scope section and an eval suite, the same file scored **94.6 [A]** on all 7 dimensions.

| | Score | Grade | Dimensions measured |
| --- | --- | --- | --- |
| Before | 68.3 | C | 4/7 (no eval suite) |
| After | 94.6 | A | 7/7 |

Defects you'd otherwise ship caught as a number that's too low — see the [full case study](docs/case-studies/shieldclaw/).

---

## Why deterministic?

Most "AI quality" tools ask another LLM to grade your prompt. That makes the score **non-reproducible** (re-run it, get a different number), **un-auditable** (the rubric lives in a hidden prompt), and **trivially gameable** (write for the judge, not the user). A score you can't reproduce isn't a measurement — it's a vibe. You can't gate a release on a number that drifts.

Schliff takes the opposite position:

- **Reproducible.** The headline composite is computed from a canonical, versioned weight registry. Calibration is **off by default**, so `verify`, `badge`, and the leaderboard return the same score on your laptop and in CI.
- **Auditable.** Every dimension is a readable scorer in [`scripts/scoring/`](skills/schliff/scripts/scoring/). The weights are a dict you can open. There is no hidden judge prompt.
- **Anti-gaming by design.** A dedicated guard layer ([`guards.py`](skills/schliff/scripts/scoring/guards.py)) plus per-scorer heuristics detect padding, keyword stuffing, and structure-mimicry instead of rewarding them.
- **Zero core dependencies.** Core Schliff is stdlib-only and runs on **Python ≥ 3.10**. (Optional `[evolve]` / `[judge]` extras pull in LLM clients for an opt-in smoke-test only — never for scoring.)

Because the number is stable, it does real work:

- **Diff** it across two commits to see exactly what a refactor cost or earned.
- **Gate** a pull request on a minimum score, with a non-zero exit code below the line.
- **Compare** two files side by side on the same rubric.

> An optional LLM judge exists for exploratory work, but it is never part of the deterministic score. The number you gate on is rule-based, end to end.

---

## The 8 scored dimensions

For the `SKILL.md` family, Schliff runs **8 scorers** per file. **7 of them form the headline composite**; `security` and `runtime` are reported as **separate opt-in signals** so a security warning never silently inflates or deflates your quality grade.

| Dimension | Weight | In headline? |
| --- | --- | --- |
| `structure` | 0.15 | ✅ |
| `triggers` | 0.20 | ✅ |
| `quality` | 0.20 | ✅ |
| `edges` | 0.15 | ✅ |
| `efficiency` | 0.10 | ✅ |
| `composability` | 0.10 | ✅ |
| `clarity` | 0.05 | ✅ |
| `security` | 0.05 | Separate signal (gate threshold 70) |
| `runtime` | — | Separate signal (no profile weight) |

The seven headline weights are renormalized to sum to **1.0** — that is the canonical basis.

> **Note:** `security` is a side signal for the `SKILL.md` / `CLAUDE.md` / `.cursorrules` / `AGENTS.md` family, but a **core 0.15 headline dimension for the `system_prompt` format**, which uses its own scorer set. Only `runtime` is excluded everywhere.

### The composite: a full-denominator model

Schliff does **not** quietly renormalize across whatever you happened to measure. Unmeasured dimensions **contribute 0 and stay in the denominator** — so coverage gaps lower your ceiling instead of quietly disappearing. Your score ceiling equals your measurement coverage. Measure 4 of the 7 headline dimensions and your maximum possible score is capped accordingly, with an explicit warning:

```text
ℹ Scored 4/7 dimensions — the score can't exceed 42% until the rest
  are measured. Run /schliff:init to add an eval suite and score:
  triggers, quality, edges.
```

This is deliberate. A partial measurement is an honest partial score, never a flattering one. Unmeasured work is missing points, not invisible. To lift the ceiling, measure more — don't hide the gap.

### Grade scale

`S` ≥ 95 · `A` ≥ 85 · `B` ≥ 75 · `C` ≥ 65 · `D` ≥ 50 · `E` ≥ 35 · `F` < 35

---

## Multi-format support

One engine, five instruction-file formats — each with its own token budget and scorer set:

| Format | Token budget | Scorers |
| --- | --- | --- |
| `SKILL.md` | 1,000 | shared 8-scorer registry |
| `CLAUDE.md` | 2,000 | shared 8-scorer registry |
| `.cursorrules` | 500 | shared 8-scorer registry |
| `AGENTS.md` | 3,000 | shared 8 scorers + `operational_coverage` (own 3-dim headline) |
| system prompts | 1,500 | dedicated set (`structure_prompt`, `output_contract`, `efficiency`, `clarity`, `security`, `composability`, `completeness`) |

Format is auto-detected; override with `--format` (`skill`, `claude`, `cursor`, `agents`, `system-prompt`).

---

## Install

```bash
pip install schliff                  # core, stdlib-only
pip install "schliff[evolve,judge]"  # optional LLM-judge / evolve extras
```

| Install | Pulls in | When you need it |
| --- | --- | --- |
| `schliff` | stdlib only | Scoring, verify, badge, CI — everything that gates a release |
| `schliff[judge]` | LLM client | Opt-in exploratory LLM-judge smoke-test (never scoring) |
| `schliff[evolve]` | LLM client | Opt-in autonomous-improvement extras |

### GitHub Action

Gate pull requests on instruction-file quality. The action defaults to your
repo-root `AGENTS.md` and posts a scored comment on every PR:

```yaml
# .github/workflows/agents-lint.yml
name: AGENTS.md Lint
on: [pull_request]
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Zandereins/schliff@v1
        with:
          minimum-score: '75'   # optional: fail the PR below this score
```

By default it scores `AGENTS.md` at the repo root; set `skill-path:` to lint a
`SKILL.md`, `CLAUDE.md`, or `.cursorrules` instead.

Prefer not to depend on a third-party action? The dependency-light equivalent:

```yaml
      - run: pip install schliff
      - run: schliff verify AGENTS.md --min-score 75
```

`schliff verify` exits non-zero below the threshold — a clean CI gate either way.

### pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Zandereins/schliff
    rev: v8.4.0
    hooks:
      - id: schliff-verify
        args: ['--min-score', '75']
```

---

## CLI

```text
schliff <command> [path] [options]
```

| Command | What it does |
| --- | --- |
| `score` | Score a file and print the grade bar |
| `verify` | CI gate — exit 0/1 based on a minimum score |
| `doctor` | Scan and grade every installed skill |
| `badge` | Generate a Markdown score badge |
| `diff` | Explain score changes between two git commits |
| `compare` | Compare two files side by side |
| `suggest` | Rank fixes by estimated score impact |
| `report` | Generate a Markdown score report |
| `demo` | Score a built-in bad skill to see Schliff in action |
| `evolve` | Improve an instruction file's score |
| `version` | Print the version |

The version is **single-sourced**: the CLI resolves it at runtime via `importlib.metadata.version("schliff")`, falling back to `dev` from a source checkout.

---

## Optional: closing the loop

Beyond grading, Schliff can apply fixes. The improvement engine **measures first, then fixes** (not the other way around):

1. **Score** the file across all dimensions.
2. **Generate** deterministic patch gradients for the weakest dimensions.
3. **Apply** the safe, rule-based patches automatically — **~32% of suggested fixes** apply deterministically through the apply gate (confidence=high, single-edit; canonical measurement: [`measure_patch_ratio.py`](skills/schliff/scripts/measure_patch_ratio.py)). The rest are handed to an optional LLM.
4. **Re-score** and keep the change only if the score improved — otherwise revert.
5. **Stop** on plateau detection or when the target is reached.

It also carries **cross-session episodic memory** ([`episodic_store.py`](skills/schliff/scripts/episodic_store.py)), so improvement runs learn from prior attempts instead of repeating them. Drive it from Claude Code with `/schliff:auto`, or use `schliff evolve` directly. This is an optional convenience layer — the deterministic score is the product.

```text
→ 7 deterministic fixes available. Run `/schliff:auto` to apply.
```

---

## How it works

The full methodology — scorer internals, the full-denominator composite, the anti-gaming guards, and the calibration model — lives in [`docs/SCORING.md`](docs/SCORING.md). Calibration is strictly opt-in: ambient auto-calibrated weights apply **only** when `SCHLIFF_CALIBRATED_WEIGHTS` is set and **only** for the interactive `score` command, and Schliff emits a `weight_source=calibrated` warning flagging that such scores are **not** comparable to the canonical scale. Everything that gates a release stays canonical.

```text
scripts/
├── cli.py                  # CLI entrypoint + dynamic version resolution
├── scoring/
│   ├── registry.py         # canonical weights, scorer lists, headline exclusions
│   ├── composite.py        # full-denominator composite model
│   ├── formats.py          # format detection + token budgets
│   ├── guards.py           # anti-gaming detection
│   └── structure.py · triggers.py · quality.py · edges.py · …
├── text_gradient.py        # deterministic patch gradients (apply gate)
├── episodic_store.py       # cross-session episodic memory
└── measure_patch_ratio.py  # canonical source for the patch-ratio claim
```

---

## Positioning

> **LLM-judge tools** ask a model how good your prompt *feels* — a different answer every run.
> **Schliff** computes how good it *measurably is* — the same answer every run, in a number you can pin to a commit and gate a release on.

Ruff lints your Python. Biome lints your JS. Schliff lints the instruction files that drive your AI — deterministically, with no model in the loop.

---

## Contributing & links

- ⭐ **Star the repo:** [github.com/Zandereins/schliff](https://github.com/Zandereins/schliff)
- 📖 **Docs:** [`docs/SCORING.md`](docs/SCORING.md)
- 🧪 **Playground:** [schliff-playground.vercel.app](https://schliff-playground.vercel.app) — paste a SKILL.md or AGENTS.md, get a live score (or `schliff demo` in the CLI)
- 🏆 **Leaderboard:** [schliff-leaderboard.vercel.app](https://schliff-leaderboard.vercel.app)

> **Structural score** = the composite renormalized over the dimensions Schliff can
> measure deterministically without an eval suite (structure, efficiency, composability,
> clarity). It is what the web playground reports for SKILL.md. The full 7-dimension
> composite additionally folds in triggers, quality, and edges — which require an eval
> suite (`schliff init`). AGENTS.md needs no eval suite: its full 3-dimension headline
> (structure, operational_coverage, efficiency) is always measurable.

Validated by **1,347 tests** (unit + integration) in `skills/schliff/tests`, with separate self and proof suites via `test-self.sh` and `test-integration.sh`.

## License

MIT © Franz Paul
