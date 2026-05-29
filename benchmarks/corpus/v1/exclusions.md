# Korpus v1 — Exclusions

What is **not** in Korpus v1 and why. License risk, scope, and dedup
decisions are recorded here for auditability.

## Excluded sources

- **ComposioHQ/awesome-claude-skills** (864 skills) — no LICENSE file at
  pinned SHA. Per ADR-0003 we do not redistribute unlicensed code, even
  for benchmark purposes. Largest excluded source by skill count.
- **agnix (agent-sh/agnix)** — competing skill linter, not a corpus of
  SKILL.md files. Out of scope for input data.
- **VoltAgent/awesome-agent-skills** — pure index of external references.
  Including it would require crawling downstream repos under heterogeneous
  licenses; defer to v8.1+ if a clean subset emerges.
- **hesreallyhim/awesome-claude-code (skills section)** — CC BY-NC-ND 4.0.
  Non-commercial clause blocks marketing/leaderboard usage; ND blocks
  synthetic perturbations.
- **majiayu000/claude-skill-registry** — heavy duplication with Anthropic
  and Rezvani sources; 2.6 GB checkout cost not justified for the
  marginal coverage.
- **sickn33/antigravity-awesome-skills** — possible Tier-B candidate for
  v8.1 once license posture is verified. Deferred from v1.

## Excluded files within included sources

- **anthropics/skills binary files** (`*.docx`, `*.pdf`, `*.pptx`,
  `*.xlsx`) — source-available but not redistributable per upstream
  `THIRD_PARTY_NOTICES.md`. Text-only SKILL.md files retained.
- **alirezarezvani/claude-skills `.gemini/` and `.cursor/` mirrors** —
  derivatives of the same skills published under `.claude/skills/`.
  Deduplicated to the canonical MIT `.claude/` copy.
