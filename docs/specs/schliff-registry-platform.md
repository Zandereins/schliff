# Schliff Registry Platform — Design Spec

Status: DRAFT
Author: Franz Paul
Date: 2026-03-28
Version: 0.1

---

## Vision

Schliff becomes the **quality layer for AI instruction files** — the "Codecov for skills."
Every shared skill gets a Schliff score. The badge becomes as ubiquitous as coverage badges.

SkillsMP has 66,500+ skills with **zero quality gate**. Schliff fills that gap.

---

## Existing Infrastructure (IST-Zustand)

Was bereits existiert und worauf wir aufbauen:

| Component | Status | Stack |
|-----------|--------|-------|
| `schliff badge <path>` | Live (v7.1) | shields.io static badge, local scoring |
| `schliff score <path>` | Live (v7.1) | 7 dimensions, composite 0-100, grades S/A/B/C/D/E/F |
| `schliff verify <path>` | Live (v7.1) | CI gate, exit 0/1 |
| `schliff report <path>` | Live (v7.1) | Markdown report mit badge |
| Web Playground | Live | Vercel serverless, POST /api/score |
| Leaderboard API | Live | Vercel, /api/submit + /api/query, /tmp storage |
| Leaderboard Web | Live | Static HTML, vercel.json |
| Grade System | S(>=95) A(>=85) B(>=75) C(>=65) D(>=50) E(>=35) F(<35) |

---

## Phase 1: Badge System (Week 1 — Zero Backend)

### 1.1 Current `schliff badge` Command

Aktueller Output:
```
[![Schliff: 87 [A]](https://img.shields.io/badge/Schliff-87%2F100_%5BA%5D-green)](https://github.com/Zandereins/schliff)
```

Das ist ein **statischer** shields.io Badge. Funktioniert, ist aber nach dem Generieren sofort veraltet.

### 1.2 Badge Formats (zu implementieren)

**Format 1: Static shields.io (existiert)**
- Pro: Zero infra, sofort verwendbar
- Contra: Veraltet nach jedem Commit, manuelles Re-Generieren noetig
- Verwendung: Lokale Nutzung, Einmal-Badge

**Format 2: shields.io Endpoint Badge (Phase 1b)**
- shields.io fetcht JSON von einem Endpoint und rendert den Badge
- URL: `https://img.shields.io/endpoint?url=<encoded-json-url>`
- JSON-Schema das shields.io erwartet:
  ```json
  {
    "schemaVersion": 1,
    "label": "Schliff",
    "message": "87/100 [A]",
    "color": "green"
  }
  ```
- Endpoint-Optionen fuer das JSON:
  - **GitHub Gist** (kostenlos, Zero Backend): `schliff badge --gist` aktualisiert ein Gist via GitHub API
  - **Vercel Edge Function** (bereits deployed): neuer Endpoint `/api/badge/<owner>/<repo>`
  - **Cloudflare Worker + KV** (guenstigste Skalierung): eigener badge service

**Format 3: Custom SVG (Phase 2)**
- Eigenes SVG mit Schliff-Branding, generiert vom Badge-Endpoint
- Erlaubt Schliff-Logo, Gradient-Farben, Dimension-Breakdown
- Beispiel: `https://schliff.dev/badge/owner/repo.svg`

### 1.3 Grade-to-Color Mapping

| Grade | Score | shields.io Color | Hex | Meaning |
|-------|-------|-------------------|-----|---------|
| S | >= 95 | `brightgreen` | #4c1 | Exceptional — production-ready, reviewed |
| A | >= 85 | `green` | #97ca00 | Excellent — high quality, minor gaps |
| B | >= 75 | `yellowgreen` | #a4a61d | Good — solid, room for improvement |
| C | >= 65 | `yellow` | #dfb317 | Acceptable — notable gaps |
| D | >= 50 | `orange` | #fe7d37 | Below average — significant issues |
| E | >= 35 | `red` | #e05d44 | Poor — major problems |
| F | < 35 | `red` | #e05d44 | Failing — fundamental issues |

