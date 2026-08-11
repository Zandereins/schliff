# Qualified distributors — plugin-channel experiment

Measured 2026-08-11. Establishes N for Gate 1 of
`docs/specs/2026-08-11-plugin-channel-experiment.md`.

**Qualification criterion:** at least two distinct external authors (not the repository owner,
not a bot) with PRs merged in the 90-day window **2026-05-13 to 2026-08-11**.

**Method:** `gh api /repos/OWNER/REPO`, `gh pr list --state merged --json author,mergedAt`, and
`gh api /orgs/OWNER/public_members` to screen owner-affiliation. Where a repo publishes a
CONTRIBUTING policy, that policy overrides a raw distinct-username count — see `hashicorp/agent-skills`
below, where several non-owner usernames merged PRs but the repo's own CONTRIBUTING.md states
external contributions are not accepted.

## Findings vs. the pre-measured numbers

The three starting candidates were re-verified and **all three numbers changed** once the 90-day
window was applied (the prior figures counted all-time merges, not windowed ones):

- `trailofbits/skills-curated`: prior note said "4 distinct authors" (all-time). Windowed, it's
  **1** — `dguido` (the repo's own CEO, a public member of the `trailofbits` org) merged 20 of 22
  PRs, all in February 2026, outside the window. Only one PR fell inside the window.
- `obra/superpowers-marketplace`: confirmed **0** merged PRs exist at all (GraphQL
  `pullRequests(states:MERGED)` returns `totalCount: 0`). The prior note's "46 open items" doesn't
  match either — actual count is 25 open + 15 closed-unmerged = 40.
- `MadAppGang/claude-code`: confirmed **0** in-window (last push 2026-03-15, before the window
  opens, and both historical merges predate it too).

## Candidates

| Repo | Stars | Last push | Archived | External authors in window | Qualifies to submit |
|---|---|---|---|---|---|
| `trailofbits/skills-curated` | 480 | 2026-07-14 | No | 1 | No — CONTRIBUTING/README section |
| `obra/superpowers-marketplace` | 1204 | 2026-08-07 | No | 0 | No — none found |
| `MadAppGang/claude-code` | 278 | 2026-03-15 | No | 0 | No — `docs/contributing.md` linked |
| `anthropics/claude-plugins-official` | 33394 | 2026-08-11 | No | 0 | No — automation policy only |
| `jeremylongshore/claude-code-plugins-plus-skills` | 2616 | 2026-08-11 | No | **3** | **Yes** — `.github/CONTRIBUTING.md` |
| `Piebald-AI/claude-code-lsps` | 511 | 2026-07-25 | No | **6** | **Yes** — README contributor section |
| `hashicorp/agent-skills` | 794 | 2026-08-10 | No | 0 (by policy) | No — CONTRIBUTING.md |
| `team-attention/plugins-for-claude-natives` | 816 | 2026-04-20 | No | 0 | No — README section |
| `ananddtyagi/cc-marketplace` | 689 | 2026-01-18 | No | 0 | No — external submit sites |
| `fivetaku/gptaku_plugins` | 999 | 2026-08-08 | No | 0 | No — none found |
| `mhattingpete/claude-skills-marketplace` | 659 | 2026-07-25 | No | 1 | No — CONTRIBUTING.md |
| `crouton-labs/crouton-kit` | 25 | 2026-08-01 | No | 1 | No — none found |
| `hoblin/claude-ruby-marketplace` | 36 | 2026-08-10 | No | 0 | No — `.github/CONTRIBUTING.md` |
| `rohitg00/awesome-claude-code-toolkit` | 2482 | 2026-05-12 | No | 0 | No — activity is 1 day pre-window |

14 candidates covered (exceeds the required 10). Two searches — `hesreallyhim/awesome-claude-code`
(52k★) and `quemsah/awesome-claude-plugins` — were checked and excluded before scoring: neither
ships a `.claude-plugin/marketplace.json`, so they are not something `/plugin marketplace add`
can target; they are link lists, not marketplaces.

## Per-candidate detail

### `trailofbits/skills-curated` — NOT QUALIFIED (1)

22 merged PRs total. 20 by `dguido` (Trail of Bits CEO, public member of the `trailofbits` org —
internal), one by `dmaynor` (2026-02-23, outside the window), one bot (`app/dependabot`, #12). In
window: only `bsamuels453` merged, 2026-07-14 (#39). One distinct external author — one short of
the bar. Submission process: README `### 3. Submit an individual skill` (line 106) plus a
`.github/ISSUE_TEMPLATE`.

### `obra/superpowers-marketplace` — NOT QUALIFIED (0)

0 merged PRs, confirmed via GraphQL `pullRequests(states:MERGED){totalCount}` = 0. 25 open, 15
closed-without-merging. No CONTRIBUTING file, no `.github/` directory found. There is no
documented submission process and no evidence merges happen at all.

### `MadAppGang/claude-code` — NOT QUALIFIED (0)

Only 2 merged PRs ever, both by `erudenko` (2025-12-12, 2026-01-31), both before the window opens.
Last push 2026-03-15 — 4+ months stale relative to today. Submission process: README links
`./docs/contributing.md` ("How to contribute to the marketplace").

### `anthropics/claude-plugins-official` — NOT QUALIFIED (0)

Very active (33394★, pushed same day), but every merge inside the window is either
`app/github-actions` performing automated dependency-SHA bumps (e.g. #5018 "bump(sentry-cli):
... Automated SHA bump ... validated via `claude plugin validate`") or `bryan-anthropic`, an
Anthropic-affiliated account (username pattern, adding plugins directly, e.g. #5113 "Add
mongodb-atlas plugin"). The current open-PR queue (30 open) is dominated by the same bot bump
PRs. No human external merge landed in the window. Submission tooling exists
(`.github/policy/schema.json`, `.github/policy/prompt.md`) but it appears to gate an automated
validation pipeline, not a human external-contribution path that is currently resulting in merges.
This is the most surprising negative result: the highest-star, most active, "official" marketplace
does not currently show any external human merge in 90 days.

### `jeremylongshore/claude-code-plugins-plus-skills` — QUALIFIED (3)

Owner `jeremylongshore` (company: intent-solutions.io) merged most PRs himself, but three
distinct non-owner, non-bot authors merged inside the window: `khendzel` (2026-07-13, #1020),
`metrox-eth` (2026-07-13, #1029), `astrotars` (2026-07-18, #1081, company `@clerk` — unrelated to
the owner). None share the owner's company/org. Documented process:
`.github/CONTRIBUTING.md` ("community-driven project and contributions of all sizes are welcome"),
plus a full PR template, CODEOWNERS, and a published contribution spec.

### `Piebald-AI/claude-code-lsps` — QUALIFIED (6)

Owner is the `Piebald-AI` org (public members: basekevin, bl-ue, georpar, mike1858, signadou —
none of whom appear in the in-window merge list). Six distinct external authors merged in window:
`callmemorgan` (05-24), `jonesmelton` (05-28), `rishitank` (06-01), `whatrwewaitingf0r` (06-01),
`rabbiveesh` (06-17), `kilianpaquier` (three PRs, 07-25). Clearly qualifies. No standalone
CONTRIBUTING.md, but the README documents a "LSP definition workflow (for contributors)" section
(line 68) as the submission process.

### `hashicorp/agent-skills` — NOT QUALIFIED (0, by explicit policy)

This is the one case where the raw numbers mislead. In window, five non-owner usernames merged
PRs (`m0ps` 07-09, `drewmullen` 07-13, `AdamTylerLynch` 07-14, `vpaul97` 07-15, `leefowlercu`
07-29/08-04/08-10, `jweigand` 07-29) and only one (`gautambaghel`) is a public `hashicorp` org
member. By username-only heuristics this would read as 4-5 external authors — comfortably
qualifying. But `CONTRIBUTING.md` states outright: *"Contributions to this repository are
currently limited to internal HashiCorp contributors. General external contributions are not
accepted at this time."* Treating the repo's own stated policy as authoritative over guessed
org-membership, this is 0 external authors and NOT QUALIFIED. This is the clearest instance in
this survey of why a distinct-username count alone is not sufficient evidence — the repo says so
itself.

### `team-attention/plugins-for-claude-natives` — NOT QUALIFIED (0)

5 merges total, all January–February 2026, all before the window opens (last push 2026-04-20, itself
before the window). README `## Contributing`: "Contributions welcome! Please open an issue or PR"
(line 531) — but no contribution has landed since.

### `ananddtyagi/cc-marketplace` — NOT QUALIFIED (0)

12 merges total, last 2026-01-18 — before the window. Notably, this repo does not accept plugin
submissions as direct PRs to itself at all: README `## 💡 Browse & Submit` routes contributors to
`claudecodecommands.directory/submit` and `subagents.cc/submit-agent`, external sites, not this
GitHub repo.

### `fivetaku/gptaku_plugins` — NOT QUALIFIED (0)

0 merged PRs found. No CONTRIBUTING, no submission-process language found in README.

### `mhattingpete/claude-skills-marketplace` — NOT QUALIFIED (1)

18 merges, 17 by the owner `mhattingpete`, one external (`gurdasnijor`, 2026-07-25) — inside the
window but alone. One short of the bar. Has a detailed root `CONTRIBUTING.md`.

### `crouton-labs/crouton-kit` — NOT QUALIFIED (1)

17 merges; owner-adjacent `CaptainCrouton89` did most, `mb6611` merged four PRs across
2026-02-23 → 2026-06-15, of which two (06-14, 06-15) fall in window — but `mb6611` is the only
distinct in-window author. One short of the bar. No submission-process documentation found.

### `hoblin/claude-ruby-marketplace` — NOT QUALIFIED (0)

29 merges; all in-window merges (05-18 through 08-10) are by the owner `hoblin` himself. Two
external merges exist (`K4sku`, `bonk-moltbot`) but both predate the window (April 2026). Has a
clear `.github/CONTRIBUTING.md` with a "Submitting Plugins" checklist — the process is documented,
it simply hasn't produced an outside merge in the last 90 days.

### `rohitg00/awesome-claude-code-toolkit` — NOT QUALIFIED (0)

Striking case: roughly 90 distinct human authors merged PRs historically, but every single one
clusters into two mass-merge windows (2026-04-18 and 2026-05-11/12 — many merged within seconds
of each other, consistent with a batch/automated import rather than independent review). Last
push is 2026-05-12, one day before the window opens. Zero activity of any kind in the 90-day
window. 0 external authors in window.

## Qualified list

**2 of 14 candidates qualify:**

1. `jeremylongshore/claude-code-plugins-plus-skills` — 3 distinct external authors in window
2. `Piebald-AI/claude-code-lsps` — 6 distinct external authors in window

**This is fewer than three.** Per the brief, that is stated plainly and not softened: of 14
marketplace-shaped repositories surveyed — including the three pre-measured ones, the official
Anthropic directory, and a HashiCorp-maintained one — only two currently show real, recent,
external-author merge activity within a 90-day window. Several repos that look active by star
count or commit frequency (`anthropics/claude-plugins-official`, `hashicorp/agent-skills`,
`rohitg00/awesome-claude-code-toolkit`) turn out on inspection to be internally-driven,
policy-restricted, or merely pre-window when the actual gate — a human, non-owner, non-bot author
getting merged in the last 90 days — is applied.

**N for Gate 1 = 2.** The gate as specified (fewer than three qualifying distributors) is not met
by the current candidate pool. Submitting to `jeremylongshore/claude-code-plugins-plus-skills` and
`Piebald-AI/claude-code-lsps` is evidenced; treating any other repo in this table as a channel that
will plausibly merge an outside PR is not currently supported by the data.
