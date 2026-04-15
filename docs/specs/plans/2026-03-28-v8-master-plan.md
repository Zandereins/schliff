# Schliff v8.0 — Master Implementation Plan

> **Execution model:** Multiple parallel Claude Code sessions, each in its own git worktree. Within each session, 6+ subagents handle parallelizable subtasks. This matches the proven v7.0/v7.1 workflow (3 worktrees, 22 commits, 2200 LOC in one day).

**Goal:** Transform Schliff from a SKILL.md quality scorer into the universal AI instruction quality standard with LLM-powered evolution, multi-format scoring, and ecosystem integration.

**Architecture:** Worktree-per-phase, Claude-session-per-worktree, subagents-within-session. Each phase produces a merge-ready branch. Phases merge to `main` sequentially via PR.

**Tech Stack:** Python 3.9+ stdlib (core), LiteLLM (evolve), FastMCP (mcp-server), GitHub Actions (CI), shields.io (badges)

**Spec:** `docs/specs/2026-03-28-v8-design.md`
**Prompts:** `docs/specs/plans/v8-session-prompts.md` — Copy-paste-ready Prompts fuer jede Session und jeden Subagent

---

## Multi-Session Worktree Strategy

### Why Multiple Sessions > Single Orchestrator

| Aspect | Single Session + Subagents | Multiple Sessions in Worktrees |
|--------|---------------------------|-------------------------------|
| Context per phase | Shared, diluted | Full 1M context per phase |
| Parallelism | Sequential dispatch | True simultaneous execution |
| Interactivity | Subagents run autonomously | Franz can steer each session |
| Recovery | One crash = all lost | One crash = one phase affected |
| Proven | New approach | v7.0: 22 commits in 1 day, v7.1: 36 files changed |

### Execution Waves

Phases run in **waves** — each wave is a set of parallel terminals. A wave completes when all its sessions merge to main.

```
WAVE 1 (Week 1-3): 2 terminals
  Terminal A: Phase 0 — Launch Prep (main, no worktree)
  Terminal B: Phase 1a — Scorer Registry (worktree)

WAVE 2 (Week 4-5): 3 terminals (after 1a merges)
  Terminal A: Phase 1b — System Prompt Scoring (worktree)
  Terminal B: Phase 1c — MCP Tool Scoring (worktree)
  Terminal C: Phase 2 — Evolution Engine (worktree)

WAVE 3 (Week 6-8): Phase 2 continues
  Terminal A: Phase 2 — Evolution Engine (continues from Wave 2)

WAVE 4 (Week 9): 3 terminals (after 2 merges)
  Terminal A: Phase 3a — GitHub Action (separate repo)
  Terminal B: Phase 3b — MCP Server (worktree)
  Terminal C: Phase 3c — Registry & Badges (worktree)

WAVE 5 (Week 10): Launch
```

### Terminal Setup Commands

**Wave 1 — starte 2 Terminals:**

```bash
# Terminal A: Launch Prep (direkt auf main, kein Worktree)
cd /Users/franzpaul/schliff
claude

# Terminal B: Scorer Registry (Worktree)
cd /Users/franzpaul/schliff
git worktree add ../schliff-phase-1a -b schliff-v8/phase-1a-scorer-registry
cd ../schliff-phase-1a
claude
```

**Wave 2 — nach Phase 1a merge, starte 3 Terminals:**

```bash
# Zuerst: Phase 1a mergen
cd /Users/franzpaul/schliff
gh pr create --base main --head schliff-v8/phase-1a-scorer-registry \
  --title "refactor: scorer registry pattern for multi-format support"
# Nach Review + Merge:
git worktree remove ../schliff-phase-1a
git pull origin main

# Terminal A: System Prompt Scoring
git worktree add ../schliff-phase-1b -b schliff-v8/phase-1b-system-prompt-scoring
cd ../schliff-phase-1b
claude

# Terminal B: MCP Tool Scoring
git worktree add ../schliff-phase-1c -b schliff-v8/phase-1c-mcp-tool-scoring
cd ../schliff-phase-1c
claude

# Terminal C: Evolution Engine
git worktree add ../schliff-phase-2 -b schliff-v8/phase-2-evolution-engine
cd ../schliff-phase-2
claude
```