Hinweis: Die aktuelle CLI-Implementierung nutzt `brightgreen` fuer S, was vom obigen Spec-Design abweicht. Das sollte angeglichen werden — S verdient ein visuell abgesetztes Gold/Brightgreen.

### 1.4 Zero-Backend Badge Flow (GitHub Gist)

```
User runs:  schliff badge --live my-skill.md

1. schliff scores the file locally
2. schliff creates/updates a GitHub Gist with the JSON:
   {
     "schemaVersion": 1,
     "label": "Schliff",
     "message": "87/100 [A]",
     "color": "green"
   }
3. schliff outputs the badge markdown:
   ![Schliff](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/<user>/<gist_id>/raw/schliff.json)

GitHub Action runs nightly or on push:
4. `schliff badge --live --gist-id <id> my-skill.md`
5. Updates the Gist → shields.io serves updated badge automatically
```

**Vorteile:**
- Vollstaendig kostenlos
- Kein eigener Server noetig
- shields.io cached mit `cacheSeconds` (min 300s)
- GitHub Gist ist hochverfuegbar

**Nachteile:**
- Braucht GitHub Token (fuer Gist-Updates)
- Ein Gist pro Badge (oder ein Gist mit mehreren Files)
- Nicht zentral aggregierbar

### 1.5 CI Auto-Update Flow

```yaml
# .github/workflows/schliff.yml
name: Schliff Score
on: [push]
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install schliff
      - run: schliff verify .claude/skills/my-skill/SKILL.md --min-score 75
      - run: schliff badge --live --gist-id ${{ secrets.GIST_ID }} .claude/skills/my-skill/SKILL.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Alternativer Ansatz mit dem `Dynamic Badges` GitHub Action:
```yaml
      - id: score
        run: |
          RESULT=$(schliff score --json .claude/skills/my-skill/SKILL.md)
          echo "score=$(echo $RESULT | jq -r '.composite_score')" >> $GITHUB_OUTPUT
          echo "grade=$(echo $RESULT | jq -r '.grade')" >> $GITHUB_OUTPUT
      - uses: schneegans/dynamic-badges-action@v1.7.0
        with:
          auth: ${{ secrets.GIST_TOKEN }}
          gistID: ${{ secrets.GIST_ID }}
          filename: schliff.json
          label: Schliff
          message: ${{ steps.score.outputs.score }}/100 [${{ steps.score.outputs.grade }}]
          color: green  # dynamisch basierend auf grade
```

### 1.6 Phase 1 Deliverables

| Deliverable | Effort | Dependencies |
|------------|--------|--------------|
| `schliff score --json` output format | 2h | Existierender code |
| `schliff badge --format [static\|endpoint\|gist]` | 4h | GitHub API |
| GitHub Action Workflow Template | 2h | Badge command |
| Docs: "Add a Schliff Badge to Your README" | 2h | Alles oben |

---

## Phase 2: Schliff Score API (Week 2-3 — Minimal Backend)

### 2.1 Architecture

```
README Badge Request:
  img.shields.io/endpoint?url=https://schliff.dev/api/badge/owner/repo

  schliff.dev/api/badge/owner/repo  →  Cloudflare Worker
    1. Check KV cache (key: "owner/repo")
    2. If cached and fresh (< 1h): return shields.io JSON
    3. If stale: return cached + trigger re-score in background
    4. If miss: return "not scored" badge, queue scoring
