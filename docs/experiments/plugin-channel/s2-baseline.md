# S2 pre-D0 baseline — plugin-channel experiment

Captured **2026-08-20**, before D0. Establishes the permanently-excluded set for the S2 branch of
Gate 2 in `docs/specs/2026-08-11-plugin-channel-experiment.md`.

**Why this file exists.** The spec requires it before the first submission PR is opened:

> Both S2 queries are run once *before* D0 and their full result set — repository, path, and the
> date of capture — is committed to `docs/experiments/plugin-channel/s2-baseline.md`. Every
> repository/path pair in that snapshot is pre-existing by definition and is **permanently
> excluded** from S2, with no dating work required. This must be captured before the first
> submission PR is opened; **if D0 arrives with no committed baseline, the S2 branch is void.**

A control taken after the intervention is not a control. D0 is `*not yet submitted*` as of
capture, so this snapshot is a genuine control.

## Method

```bash
gh api -X GET search/code -f q='"Zandereins/schliff" -user:Zandereins' -f per_page=100
gh api -X GET search/code -f q='"schliff@schliff" -user:Zandereins'  -f per_page=100
```

**Completeness proof.** `search/code` pages at 30 by default and truncates silently — the same
class of error that made a count in `distributors.md` wrong by a factor of five. Both queries ran
with `per_page=100`, and the returned item count was checked against the API's own `total_count`:

| Query | `total_count` | items returned | complete |
| --- | --- | --- | --- |
| `"Zandereins/schliff" -user:Zandereins` | 48 | 48 | yes |
| `"schliff@schliff" -user:Zandereins` | 0 | 0 | yes |

The second query returning zero is itself a recorded result: at capture, no file in any public
repository outside the owner's account contained the plugin install identifier `schliff@schliff`.

## Excluded set — 48 repository/path pairs across 22 repositories

Every pair below is pre-existing as of 2026-08-20 and is **permanently excluded from S2**, with no
dating work required — the blanket wording the spec pre-registered, not a narrower reading of it.

The `Matched` column records which query returned each row (all 48 from Q1, `"Zandereins/schliff"`;
Q2, `"schliff@schliff"`, returned nothing). It is provenance, **not** a limit on the exclusion: a
path listed here is out of S2 entirely, including for the query that did not match it at capture.

*What that costs, stated rather than quietly avoided.* If `hesreallyhim/awesome-claude-code`
`README.md` gains a `schliff@schliff` install line after D0, that would be a genuine signal and
this baseline discards it. An earlier draft of this file scoped exclusions per query to keep such
a hit alive. That draft was wrong: it loosened a pre-registered criterion in the permissive
direction — toward a false GREEN — with the case already in view, which is the move this
experiment's own condition-(2) amendment refuses to make. The spec settled this trade-off in
advance: *"a branch that silently admits pre-intervention evidence is worse than one that turns
away a real signal it cannot date, because only the first kind of error can manufacture a false
GREEN."* The lost signal is the price that sentence already agreed to pay.

Recorded as repository, path, matched query and capture date, per the spec. No judgement about any
author's intent is recorded here, and none is implied by inclusion: appearing in this table means
the reference existed before the intervention, nothing else.

