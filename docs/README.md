# Schliff Documentation

Start here. Schliff is a **deterministic linter and scoring engine** for AI
instruction files — the "Ruff for `SKILL.md`", now multi-format. Same input →
same score, with zero core dependencies (stdlib-only, Python ≥ 3.9). For install
and quick start, see the [project README](../README.md).

**Current version: 8.8.0.**

## Understand the tool

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the scoring pipeline fits together: the scorer registry, the composite model, and the script-level file tree.
- **[SCORING.md](SCORING.md)** — dimensions, weights, grades, and methodology.
- **[adr/](adr/)** — Architecture Decision Records (0001–0007): the *why* behind the design (failure-mode-first scoping, calibration protocol, same-family LLM default, spec-versioning, …).

## What it measures

- **Multi-format.** Scores `SKILL.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, and system prompts. The `SKILL.md` family (also `CLAUDE.md` / `.cursorrules` / `AGENTS.md`) shares one scorer registry; system prompts have their own scorer and weight set. Each format carries its own token budget.
- **Headline dimensions** (`SKILL.md` family): structure, triggers, quality, edges, efficiency, composability, clarity. These seven form the headline composite, renormalized to sum to 1.0.
- **Full-denominator composite.** Unmeasured dimensions contribute 0 and *stay in the basis* — the score ceiling equals weight-coverage, so a partially measured skill can't inflate its grade. (Optional weight **calibration** is **off by default** to keep `verify` / `badge` / leaderboard reproducible across machines; opt in via `SCHLIFF_CALIBRATED_WEIGHTS` for the interactive `score` command only.)
- **Security & runtime as separate signals.** For the `SKILL.md` family, the security scorer runs but is reported as a standalone signal (gate threshold 70), and runtime is reported as a signal too — neither is folded into that headline. For the **system-prompt** format, security *is* a core headline dimension.
- **Anti-gaming detection** is built into the engine, and **~32 % of suggested patches** are applied deterministically (rule-based, no LLM; canonical source `measure_patch_ratio.py`) with cross-session episodic memory.
- **Grades:** S ≥ 95, A ≥ 85, B ≥ 75, C ≥ 65, D ≥ 50, E ≥ 35, F < 35.

LLM-judge and evolve features are optional extras (`[judge]`, `[evolve]`); the core engine never requires a network call.

## See it on real files

- **[case-studies/shieldclaw/](case-studies/shieldclaw/)** — before/after of a real skill optimization, with baseline and optimized score artifacts and the eval suite.
- **[launch/state-of-ai-instructions.md](launch/state-of-ai-instructions.md)** — the public report: 120 instruction files scored across 60 repos. **Historical:** measured 2026-04-17 on schliff v7.1.0; the figures do not reproduce on the current engine (see the header note in the file). The corpus itself is not bundled (third-party files, varying licenses); regenerate it locally with the pipeline in [`../skills/schliff/scripts/launch/`](../skills/schliff/scripts/launch/) (`collect_corpus.py` → `score_corpus.py` → `aggregate_stats.py`).

## Internal / working docs (not part of the public guide)

`specs/`, `research/`, `ops/`, and `superpowers/` hold in-progress design specs,
research notes, runbooks, and planning artifacts. They are kept for transparency
and reproducibility but are working documents, not stable public documentation —
read them as such.
