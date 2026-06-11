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

> **`/api/query` rate limit (issue #52) — solved by KV, no 2nd firewall rule
> needed.** A *firewall* per-IP cap needs a second rule, which this plan rejects
> (see the plan limit above). Instead, once Upstash is provisioned (see §5), the
> functions enforce a **KV-backed per-IP limiter in code**: 100/60s/IP on
> `/api/query` and 20/60s/IP on `/api/submit` (defense in depth behind the
> firewall's 10/60s). Fail-open: a KV outage never blocks a request. Until Upstash
> is provisioned the endpoint stays uncapped — accepted at current near-zero
> traffic (read-only, public `unverified:true` data, results capped at 200 in code).
> A firewall rule remains available as an alternative on a higher plan:
>
> ```bash
> # Alternative (only if NOT using the KV limiter, and on a plan allowing a 2nd rule):
> vercel firewall rules add "rl-api-query" --scope zaneins-projects --yes \
>   --action rate_limit --rate-limit-requests 100 --rate-limit-window 60 \
>   --rate-limit-keys ip --rate-limit-action deny \
>   --condition '{"type":"path","op":"pre","value":"/api/query"}'
> vercel firewall publish --scope zaneins-projects --yes
> ```

## 4. Verify the gate is live

```bash
for i in $(seq 1 75); do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST https://schliff-playground.vercel.app/api/score \
  -H 'Content-Type: application/json' -d '{"content":"# test\n","filename":"SKILL.md"}'; done | sort | uniq -c
# verified 2026-06-03: 60x 200 then 15x 403
```

> Note: the `deny` action returns **403 Forbidden**, not 429. Both mean blocked;
> if you specifically want 429, use a `rate_limit`/challenge action instead.

## 5. Persistence (leaderboard) — durable storage via Upstash (issue #51)

`web/leaderboard/api/{submit,query}.py` support **two storage backends**, chosen at
runtime by whether the Upstash/Vercel-KV env vars are present (design:
`docs/specs/2026-06-11-leaderboard-kv-storage.md`):

- **Durable (Upstash Redis / Vercel KV, $0)** — when `KV_REST_API_URL` +
  `KV_REST_API_TOKEN` (or `UPSTASH_REDIS_REST_*`) are set, submissions live in a
  Redis hash. Each submit is one atomic `HSET` (dedup + no read-modify-write race,
  durable across cold starts); query does `HGETALL` unioned with the bundled seed
  rows. stdlib-only (`urllib`), no new dependency. **This is the fix for #51.**
- **`/tmp` fallback (demo-grade)** — when the env vars are absent, the endpoints use
  the per-instance `/tmp` store, **wiped on every cold start**. The within-instance
  race is still fixed there (flock + atomic `os.replace`, #51 / tmp-01). This is the
  default until Upstash is provisioned, so deploying the KV code changes nothing
  until you opt in.

**Provision (one-time, Franz's step):**

```bash
# from web/leaderboard/ (linked to schliff-leaderboard)
vercel install upstash      # provisions Upstash Redis + syncs KV_REST_API_* env vars
vercel deploy --prod        # redeploy so the functions pick up the env vars
```

**Verify durability is live (before closing #51/#52):**

```bash
# POST a submission, force a redeploy (new cold start), then confirm it survived:
curl -s -X POST https://schliff-leaderboard.vercel.app/api/submit \
  -H 'Content-Type: application/json' \
  -d '{"skill_name":"kv-smoke","repo_url":"https://github.com/Zandereins/schliff","format":"SKILL.md","composite":88,"grade":"A","version":"8.1.0","dimensions":{"structure":90,"triggers":90,"quality":90,"edges":90,"efficiency":90,"composability":90,"clarity":90}}'
vercel deploy --prod
curl -s 'https://schliff-leaderboard.vercel.app/api/query?limit=200' | grep -c kv-smoke   # expect >=1 after cold start
# /api/query limiter: 100 GETs in <60s from one IP -> the 101st returns 429.
```

Logic is unit-tested (`skills/schliff/tests/unit/test_leaderboard_kv.py`, fake
Upstash) + `test_leaderboard_storage.py` (the /tmp fallback); the live round-trip
above is the only step that needs the real store.

## 6. After launch

- Watch `vercel logs <project> --prod` for 5xx / abuse spikes.
- Custom domains (optional): Project → Domains.
- The leaderboard already tags every entry `verified:false` / `unverified:true`
  and ranks within a single score-model epoch (`?score_model=N`) — no action needed.
