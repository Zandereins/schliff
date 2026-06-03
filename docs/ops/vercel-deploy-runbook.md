# Vercel Deploy + Firewall Runbook (playground & leaderboard)

> Status as of 2026-06-03: **DEPLOYED**. Both projects are live and public in
> team `zaneins-projects`:
> - Playground: https://schliff-playground.vercel.app (`POST /api/score`)
> - Leaderboard: https://schliff-leaderboard.vercel.app (`GET /api/query`, `POST /api/submit`)
>
> Firewall rate limits are published and verified (see §3/§4). Production is
> public by default; Deployment Protection only gated preview deployments. The
> sections below are kept as the canonical procedure for re-deploys / new envs.
>
> Original note (pre-deploy): the endpoints have only per-request input caps in
> code; cross-request rate limiting can only live at the Vercel Firewall (no
> `vercel.json` field for it) — **set it BEFORE announcing the URLs**.

There are **two independent apps**, each its own Vercel project:

| App | Root dir | Endpoints |
|-----|----------|-----------|
| Playground | `playground/` | `POST /api/score` |
| Leaderboard | `web/leaderboard/` | `POST /api/submit`, `GET /api/query` |

Both are Python serverless functions (`api/*.py`, `BaseHTTPRequestHandler`) with a
bundled `vercel.json`. Storage for the leaderboard is **ephemeral `/tmp`** (seeded
from `web/leaderboard/data/submissions.json`) — see the "Persistence" note.

---

## 0. Prerequisites

```bash
npm i -g vercel          # or: brew install vercel-cli
vercel login             # interactive — run yourself; use: ! vercel login
vercel teams switch zaneins-projects
```

## 1. Create + deploy the Playground project

> Note: `api/score.py` bootstraps `sys.path` for schliff's scoring package at
> cold start (the engine's submodules import each other via `from scoring.x`,
> which needs the package's `scripts/` dir on the path — the CLI does the same).
> Without it the function 500s on every request against the pip-installed wheel;
> an editable install masks this locally. Do not remove that bootstrap block.

```bash
cd playground
vercel link            # create new project, e.g. name: schliff-playground
vercel deploy          # preview deploy first — sanity check
# open the preview URL, POST a skill to /api/score, confirm a score comes back
vercel deploy --prod   # promote to production
```

## 2. Create + deploy the Leaderboard project

```bash
cd ../web/leaderboard
vercel link            # new project, e.g. name: schliff-leaderboard
vercel deploy
# GET /api/query should return the seed entries; POST /api/submit should accept a valid body
vercel deploy --prod
```

## 3. Firewall rate limits — REQUIRED before going public

Rate limiting is **not** a `vercel.json` field. Set it per project in the
dashboard (Project → **Firewall** → **Custom Rules** / **Rate Limiting**) or via
the `vercel firewall` CLI. Target rules (from the pre-launch audit):

| Project | Path | Limit | Action |
|---------|------|-------|--------|
| schliff-playground | `/api` (and `/api/score`) | 60 req / 60s / IP | deny |
| schliff-leaderboard | `/api/submit` | 10 req / 60s / IP | deny |
| schliff-leaderboard | `/api/query` | 60 req / 60s / IP | deny (optional, read-only) |
| both | — | **Bot Protection: ON** | challenge |

Dashboard path: **Project → Firewall → Configure → Add Rule → Rate Limit**, key
by IP, set the window/limit above, action = Deny (429). Toggle **Bot Protection**
on in the same Firewall view.

CLI (verified 2026-06-03 — the firewall CLI is draft→publish; run from each
project's linked directory so the right project is targeted):

```bash
# from playground/ (linked to schliff-playground)
vercel firewall rules add "rl-api-score" --scope zaneins-projects --yes \
  --action rate_limit --rate-limit-requests 60 --rate-limit-window 60 \
  --rate-limit-keys ip --rate-limit-action deny \
  --condition '{"type":"path","op":"pre","value":"/api/score"}'
vercel firewall publish --scope zaneins-projects --yes

# from web/leaderboard/ (linked to schliff-leaderboard)
vercel firewall rules add "rl-api-submit" --scope zaneins-projects --yes \
  --action rate_limit --rate-limit-requests 10 --rate-limit-window 60 \
  --rate-limit-keys ip --rate-limit-action deny \
  --condition '{"type":"path","op":"pre","value":"/api/submit"}'
vercel firewall publish --scope zaneins-projects --yes
```

> Plan limit (observed): this plan allows **one rate-limit rule per project** —
> a second (e.g. the optional `/api/query` cap) is rejected with "Rate limiting
> is not available for this plan". The two required rules above are within limit.

> Why these numbers: `/api/score` runs the scoring engine per request (CPU-bound,
> input already capped at 256 KB of text in code) → 60/min/IP is generous for a
> human, throttles a script. `/api/submit` writes leaderboard state and is
> unauthenticated/unverified → 10/min/IP limits flooding. `/api/query` is
> read-only; cap it only if you see abuse.

## 4. Verify the gate is live

```bash
for i in $(seq 1 75); do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST https://schliff-playground.vercel.app/api/score \
  -H 'Content-Type: application/json' -d '{"content":"# test\n","filename":"SKILL.md"}'; done | sort | uniq -c
# verified 2026-06-03: 60x 200 then 15x 403
```

> Note: the `deny` action returns **403 Forbidden**, not 429. Both mean blocked;
> if you specifically want 429, use a `rate_limit`/challenge action instead.

## 5. Persistence (leaderboard) — known limitation

`web/leaderboard/api/{submit,query}.py` store to `/tmp/schliff-leaderboard`,
which is **wiped on every cold start** (documented `TODO` in `submit.py`). The
leaderboard is demo-grade until migrated to durable storage (Vercel KV / Postgres
/ Blob). For a real launch, provision Vercel KV and swap `_load_submissions` /
`_save_submissions` before relying on submitted data.

## 6. After launch
- Watch `vercel logs <project> --prod` for 5xx / abuse spikes.
- Custom domains (optional): Project → Domains.
- The leaderboard already tags every entry `verified:false` / `unverified:true`
  and ranks within a single score-model epoch (`?score_model=N`) — no action needed.