**Wave 4 — nach Phase 2 merge, starte 3 Terminals:**

```bash
# Terminal A: GitHub Action (neues Repo, kein Worktree)
mkdir ../schliff-action && cd ../schliff-action
git init && gh repo create Zandereins/schliff-action --public --source=.
claude

# Terminal B: MCP Server
cd /Users/franzpaul/schliff
git worktree add ../schliff-phase-3b -b schliff-v8/phase-3b-mcp-server
cd ../schliff-phase-3b
claude

# Terminal C: Registry & Badges
git worktree add ../schliff-phase-3c -b schliff-v8/phase-3c-registry-badges
cd ../schliff-phase-3c
claude
```

### Session Context Prompt (Copy-Paste fuer jede Session)

Jede neue Claude-Session bekommt diesen Kontext:

```
Lies zuerst:
1. docs/specs/2026-03-28-v8-design.md (Haupt-Spec, Section {N})
2. docs/specs/plans/2026-03-28-v8-master-plan.md (dieser Plan, Phase {X})
3. {phase-spezifische Spec falls vorhanden}

Du arbeitest in Worktree: {pfad}
Branch: {branch}
Phase: {name}

Verwende 6 parallele Subagents innerhalb dieser Session fuer unabhaengige Aufgaben.
Committe nach jedem logischen Schritt mit Conventional Commits (Englisch, Praesens).
Teste nach jeder Aenderung: pytest skills/schliff/tests/ -v
Zero Regression: alle 732+ bestehenden Tests muessen weiterhin bestehen.
```

### Subagent-Nutzung INNERHALB jeder Session

Jede Claude-Session dispatched 6 Subagents fuer parallele Arbeit an unabhaengigen Dateien:

| Rolle | Was | Wann |
|-------|-----|------|
| Architect | Scaffolds, Interfaces, Stubs | Zuerst (andere Agents brauchen die Interfaces) |
| Impl A | Erste Haelfte der Features | Nach Architect, parallel mit Impl B |
| Impl B | Zweite Haelfte der Features | Nach Architect, parallel mit Impl A |
| Test Lead | Tests, Fixtures, Edge Cases | Parallel mit Impl A/B |
| Integration | CLI, Composite, Wiring | Nach Impl A/B |
| QA/Review | Full Test Run, Fixes | Zuletzt |

**Reihenfolge:** Architect (1) -> Impl A + Impl B + Test Lead (3 parallel) -> Integration (1) -> QA (1)

### Cleanup nach jeder Phase

```bash
# 1. PR erstellen
gh pr create --base main --head {branch} --title "{title}"

# 2. Nach Review + Merge
git worktree remove ../schliff-phase-{X}

# 3. Main aktualisieren (fuer naechste Wave)
cd /Users/franzpaul/schliff
git pull origin main
```

---

## Phase Dependency Graph

```
WAVE 1:
  Phase 0: Launch Prep ──────────────── (main, parallel)
  Phase 1a: Scorer Registry ─────────── (worktree, CRITICAL PATH)

WAVE 2 (after 1a merges):
  Phase 1b: System Prompt Scoring ───── (worktree)
  Phase 1c: MCP Tool Scoring ────────── (worktree)
  Phase 2: Evolution Engine ─────────── (worktree, laeuft in Wave 3 weiter)

WAVE 3:
  Phase 2: (continues) ─────────────── (worktree)

WAVE 4 (after 2 merges):
  Phase 3a: GitHub Action ───────────── (separates Repo)
  Phase 3b: MCP Server ─────────────── (worktree)
  Phase 3c: Registry & Badges ──────── (worktree)

WAVE 5: Launch
```

---

## Phase 0: Launch Prep

**Wave:** 1 (parallel zu Phase 1a)
**Terminal:** A
**Location:** Direkt auf main (kein Worktree — nur Docs/Content)
**Duration:** 2 Tage

### Session-Kontext

```
Du arbeitest direkt auf main in /Users/franzpaul/schliff.
Nur Docs und Content — kein Code, keine Scoring-Aenderungen.
Lies: docs/specs/2026-03-28-v8-design.md, Section 8 (Launch Strategy)
```

### Subagent-Dispatch (6 parallel)