| # | Repository | Path | Matched | Captured | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | `Adam077K/Beamix` | `docs/08-agents_work/2026-08-09-skill-harvest/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from S2 |
| 2 | `SparshKaushik/trackawesomelist` | `2026/07/03/index.html` | Q1 | 2026-08-20 | excluded from S2 |
| 3 | `SparshKaushik/trackawesomelist` | `2026/27/index.html` | Q1 | 2026-08-20 | excluded from S2 |
| 4 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/index.html` | Q1 | 2026-08-20 | excluded from S2 |
| 5 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/readme/index.html` | Q1 | 2026-08-20 | excluded from S2 |
| 6 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/rss.xml` | Q1 | 2026-08-20 | excluded from S2 |
| 7 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/week/index.html` | Q1 | 2026-08-20 | excluded from S2 |
| 8 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/week/rss.xml` | Q1 | 2026-08-20 | excluded from S2 |
| 9 | `StevenSixon/my-daily-news` | `projects/hesreallyhim__awesome-claude-code/README.snapshot.md` | Q1 | 2026-08-20 | excluded from S2 |
| 10 | `bradAGI/awesome-cli-coding-agents` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 11 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/06/25-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 12 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/03-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 13 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/07-15-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 14 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/20-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 15 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/21-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 16 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/23-06-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 17 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/28-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 18 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/29-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 19 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/29-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 20 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/30-23-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 21 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/08/04-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 22 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/08/04-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 23 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/08/10-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from S2 |
| 24 | `gabrielmoreira/awesome-ai-rabbit-holes` | `catalog/items/github/zandereins/schliff.yml` | Q1 | 2026-08-20 | excluded from S2 |
| 25 | `harrysun-code/awesome-with-star` | `awesome/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from S2 |
| 26 | `hesreallyhim/awesome-claude-code` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 27 | `hesreallyhim/awesome-claude-code` | `THE_RESOURCES_TABLE_NEW.csv` | Q1 | 2026-08-20 | excluded from S2 |
| 28 | `ianshank/Agents` | `docs/claude-code-ecosystem-research.md` | Q1 | 2026-08-20 | excluded from S2 |
| 29 | `icopy-site/awesome` | `docs/awesome/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from S2 |
| 30 | `icopy-site/awesome-cn` | `docs/awesome/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from S2 |
| 31 | `szabgab/pydigger-data` | `data/pypi/sc/schliff.json` | Q1 | 2026-08-20 | excluded from S2 |
| 32 | `thedixitjain/the-mega-skill-library` | `reference/hesreallyhim~awesome-claude-code/README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 33 | `trackawesomelist/trackawesomelist` | `content/2026/07/03/README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 34 | `trackawesomelist/trackawesomelist` | `content/2026/27/README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 35 | `trackawesomelist/trackawesomelist` | `content/hesreallyhim/awesome-claude-code/README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 36 | `trackawesomelist/trackawesomelist` | `content/hesreallyhim/awesome-claude-code/readme/README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 37 | `trackawesomelist/trackawesomelist` | `content/hesreallyhim/awesome-claude-code/week/README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 38 | `wan-huiyan/agent-review-panel` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 39 | `wan-huiyan/causal-impact-campaign` | `docs/README-v1.6.md` | Q1 | 2026-08-20 | excluded from S2 |
| 40 | `wan-huiyan/claude-ecosystem-hygiene` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 41 | `wan-huiyan/ml-training-window-assessor` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 42 | `wan-huiyan/publish-skill` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 43 | `wan-huiyan/publish-skill` | `plugins/publish-skill/SKILL.md` | Q1 | 2026-08-20 | excluded from S2 |
| 44 | `wan-huiyan/skill-sync` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 45 | `wan-huiyan/skill-sync` | `plugins/skill-sync/SKILL.md` | Q1 | 2026-08-20 | excluded from S2 |
| 46 | `yenanjing/awesome-ai-for-science` | `README.md` | Q1 | 2026-08-20 | excluded from S2 |
| 47 | `yenanjing/awesome-ai-for-science` | `data/repos.json` | Q1 | 2026-08-20 | excluded from S2 |
| 48 | `zhoux77899/claude-code-insights` | `plugins/cached-repos.txt` | Q1 | 2026-08-20 | excluded from S2 |

## What this file does not do

It does not exclude a *repository* — it excludes a repository/path pair. A new file in
`wan-huiyan/skill-sync`, for instance, is not covered by the row for that repository's existing
path and must be dated by the spec's two-step procedure like any other hit.

It also does not decide Gate 2. A hit outside this table still has to clear conditions (2), (3)
and (4) of the qualitative branch — not-a-bot, unsolicited, and attributable to the plugin
channel. This file only removes the dating work for what was already there.