```

### 2.2 Endpoint Design

**GET `/api/badge/:owner/:repo`**
Returns shields.io-kompatibles JSON:
```json
{
  "schemaVersion": 1,
  "label": "Schliff",
  "message": "87/100 [A]",
  "color": "green",
  "cacheSeconds": 3600
}
```

**GET `/api/badge/:owner/:repo?style=flat-square`**
Pass-through von shields.io Style-Parametern.

**GET `/api/badge/:owner/:repo.svg`**
Direkt-SVG (Custom Rendering, kein shields.io Umweg).

**GET `/api/score/:owner/:repo`**
Vollstaendiges Score-JSON:
```json
{
  "composite": 87.3,
  "grade": "A",
  "dimensions": {
    "structure": 92, "triggers": 85, "quality": 88,
    "edges": 82, "efficiency": 90, "composability": 78, "runtime": null
  },
  "measured_at": "2026-03-28T14:30:00Z",
  "version": "7.1.0",
  "skill_path": ".claude/skills/deploy/SKILL.md"
}
```

**POST `/api/score`**
Schliff-Playground (existiert bereits auf Vercel). Kann erweitert werden um Ergebnisse zu cachen.

**POST `/api/publish`**
Score einreichen + im Cache speichern (authenticated via GitHub Token).

### 2.3 Implementation Options

| Option | Pro | Contra | Cost @ 100k users |
|--------|-----|--------|-------------------|
| **Cloudflare Worker + KV** | Schnellste Latenz, 100k reads/day free, KV global | KV eventual consistency, Worker-Size Limits | $0 (Free Tier reicht bis ~3M req/mo) |
| **Vercel Edge Functions** | Bereits deployed (Playground + Leaderboard), einfache Migration | Vercel Free Tier: 100k invocations/mo, dann teuer | $0-20/mo |
| **Vercel + Upstash Redis** | Serverless Redis, schneller als /tmp | Upstash Free: 10k commands/day | $0-10/mo |
| **GitHub Pages + GitHub Actions** | Zero cost, scores in Repo gespeichert | Keine dynamische Berechnung, nur statisch | $0 |

**Empfehlung: Hybrid-Ansatz**
1. **Phase 2a**: Vercel erweitern (existiert bereits) — neuer `/api/badge/` Endpoint, Upstash Redis fuer Cache statt /tmp
2. **Phase 2b**: Cloudflare Worker als Badge-Proxy vor Vercel (CDN + KV Cache)
3. Migration zu Cloudflare komplett wenn Vercel-Limits erreicht werden

### 2.4 Score Caching Strategy

```
Score Lifecycle:
  1. User runs `schliff score --publish` lokal
  2. CLI POST an /api/publish mit Score-Daten + GitHub Token
  3. API validiert Token (GitHub API: token owner == repo owner?)
  4. Score wird in KV/Redis gespeichert: key="owner/repo/skill-path"
  5. Badge-Endpoint liest aus Cache
  6. TTL: 24h — wird bei jedem `--publish` erneuert
  7. GitHub Action: `schliff score --publish` bei jedem Push → immer aktuell
```

Kein Server-seitiges Scoring noetig — der Score wird **lokal berechnet und verifiziert**:
- Manipulation? Ja, moeglich. Aber: das ist auch bei Codecov so.
- Mitigation: `schliff verify` in CI, oeffentlich einsehbarer Workflow
- Langfristig: Attestation via GitHub Actions OIDC Token

### 2.5 Cost Analysis

| Scale | Requests/mo | CF Worker | CF KV | Vercel | Total |
|-------|-------------|-----------|-------|--------|-------|
| 1k users | ~30k | Free | Free | Free | $0 |
| 10k users | ~300k | Free | Free | $20 (Pro) | $20 |
| 100k users | ~3M | Free | $0.50 | $20 (Pro) | $20.50 |
| 1M users | ~30M | $5 | $5 | N/A (CF only) | $10 |

---

## Phase 3: Schliff Registry (Month 2-3)

### 3.1 Concept

```
schliff.dev/registry
├── Browse: Kategorien, Score-Filter, Formate
├── Skill Detail: Score, Dimensionen, History, README, Install
├── Search: Keyword + Semantic
└── Publish: schliff publish <path>
```

### 3.2 Quality Gate

**Minimum-Anforderungen fuer Veroeffentlichung:**
- Composite Score >= 75 (Grade B)
- Keine Dimension unter 50 (kein D/E/F in Einzeldimensionen)
- Muss `schliff verify` bestehen
- Gueltiges Frontmatter (name, description, triggers)
- Keine bekannten Security-Issues (security dimension >= 70)

**Warum B und nicht A?**
- A (>=85) wuerde zu viele Skills ausschliessen → Adoptions-Huerden
- B (>=75) ist "gut genug" — zeigt aktive Qualitaetsbemühungen
- S/A Skills bekommen "Schliff Certified" Badge (siehe Section 5)

### 3.3 Skill Metadata Schema

```json
{
  "name": "deploy-aws",
  "version": "1.2.0",
  "description": "Automated AWS deployment with rollback and health checks",
  "author": {
    "name": "franzpaul",
    "github": "Zandereins"
  },
  "format": "SKILL.md",
  "category": ["deployment", "aws", "devops"],
  "compatible_with": ["claude-code", "codex-cli"],
  "score": {
    "composite": 91.3,
    "grade": "A",
    "dimensions": { ... },
    "version": "7.1.0",
    "scored_at": "2026-03-28T14:30:00Z"
  },
  "source": {
    "repo": "https://github.com/Zandereins/deploy-aws-skill",
    "path": ".claude/skills/deploy-aws/SKILL.md"
  },
  "published_at": "2026-03-28T15:00:00Z",
  "downloads": 142,
  "checksum": "sha256:abc123..."
}
```

### 3.4 CLI Commands

```bash
# Publish
schliff publish .claude/skills/deploy-aws/SKILL.md
  → Scores locally
  → Validates quality gate
  → Uploads to registry
  → Returns: https://schliff.dev/registry/deploy-aws