| # | Aufgabe | Output |
|---|---------|--------|
| 1 | README restructure (neue Section-Order, Tagline, Why?) | `README.md` |
| 2 | Show HN Post Draft (300 Woerter, Comment-Strategie) | `docs/launch/show-hn-draft.md` |
| 3 | Twitter Thread Draft (7 Tweets) | `docs/launch/twitter-thread.md` |
| 4 | Reddit Posts Draft (r/ClaudeAI, r/Python, r/ML) | `docs/launch/reddit-posts.md` |
| 5 | Awesome-List PR Drafts (10 Listen) | `docs/launch/awesome-list-prs.md` |
| 6 | "State of AI Instructions" Report Skeleton | `docs/launch/state-of-ai-instructions.md` |

### Merge

Direkte Commits auf main (kein PR noetig, nur Docs).

---

## Phase 1a: Scorer Registry + Patterns Split

**Wave:** 1 (parallel zu Phase 0)
**Terminal:** B
**Worktree:** `../schliff-phase-1a`
**Branch:** `schliff-v8/phase-1a-scorer-registry`
**Duration:** 3 Tage
**Spec:** Section 2 of v8-design.md

**CRITICAL PATH** — alles andere haengt davon ab.

### Session-Kontext

```
Du arbeitest in ../schliff-phase-1a auf Branch schliff-v8/phase-1a-scorer-registry.
Lies: docs/specs/2026-03-28-v8-design.md, Section 2 (Scorer Registry)

ZERO REGRESSION: Alle 732 bestehenden Tests muessen nach dem Refactoring identisch bestehen.
Jede SKILL.md/CLAUDE.md/.cursorrules/AGENTS.md muss den EXAKT gleichen Score produzieren.
```

### File Map

```
CREATE:
  skills/schliff/scripts/scoring/registry.py          # Format -> scorer-set + weight profiles
  skills/schliff/scripts/scoring/patterns/__init__.py  # Re-export shim
  skills/schliff/scripts/scoring/patterns/base.py      # Format-agnostic patterns
  skills/schliff/scripts/scoring/patterns/skill_md.py  # SKILL.md patterns
  skills/schliff/tests/test_registry.py
  skills/schliff/tests/test_patterns_split.py

MODIFY:
  skills/schliff/scripts/scoring/patterns.py           # -> re-export shim
  skills/schliff/scripts/shared.py                     # build_scores() uses registry
  skills/schliff/scripts/scoring/composite.py          # weight profiles per format
  skills/schliff/scripts/cli.py                        # --format flag extension
```

### Subagent-Reihenfolge

```
Step 1: Architect (1 Agent)
  - registry.py mit SCORER_REGISTRY, WEIGHT_PROFILES, get_scorers(), get_weights()
  - patterns/__init__.py als re-export shim

Step 2: 3 Agents parallel
  - Impl A: patterns/base.py (hedging, filler, security, noise patterns extrahieren)
  - Impl B: patterns/skill_md.py (frontmatter, trigger, scope patterns extrahieren)
  - Test Lead: test_registry.py + test_patterns_split.py (Regression-Snapshots)

Step 3: Integration (1 Agent)
  - shared.py: build_scores() nutzt Registry
  - composite.py: Weight Profiles pro Format
  - cli.py: --format Flag erweitern

Step 4: QA (1 Agent)
  - pytest skills/schliff/tests/ -v (alle 732+ Tests)
  - schliff score skills/schliff/SKILL.md == identischer Output zu main
  - ruff check skills/schliff/
```

### Merge-Kriterien

- [ ] Alle 732 Tests bestehen
- [ ] Neue Registry-Tests bestehen
- [ ] Score-Output identisch zu main
- [ ] `gh pr create --base main --head schliff-v8/phase-1a-scorer-registry --title "refactor: scorer registry pattern for multi-format support"`

---

## Phase 1b: System Prompt Scoring

**Wave:** 2
**Terminal:** A
**Worktree:** `../schliff-phase-1b`
**Branch:** `schliff-v8/phase-1b-system-prompt-scoring`
**Voraussetzung:** Phase 1a gemergt
**Duration:** 5 Tage
**Spec:** Section 3.1 + `docs/specs/system-prompt-scoring-spec.md`

### Session-Kontext

