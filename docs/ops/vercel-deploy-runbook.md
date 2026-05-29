# Vercel Deploy + Firewall Runbook (playground & leaderboard)

> Status as of 2026-05-29: **no Schliff project exists on Vercel** (team
> `zaneins-projects` has only `project-beat` and `franz-site`). This is a
> from-scratch deploy. **Set the Firewall rate limits BEFORE you announce the
> URLs** — the endpoints have only per-request input caps in code; cross-request
> rate limiting can only live at the Vercel Firewall (no `vercel.json` field for it).

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

CLI alternative (verify exact flags against `vercel firewall --help`; the CLI
surface changes):

```bash
vercel firewall rules add --project schliff-playground \
  --condition 'path eq /api/score' --rate-limit '60/60s/ip' --action deny
vercel firewall rules add --project schliff-leaderboard \
  --condition 'path eq /api/submit' --rate-limit '10/60s/ip' --action deny
```

> Why these numbers: `/api/score` runs the scoring engine per request (CPU-bound,
> input already capped at 256 KB of text in code) → 60/min/IP is generous for a
> human, throttles a script. `/api/submit` writes leaderboard state and is
> unauthenticated/unverified → 10/min/IP limits flooding. `/api/query` is
> read-only; cap it only if you see abuse.

## 4. Verify the gate is live

```bash
# should start returning 429 after the limit within a 60s window
for i in $(seq 1 70); do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST https://<playground-domain>/api/score \
  -H 'Content-Type: application/json' -d '{"content":"# test\n","filename":"SKILL.md"}'; done | sort | uniq -c
# expect a mix of 200 then 429
```

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