# Search
schliff search "aws deployment" --min-score 80 --format SKILL.md
  → deploy-aws         91.3 [A]  "Automated AWS deployment..."
  → lambda-deploy      82.1 [B]  "Serverless deployment..."

# Install
schliff install deploy-aws
  → Downloads SKILL.md to .claude/skills/deploy-aws/SKILL.md
  → Runs schliff verify on downloaded file
  → "Installed deploy-aws v1.2.0 [A] 91.3/100"

# Update
schliff update deploy-aws
  → Checks registry for newer version
  → Downloads + verifies
```

### 3.5 Storage Architecture

**Phase 3a — Minimal (SQLite + Litestream)**
- SQLite-Datenbank auf Fly.io oder Railway (Single Node)
- Litestream fuer kontinuierliche Backups zu S3/R2
- Skill-Dateien in Cloudflare R2 (S3-kompatibel)
- Cost: $0-5/mo (Fly.io Free Tier + R2 Free Tier)

**Phase 3b — Skalierbar (Turso/libSQL)**
- Turso: gehostetes libSQL (SQLite-Fork), edge-replicated
- Free Tier: 9GB storage, 500M rows read/mo
- Skill-Dateien weiterhin in R2
- Cost: $0-29/mo

**Phase 3c — Full (Supabase)**
- PostgreSQL + Edge Functions + Auth + Realtime
- Free Tier: 500MB DB, 1GB storage, 50k MAU
- Vorteil: Auth, Realtime Updates, Dashboard out of the box
- Cost: $0-25/mo

**Empfehlung: Phase 3a (SQLite + Litestream).**
- Einfachste Migration von /tmp-JSON (existierender Leaderboard-Code)
- Kein ORM noetig, SQL direkt
- Backup automatisch
- Upgrade zu Turso spaeter trivial (gleicher SQL-Dialekt)

### 3.6 Registry Database Schema

```sql
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    author_github TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('SKILL.md','.cursorrules','CLAUDE.md','AGENTS.md')),
    source_repo TEXT NOT NULL,
    source_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,          -- sha256 of skill content
    latest_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    downloads INTEGER NOT NULL DEFAULT 0,
    is_certified BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE skill_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    version TEXT NOT NULL,
    composite_score REAL NOT NULL,
    grade TEXT NOT NULL,
    dimensions_json TEXT NOT NULL,       -- JSON blob
    schliff_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    published_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(skill_id, version)
);

CREATE TABLE categories (
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    category TEXT NOT NULL,
    PRIMARY KEY (skill_id, category)
);