```
Du arbeitest in ../schliff-phase-1b auf Branch schliff-v8/phase-1b-system-prompt-scoring.
Lies:
1. docs/specs/2026-03-28-v8-design.md, Section 3.1
2. docs/specs/system-prompt-scoring-spec.md (VOLLSTAENDIGE Detail-Spec mit Regex-Patterns)

System Prompt Scoring hat KEINEN Wettbewerb — das ist Schliff's groesste Expansion.
7 neue Dimensionen: structure_prompt, output_contract, efficiency (adaptiert),
clarity (transferiert), security (adaptiert), composability (adaptiert), completeness (NEU).
```

### File Map

```
CREATE:
  skills/schliff/scripts/scoring/structure_prompt.py
  skills/schliff/scripts/scoring/output_contract.py
  skills/schliff/scripts/scoring/completeness.py
  skills/schliff/scripts/scoring/patterns/system_prompt.py
  skills/schliff/tests/test_system_prompt_scoring.py
  skills/schliff/tests/fixtures/system_prompts/good_api_assistant.txt
  skills/schliff/tests/fixtures/system_prompts/mediocre_chatbot.txt
  skills/schliff/tests/fixtures/system_prompts/bad_minimal.txt

MODIFY:
  skills/schliff/scripts/scoring/registry.py
  skills/schliff/scripts/scoring/formats.py
  skills/schliff/scripts/scoring/patterns/__init__.py
  skills/schliff/scripts/shared.py
  skills/schliff/scripts/scoring/composite.py
```

### Subagent-Reihenfolge

```
Step 1: Architect (1 Agent)
  - registry.py: system_prompt Entry + Weight Profile hinzufuegen
  - formats.py: system_prompt Detection (Heuristik: kein Frontmatter + Role-Definition-Patterns)
  - Scorer-Stubs mit korrektem Interface

Step 2: 3 Agents parallel
  - Impl A: structure_prompt.py + patterns/system_prompt.py (10 Checks, je 10 Punkte)
  - Impl B: output_contract.py + completeness.py (2 neue Dimensionen)
  - Test Lead: test_system_prompt_scoring.py + 3 Fixture-Files (good/mediocre/bad)

Step 3: Integration (1 Agent)
  - shared.py: build_scores() mit neuen Scorern
  - composite.py: system_prompt Weight Profile
  - efficiency/clarity/security fuer system_prompt adaptieren

Step 4: QA (1 Agent)
  - Alle bestehenden 732+ Tests bestehen
  - 50+ neue Tests bestehen
  - schliff score --format system-prompt good_prompt.txt -> sinnvoller Score
  - schliff score --format system-prompt bad_prompt.txt -> erkennt Probleme
```

---

## Phase 1c: MCP Tool Description Scoring

**Wave:** 2 (parallel zu 1b)
**Terminal:** B
**Worktree:** `../schliff-phase-1c`
**Branch:** `schliff-v8/phase-1c-mcp-tool-scoring`
**Voraussetzung:** Phase 1a gemergt
**Duration:** 3 Tage
**Spec:** Section 3.2 of v8-design.md

### Session-Kontext

```
Du arbeitest in ../schliff-phase-1c auf Branch schliff-v8/phase-1c-mcp-tool-scoring.
Lies: docs/specs/2026-03-28-v8-design.md, Section 3.2

MCP Tool Descriptions sind JSON mit name + description + inputSchema.
6 Dimensionen: schema_quality (25%), trigger_alignment (20%), efficiency (15%),
clarity (15%), security (15%), composability (10%).
```

### File Map

```
CREATE:
  skills/schliff/scripts/scoring/schema_quality.py
  skills/schliff/scripts/scoring/trigger_alignment.py
  skills/schliff/scripts/scoring/patterns/mcp_tool.py
  skills/schliff/tests/test_mcp_tool_scoring.py
  skills/schliff/tests/fixtures/mcp_tools/good_tool.json
  skills/schliff/tests/fixtures/mcp_tools/bad_tool.json

MODIFY:
  skills/schliff/scripts/scoring/registry.py
  skills/schliff/scripts/scoring/formats.py
  skills/schliff/scripts/shared.py
  skills/schliff/scripts/scoring/composite.py
```

