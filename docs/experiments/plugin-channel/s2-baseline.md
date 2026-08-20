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

Every pair below is pre-existing as of 2026-08-20. **The exclusion is scoped to the query that
matched it, not to S2 as a whole** — all 48 rows were returned by Q1 (`"Zandereins/schliff"`), and
none by Q2 (`"schliff@schliff"`), which returned nothing at all.

That distinction decides a real case. `hesreallyhim/awesome-claude-code` `README.md` and
`zhoux77899/claude-code-insights` `plugins/cached-repos.txt` are exactly the kind of file where a
plugin-install line would appear after a submission. If such a file gains `schliff@schliff` after
D0, that is the clearest true positive this experiment can produce — and a blanket exclusion would
have thrown it away as "pre-existing" because the same path already mentioned the repository by
name. A Q1 hit is excluded from Q1 only; the same path can still produce a qualifying Q2 hit, and
that hit is dated by the spec's two-step procedure like any other.

Recorded as repository, path, matched query and capture date, per the spec. No judgement about any
author's intent is recorded here, and none is implied by inclusion: appearing in this table means
the reference existed before the intervention, nothing else.

| # | Repository | Path | Matched | Captured | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | `Adam077K/Beamix` | `docs/08-agents_work/2026-08-09-skill-harvest/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 2 | `SparshKaushik/trackawesomelist` | `2026/07/03/index.html` | Q1 | 2026-08-20 | excluded from Q1 |
| 3 | `SparshKaushik/trackawesomelist` | `2026/27/index.html` | Q1 | 2026-08-20 | excluded from Q1 |
| 4 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/index.html` | Q1 | 2026-08-20 | excluded from Q1 |
| 5 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/readme/index.html` | Q1 | 2026-08-20 | excluded from Q1 |
| 6 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/rss.xml` | Q1 | 2026-08-20 | excluded from Q1 |
| 7 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/week/index.html` | Q1 | 2026-08-20 | excluded from Q1 |
| 8 | `SparshKaushik/trackawesomelist` | `hesreallyhim/awesome-claude-code/week/rss.xml` | Q1 | 2026-08-20 | excluded from Q1 |
| 9 | `StevenSixon/my-daily-news` | `projects/hesreallyhim__awesome-claude-code/README.snapshot.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 10 | `bradAGI/awesome-cli-coding-agents` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 11 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/06/25-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 12 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/03-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 13 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/07-15-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 14 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/20-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 15 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/21-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 16 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/23-06-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 17 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/28-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 18 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/29-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 19 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/29-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 20 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/07/30-23-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 21 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/08/04-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 22 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/08/04-22-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 23 | `devops-actions/github-actions-marketplace-news` | `content/posts/2026/08/10-14-Zandereins-schliff.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 24 | `gabrielmoreira/awesome-ai-rabbit-holes` | `catalog/items/github/zandereins/schliff.yml` | Q1 | 2026-08-20 | excluded from Q1 |
| 25 | `harrysun-code/awesome-with-star` | `awesome/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 26 | `hesreallyhim/awesome-claude-code` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 27 | `hesreallyhim/awesome-claude-code` | `THE_RESOURCES_TABLE_NEW.csv` | Q1 | 2026-08-20 | excluded from Q1 |
| 28 | `ianshank/Agents` | `docs/claude-code-ecosystem-research.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 29 | `icopy-site/awesome` | `docs/awesome/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 30 | `icopy-site/awesome-cn` | `docs/awesome/awesome-claude-code.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 31 | `szabgab/pydigger-data` | `data/pypi/sc/schliff.json` | Q1 | 2026-08-20 | excluded from Q1 |
| 32 | `thedixitjain/the-mega-skill-library` | `reference/hesreallyhim~awesome-claude-code/README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 33 | `trackawesomelist/trackawesomelist` | `content/2026/07/03/README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 34 | `trackawesomelist/trackawesomelist` | `content/2026/27/README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 35 | `trackawesomelist/trackawesomelist` | `content/hesreallyhim/awesome-claude-code/README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 36 | `trackawesomelist/trackawesomelist` | `content/hesreallyhim/awesome-claude-code/readme/README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 37 | `trackawesomelist/trackawesomelist` | `content/hesreallyhim/awesome-claude-code/week/README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 38 | `wan-huiyan/agent-review-panel` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 39 | `wan-huiyan/causal-impact-campaign` | `docs/README-v1.6.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 40 | `wan-huiyan/claude-ecosystem-hygiene` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 41 | `wan-huiyan/ml-training-window-assessor` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 42 | `wan-huiyan/publish-skill` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 43 | `wan-huiyan/publish-skill` | `plugins/publish-skill/SKILL.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 44 | `wan-huiyan/skill-sync` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 45 | `wan-huiyan/skill-sync` | `plugins/skill-sync/SKILL.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 46 | `yenanjing/awesome-ai-for-science` | `README.md` | Q1 | 2026-08-20 | excluded from Q1 |
| 47 | `yenanjing/awesome-ai-for-science` | `data/repos.json` | Q1 | 2026-08-20 | excluded from Q1 |
| 48 | `zhoux77899/claude-code-insights` | `plugins/cached-repos.txt` | Q1 | 2026-08-20 | excluded from Q1 |

## What this file does not do

It does not exclude a *repository* — it excludes a repository/path pair, for one query. A new
file in `wan-huiyan/skill-sync`, for instance, is not covered by the row for that repository's
existing path; neither is that same path acquiring a `schliff@schliff` reference it did not carry
at capture. Both must be dated by the spec's two-step procedure like any other hit.

It also does not decide Gate 2. A hit outside this table still has to clear conditions (2), (3)
and (4) of the qualitative branch — not-a-bot, unsolicited, and attributable to the plugin
channel. This file only removes the dating work for what was already there.
