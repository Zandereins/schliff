# Context-cost measurement — frozen corpus and the number that gets published

Status: **corpus frozen 2026-09-01, both decisions settled the same day; re-frozen 2026-09-03
after the corpus drifted** (see [The corpus drifted before the measurement](#the-corpus-drifted-before-the-measurement)).
Measurement is scheduled for 2026-09-04, the case study for 2026-09-14.

- **`backups/` is excluded from discovery.** The frozen corpus is **212 files → 150 installations,
  461,824 tokens**.
- **The headline is `resident`: 8,212 tokens across 109 artifacts.** `invoke` and the on-disk figure
  are named alongside it, never alone. Both figures on the first freeze are in the drift section.

## Why this exists

The field number is measured against `~/.claude`, which lives in no repository and which plugin
updates rewrite on their own schedule. Measured:

| date | SKILL.md discovered |
|---|---|
| 2026-08-29 | 159 |
| 2026-08-31 | 161 — a plugin update ran at 08:37 that morning |
| 2026-09-01 | 161, then **159** once `backups/` was excluded |
| 2026-09-03 | **212** — the user-scoped `vercel` install moved from 0.45.1 to 0.48.0; a project-scoped 0.45.1 install remains |

Two of those rows are plugin updates nobody in this repository triggered (08-31 and 09-03); a number
published on 2026-09-14 against a corpus that moves on its own schedule cannot be reproduced by
anyone, including its author. `corpus-2026-09-03.jsonl` is the freeze: one line per file the
measurement reads, path relative to `~/.claude`, full sha256 of the raw bytes, size.
`corpus-2026-09-01.jsonl` is the first freeze, superseded on 2026-09-03 and kept so the drift
between the two is auditable. Manifests are named by the day they were frozen, not the day they are
measured against.

**Every file any published number reads**, which is more than the SKILL.md and different per number:

| number | computed from |
|---|---|
| `resident` (the headline) | the `description:` frontmatter of each loaded artifact — SKILL.md **and** `commands/**/*.md`, gated by `settings.json` → `enabledPlugins` |
| `invoke` | the bodies of those same artifacts |
| on-disk | SKILL.md + `references/*.md` |
| installation count | the payload digest: SKILL.md + `references/*.md` + `eval-suite.json` |

Neither `references/*.md` nor `eval-suite.json` contributes a single token to `resident`; the suite
contributes none to any token figure at all and feeds only the deduplication that produces the
installation count. Two earlier versions of this freeze got that wrong in opposite directions —
first it covered SKILL.md alone (measured: rewriting one reference moved a skill from 26 to 3,925
tokens with `verify` reporting `0 drifted`), then it covered what `doctor` reads and left the
headline's own inputs out (measured: 21 of 106 artifacts and 830 of 7,975 resident tokens unfrozen).

The manifest holds **580 files**: 212 SKILL.md, 342 references, 4 eval suites, 21 commands, and
`settings.json`. Every artifact `manifest` reports is in it. (The first freeze held 431: 159
SKILL.md, 246 references, 4 eval suites, 21 commands, `settings.json`.)

```bash
python3 scripts/measurement/run_measurement.py docs/case-studies/context-cost/corpus-2026-09-03.jsonl
```

That is the whole measurement: it verifies the freeze, takes the three figures from the tools that
own them, and writes `measurement-<date>.json` beside the manifest it was taken against. **On drift
it names every changed file, writes nothing, and exits 1** — re-freezing is a decision, not
something a script should make quietly. `freeze_corpus.py verify` runs the same check on its own,
without taking a measurement. The choice after a refusal is made deliberately and outside the command: re-freeze and say so in the
case study, or restore the corpus to the frozen state and re-run. What it will not do is produce a
number whose corpus is unknown. Add `--rehearsal` to try the run without writing a file that looks
like the pre-registered one.

The file list comes from `skill_mesh.discover_skills`, which owns the question of which files count.
The hashes do not: they are full sha256 over raw bytes, not that module's `content_hash`, which is
truncated to 16 characters and computed over content schliff has already decoded and BOM-stripped.
That value is an identity for deduplication, and it would tie the freeze to a reader that changed
twice in the week this was written. A freeze must not depend on the tool it freezes.

## What the corpus actually contains

The freeze made this auditable for the first time, and it is not what "159 skills in `~/.claude`"
suggests. As discovered on 2026-09-01, **before** `backups/` was excluded:

| count | location | what it is | in the frozen corpus |
|---|---|---|---|
| 111 | `plugins/cache/` | plugin payloads, the install location | yes |
| 46 | `plugins/marketplaces/` | the same plugins, second copy | yes |
| 2 | `backups/` | **schliff's own backups, from 2026-06-11** | **no — excluded** |
| 2 | `skills/` | hand-installed: `hydra` and `schliff` | yes |

The first manifest therefore held those **159 SKILL.md** and no `backups/` rows; the current one
holds 212, for the reason given in the drift section. The full line count and composition are
stated once, in the section above — repeating it here is how this sentence came to claim 409 after
the manifest had grown to 431.

**Two hand-installed skills.** Everything else is plugin material, most of it present twice — which
is what `doctor`'s payload deduplication collapsed to 136 installations on the first freeze and
150 on the second.

### The backups are counted as installations

**As measured on 2026-09-01, before the fix in this change**, `doctor ~/.claude` reported **three**
rows named `schliff`:

```
9001 tokens  backups/schliff-skill-backups/schliff.bak.20260611071745/SKILL.md
9013 tokens  backups/schliff/skills.bak.20260611075414/SKILL.md
9591 tokens  skills/schliff/SKILL.md
```

The two June backups contributed **18,014 of the then-438,597 tokens (4.1%)** and two of the then-138
installations. `shared.EXCLUDED_DIRS` covered `node_modules`, `.venv`, `site-packages` and similar,
but not `backups`. It does now, and the scan reports one row named `schliff`.

One of them is byte-identical to the live `skills/schliff/SKILL.md` and still did not collapse with
it, correctly: the payload digest also covers `references/*.md` and `eval-suite.json`, which the
backup directory does not carry. So the digest was right and the discovery was wrong — a backup
directory is not an install location.

**Decided 2026-09-01: excluded.** `backups` is in `shared.EXCLUDED_DIRS`, guarded by
`test_a_backup_is_not_an_installed_skill`. On the first freeze the corpus was **136 installations and
420,583 tokens** — measured by running `run_doctor` with the exclusion, not by subtracting.

This completes a fix the project already made and then bypassed. `install.sh` used to write
`~/.claude/skills/schliff.bak.<ts>`, inside the skill scan path, duplicating the whole `/schliff:*`
namespace; on 2026-06-11 it moved to `~/.claude/backups/` for exactly that reason
(`docs/specs/2026-06-11-agentic-integration.md`). That protected Claude Code's scan path but not a
scan pointed at `~/.claude` itself. `~/.claude/backups/` is a Claude Code convention directory — its
own `.claude.json.backup.*` files live there too — so nothing under it is a loadable skill.

That run also reported **159 files discovered**, which is the number the plan names as the scope
(212 on the second freeze, so the plan's scope figure is dated too).
The match is a coincidence and must not be read as confirmation: the plan's 159 was measured on
2026-08-29, when the corpus held those same two backups and not yet the two files a plugin update
added on 08-31. Two different sets, same size. This is a path exclusion,
the shape this repository has rejected before — but `EXCLUDED_DIRS` already is exactly such a list,
so it is an entry in an existing mechanism rather than a new enumeration.

## Which number is the headline

The plan commits to "context cost, explicitly not the grades". It does not say which of these:

| source | number (first freeze, 2026-09-01) | the question it answers |
|---|---|---|
| `manifest` resident | **7,975 tokens** across 106 artifacts | what sits in every context before you do anything |
| `manifest` invoke | **364,126 tokens** | what it costs if everything is invoked |
| `doctor ~/.claude` | **420,583 tokens** across 136 installations | everything on disk, payload-deduplicated |

Two orders of magnitude apart, and two different stories: *"your setup costs 8k tokens before you
type"* against *"421k tokens of skill material on disk"*. The re-freeze moved every figure (the
values are in the drift section below) and none of the gaps between them.

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

## The corpus drifted before the measurement

On 2026-09-03, one day before the pre-registered run, `freeze_corpus.py verify` against the
2026-09-01 manifest reported:

```
431 frozen, 580 present, 194 drifted
```

By label, counted by hand from the 194 lines `verify` prints (it prints one line per file and no
per-label totals): 153 added, 4 removed, 3 changed, 32 no longer resolved, 2 newly resolved. The
4 removed are `vercel/0.45.1/commands/*.md`, all still on disk: commands are frozen only for the
resolved version, because no published number reads the commands of an unresolved one, so a version
flip shows as removed/added for commands and as unresolved/resolved for SKILL.md.

The cause is a plugin update: the user-scoped `vercel` install moved from 0.45.1 to 0.48.0, and
`frontend-design` and `skill-creator` switched to a new marketplace revision. `settings.json` and the `claude-security`
and `frontend-design` marketplace copies changed as well. The version detection built for exactly
this case fired on its first real occasion, and `run_measurement.py` refused and wrote nothing.

**Decided 2026-09-03: re-freeze and say so, rather than restore the corpus to the frozen state.**
The corpus is a living system that plugin updates rewrite on their own schedule; a restore would
have meant editing Claude Code's own plugin pointers to make a number reproducible, which is the
wrong direction. The first manifest stays in the repository so the drift is auditable.

Effect on all three figures, measured with `--rehearsal` against the new manifest on 2026-09-03
(the record is `rehearsal-2026-09-03.json`, committed beside the manifests):

| figure | 2026-09-01 freeze | 2026-09-03 freeze |
|---|---|---|
| `resident` (the headline) | 7,975 tokens across 106 artifacts | **8,212 tokens across 109 artifacts** |
| `invoke` | 364,126 tokens | 372,812 tokens |
| on disk | 420,583 tokens across 136 installations | 461,824 tokens across 150 installations |
| SKILL.md discovered | 159 | 212 |

The on-disk figure grew more than the headline, and not because of a leftover: 0.45.1 is not a
stale cache but a second live install. `installed_plugins.json` lists `vercel` twice — 0.45.1
project-scoped for another repository, 0.48.0 user-scoped — so both versions are installed material
and `doctor` counts one installation per payload across them. 38 of the 48 0.45.1 rows carry their
byte-identical 0.48.0 twin in `also_installed_at` and were already counted on 2026-09-01; the growth
is 14 new payload groups: the 13 under 0.48.0 that have no twin — three new skills and ten whose
payload changed — at 39,273 tokens, and a second `frontend-design` payload at 1,971, because the new
marketplace revision rewrote its SKILL.md while the older cache revisions keep the old one; the
`claude-security` copy was replaced in place at −3. Together, 41,241. Deleting the 0.45.1 directory would break the other project's
install and would not return the figure to 420,583: the 0.48.0 rows would be counted instead.

In the manifest all 48 0.45.1 SKILL.md rows lack a `resolved` key, as do 76 others (orphaned
revisions, `upstream/` nests, marketplace copies) — non-resolution is encoded by absence, the key is
only ever written as `true`. They contribute nothing to `resident`,
which is gated by what `settings.json` enables. The headline moved by three artifacts and a net 237
tokens: 0.48.0 adds three skills and rewrites the `description:` of four carried-over ones, so the
237 is not the sum of the three new descriptions.

**Known defect, found in review on 2026-09-03 and not yet fixed:** the "2 newly resolved" rows are
`frontend-design/ed404106fcd8` and `skill-creator/ed404106fcd8`, and `installed_plugins.json` does
not install them — it installs `0120fb83da5d`. `manifest.py` resolves a plugin's version directory
by newest mtime, and Claude Code writes `.orphaned_at` into the old directory a few milliseconds
after creating the new one, so the orphan wins on every update. The two revisions carry an identical
`description:`, so `resident` is unaffected today; `invoke` is understated by roughly 278 tokens.
The fix belongs in the reader, not in this freeze, and is a decision for the owner before or after
the run.

The headline decision above was taken on the 2026-09-01 values and is not reopened by the
re-freeze: the ranking of the three figures, and the two orders of magnitude between the first and
the last, are unchanged.