### Subagent-Reihenfolge

Gleiche Struktur wie Phase 1b: Architect -> 3 parallel (Impl A, Impl B, Tests) -> Integration -> QA

---

## Phase 2: Evolution Engine

**Wave:** 2-3 (startet parallel zu 1b/1c, laeuft laenger)
**Terminal:** C (Wave 2), dann A (Wave 3)
**Worktree:** `../schliff-phase-2`
**Branch:** `schliff-v8/phase-2-evolution-engine`
**Voraussetzung:** Phase 1a gemergt (1b/1c NICHT noetig)
**Duration:** 8 Tage
**Spec:** Section 4 of v8-design.md

### Session-Kontext

```
Du arbeitest in ../schliff-phase-2 auf Branch schliff-v8/phase-2-evolution-engine.
Lies: docs/specs/2026-03-28-v8-design.md, Section 4 (Evolution Engine)

Das ist Schliff's "Karpathy-Moment": schliff evolve verbessert Instruction Files autonom.
Geschlossener Loop: deterministisch scoren -> LLM verbessern -> deterministisch verifizieren.
Kein anderes Tool kann das.

WICHTIG:
- LiteLLM ist OPTIONAL (pip install schliff[evolve])
- Core schliff score bleibt zero-dependency
- --budget 0 = nur deterministische Patches, kein LLM
- Lazy-Import: litellm wird NUR in cmd_evolve importiert
```

### File Map

```
CREATE:
  skills/schliff/scripts/evolve/__init__.py
  skills/schliff/scripts/evolve/engine.py
  skills/schliff/scripts/evolve/llm.py
  skills/schliff/scripts/evolve/prompts.py
  skills/schliff/scripts/evolve/guard.py
  skills/schliff/scripts/evolve/budget.py
  skills/schliff/scripts/evolve/plateau.py
  skills/schliff/scripts/evolve/lineage.py
  skills/schliff/scripts/evolve/content.py
  skills/schliff/tests/test_evolve_guard.py
  skills/schliff/tests/test_evolve_budget.py
  skills/schliff/tests/test_evolve_plateau.py
  skills/schliff/tests/test_evolve_lineage.py
  skills/schliff/tests/test_evolve_engine.py
  skills/schliff/tests/test_evolve_prompts.py

MODIFY:
  skills/schliff/scripts/cli.py
  pyproject.toml
```

### Subagent-Reihenfolge

```
Step 1: Architect (1 Agent)
  - evolve/__init__.py
  - content.py (Content extraction, hashing, patch application)
  - Dataclasses: Generation, GuardResult, CompletionResult, LineageRecord, etc.

Step 2: 3 Agents parallel
  - Impl A: guard.py + budget.py + plateau.py (pure logic, kein LLM)
  - Impl B: llm.py + prompts.py (LiteLLM integration, Provider Resolution, Prompt Templates)
  - Test Lead: Alle 6 Test-Files (Mock-LLM-Responses, Guard/Budget/Plateau/Lineage Tests)

Step 3: 2 Agents parallel
  - Engine: engine.py (Hauptloop Phase 0-3) + lineage.py (JSONL I/O + Snapshots)
  - CLI: cli.py (cmd_evolve einhaengen) + pyproject.toml (optional-dependencies)

Step 4: QA (1 Agent)
  - Full test suite (732+ bestehende + neue evolve Tests)
  - schliff evolve --budget 0 SKILL.md (nur deterministische Patches, kein LLM noetig)
  - schliff evolve --dry-run SKILL.md (zeigt Plan ohne Aenderungen)
  - ruff check
```

---

## Phase 3a: GitHub Action

**Wave:** 4
**Terminal:** A
**Location:** Neues Repo `Zandereins/schliff-action`
**Duration:** 3 Tage
**Spec:** Section 5 of v8-design.md

### Session-Kontext

```
Du erstellst ein neues Repo: Zandereins/schliff-action
Lies: docs/specs/2026-03-28-v8-design.md, Section 5 (GitHub Action)

Composite Action (setup-python + pip install schliff).
Codecov-Style PR Comments mit Score-Delta und Dimension-Breakdown.
Dynamic Badges via shields.io Endpoint + GitHub Gist.
```

### Files

