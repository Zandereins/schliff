# Phase-0 Snapshot — Source SKILL.md Corpus (the 10)

Durable, reboot-proof copies of the 10 SKILL.md files open-coded in Phase 0
(`docs/research/2026-04-28-skill-failure-modes.md`). Captured **2026-05-22** so the
human re-coding pass and the committed notes are verifiable against a fixed source
(originals for 01–07 lived in ephemeral `/tmp` and version-pinned plugin caches).

Only the `SKILL.md` (unit of analysis) is snapshotted. The **Bundle** column records
whether referenced scripts/examples/sibling files existed *at snapshot time* — this is
load-bearing: the 10-council pass overturned three draft "missing/dangling" premises
by checking exactly these (01 script present, 04 examples present, 07 siblings present).

| # | Snapshot file | Origin (2026-05-22) | sha256 | Bundle present at source |
|---|---|---|---|---|
| 01 | `01-webapp-testing.SKILL.md` | `/tmp/schliff-corpus-v1/anthropics-skills/skills/webapp-testing/SKILL.md` | `51b7349e…6556a2` | ✅ `scripts/with_server.py`, `examples/console_logging.py` |
| 02 | `02-canvas-design.SKILL.md` | `/tmp/schliff-corpus-v1/anthropics-skills/skills/canvas-design/SKILL.md` | `a1f28807…a6448b` | refs `./canvas-fonts`, `LICENSE.txt` (not snapshotted) |
| 03 | `03-brand-guidelines.SKILL.md` | `/tmp/schliff-corpus-v1/anthropics-skills/skills/brand-guidelines/SKILL.md` | `1120b376…4fa9fe` | ⚠ only `LICENSE.txt` — **no script** (key finding) |
| 04 | `04-internal-comms.SKILL.md` | `/tmp/schliff-corpus-v1/anthropics-skills/skills/internal-comms/SKILL.md` | `067b7587…8d6475` | ✅ all 4 `examples/*.md` present |
| 05 | `05-karpathy-guidelines.SKILL.md` | `/tmp/schliff-corpus-v1/karpathy-skills/skills/karpathy-guidelines/SKILL.md` | `6e22cc54…b2aea7` | MIT-in-file, no root LICENSE (analyze-only) |
| 06 | `06-brainstorming.SKILL.md` | `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/SKILL.md` | `bba47904…e415f90` | refs sibling skill `writing-plans` |
| 07 | `07-systematic-debugging.SKILL.md` | `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/systematic-debugging/SKILL.md` | `4999cb85…badb473` | ✅ `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` present |
| 08 | `08-Nemp-memory.SKILL.md` | `docs/launch/corpus/skill/SukinShetty__Nemp-memory__SKILL.md.md` | `d0dedf4e…f49e35` | n/a (stub, frontmatter only) |
| 09 | `09-algorithms.SKILL.md` | `docs/launch/corpus/skill/luofengmacheng__algorithms__skill.md.md` | `88b11df2…1bc064` | n/a (no frontmatter) |
| 10 | `10-GAP-Design-System.SKILL.md` | `docs/launch/corpus/skill/neatsarab__GAP-Design-System__Skill.md.md` | `713500708…f440a5` | n/a (1986-line dump) |

## Licenses / use

- 01–04 Anthropic example skills — Apache-2.0.
- 05 karpathy-guidelines — MIT declared in-file, no root LICENSE → **analyze-only**; benchmark inclusion gated on license confirmation (B1).
- 06–07 superpowers (obra) — MIT.
- 08–10 community — license unspecified upstream; treated as reference specimens only.

Snapshotted for internal failure-mode research/reproducibility. Verify integrity with
`shasum -a 256 -c` against the hashes above (full digests in git history of this commit).
