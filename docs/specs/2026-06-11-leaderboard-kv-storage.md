# Leaderboard durable storage + read rate-limit (issues #51, #52)

- **Status:** implemented behind fallback; pending Upstash provisioning + live verification
- **Date:** 2026-06-11
- **Issues:** #51 (durable storage / tmp-01 race / dos-02), #52 (`/api/query` rate-limit)
- **Supersedes (partial):** the `/tmp` demo-grade storage note in `web/leaderboard/api/submit.py`

## Goal

Make the community leaderboard durable across cold starts and abuse-resistant, at
**$0**, without adding a runtime dependency or regressing the current live deploy.

## Context

`web/leaderboard/api/{submit,query}.py` are standalone Vercel Python functions.
Storage is per-instance ephemeral `/tmp` seeded from `data/submissions.json`:

- **#51 tmp-01 (race):** fixed separately (flock + atomic `os.replace`, PR #58) — but
  `/tmp` is still per-instance and **wiped on cold start** (data loss), and a global
  write limit is impossible in-function (stateless).
- **#51 dos-02:** IP-rotation bypasses the single per-IP firewall rule; only bounded
  today because cold start wipes the store.
- **#52 authz-02:** `GET /api/query` has no per-IP limit; the plan allows only one
  firewall rate-limit rule per project (used by `/api/submit`).

`docs/specs/schliff-registry-platform.md` already chose **Upstash Redis (= Vercel KV,
$0)** as the persistence path. One shared store solves all three.

## Requirements

1. Durable submissions store shared across instances/cold starts.
2. Atomic dedup upsert (no read-modify-write race, distributed).
3. Per-IP read rate-limit on `/api/query` and write rate-limit on `/api/submit`,
   independent of the firewall (sidesteps the 1-rule plan limit).
4. **Zero new runtime dependency** (stdlib `urllib` against the Upstash REST API).
5. **Fallback-safe:** if KV env vars are absent, behaviour is byte-identical to the
   current `/tmp` path — so merging this is safe before the store is provisioned.
6. No shared-module import between the two function files (Vercel handler context
   makes sibling imports unreliable — the repo already hand-duplicates
   `_score_model_for`). Duplicate the compact KV helper inline; a unit test asserts
   the two copies stay behaviourally in sync.

## Technical decisions

- **Backend:** Upstash Redis REST API. Config from `KV_REST_API_URL`/`KV_REST_API_TOKEN`
  (Vercel integration) **or** `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN`
  (native). `_kv_config()` returns `None` when unset → `/tmp` fallback.
- **Data model:** a single Redis **hash** `schliff:submissions`, field =
  `sha256(repo_url + "\n" + skill_name)` (the dedup identity, NFKC-normalized
  upstream), value = entry JSON. Submit = one atomic `HSET` (returns 1=new, 0=update)
  → dedup and atomicity for free, no lock, no read-modify-write. Query = `HGETALL`.
- **Seeding:** no seed-write. `query` **unions** KV entries with bundled
  `data/submissions.json` rows whose dedup identity is not already in KV (KV wins on
  conflict). Seed rows always show; real submissions live in KV. Avoids a seed-race.
- **Rate-limit:** fixed-window per key via `INCR` + `EXPIRE` (`EXPIRE` only on the
  first increment). `/api/query`: 100/60s/IP. `/api/submit`: 20/60s/IP (defense in
  depth behind the firewall's 10/60s). Key from `x-forwarded-for` (first hop) →
  `x-real-ip` → `"unknown"`. **Fail-open:** any KV error during the limiter check is
  swallowed (never 500/429 a request because the limiter is unreachable).
- **Timeouts:** 5s on every REST call; storage errors in the read/write path surface
  as the existing generic 500 (no fallback-to-/tmp mid-request, to avoid split-brain).

## Verification

- **Unit (now):** fake in-memory Upstash REST (HSET/HGETALL/INCR/EXPIRE) injected at
  the `_kv_command` boundary — atomic upsert + updated flag, query union-with-seed,
  rate-limit allow→block, fail-open on error, and fallback-when-unconfigured. Plus the
  existing `/tmp` concurrency tests (unchanged) and a cross-file sync test.
- **Wire format:** verified against Upstash REST docs (pipeline + single-command
  `{"result"|"error"}` shape) and Vercel docs (`vercel install upstash` env sync).
- **Live (gated, before closing issues):** after `vercel install upstash`, redeploy
  and confirm a POST→GET round-trip survives a forced redeploy/cold start, and that
  the `/api/query` limiter returns 429 past 100/60s.

## Provisioning (Franz's step)

```bash
# from web/leaderboard/ (linked to schliff-leaderboard)
vercel install upstash            # provisions Upstash Redis + syncs KV_REST_API_* env
vercel deploy --prod              # redeploy so the functions pick up the env vars
```

Until that runs, the deployed functions see no KV config and keep using `/tmp`
(demo-grade) with the race fix — no behaviour change, no risk.

## Open / deferred

- Migrating the bundled seed into KV (vs. union-at-read) — union is simpler and
  chosen; revisit only if seed grows large.
- Per-IP vs. global write limit for dos-02 — per-IP chosen (matches firewall
  semantics); a global cap can be added as a second key if coordinated abuse appears.