```
action.yml, README.md, examples/minimal.yml, examples/full.yml,
examples/monorepo.yml, .github/workflows/test.yml
```

---

## Phase 3b: MCP Server

**Wave:** 4 (parallel zu 3a + 3c)
**Terminal:** B
**Worktree:** `../schliff-phase-3b`
**Branch:** `schliff-v8/phase-3b-mcp-server`
**Duration:** 3 Tage
**Spec:** Section 6 of v8-design.md

### Session-Kontext

```
Du arbeitest in ../schliff-phase-3b auf Branch schliff-v8/phase-3b-mcp-server.
Lies: docs/specs/2026-03-28-v8-design.md, Section 6 (MCP Server)

5 Tools via FastMCP: schliff_score, schliff_suggest, schliff_verify,
schliff_compare, schliff_diff.
Direkte Python-Imports (kein Subprocess), pip install schliff[mcp].
KEIN schliff_fix/evolve im MCP — der Agent IST der LLM.
```

### Files

```
CREATE: skills/schliff/scripts/mcp_server.py, skills/schliff/tests/test_mcp_server.py
MODIFY: pyproject.toml (schliff-mcp entry point, [mcp] extra)
```

---

## Phase 3c: Registry & Badges

**Wave:** 4 (parallel zu 3a + 3b)
**Terminal:** C
**Worktree:** `../schliff-phase-3c`
**Branch:** `schliff-v8/phase-3c-registry-badges`
**Duration:** 3 Tage
**Spec:** Section 7 + `docs/specs/schliff-registry-platform.md`

### Session-Kontext

```
Du arbeitest in ../schliff-phase-3c auf Branch schliff-v8/phase-3c-registry-badges.
Lies:
1. docs/specs/2026-03-28-v8-design.md, Section 7
2. docs/specs/schliff-registry-platform.md (Detail-Spec)

Nur Phase 1 der Registry: Badges ($0 Infrastruktur).
schliff badge --gist, shields.io Endpoint, GitHub Action Template.
```

---

## Execution Checklist

### Pre-Flight (vor Wave 1)

```bash
cd /Users/franzpaul/schliff
git status                                    # Sauber?
pytest skills/schliff/tests/ -v               # 732 Tests gruen?
git tag v7.1.0-pre-v8                         # Snapshot taggen
```

### Wave-Uebersicht

| Wave | Woche | Terminals | Phasen |
|------|-------|-----------|--------|
| 1 | 1-3 | 2 | Phase 0 (main) + Phase 1a (worktree) |
| 2 | 4-5 | 3 | Phase 1b + 1c + 2 (je worktree) |
| 3 | 6-8 | 1 | Phase 2 (continues) |
| 4 | 9 | 3 | Phase 3a (neues Repo) + 3b + 3c (je worktree) |
| 5 | 10 | 1 | Launch |

### Per-Phase Completion

Fuer JEDE Phase vor Merge:
1. Alle bestehenden Tests bestehen (zero regression)
2. Alle neuen Tests bestehen
3. `ruff check skills/schliff/` bestanden
4. QA-Agent hat reviewed
5. PR erstellt: `gh pr create --base main --head {branch} --title "{title}"`
6. Squash-Merge nach Review
7. Worktree aufraemen: `git worktree remove ../schliff-phase-{X}`
8. Main updaten: `cd /Users/franzpaul/schliff && git pull origin main`

### Launch Week (Woche 10)

- [ ] README restructured (Phase 0)
- [ ] Show HN post ready (Phase 0)
- [ ] "State of AI Instructions" report mit echten Daten
- [ ] System Prompts scored (Phase 1b)
- [ ] MCP Tools scored (Phase 1c)
- [ ] `schliff evolve` funktioniert (Phase 2)
- [ ] GitHub Action auf Marketplace (Phase 3a)
- [ ] MCP Server installierbar (Phase 3b)
- [ ] Dynamic Badges funktionieren (Phase 3c)
- [ ] Post Show HN (Dienstag 08:30 ET / 14:30 MESZ)
- [ ] Post Twitter Thread (gleicher Tag)
- [ ] Post r/ClaudeAI (gleicher Tag +2h)
- [ ] Post r/Python (Mittwoch)
- [ ] Submit Awesome-List PRs (Freitag)