CREATE INDEX idx_skills_composite ON skill_versions(composite_score DESC);
CREATE INDEX idx_skills_grade ON skill_versions(grade);
CREATE INDEX idx_categories_cat ON categories(category);
```

---

## Phase 4: Leaderboard (Week 2 — erweitert)

### 4.1 Bestand

Es existiert bereits:
- `web/leaderboard/` mit Vercel deployment
- `api/submit.py` — POST-Endpoint, validiert, speichert in /tmp JSON
- `api/query.py` — GET mit sort, filter, pagination
- `web/leaderboard/index.html` — Static HTML frontend

### 4.2 CLI Leaderboard Command

```bash
schliff leaderboard
  → Fetched from schliff.dev/api/query
  → Displays top 20 in terminal:

  #  Skill                Score  Grade  Format      Author
  1  deploy-aws           97.2   [S]    SKILL.md    @Zandereins
  2  code-review          94.8   [S]    SKILL.md    @alice
  3  testing-harness      91.3   [A]    SKILL.md    @bob
  ...

schliff leaderboard --category deployment --min-score 80
schliff leaderboard --format .cursorrules
```

### 4.3 Score Collection Without Central Server

Fuer Szenarien ohne eigenen Server:

**Option A: GitHub-based (Dezentral)**
- Jeder User hat ein `schliff-scores.json` in seinem Repo
- GitHub Action aktualisiert es bei jedem Push
- Leaderboard aggregiert ueber GitHub API (Search Code API)
- Problem: Rate Limits, langsam

**Option B: GitHub Discussions (Semi-zentral)**
- Scores werden als GitHub Discussion Comments gepostet
- Bot aggregiert periodisch
- Problem: Formatierung, Parsing

**Option C: Vercel + persistent storage (Empfohlen)**
- Migration von /tmp zu Upstash Redis oder Turso
- Existierender submit/query Code bleibt fast gleich
- Cost: $0 (Upstash Free: 10k commands/day = ~300 submissions/day)

**Empfehlung: Option C.** Der Code existiert bereits, nur Storage-Backend austauschen.

### 4.4 Web Leaderboard Erweiterungen

- Filter nach Kategorie (Claude Code, Cursor, MCP, System Prompts)
- Score-Trend Sparklines (wenn historische Daten vorhanden)
- "Submit Your Score" Button → generiert `schliff score --publish` Command
- Social Share: "I scored [A] 91.3 on Schliff — #SchliffScore"

---

## Phase 5: "Schliff Certified" Program

### 5.1 Certification Criteria

Ein Skill ist "Schliff Certified" wenn:

1. **Score:** Composite >= 85 (Grade A oder S)
2. **Dimensions:** Keine Einzeldimension unter 70
3. **Anti-Gaming:** Besteht Anti-Gaming-Checks (existierende `benchmarks/anti-gaming/`)
4. **Consistency:** Score stabil ueber 3+ Scoring-Runs (kein Zufall)
5. **Metadata:** Vollstaendiges Frontmatter, Description > 20 Woerter
6. **Security:** Security-Dimension >= 80

### 5.2 Badge Varianten

**Regular Score Badge:**
```
[![Schliff: 91 [A]](https://img.shields.io/badge/Schliff-91%2F100_%5BA%5D-green)](https://schliff.dev)
```

**Certified Badge:**
```
[![Schliff Certified](https://img.shields.io/badge/Schliff_Certified-%E2%9C%93_91%2F100-brightgreen?logo=data:...)](https://schliff.dev/certified/skill-name)
```

- Certified Badge hat ein Haekchen und "Certified" Label
- Verlinkt auf eine Certified-Detailseite mit Score-Breakdown
- Kann nicht selbst vergeben werden — nur ueber API nach Validierung

### 5.3 Marketplace-Adoption

**SkillsMP Integration:**
- SkillsMP hat eine API (`skillsmp.com/docs/api`)
- Vision: SkillsMP zeigt Schliff-Scores neben jedem Skill
- Implementierung:
  1. SkillsMP fetcht Score von `schliff.dev/api/score/owner/repo`
  2. Oder: Schliff-Badge im Skill-README wird von SkillsMP gerendert
  3. Langfristig: SkillsMP sortiert/filtert nach Schliff-Score

**ClawHub / andere Marktplaetze:**
- Gleicher API-Endpunkt
- Badge-Standard macht Adoption trivial (nur Markdown-Image)

### 5.4 Certification Process

```
1. Author runs: schliff certify .claude/skills/my-skill/SKILL.md
2. CLI scores locally, checks all criteria
3. If pass: CLI submits certification request to API
4. API verifies:
   - GitHub token ownership
   - Re-runs scoring server-side (tamper check)
   - Anti-gaming battery
5. If pass: skill marked as certified in registry
6. CLI outputs certified badge markdown
7. Certification valid for 90 days or until content changes
```

---

## Phase 6: "Score Your Stack" Community Challenge

### 6.1 Konzept

Users lassen `schliff doctor` auf alle ihre Instruction Files laufen und teilen die Ergebnisse.

### 6.2 Mechanik

```bash
# User runs:
schliff doctor --share

Output:
  Scanned 12 skills in ~/.claude/skills/

  Average Score: 78.4 [B]
  Highest: deploy-aws 97.2 [S]
  Lowest: quick-fix 42.1 [D]

  Share your results:
  → https://schliff.dev/stack/abc123 (valid 30 days)
  → Copy tweet: "My Claude Code stack scored [B] 78.4 avg across 12 skills. Can you beat it? #SchliffScore schliff.dev/stack/abc123"
```

### 6.3 Viralitaets-Mechanismen

1. **Competitive:** "Can you beat my score?" — Gamification-Trigger
2. **Visual:** Heatmap/Scorecard als OG-Image auf der Share-URL
3. **Easy:** Ein Command → shareable Link
4. **Hashtag:** `#SchliffScore` (kurz, klar, searchable)
5. **Zeitdruck:** "Score Your Stack Week" — eine Woche lang doppelte Leaderboard-Punkte
6. **Influencer:** 5-10 Claude Code Power-User direkt ansprechen, vorscoren
7. **Before/After:** `schliff doctor && schliff auto --all && schliff doctor` — Delta zeigen

### 6.4 Share-Page (schliff.dev/stack/:id)

- OG Image: Score-Heatmap als PNG (generiert via Vercel OG)
- Skill-Liste mit Scores
- "Score Your Own Stack" CTA → `pip install schliff`
- Twitter/X Share Button mit vorausgefuelltem Tweet

---

## Phase 7: Technical Architecture Summary

### 7.1 Minimal Infrastructure Matrix

| Phase | Was | Infra | Cost |
|-------|-----|-------|------|
| 1 (Week 1) | Badges | shields.io + GitHub Gist | $0 |
| 1b (Week 1) | CI Badge Auto-Update | GitHub Actions | $0 |
| 2a (Week 2) | Badge API | Vercel (existiert) + Upstash Redis | $0 |
| 2b (Week 3) | Score API | Vercel + Upstash | $0 |
| 3a (Month 2) | Registry MVP | Vercel + Turso + R2 | $0-5/mo |
| 3b (Month 3) | Registry Full | Vercel + Turso + R2 + Auth | $5-29/mo |
| 4 (Week 2) | Leaderboard Persist | Upstash Redis (ersetzt /tmp) | $0 |
| 5 (Month 2) | Certification | Existierende Infra + Server-Side Scoring | $0-5/mo |
| 6 (Month 1) | Community Challenge | Vercel OG + Share Pages | $0 |

### 7.2 Phase 1 — Zero Backend

```
┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│  schliff CLI  │────▶│  GitHub Gist   │────▶│  shields.io  │
│  (lokal)      │     │  (JSON)        │     │  (Badge SVG) │
└──────────────┘     └────────────────┘     └──────────────┘
       │                                           │
       │ schliff badge --gist                      │ README embed
       ▼                                           ▼
┌──────────────┐                          ┌──────────────┐
│ GitHub Action │                          │   README.md  │
│ (on push)     │                          │   Badge      │
└──────────────┘                          └──────────────┘
```

### 7.3 Phase 2 — Minimal API

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│  schliff CLI  │────▶│  schliff.dev/api/   │────▶│  Upstash     │
│  --publish    │     │  (Vercel Edge)      │     │  Redis       │
└──────────────┘     └────────────────────┘     └──────────────┘
                            │         │
                     ┌──────┘         └───────┐
                     ▼                        ▼
              ┌──────────────┐     ┌──────────────────┐
              │ /api/badge/  │     │ /api/score/       │
              │ → shields.io │     │ → Full JSON       │
              │   JSON       │     └──────────────────┘
              └──────────────┘
```

### 7.4 Phase 3 — Full Registry

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│  schliff CLI  │────▶│  schliff.dev        │────▶│  Turso       │
│  publish/     │     │  (Vercel)           │     │  (SQLite)    │
│  install/     │     │                     │     └──────────────┘
│  search       │     │  /registry          │            │
└──────────────┘     │  /api/publish       │     ┌──────────────┐
                     │  /api/search        │────▶│  Cloudflare  │
                     │  /api/install       │     │  R2 (files)  │
                     │  /api/badge         │     └──────────────┘
                     │  /leaderboard       │
                     │  /playground        │     ┌──────────────┐
                     │  /stack/:id         │────▶│  Upstash     │
                     └────────────────────┘     │  Redis       │
                                                └──────────────┘
```

### 7.5 Cost at Scale

| Users | Requests/mo | Storage | Compute | CDN | Total/mo |
|-------|-------------|---------|---------|-----|----------|
| 1k | 30k | < 100MB | Vercel Free | CF Free | $0 |
| 10k | 300k | < 1GB | Vercel Pro ($20) | CF Free | $20 |
| 100k | 3M | < 10GB | Vercel Pro + CF Worker | CF Pro ($20) | $45 |
| 1M | 30M | < 100GB | CF Workers ($5) + Turso ($29) | CF Pro | $75 |

---

## Implementierungs-Reihenfolge

### Week 1 (sofort)
1. `schliff score --json` — JSON-Output fuer CI/Automatisierung
2. `schliff badge --format endpoint` — shields.io Endpoint Badge Support
3. `schliff badge --gist` — Auto-Update via GitHub Gist
4. GitHub Action Template: `.github/workflows/schliff.yml`
5. Docs: "Add a Schliff Badge to Your README"

### Week 2
6. `/api/badge/:owner/:repo` Endpoint auf Vercel
7. Leaderboard Storage-Migration: /tmp → Upstash Redis
8. `schliff score --publish` — Score an API senden
9. `schliff leaderboard` CLI-Command (existierender API-Client)

### Week 3-4
10. `schliff doctor --share` — Share-Link generieren
11. Share-Page mit OG-Image (Vercel OG)
12. Community Challenge Launch: "Score Your Stack Week"

### Month 2
13. Registry MVP: publish, search, install
14. Turso-Datenbank + Schema
15. `schliff certify` Command
16. Certified Badge System

### Month 3
17. Registry Web UI (Browse, Detail-Seiten)
18. SkillsMP Integration (Badge in Listings)
19. Custom SVG Badges mit Schliff-Branding

---

## Offene Fragen

1. **Auth-Strategie:** GitHub OAuth fuer publish/certify? Oder simpler: GitHub Token im CLI wie bei `gh`?
2. **Namespace:** `schliff install deploy-aws` — wer "besitzt" den Namen `deploy-aws`? First-come-first-serve? Scoped wie `@user/skill`?
3. **Versionierung:** SemVer fuer Skills? Oder einfach inkrementell?
4. **Anti-Gaming Server-Side:** Wie viel Server-seitiges Re-Scoring ist noetig? Nur fuer Certification, oder fuer alle published Scores?
5. **SkillsMP Kontakt:** Wer betreibt SkillsMP? Gibt es eine Partnerschafts-Moeglichkeit?
6. **Domain:** `schliff.dev` — bereits registriert?

---

## Zusammenfassung

Die Kernidee ist ein **progressiver Ausbau** von Zero-Infra zu Minimal-Infra zu Full-Platform:

- **Phase 1** kostet nichts und liefert sofort sichtbaren Wert (Badges in READMEs)
- **Phase 2** nutzt existierende Vercel-Infrastruktur und fuegt nur Redis hinzu ($0)
- **Phase 3** bringt die eigentliche Registry — aber erst wenn genuegend Nutzer + Scores existieren
- Die gesamte Platform kann bis 10k User fuer $20/mo betrieben werden

Der strategische Hebel: **Badges sind viral.** Jeder Badge in einem README ist Werbung fuer Schliff. Die Badge-Adoptions-Rate entscheidet ueber den Erfolg der gesamten Platform.
