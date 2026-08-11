<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Zandereins/schliff/main/docs/assets/hero-dark.svg">
    <img src="https://raw.githubusercontent.com/Zandereins/schliff/main/docs/assets/hero-light.svg" alt="Schliff — deterministic quality scores for AGENTS.md" width="840">
  </picture>
</div>

**The Ruff for `AGENTS.md` — deterministic quality scores for the instruction files that drive your AI. Same input, same score, on every machine.**

[![PyPI](https://img.shields.io/pypi/v/schliff?color=blue&label=PyPI&v=8.11.1)](https://pypi.org/project/schliff/)
[![Python](https://img.shields.io/pypi/pyversions/schliff)](https://pypi.org/project/schliff/)
[![Tests](https://github.com/Zandereins/schliff/actions/workflows/test.yml/badge.svg)](https://github.com/Zandereins/schliff/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Your AI instruction files silently degrade — and nothing catches it.** `AGENTS.md` is read by Cursor, Codex, Copilot, and Claude Code — one rotting file now quietly degrades four tools. A trigger phrase rots, an edge case slips, the file balloons past its token budget. No error, no red test — just agents that quietly get worse.

Schliff scores `AGENTS.md` — and the rest of the family (`SKILL.md`, `CLAUDE.md`, `.cursorrules`, system prompts) — against an explicit, versioned rubric. No LLM judge in the critical path. No network. No randomness. A rule engine you can read, pin, and gate CI on.

**Inside Claude Code** — wires up the `/schliff:*` commands (scoring, `/schliff:auto`, `/schliff:doctor`, ...):

```text
/plugin marketplace add Zandereins/schliff
/plugin install schliff@schliff
```

**From a terminal** — for CI, pre-commit, or scripting outside Claude Code:

```bash
# no venv, no commitment — needs uv (https://docs.astral.sh/uv/):
uvx schliff score AGENTS.md   # or any SKILL.md / CLAUDE.md / .cursorrules
uvx schliff demo              # no instruction file handy? score a built-in bad one

# or install it:
pip install schliff
schliff score AGENTS.md
```

This is the real, current output of `schliff score AGENTS.md` on this repo's own
[`AGENTS.md`](AGENTS.md) — clone and run it yourself:

```text
schliff v8.11.1

  structure             ██████████  100/100  perfect
  operational_coverage  ██████████  100/100  perfect
  efficiency            ████████░░   78/100  good
  composability         ██████████   95/100  excellent
  clarity               ██████████  100/100  perfect

  Structural Score  ███████████████████░  95.6/100  [S]

  Tokens: 1,065 / 3,000 (ok)
  Format: agents.md (normalized)
```

No model produced that number. Run it on another laptop and you get 95.6 again — **a score you can't reproduce isn't a measurement, it's a vibe.** And we hold *ourselves* to that: this repo's own badge (scored in isolation) once disagreed with its own CLI (scored in-repo) by ~15 points on the *same bytes*, because `structure` was crediting an on-disk `references/` neighbourhood instead of the file's content. We fixed the engine, not the file ([#129](https://github.com/Zandereins/schliff/pull/129)) — now `cp AGENTS.md /tmp && schliff score /tmp/AGENTS.md` returns the same number as CI and the badge. (The `agents.md` headline weights `structure`·`operational_coverage`·`efficiency` at 0.4/0.4/0.2; `composability` and `clarity` are shown for information, not counted.)

*The quick-start and case-study numbers here are reproducible from released `schliff==8.11.1` (`pip install schliff==8.11.1` or `uvx schliff@8.11.1`); the hydra field run below is dated to the version it was measured on.*

---

## A real catch

The SKILL.md for ShieldClaw — a real prompt-injection-defense skill, now archived — is Schliff's reproducible before/after. The fixtures ship in [`docs/case-studies/shieldclaw/`](docs/case-studies/shieldclaw/); every number below is the current engine's output, reproducible with `schliff score`. (For the 28.7 row, score a copy of `SKILL-before.md` outside that directory — in place, the engine auto-discovers the sibling eval suite.)

| | Score | Grade | Dimensions measured |
| --- | --- | --- | --- |
| Before, scored in isolation | 28.7 | F | 4/7 — no eval suite; explicit ceiling warning |
| Before, with its eval suite | 84.5 | B | 7/7 |
| After fixes | 94.6 | A | 7/7 |

Two separate effects, and Schliff refuses to conflate them. Adding the eval suite lifted the **measurement ceiling** (28.7 → 84.5) — that is coverage, not quality. The **quality** delta is 84.5 → 94.6, driven by composability **20 → 86** and efficiency **60 → 83** after adding scope boundaries, an I/O contract, and handoffs — structural gaps a linter can't see, caught as a number that was too low.

A second field run, against an external repo ([hydra](docs/case-studies/hydra/), measured on released `schliff==8.4.0`, 2026-07-03): **71.0 [C] → 76.5 [B]** — edges 82→100, composability 56→81, fix merged upstream ([Zandereins/hydra#34](https://github.com/Zandereins/hydra/pull/34)). Efficiency deliberately stayed at 47: a ~14k-token file against a 1,000-token budget was an **informed decline**, not a blind chase of the number. (External repo — not re-runnable from these fixtures.)

---

## Why deterministic?

Most "AI quality" tools ask another LLM how good your prompt *feels* — a different answer every run. That makes the score **non-reproducible** (re-run it, get a different number), **un-auditable** (the rubric lives in a hidden prompt), and **trivially gameable** (write for the judge, not the user). You can't gate a release on a number that drifts. Schliff computes how good the file *measurably is* — the same answer every run.

Deterministic means reproducible and auditable — it does not automatically mean the number is right. Schliff's claim is narrower and checkable: the rubric is open source, every scorer is readable, the weights are a dict, and the case studies above show the score moving with real fixes. If you disagree with the rubric, you can read it and file an issue — you can't do that with a judge prompt.

Config linters tell you whether the file is *valid* — a list of pass/fail rules. Schliff tells you how *good* it is — one graded 0–100 score you can gate, diff across commits, and rank.

- **Reproducible.** The headline composite is computed from a canonical, versioned weight registry. Calibration is **off by default**, so `verify` and `badge` return the same score on your laptop and in CI.
- **Auditable.** Every dimension is a readable scorer in [`scripts/scoring/`](skills/schliff/scripts/scoring/). The weights are a dict you can open. There is no hidden judge prompt.
- **Anti-gaming, precisely scoped.** A dedicated guard layer ([`guards.py`](skills/schliff/scripts/scoring/guards.py)) detects and floors padding, junk fences, platitude farms, and keyword stuffing — worthless text cannot outrank operational text. A *plausible lie* about your repo is out of reach of any static scorer (see [What the score does not measure](#what-the-score-does-not-measure)).
- **Zero core dependencies.** Core Schliff is stdlib-only and runs on **Python ≥ 3.10**. (Optional `[evolve]` / `[judge]` extras pull in LLM clients for an opt-in smoke-test only — never for scoring.)

Because the number is stable, it does real work: gate pull requests on it [in CI](#use-it-in-ci), or diff and compare it across commits with the [CLI](#cli).

An optional LLM judge exists for exploratory work, but it is never part of the deterministic score. The number you gate on is rule-based, end to end.

**Where AI is and is not involved.** Scoring calls no model: install core Schliff and nothing
leaves your machine. Two opt-in extras do call one — `[evolve]` for the improvement loop and
`[judge]` for an exploratory smoke-test — and when they do, the request runs **from your machine
with your own API key, to the provider you configure**. This project operates no inference
service, holds no key of yours, and receives nothing you score. Without the extra installed the
LLM paths refuse to run rather than degrading silently, and `schliff evolve --budget 0` stays
deterministic even with it installed.

---

## The scoring model

Full methodology: [`docs/SCORING.md`](docs/SCORING.md).

For the `SKILL.md` family, Schliff runs **8 scorers** per file. **7 of them form the headline composite**; `security` (always computed) and `runtime` (opt-in) are reported as **separate signals** so a security warning never silently inflates or deflates your quality grade.

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

> [!NOTE]
> `security` is a side signal for the `SKILL.md` / `CLAUDE.md` / `.cursorrules` / `AGENTS.md` family, but a **core 0.15 headline dimension for the `system_prompt` format**, which uses its own scorer set. Only `runtime` is excluded everywhere.

### The composite: a full-denominator model

Schliff does **not** quietly renormalize across whatever you happened to measure. Unmeasured dimensions **contribute 0 and stay in the denominator** — so coverage gaps lower your ceiling instead of quietly disappearing. Your score ceiling equals your measurement coverage. Measure 4 of the 7 headline dimensions and your maximum possible score is capped accordingly, with an explicit warning:

```text
ℹ Scored 4/7 dimensions — the score can't exceed 42% until the rest
  are measured. Run /schliff:init to add an eval suite and score:
  triggers, quality, edges.
```

> [!IMPORTANT]
> This is deliberate. A partial measurement is an honest partial score, never a flattering one. Unmeasured work is missing points, not invisible. To lift the ceiling, measure more — don't hide the gap.

> [!NOTE]
> **Structural score** = the composite renormalized over the dimensions Schliff can measure deterministically without an eval suite (structure, efficiency, composability, clarity). The full 7-dimension composite additionally folds in triggers, quality, and edges — which require an eval suite, generated with the `/schliff:init` Claude Code slash command. AGENTS.md needs no eval suite: its full 3-dimension headline (structure, operational_coverage, efficiency) is always measurable.

> [!NOTE]
> Calibration is strictly opt-in: ambient auto-calibrated weights apply **only** when `SCHLIFF_CALIBRATED_WEIGHTS` is set and **only** for the interactive `score` command, and Schliff emits a `weight_source=calibrated` warning flagging that such scores are **not** comparable to the canonical scale. Everything that gates a release stays canonical.

### Grade scale

`S` ≥ 95 · `A` ≥ 85 · `B` ≥ 75 · `C` ≥ 65 · `D` ≥ 50 · `E` ≥ 35 · `F` < 35

---

## What the score does not measure

- **Structure, not truth.** The *score* cannot verify that a documented command exists or runs. A syntactically plausible fabrication — invented-but-real-looking commands in well-formed sections — scores in the S range. This is a documented, test-pinned limit ([`test_known_limit_plausible_fabrication_scores_high`](skills/schliff/tests/unit/test_operational_coverage.py), spec §11). The `check-commands` subcommand closes part of this gap outside the score — see [Catching command drift](#catching-command-drift) below.
- **Not agent behavior.** A high score doesn't prove your agent gets better — validity evidence today is case-study-level (the two dated before/afters above), not benchmark-level.
- **Token counts are estimates.** stdlib `len//4`, not a tokenizer.
- **Coverage is on you.** `triggers`/`quality`/`edges` need an eval suite (`/schliff:init`) or the ceiling warning caps the score. AGENTS.md has no such gap.
- **Informed declines are valid.** A low dimension can be a deliberate tradeoff (hydra left efficiency at 47 rather than gut a 14k-token file).

A high Schliff score is necessary, not sufficient.

---

## Catching command drift

The score reads structure. `check-commands` reads your repo: for every setup/build/test
command in an `AGENTS.md` or `CLAUDE.md`, it asks whether the thing actually exists.

Given this `AGENTS.md`:

````markdown
# Example

## Test

```bash
make test
```
````

and a `Makefile` that only defines `lint:`:

```console
$ schliff check-commands AGENTS.md --repo .
DANGLING  AGENTS.md:6  `make test` — make target 'test' is not defined in Makefile

1 dangling, 0 resolved, 0 unknown (of 1 command).
$ echo $?
1
```

Non-zero exit makes it a CI gate. Schliff runs it against its own `AGENTS.md` on every
pull request and every push to `main` ([`test.yml`](.github/workflows/test.yml)), which is
the only adoption claim made here.

**What it resolves, precisely** — the honest scope matters more than the headline:

- **Make targets** and **npm/pnpm/yarn scripts**, plus referenced script paths on disk.
- **Conservative by design:** a command is reported `dangling` only when absence is
  *provable* (the manifest exists and the target is definitively missing). Anything
  unprovable is `unknown`, never `dangling` — one false accusation would burn the tool.
- **Known gap:** `make` targets are recognised only from a fixed vocabulary — `make test`
  is examined, `make test-unit` is not looked at at all. That is a deliberate tradeoff, not
  an oversight: the same narrow matching is what stops English prose like *"make sure the
  tests pass"* from being read as a command. Measured over 259 real instruction files,
  loosening it would catch 2 genuine commands and 14 non-commands
  ([#133](https://github.com/Zandereins/schliff/issues/133)). It stays silent rather than
  guessing — but silence here is a coverage limit, not a clean bill.

It is a drift guard, not a bug finder: across a sweep of real repositories most findings
were in small or unmaintained projects, because well-maintained repos generally keep
their documented commands working.

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

## Use it in CI

Published on the GitHub Marketplace as [AGENTS.md Lint (Schliff)](https://github.com/marketplace/actions/agents-md-lint-schliff).

### GitHub Action

Gate pull requests on instruction-file quality. The action defaults to your
repo-root `AGENTS.md` and posts a scored comment on every PR:

```yaml
# .github/workflows/agents-lint.yml
name: AGENTS.md Lint
on: [pull_request]
permissions:
  contents: read
  pull-requests: write   # the comment step needs this; omit it and set comment-on-pr: false
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: Zandereins/schliff@v1
        with:
          minimum-score: '75'   # optional: fail the PR below this score
```

`comment-on-pr` defaults to `true`, and posting a comment needs
`pull-requests: write` — without the `permissions:` block above you inherit the
repository default, which in many repos is read-only, and the comment step then
fails while the score still gates the PR.

> **Never switch this to `pull_request_target` to get comments on fork PRs.**
> That trigger runs with a write-scoped token in the base repository while
> checking out untrusted code, which is the standard way CI secrets get stolen.
> On a fork PR the token is read-only by design: the score and the exit code
> still work, only the comment is skipped. That degradation is the intended
> behaviour, not a problem to route around.

By default it scores `AGENTS.md` at the repo root; set `skill-path:` to lint a
`SKILL.md`, `CLAUDE.md`, or `.cursorrules` instead. One caveat: the Action
installs the latest released engine from PyPI, so after a release its scores can
lead an older pinned install; pin it with `schliff-version: '8.11.1'` in the
`with:` block if you need byte-stable gates.

### CI gate without the Action

Prefer not to depend on a third-party action? The dependency-light equivalent:

```yaml
      - run: pip install schliff
      - run: schliff verify AGENTS.md --min-score 75
```

`schliff verify` exits non-zero when the score falls short and works for every
supported format — the minimum is scaled by measurement coverage, so `SKILL.md`
files without an eval suite aren't auto-failed. Requires schliff ≥ 8.5.0 for
`AGENTS.md`: older engines scored it under the SKILL profile
([#101](https://github.com/Zandereins/schliff/issues/101)).

### pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Zandereins/schliff
    rev: v8.11.1
    hooks:
      - id: schliff-verify
        args: ['--min-score', '75']
```

The hook fires on `SKILL.md` files (its `files` filter); gate `AGENTS.md` with the Action or `schliff verify AGENTS.md` in CI.

---

## CLI

```text
schliff <command> [path] [options]
```

| Command | What it does |
| --- | --- |
| `score` | Score a file and print the grade bar |
| `verify` | CI gate — exit 0/1 based on a minimum score |
| `check-commands` | CI gate — flag setup/build/test commands that don't exist in the repo (exit 1 if dangling) |
| `doctor` | Scan and grade every installed skill |
| `badge` | Generate a Markdown score badge |
| `diff` | Explain score changes between two git commits |
| `compare` | Compare two files side by side |
| `suggest` | Rank fixes by estimated score impact |
| `report` | Generate a Markdown score report |
| `demo` | Score a built-in bad skill to see Schliff in action |
| `evolve` | Improve an instruction file's score |
| `version` | Print the version |

---

## Optional: closing the loop

Beyond grading, Schliff can apply fixes. The improvement engine **measures first, then fixes** (not the other way around):

1. **Score** the file across all dimensions.
2. **Generate** deterministic patch gradients for the weakest dimensions.
3. **Apply** the safe, rule-based patches automatically — **~32% of suggested fixes** apply deterministically through the apply gate (confidence=high, single-edit), as measured by the canonical script [`measure_patch_ratio.py`](skills/schliff/scripts/measure_patch_ratio.py) — re-run it to check. The rest are handed to an optional LLM.
4. **Re-score** and keep the change only if the score improved — otherwise revert.
5. **Stop** on plateau detection or when the target is reached.

It also carries **cross-session episodic memory** ([`episodic_store.py`](skills/schliff/scripts/episodic_store.py)), so improvement runs learn from prior attempts instead of repeating them. Drive it from Claude Code with `/schliff:auto`, or use `schliff evolve` directly. This is an optional convenience layer — the deterministic score is the product.

```bash
pip install "schliff[evolve,judge]"  # optional LLM extras for this layer only
```

LLM extras power this optional layer only; they are never used for scoring.

| Install | Pulls in | When you need it |
| --- | --- | --- |
| `schliff` | stdlib only | Scoring, verify, badge, CI — everything that gates a release |
| `schliff[judge]` | `anthropic`, `pydantic` | Opt-in exploratory LLM-judge smoke-test (never scoring) |
| `schliff[evolve]` | `litellm` | Opt-in autonomous-improvement extras |

---

## Under the hood

The full methodology — scorer internals, the full-denominator composite, the anti-gaming guards, and the calibration model — lives in [`docs/SCORING.md`](docs/SCORING.md).

```text
scripts/
├── cli.py                  # CLI entrypoint
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

## Links & docs

- **Docs:** [`docs/SCORING.md`](docs/SCORING.md)
- **Try it without installing:** `uvx schliff@latest demo` scores a built-in bad skill; `schliff score <file>` scores your own.
- **Case studies:** [`docs/case-studies/`](docs/case-studies/)

## License

MIT © Franz Paul
