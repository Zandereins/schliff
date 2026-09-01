# Context-cost measurement — frozen corpus and the number that gets published

Status: **corpus frozen 2026-09-01, both decisions settled the same day.** Measurement is scheduled
for 2026-09-04, the case study for 2026-09-14.

- **`backups/` is excluded from discovery.** The frozen corpus is **159 files → 136 installations,
  420,583 tokens**.
- **The headline is `resident`: 7,975 tokens across 106 artifacts.** `invoke` and the on-disk figure
  are named alongside it, never alone.

## Why this exists

The field number is measured against `~/.claude`, which lives in no repository and which plugin
updates rewrite on their own schedule. Measured:

| date | SKILL.md discovered |
|---|---|
| 2026-08-29 | 159 |
| 2026-08-31 | 161 — a plugin update ran at 08:37 that morning |
| 2026-09-01 | 161, then **159** once `backups/` was excluded |

A number published on 2026-09-14 against a corpus that has moved three times cannot be reproduced
by anyone, including its author. `corpus-2026-09-01.jsonl` is the freeze: one line per discovered
file, path relative to `~/.claude`, full sha256 of the raw bytes, size.

```bash
python3 scripts/measurement/freeze_corpus.py verify docs/case-studies/context-cost/corpus-2026-09-01.jsonl
```

Exits non-zero and names every added, removed or changed file. **Run this immediately before the
measurement.** If it reports drift, the choice is to re-freeze and say so, or to measure against the
frozen set — not to publish a number whose corpus is unknown.

The file list comes from `skill_mesh.discover_skills`, which owns the question of which files count.
The hashes do not: they are full sha256 over raw bytes, not that module's `content_hash`, which is
truncated to 16 characters and computed over content schliff has already decoded and BOM-stripped.
That value is an identity for deduplication, and it would tie the freeze to a reader that changed
twice in the week this was written. A freeze must not depend on the tool it freezes.

## What the corpus actually contains

The freeze made this auditable for the first time, and it is not what "159 skills in `~/.claude`"
suggests:

| count | location | what it is |
|---|---|---|
| 111 | `plugins/cache/` | plugin payloads, the install location |
| 46 | `plugins/marketplaces/` | the same plugins, second copy |
| 2 | `backups/` | **schliff's own backups, from 2026-06-11** |
| 2 | `skills/` | hand-installed: `hydra` and `schliff` |

**Two hand-installed skills.** Everything else is plugin material, most of it present twice — which
is what `doctor`'s payload deduplication collapses from 161 files to 138 installations.

### The backups are counted as installations

`doctor ~/.claude` reports **three** rows named `schliff`:

```
9001 tokens  backups/schliff-skill-backups/schliff.bak.20260611071745/SKILL.md
9013 tokens  backups/schliff/skills.bak.20260611075414/SKILL.md
9591 tokens  skills/schliff/SKILL.md
```

The two June backups contribute **18,014 of the 438,597 tokens (4.1%)** and two of the 138
installations. `shared.EXCLUDED_DIRS` covers `node_modules`, `.venv`, `site-packages` and similar,
but not `backups`.

One of them is byte-identical to the live `skills/schliff/SKILL.md` and still does not collapse with
it, correctly: the payload digest also covers `references/*.md` and `eval-suite.json`, which the
backup directory does not carry. So the digest is right and the discovery is wrong — a backup
directory is not an install location.

**Decided 2026-09-01: excluded.** `backups` is in `shared.EXCLUDED_DIRS`, guarded by
`test_a_backup_is_not_an_installed_skill`. The corpus is **136 installations and 420,583 tokens** —
measured by running `run_doctor` with the exclusion, not by subtracting.

This completes a fix the project already made and then bypassed. `install.sh` used to write
`~/.claude/skills/schliff.bak.<ts>`, inside the skill scan path, duplicating the whole `/schliff:*`
namespace; on 2026-06-11 it moved to `~/.claude/backups/` for exactly that reason
(`docs/specs/2026-06-11-agentic-integration.md`). That protected Claude Code's scan path but not a
scan pointed at `~/.claude` itself. `~/.claude/backups/` is a Claude Code convention directory — its
own `.claude.json.backup.*` files live there too — so nothing under it is a loadable skill.

That run also reports **159 files discovered**, which is the number the plan names as the scope.
The match is a coincidence and must not be read as confirmation: the plan's 159 was measured on
2026-08-29, when the corpus held those same two backups and not yet the two files a plugin update
added on 08-31. Two different sets, same size. This is a path exclusion,
the shape this repository has rejected before — but `EXCLUDED_DIRS` already is exactly such a list,
so it is an entry in an existing mechanism rather than a new enumeration.

## Which number is the headline

The plan commits to "context cost, explicitly not the grades". It does not say which of these:

| source | number | the question it answers |
|---|---|---|
| `manifest` resident | **7,975 tokens** across 106 artifacts | what sits in every context before you do anything |
| `manifest` invoke | **364,126 tokens** | what it costs if everything is invoked |
| `doctor ~/.claude` | **438,597 tokens** across 138 installations | everything on disk, payload-deduplicated |

Two orders of magnitude apart, and two different stories: *"your setup costs 8k tokens before you
type"* against *"438k tokens of skill material on disk"*.

**Decided 2026-09-01, before the measurement and not while writing the case study — `resident`.**

Those 7,975 tokens are the only unavoidable ones: 106 artifacts contributing roughly 75 tokens each
(name plus description) to every context window, before anything is invoked. That is "context cost"
in the literal sense the plan commits to.

`invoke` is a ceiling nobody reaches — it assumes every skill is invoked. The on-disk figure is not
a context cost at all; it is the size of the material, and calling it one would be the most
attackable claim in the study.

**All three appear in the same paragraph** of the case study, so none can be quoted in isolation.
The decision is recorded here rather than settled during writing, because deciding afterwards means
deciding by which number reads better — the rationalisation pre-registration exists to prevent.
