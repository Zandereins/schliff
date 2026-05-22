# Korpus v1 — Schliff v8.0 Benchmark Corpus

## Purpose

Korpus v1 is the closed-snapshot benchmark used to measure Schliff's
deterministic skill-linting and scoring engine during the v8.0 14-day
sprint. It pins ~191 SKILL.md files across four sources so that score
deltas between commits reflect engine changes, not corpus drift.

This corpus is the single source of truth for v8.0 eval runs, leaderboard
publication, and reproducibility checks. Every benchmark number cited in
v8.0 release notes must be reproducible against this manifest.

## Schema overview

- `manifest.schema.json` — JSON Schema (draft 2020-12) describing one row
  per included or excluded source / skill.
- `manifest.jsonl` — JSONL with one row per source on Day 0; expands to
  one row per skill on Day 1 after enumeration.
- `exclusions.md` — Human-readable rationale for excluded sources.

Validate any row against the schema before committing changes.

## How to consume

```python
import json, jsonschema
schema = json.load(open("manifest.schema.json"))
for line in open("manifest.jsonl"):
    row = json.loads(line)
    jsonschema.validate(row, schema)
```

Downstream tooling (`schliff bench`, eval runner) consumes
`manifest.jsonl` as the canonical list.

## License handling per source

| Source | License | Handling |
|---|---|---|
| anthropics/skills | NOASSERTION (mixed) | Include text-only files; binary files (docx/pdf/pptx/xlsx) excluded per source `THIRD_PARTY_NOTICES.md` |
| alirezarezvani/claude-skills | MIT | Include `.claude/skills/` only; dedup `.gemini/` and `.cursor/` mirrors |
| Zandereins/schliff (dogfood) | MIT | Internal, redistribute freely |
| synthetic-variations | n/a | Generated artifacts, no upstream license |

Excluded sources with license risk are catalogued in `exclusions.md`.

## Reproducibility

All upstream sources are pinned by commit SHA. The corpus is **frozen**
for the duration of the v8.0 release. Re-running the eval against this
manifest at any commit must yield identical inputs (modulo synthetic
seed, which is recorded alongside generated files).

## Update cadence

Korpus v1 is **frozen for v8.0**. v8.1 and later will fork a new `v2/`
directory rather than mutate this manifest. Hotfixes that require corpus
changes (e.g. takedown of an upstream repo) will be documented here as
ADR addenda but will not alter pinned SHAs.

## Known discrepancies (resolve in P2/B1 — logged Day 1)

The corpus contract for `alirezarezvani/claude-skills` was written against
an assumed layout that does not match the pinned snapshot `f567c61d`:

- **No `.claude/skills/` directory exists** at this SHA. The `.claude/`
  dir contains only `commands/`. Canonical skills live in top-level
  category dirs (`engineering/`, `marketing-skill/`, `c-level-advisor/`,
  `ra-qm-team/`, `product-team/`, `project-management/`, `business-growth/`,
  `finance/`, `engineering-team/`). Mirror/plugin copies live under
  `.gemini/`, `.codex/`, `.cursor`, `.codex-plugin/`, `.claude-plugin/`.
- **Skill count is ~239 non-mirror `SKILL.md`** (incl. nested sub-skills
  like `playwright-pro/skills/*`), not the 108 assumed in spec §9 and the
  "~191 total" figure in this README's Purpose section.

**B1 action items:** (1) correct the path filter in this README's
"License handling" table (`.claude/skills/` → top-level category dirs,
exclude `.gemini`/`.codex`/`.cursor`/`*-plugin` mirrors); (2) re-enumerate
and update `manifest.jsonl`; (3) reconcile spec §9 corpus counts. Day-1
Phase-0 reading proceeds unblocked against the top-level category dirs.
