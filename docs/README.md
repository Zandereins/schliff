# Schliff Documentation

Start here. Schliff is a deterministic linter and scoring engine for Claude Code
`SKILL.md` files — the "Ruff for SKILL.md". For install and quick start, see the
[project README](../README.md).

## Understand the tool
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the scoring pipeline fits together.
- **[SCORING.md](SCORING.md)** — the seven dimensions, weights, grades, and methodology.
- **[adr/](adr/)** — Architecture Decision Records (0001–0007): the *why* behind the design.

## See it on real files
- **[case-studies/shieldclaw/](case-studies/shieldclaw/)** — before/after of a real skill optimization (with score artifacts).
- **[launch/state-of-ai-instructions.md](launch/state-of-ai-instructions.md)** — the public report: 120 instruction files scored across 60 repos, with the reproducible corpus under [launch/corpus/](launch/corpus/).

## Internal / working docs (not part of the public guide)
`specs/`, `research/`, and `superpowers/` hold in-progress design specs, research
notes, and planning artifacts. They are kept for transparency and reproducibility
but are working documents, not stable public documentation — read them as such.
