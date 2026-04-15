# Schliff v8 — Session & Subagent Prompts

Copy-paste-ready Prompts fuer jede Claude-Session und jeden Subagent-Dispatch.

---

## Wave 1, Terminal A: Phase 0 — Launch Prep

### Session-Start-Prompt (paste when opening Claude)

```
Lies zuerst diese Dateien:
1. docs/specs/2026-03-28-v8-design.md — Section 8 (Launch Strategy)
2. docs/specs/plans/2026-03-28-v8-master-plan.md — Phase 0

Du arbeitest direkt auf main in /Users/franzpaul/schliff. Nur Docs und Content, kein Scoring-Code.

Aufgabe: Launch-Content fuer Schliff v8 vorbereiten. Dispatche 6 Subagents parallel (alle schreiben in unterschiedliche Dateien, kein Konflikt). Committe nach jedem fertigen Subagent.
```

### Subagent 1: README Restructure

```
Restructure /Users/franzpaul/schliff/README.md.

Lies zuerst die aktuelle README. Dann reorganisiere in diese Section-Reihenfolge:

1. Titel + Tagline: "The quality score for AI instructions."
2. Badges-Zeile (version, downloads, tests, license, schliff score)
3. One-liner Pitch (1 Satz: was es tut + warum)
4. Install + schliff demo (ABOVE THE FOLD — erster Code-Block auf der Seite)
5. Demo GIF (existierendes Asset, direkt nach Install)
6. NEUE "Why?" Section mit 4 Bullet Points:
   - Instruction files degrade silently — triggers overlap, agent fires on wrong tasks
   - "always X" vs "never X" contradictions hide in long files
   - No eval suite = 3 dimensions score zero (triggers, quality, edges)
   - Hedging wastes tokens — "you might want to consider" = noise
7. "What Schliff Catches" (bestehende 8-Dimensionen-Tabelle — behalten)
8. Quick Start (score, compare, suggest, doctor — kondensieren)
9. NEUE "State of AI Instructions" Teaser-Section:
   > We scored 100+ public instruction files. 73% score below C.
   > [Read the full report →](docs/launch/state-of-ai-instructions.md)
10. CI Integration (GitHub Action Beispiel — 3-Zeilen YAML)
11. Architecture (in <details> collapsible verschieben)
12. Badge / Contributing / License (kondensieren)

Regeln:
- Bestehenden Content preservieren, nur reorganisieren
- Keine Emojis
- Technischer, direkter Ton
- Commit: "docs: restructure README for v8 launch"

This is a WRITE task — modify the README file directly.
```

### Subagent 2: Show HN Post Draft

```
Erstelle docs/launch/show-hn-draft.md mit dem Show HN Post fuer Schliff.

Titel (max 60 Zeichen):
"Show HN: Schliff -- A deterministic quality scorer for AI instruction files"

Post-Text (max 300 Woerter):
- Absatz 1: Problem (2 Saetze) — AI instructions degrade silently
- Absatz 2: Was Schliff ist (2 Saetze) — 8-dimension scorer, zero deps, Python stdlib
- Absatz 3: Was es findet das ueberrascht (4 Bullet Points):
  * Copy-paste examples that inflate quality scores (dedup detection drops 94 -> 43)
  * "always X" vs "never X" contradictions hiding in long files
  * Hedging language ("you might want to consider") that wastes agent tokens
  * Missing scope boundaries that cause agents to hallucinate responsibilities
- Absatz 4: Anti-Gaming (1 Satz) — 6 detection vectors
- Absatz 5: Autonomous improvement (2 Saetze) — optional Claude Code loop, 54 [D] to 98 [S]
- Absatz 6: CI integration (1 Satz) — like Codecov
- Absatz 7: State of AI report (1 Satz) — scored 100+ public skills, 73% below C
- Absatz 8: Stats (1 Satz) — 732 tests, MIT, no API key needed
- Link: https://github.com/Zandereins/schliff
- Frage: "What dimensions matter most for instruction quality?"

Danach: Comment-Strategie-Section mit vorbereiteten Antworten auf 5 haeufige Fragen:
1. "Why not just use a linter like ruff?"
2. "This seems over-engineered for a markdown file"
3. "Why deterministic instead of LLM-based scoring?"
4. "How does this compare to prompt engineering tools?"
5. "Score inflation / gaming?"

Commit: "docs: add Show HN post draft"

This is a WRITE task — create the file directly.
```

### Subagent 3: Twitter Thread Draft

```
Erstelle docs/launch/twitter-thread.md mit einem 7-Tweet Thread.

Tweet 1 — Hook (max 280 Zeichen):
AI coding agents are only as good as their instruction files. I scored 100+ public SKILL.md and CLAUDE.md files. 73% score below C. The most common problem: they tell the agent WHAT to do but never define WHEN to activate or HOW to fail. Here's what I found.

Tweet 2 — The Problem (max 280 Zeichen):
Instruction files degrade silently. Triggers overlap, instructions contradict ("always X" vs "never X"), no edge cases defined, hedging wastes tokens. There was no linter for this.

Tweet 3 — The Solution (max 280 Zeichen):
Schliff: deterministic quality scoring for AI instruction files. 8 dimensions. Zero dependencies. No LLM needed. Same input, same score, every time. pip install schliff && schliff score path/to/SKILL.md. Works with SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md.

Tweet 4 — Demo (max 280 Zeichen):
A vague deployment helper goes from 54 [D] to 98 [S] in 18 autonomous iterations. Structure: 70->100. Triggers: 0->100. Quality: 0->95. Efficiency: 35->93. The scorer is the ruler. Claude is the craftsman. [DEMO GIF PLACEHOLDER]

Tweet 5 — Data (max 280 Zeichen):
The "State of AI Instructions" report: 61% of public skills score 0/100 on triggers, quality, AND edges. Average score: 47 [D]. Most common fix: adding an eval-suite unlocks 3 unmeasured dimensions. Top skills use <300 tokens with higher scores than 1000+ token files.

Tweet 6 — Try It (max 280 Zeichen):
Try it in 10 seconds: pip install schliff && schliff demo. Score your files: schliff score SKILL.md. Get fixes: schliff suggest SKILL.md. Scan all skills: schliff doctor. 732 tests. MIT license. Zero dependencies.

Tweet 7 — CTA (max 280 Zeichen):
The Codecov for AI instruction files. github.com/Zandereins/schliff. If you maintain skills for Claude Code, Cursor, or Copilot — your files probably score lower than you think.

Commit: "docs: add Twitter thread draft"

This is a WRITE task — create the file directly.
```

### Subagent 4: Reddit Posts Draft

```
Erstelle docs/launch/reddit-posts.md mit 3 Reddit-Posts.

POST 1: r/ClaudeAI
Titel: "I built a linter for SKILL.md and CLAUDE.md files — scored 100+ public skills, 73% are below C"
Body: Problem (skills degrade), Solution (Schliff, 8 dimensions, deterministic), Ueberraschende Findings (4 Bullet Points mit Zahlen), How to try (pip install, 3 Commands), Autonomous loop (/schliff:auto, 54->98), CI integration, Stats (732 tests, MIT, zero deps). Angebot: "Happy to score anyone's SKILL.md live in the comments — just paste a link."

POST 2: r/Python
Titel: "schliff: a zero-dependency Python CLI that lints AI instruction files (SKILL.md, CLAUDE.md, .cursorrules) — 732 tests, stdlib only"
Body: Technischer Winkel — pure stdlib, TF-IDF heuristics, sqrt density curves, anti-gaming detection, pre-commit hook, GitHub Action. Architektur-Interesse: "The scoring engine is ~2,000 lines of pure stdlib Python with no ML/LLM in the scoring path."

POST 3: r/MachineLearning (mit [P] Tag)
Titel: "[P] Deterministic scoring for AI agent instruction files — no ML needed, 8-dimension static analysis"
Body: Akademischer Winkel — Approach beschreiben (TF-IDF, antonym pairs, entropy analysis), Anti-Gaming (6 patterns), Key Findings, Link zu docs/SCORING.md.

Commit: "docs: add Reddit posts draft"

This is a WRITE task — create the file directly.
```

### Subagent 5: Awesome-List PR Drafts

```
Erstelle docs/launch/awesome-list-prs.md mit 10 PR-Drafts fuer Awesome-Listen.

Fuer jede Liste:
- Repository URL
- Kategorie in der Liste
- PR-Titel
- PR-Body (3-5 Saetze, auf die Zielgruppe der Liste zugeschnitten)

Listen:
1. hesreallyhim/awesome-claude-code — Kategorie: Skills/Tools
2. jqueryscript/awesome-claude-code — Kategorie: Tools
3. travisvn/awesome-claude-skills — Kategorie: Development & Quality
4. analysis-tools-dev/static-analysis — Kategorie: Multi-Language oder neue Kategorie "AI Instruction Files"
5. caramelomartins/awesome-linters — Kategorie: AI/LLM oder Markdown
6. vintasoftware/python-linters-and-code-analysis — Kategorie: Linters
7. ml-tooling/best-of-python-dev — Kategorie: Code Quality
8. rohitg00/awesome-claude-code-toolkit — Kategorie: Quality Tools
9. wong2/awesome-mcp-servers — Kategorie: Testing/Quality (wenn MCP Server fertig)
10. sourcegraph/awesome-code-ai — Kategorie: Developer Tools

Commit: "docs: add awesome-list PR drafts"

This is a WRITE task — create the file directly.
```

### Subagent 6: State of AI Instructions Report

```
Erstelle docs/launch/state-of-ai-instructions.md — das Skelett fuer den "State of AI Instructions 2026" Report.

Struktur:

# State of AI Instructions 2026

## Executive Summary
"We scored 100+ public AI instruction files. 73% score below C. Here's what we found."

## Methodology
- Scored with schliff v7.1.0, all 8 dimensions + security
- Sources: awesome-claude-code, awesome-cursorrules, awesome-claude-skills, public GitHub repos
- Anonymized individual repos, show aggregates + top 10 with permission
- Scoring is deterministic: same file, same score, every run

## Key Findings

### Finding 1: The Eval Gap
"61% of public skills score 0/100 on triggers, quality, AND edges — because they have no eval suite."
[DATA TABLE PLACEHOLDER — fill after scoring]

### Finding 2: The Token Paradox
"Files under 300 tokens consistently outscore 1000+ token files."
[SCATTER PLOT PLACEHOLDER]

### Finding 3: The Contradiction Trap
"34% of files over 200 lines contain at least one 'always X' vs 'never X' contradiction."
[EXAMPLES PLACEHOLDER]

### Finding 4: Format Matters
"SKILL.md with frontmatter scores 23 points higher than .cursorrules on average."
[FORMAT COMPARISON TABLE PLACEHOLDER]

### Finding 5: The Security Blind Spot
"Less than 5% of files pass the security check."
[SECURITY FINDINGS PLACEHOLDER]

## Score Distribution
[HISTOGRAM PLACEHOLDER — overall scores]

## Dimension Heatmap
[HEATMAP PLACEHOLDER — avg score per dimension]

## Top 10 Best-Scored Public Skills
[TABLE PLACEHOLDER — with permission]

## Bottom 10 Common Anti-Patterns
1. No eval suite (unlockable dimensions)
2. Missing frontmatter
3. Hedging language
4. Contradicting instructions
5. No scope boundaries
6. No error handling section
7. Copy-paste examples
8. Token bloat (>1000 tokens, low density)
9. No security patterns
10. Stale file references

## Actionable Takeaways
"3 fixes that move any file from D to B in under 10 minutes"
1. Add an eval-suite (schliff init or manual — unlocks 3 unmeasured dimensions)
2. Add frontmatter with name + description (structure score jumps 20+ points)
3. Remove hedging language (efficiency score jumps 10+ points)

## Methodology Details
- Scoring dimensions: structure (15%), triggers (20%), quality (20%), edges (15%), efficiency (10%), composability (10%), clarity (5%), security (8%)
- Anti-gaming: 6 detection vectors active
- Tool: pip install schliff && schliff score <file>

## About Schliff
[Brief description + link]

Commit: "docs: add State of AI Instructions report skeleton"

This is a WRITE task — create the file directly.
```

---

## Wave 1, Terminal B: Phase 1a — Scorer Registry

### Session-Start-Prompt

```
Lies zuerst diese Dateien:
1. docs/specs/2026-03-28-v8-design.md — Section 2 (Architecture: Scorer Registry)
2. docs/specs/plans/2026-03-28-v8-master-plan.md — Phase 1a
3. skills/schliff/scripts/scoring/patterns.py — verstehe die bestehenden Patterns
4. skills/schliff/scripts/shared.py — verstehe build_scores()
5. skills/schliff/scripts/scoring/composite.py — verstehe compute_composite()

Du arbeitest in Worktree ../schliff-phase-1a auf Branch schliff-v8/phase-1a-scorer-registry.

Aufgabe: Refactore die Scoring-Architektur fuer Multi-Format-Support. Fuehre ein Scorer Registry Pattern ein und splitte patterns.py in Submodule.

KRITISCHE CONSTRAINT: ZERO REGRESSION. Jede bestehende Datei (SKILL.md, CLAUDE.md, .cursorrules, AGENTS.md) muss den EXAKT gleichen Score produzieren wie vorher. Alle 732 Tests muessen bestehen.

Arbeitsreihenfolge:
1. Architect-Subagent: registry.py + patterns/__init__.py scaffolden
2. Drei parallele Subagents: patterns/base.py, patterns/skill_md.py, tests
3. Integration-Subagent: shared.py + composite.py + cli.py anpassen
4. QA-Subagent: Full test run + Score-Vergleich
```

### Subagent 1: Architect — Registry + Shim

```
Erstelle zwei Dateien in diesem Worktree:

DATEI 1: skills/schliff/scripts/scoring/registry.py

Inhalt: Scorer Registry mit Format-zu-Scorer-Mapping und Weight Profiles.
Lies die Spec in docs/specs/2026-03-28-v8-design.md Section 2 fuer die genauen Datenstrukturen.

Muss enthalten:
- SCORER_REGISTRY: dict[str, list[str]] — welche Scorer pro Format laufen
- WEIGHT_PROFILES: dict[str, dict[str, float]] — Gewichte pro Format
- FORMAT_ALIASES: dict[str, str] — Kurzformen fuer --format Flag
- get_scorers(fmt: str) -> list[str]
- get_weights(fmt: str) -> dict[str, float]

Alle 4 bestehenden Formate (skill.md, claude.md, cursorrules, agents.md) muessen die gleichen 8 Scorer und gleichen Gewichte haben wie bisher. Kommentare fuer zukuenftige Formate (system_prompt, mcp_tool) als auskommentierte Eintraege.

DATEI 2: skills/schliff/scripts/scoring/patterns/__init__.py

Re-Export-Shim der backward compatibility garantiert:
- Importiert alles aus patterns.base und patterns.skill_md
- Bestehender Code der `from scoring.patterns import X` nutzt funktioniert weiter

Erstelle auch das leere Verzeichnis: skills/schliff/scripts/scoring/patterns/

Commit: "feat: scaffold scorer registry and patterns subpackage"

This is a WRITE task — create the files directly.
```

### Subagent 2: Patterns Base

```
Erstelle skills/schliff/scripts/scoring/patterns/base.py

Lies zuerst: skills/schliff/scripts/scoring/patterns.py (die bestehende monolithische Datei)

Extrahiere alle FORMAT-AGNOSTISCHEN Patterns in base.py. Das sind Patterns die fuer JEDES Format gelten, nicht nur SKILL.md:

- Hedging patterns (_RE_HEDGING, HEDGING_PHRASES, etc.)
- Filler patterns (_RE_FILLER, _RE_OBVIOUS, etc.)
- Security patterns (_RE_SECURITY_*, SECURITY_PATTERNS, etc.)
- Noise patterns (_RE_NOISE, _RE_REPEATED_LINE, etc.)
- General NLP patterns (sentence splitting, word counting, etc.)
- Anti-gaming patterns (_RE_KEYWORD_STUFFING, etc.)

NICHT extrahieren (die bleiben fuer skill_md.py):
- Frontmatter patterns (_RE_FRONTMATTER_*)
- Trigger patterns (_RE_TRIGGER_*, _RE_POSITIVE_SCOPE, etc.)
- Scope/Composability patterns (_RE_SCOPE_*, _RE_HANDOFF_*, etc.)
- Structure patterns (_RE_SECTION_*, _RE_EXAMPLE_*, etc.)

Jedes Pattern muss den EXAKT gleichen Regex haben wie im Original.
Fuege am Anfang ein __all__ hinzu das alle exportierten Namen auflistet.

Commit: "refactor: extract format-agnostic patterns to patterns/base.py"

This is a WRITE task — create the file directly.
```

### Subagent 3: Patterns Skill-MD

```
Erstelle skills/schliff/scripts/scoring/patterns/skill_md.py

Lies zuerst: skills/schliff/scripts/scoring/patterns.py (die bestehende monolithische Datei)

Extrahiere alle SKILL.MD-SPEZIFISCHEN Patterns. Das sind Patterns die nur fuer Instruktionsdateien mit SKILL.md-Struktur gelten:

- Frontmatter patterns (_RE_FRONTMATTER_NAME, _RE_FRONTMATTER_DESC, etc.)
- Trigger patterns (_RE_TRIGGER_*, _RE_POSITIVE_SCOPE, _RE_NEGATIVE_SCOPE, etc.)
- Scope/Composability patterns (_RE_SCOPE_*, _RE_HANDOFF_*, _RE_ERROR_*, etc.)
- Structure patterns (_RE_SECTION_*, _RE_EXAMPLE_*, _RE_HEADER_*, etc.)
- Edge case patterns (_RE_EDGE_*, etc.)
- Quality patterns (_RE_ASSERTION_*, _RE_FEATURE_*, etc.)

Jedes Pattern muss den EXAKT gleichen Regex haben wie im Original.
Fuege am Anfang ein __all__ hinzu.

WICHTIG: Patterns die SOWOHL in base.py als auch hier gebraucht werden: importiere sie aus base.py, dupliziere sie NICHT.

Commit: "refactor: extract SKILL.md patterns to patterns/skill_md.py"

This is a WRITE task — create the file directly.
```

### Subagent 4: Test Lead

```
Erstelle zwei Test-Dateien:

DATEI 1: skills/schliff/tests/test_registry.py

Tests fuer das Scorer Registry:
- test_registry_has_all_existing_formats(): Alle 4 Formate vorhanden
- test_registry_scorers_match_existing(): Alle 4 Formate haben die 8 Standard-Scorer
- test_weight_profiles_exist_for_all_formats(): Jedes Format in SCORER_REGISTRY hat ein Weight Profile
- test_weight_profiles_keys_match_scorers(): Weight-Keys == Scorer-Liste pro Format
- test_get_scorers_with_alias(): "skill" == "skill.md", "claude" == "claude.md", etc.
- test_get_scorers_unknown_format_raises(): ValueError fuer unbekanntes Format
- test_get_weights_returns_correct_profile(): Bekannte Gewichte pruefen

DATEI 2: skills/schliff/tests/test_patterns_split.py

Regressions-Tests fuer den Pattern-Split:
- test_patterns_backward_compat_import(): `from scoring.patterns import _RE_FRONTMATTER_NAME` funktioniert
- test_base_patterns_importable(): Alle base patterns importierbar
- test_skill_md_patterns_importable(): Alle skill_md patterns importierbar
- test_no_pattern_lost(): Zaehle Patterns im Original vs. base + skill_md (gleiche Anzahl)
- test_score_regression_skill_md(): Score von skills/schliff/SKILL.md ist identisch zu erwartetem Wert
  (Lies zuerst den aktuellen Score mit `schliff score skills/schliff/SKILL.md --json` und hardcode ihn als Erwartung)

Fuehre die Tests aus: pytest skills/schliff/tests/test_registry.py skills/schliff/tests/test_patterns_split.py -v
Erwartung: Tests fuer noch nicht existierende Module werden fehlschlagen — das ist OK, die kommen von den anderen Agents.

Commit: "test: add scorer registry and pattern split regression tests"

This is a WRITE task — create the files directly.
```

### Subagent 5: Integration

```
Modifiziere 3 bestehende Dateien um das Registry Pattern einzuweben:

Lies zuerst:
- skills/schliff/scripts/scoring/registry.py (vom Architect erstellt)
- skills/schliff/scripts/shared.py (bestehend)
- skills/schliff/scripts/scoring/composite.py (bestehend)
- skills/schliff/scripts/cli.py (bestehend)

DATEI 1: skills/schliff/scripts/shared.py
- Importiere get_scorers, get_weights aus scoring.registry
- In build_scores(): Wenn ein `fmt` Parameter uebergeben wird, nutze get_scorers(fmt) um zu bestimmen welche Scorer laufen
- Fuer bestehende Aufrufe ohne fmt: bisheriges Verhalten beibehalten (alle 8 Scorer)
- Das ist eine MINIMALE Aenderung — die Registry wird konsultiert aber das Ergebnis ist identisch

DATEI 2: skills/schliff/scripts/scoring/composite.py
- Importiere get_weights aus scoring.registry
- In compute_composite(): Wenn ein `fmt` Parameter uebergeben wird, nutze get_weights(fmt) statt der hardcodierten Gewichte
- Fuer bestehende Aufrufe ohne fmt: bisherige hardcodierte Gewichte (backward compat)

DATEI 3: skills/schliff/scripts/cli.py
- Erweitere den --format Flag um die neuen Aliases aus FORMAT_ALIASES
- Fuer v8: system-prompt und mcp-tool als gueltige Werte akzeptieren (werden in Phase 1b/1c implementiert)

ZERO REGRESSION: Bestehende Aufrufe ohne --format muessen identische Ergebnisse liefern.

Commit: "refactor: wire scorer registry into build_scores and composite"

This is an EDIT task — modify existing files. Read each file first, then make minimal changes.
```

### Subagent 6: QA

```
Fuehre eine vollstaendige Qualitaetspruefung durch:

1. Laufe alle Tests: pytest skills/schliff/tests/ -v --tb=short
   Erwartung: Alle 732+ Tests muessen bestehen

2. Vergleiche Score-Output:
   schliff score skills/schliff/SKILL.md
   Der Composite Score muss identisch sein zum Wert auf main (99.0 oder was auch immer aktuell ist)

3. Teste Multi-Format Backward Compat:
   Erstelle eine temporaere CLAUDE.md und .cursorrules Datei, score sie, loesche sie

4. Linter: ruff check skills/schliff/
   Erwartung: Keine Fehler

5. Teste das neue --format Flag:
   schliff score skills/schliff/SKILL.md --format skill.md
   schliff score skills/schliff/SKILL.md --format skill
   Beide muessen identischen Output liefern

6. Falls Fehler: FIXEN (du darfst alle Dateien anfassen)

7. Commit alle Fixes: "fix: resolve QA findings in scorer registry refactor"

This is a research + fix task. Read files, run commands, fix issues.
```

---

## Wave 2, Terminal A: Phase 1b — System Prompt Scoring

### Session-Start-Prompt

```
Lies zuerst diese Dateien:
1. docs/specs/2026-03-28-v8-design.md — Section 3.1 (System Prompts)
2. docs/specs/system-prompt-scoring-spec.md — VOLLSTAENDIGE Detail-Spec mit allen Regex-Patterns und Rubrics
3. docs/specs/plans/2026-03-28-v8-master-plan.md — Phase 1b
4. skills/schliff/scripts/scoring/registry.py — verstehe das Registry Pattern
5. skills/schliff/scripts/scoring/structure.py — verstehe das Scorer-Interface (return dict mit "score", "issues", "details")
6. skills/schliff/scripts/scoring/efficiency.py — Beispiel fuer einen transferierbaren Scorer

Du arbeitest in Worktree ../schliff-phase-1b auf Branch schliff-v8/phase-1b-system-prompt-scoring.

System Prompt Scoring hat KEINEN Wettbewerb — das ist Schliff's groesste Expansion.
7 Dimensionen: structure_prompt (15%), output_contract (15%), efficiency (15%), clarity (15%), security (15%), composability (10%), completeness (15%).

Arbeitsreihenfolge:
1. Architect: registry.py + formats.py updaten, Scorer-Stubs erstellen
2. Drei parallele Subagents: structure_prompt.py, output_contract.py + completeness.py, Tests
3. Integration: shared.py + composite.py verdrahten
4. QA: Full test run

Die Detail-Spec (system-prompt-scoring-spec.md) enthaelt fuer JEDE Dimension:
- Exakte Regex-Patterns
- Scoring-Rubric (was ergibt 100, was 50, was 0)
- Anti-Gaming-Regeln
Verwende diese Patterns 1:1 — sie wurden von einem Opus-Research-Agent erarbeitet und validiert.
```

### Subagent 1: Architect

```
Aktualisiere 3 bestehende Dateien und erstelle Scorer-Stubs:

1. skills/schliff/scripts/scoring/registry.py:
   Fuege hinzu:
   - "system_prompt" in SCORER_REGISTRY mit: ["structure_prompt", "output_contract", "efficiency", "clarity", "security", "composability", "completeness"]
   - "system_prompt" in WEIGHT_PROFILES mit: {"structure_prompt": 15, "output_contract": 15, "efficiency": 15, "clarity": 15, "security": 15, "composability": 10, "completeness": 15}

2. skills/schliff/scripts/scoring/formats.py:
   Erweitere detect_format() um system_prompt Erkennung:
   - Heuristik: Datei hat KEIN YAML Frontmatter UND enthaelt Role-Definition-Patterns (regex: (?i)(you are|your role is|act as|your purpose))
   - ODER: --format system-prompt explizit gesetzt
   - Dateiendungen: .txt, .prompt, .system (wenn Role-Definition-Pattern matched)

3. Erstelle Scorer-Stubs (leere Funktionen mit korrektem Interface):
   - skills/schliff/scripts/scoring/structure_prompt.py: def score_structure_prompt(path, content=None, **kw) -> dict
   - skills/schliff/scripts/scoring/output_contract.py: def score_output_contract(path, content=None, **kw) -> dict
   - skills/schliff/scripts/scoring/completeness.py: def score_completeness(path, content=None, **kw) -> dict
   Jeder Stub returned: {"score": 0, "issues": [], "details": {}}

4. skills/schliff/scripts/scoring/patterns/__init__.py:
   Fuege hinzu: from scoring.patterns.system_prompt import *  # noqa

Commit: "feat: register system_prompt format and scaffold scorers"

This is a WRITE + EDIT task.
```

### Subagent 2: structure_prompt + patterns/system_prompt.py

```
Erstelle 2 Dateien:

DATEI 1: skills/schliff/scripts/scoring/patterns/system_prompt.py

Lies die Spec: docs/specs/system-prompt-scoring-spec.md — alle Regex-Patterns fuer System Prompts.

Enthaelt alle Regex-Patterns fuer System Prompt Scoring:
- ROLE_DEFINITION_RE = re.compile(r'(?i)(you are|your role is|act as|you\'re a|as a \w+ assistant|your purpose)')
- TASK_DESCRIPTION_RE = re.compile(r'(?i)(your (task|job|goal|objective|mission) is|you (will|should|must) \w+ (the|a|an)|primary function)')
- CONSTRAINT_BLOCK_RE = re.compile(r'(?i)(constraints?:|rules?:|limitations?:|boundaries:|guardrails:|do not|never|must not|always)')
- OUTPUT_FORMAT_RE = re.compile(r'(?i)(respond (in|with|using)|output (format|as)|return (a|the)|format:|your (response|reply|answer) (should|must|will))')
- EXAMPLES_RE = re.compile(r'(?i)(example[s]?:|for example|e\.g\.|<example>|input.*output|here\'?s (a|an|one))')
- SECTION_SEPARATOR_RE = re.compile(r'(<\w+>|^##?\s|^---$)', re.MULTILINE)
- DEAD_CONTENT_RE = re.compile(r'(?i)(TODO|FIXME|HACK|XXX|placeholder|TBD|to be determined|fill in)')
- Plus alle weiteren Patterns aus der Spec fuer output_contract, completeness, security

DATEI 2: skills/schliff/scripts/scoring/structure_prompt.py

Implementiere score_structure_prompt(path, content=None, **kw) -> dict

10 Checks, je 10 Punkte (additiv, 0-100):
1. Role definition — ROLE_DEFINITION_RE matched
2. Task description — TASK_DESCRIPTION_RE matched
3. Constraint block — CONSTRAINT_BLOCK_RE mit 2+ Matches
4. Output format spec — OUTPUT_FORMAT_RE matched
5. Examples present — EXAMPLES_RE matched
6. Section separators — 2+ distinct matches von SECTION_SEPARATOR_RE
7. Logical ordering — Role/Context in ersten 25% des Textes, Constraints in Mitte
8. Length appropriateness — 50-2000 Woerter = 10, <50 oder >2000 = 5
9. Progressive detail — Erster Absatz <50 Woerter UND weitere Sections existieren
10. No dead content — DEAD_CONTENT_RE hat 0 Matches

Return: {"score": int, "issues": list[str], "details": {"checks": dict_mit_check_ergebnissen}}

WICHTIG: Code-Bloecke (``` ... ```) vor der Analyse strippen — nur Prosa bewerten.

Commit: "feat: implement structure_prompt scorer with 10 checks"

This is a WRITE task — create the files directly.
```

### Subagent 3: output_contract + completeness

```
Erstelle 2 Dateien:

Lies die Spec: docs/specs/system-prompt-scoring-spec.md — Dimension 2 (output_contract) und Dimension 7 (completeness).

DATEI 1: skills/schliff/scripts/scoring/output_contract.py

Implementiere score_output_contract(path, content=None, **kw) -> dict

10 Checks, je 10 Punkte (additiv, 0-100):
1. Format specification — Regex: (?i)(respond (in|with|using) (json|xml|markdown|yaml|plain text|html|csv))
2. Length constraints — Regex: (?i)(max(imum)? (\d+ )?(words?|sentences?|paragraphs?|tokens?|characters?)|keep .{0,20} (short|brief|concise)|limit .{0,20} to)
3. Tone/voice — Regex: (?i)(tone:|voice:|style:|be (formal|casual|friendly|professional|technical|concise|verbose)|write (as|like|in the style))
4. Schema definition — Regex: (?i)(schema:|json schema|interface \{|type \{|\{[\s\S]*"type":|fields?:|properties?:)
5. Required fields — Regex: (?i)(must (include|contain|have|return)|required (fields?|sections?|elements?)|always include)
6. Forbidden content — Regex: (?i)(never (include|mention|output|return|generate)|do not (include|mention|output|return)|forbidden|prohibited|must not contain)
7. Response structure — Regex: (?i)(structure your|organize your|format your|your response should (have|contain|follow)|sections?:|steps?:)
8. Error response format — Regex: (?i)(if .{0,30} (error|fail|invalid|unable)|error (response|format|handling)|when .{0,30} (cannot|fails?|wrong))
9. Validation instruction — Regex: (?i)(validate|verify|check|ensure|confirm) .{0,40} (before|after|that)
10. Example output — Regex: (?i)(example (output|response)|here'?s .{0,20} example|sample (output|response)|expected (output|response))

DATEI 2: skills/schliff/scripts/scoring/completeness.py

Implementiere score_completeness(path, content=None, **kw) -> dict

10 Checks, je 10 Punkte (additiv, 0-100):
1. Error handling — Regex: (?i)(if .{0,30}(error|fail|exception|invalid)|error handling|when .{0,20}(goes wrong|fails|breaks))
2. Edge cases — Regex: (?i)(edge case|corner case|special case|unusual|unexpected|extreme|boundary)
3. Ambiguity handling — Regex: (?i)(if (unclear|ambiguous|uncertain|unsure)|when .{0,20}(not sure|don't know|unclear)|ask for clarification)
4. Off-topic handling — Regex: (?i)(off.?topic|out of scope|not your (role|job|responsibility)|if asked about .{0,30} (decline|redirect|refuse))
5. Multi-turn handling — Regex: (?i)(multi.?turn|conversation|follow.?up|previous (message|context)|maintain .{0,20}(context|state|thread))
6. Language/locale — Regex: (?i)(language|locale|english|respond in|translate|multilingual|i18n)
7. Empty/null input — Regex: (?i)(empty|null|blank|no input|missing (input|data|information)|if .{0,20}(nothing|no .{0,10}provided))
8. Rate/length limits — Regex: (?i)(rate limit|too (long|many|much|large)|maximum|truncat|overflow|exceed)
9. Graceful degradation — Regex: (?i)(graceful|fallback|degrad|best effort|partial|approximate|when .{0,20}(limited|incomplete|partial))
10. Non-obvious examples — Regex: (?i)(for (instance|example)|e\.g\.|such as|consider .{0,20}(case|scenario|situation)) (nur zaehlen wenn in Kombination mit edge/error/ambiguity)

Commit: "feat: implement output_contract and completeness scorers"

This is a WRITE task — create the files directly.
```

### Subagent 4: Test Lead

```
Erstelle Test-Suite und Fixtures:

DATEI 1: skills/schliff/tests/fixtures/system_prompts/good_api_assistant.txt
Ein guter System Prompt (~300 Woerter) der alle 7 Dimensionen hoch scoren sollte:
- Klare Rollendefinition
- Task Description
- Constraints Block
- Output Format (JSON)
- 2 Beispiele
- Error Handling
- Off-Topic Handling
- Security Boundaries

DATEI 2: skills/schliff/tests/fixtures/system_prompts/mediocre_chatbot.txt
Ein mittlerer System Prompt (~150 Woerter):
- Rollendefinition vorhanden
- Vage Task Description
- Keine Constraints
- Kein Output Format
- Keine Beispiele
- Grundlegendes Error Handling

DATEI 3: skills/schliff/tests/fixtures/system_prompts/bad_minimal.txt
Ein schlechter System Prompt (~30 Woerter):
- "You are a helpful assistant. Answer questions accurately."
- Kein Output Contract, keine Constraints, keine Beispiele, keine Edge Cases

DATEI 4: skills/schliff/tests/test_system_prompt_scoring.py
50+ Tests:

Fuer JEDE der 7 Dimensionen:
- test_{dim}_good_fixture(): Score >= 70
- test_{dim}_mediocre_fixture(): Score 30-70
- test_{dim}_bad_fixture(): Score <= 30
- test_{dim}_empty_string(): Score == 0 oder minimaler Wert

Fuer structure_prompt speziell:
- test_structure_role_definition_detected()
- test_structure_no_role_definition()
- test_structure_code_blocks_stripped()
- test_structure_length_penalty_short()
- test_structure_length_penalty_long()
- test_structure_dead_content_detected()

Fuer output_contract:
- test_output_contract_json_format_detected()
- test_output_contract_length_constraint_detected()
- test_output_contract_no_contract()

Fuer completeness:
- test_completeness_error_handling_detected()
- test_completeness_edge_cases_detected()
- test_completeness_empty_prompt()

Composite Tests:
- test_composite_system_prompt_good(): Composite Score 75-100
- test_composite_system_prompt_bad(): Composite Score < 40
- test_system_prompt_does_not_regress_skill_md(): Scoring einer SKILL.md aendert sich nicht

Commit: "test: add system prompt scoring test suite with fixtures"

This is a WRITE task — create all files directly.
```

### Subagent 5: Integration

```
Verdrahte die neuen System Prompt Scorer in den bestehenden Scoring-Flow.

Lies zuerst:
- skills/schliff/scripts/shared.py — build_scores()
- skills/schliff/scripts/scoring/composite.py — compute_composite()
- skills/schliff/scripts/scoring/registry.py (aktualisiert vom Architect)

Aenderungen:

1. skills/schliff/scripts/shared.py:
   - Wenn fmt == "system_prompt": importiere und rufe die neuen Scorer auf (structure_prompt, output_contract, completeness)
   - Fuer efficiency, clarity, security, composability: nutze die bestehenden Scorer, aber mit system_prompt-spezifischen Anpassungen (z.B. andere Noise-Patterns)
   - Falls ein Scorer fuer das Format nicht existiert: ueberspringen (nicht crashen)

2. skills/schliff/scripts/scoring/composite.py:
   - Nutze get_weights("system_prompt") wenn fmt == "system_prompt"
   - Renormalisierung muss mit den neuen 7 Dimensionen funktionieren

3. skills/schliff/scripts/cli.py:
   - schliff score --format system-prompt path.txt muss funktionieren
   - Auto-Detection: Wenn Datei kein Frontmatter hat und Role-Definition-Pattern enthaelt, als system_prompt behandeln

ZERO REGRESSION: Bestehende Aufrufe ohne --format system-prompt duerfen sich nicht aendern.

Commit: "feat: wire system prompt scoring into build_scores and composite"

This is an EDIT task — read files first, then make minimal changes.
```

### Subagent 6: QA

```
Fuehre vollstaendige Qualitaetspruefung durch:

1. pytest skills/schliff/tests/ -v --tb=short
   Erwartung: Alle 732+ bestehenden Tests + 50+ neue Tests bestehen

2. Score Regression Check:
   schliff score skills/schliff/SKILL.md --json
   Score muss identisch zu main sein

3. Teste System Prompt Scoring:
   schliff score --format system-prompt skills/schliff/tests/fixtures/system_prompts/good_api_assistant.txt
   schliff score --format system-prompt skills/schliff/tests/fixtures/system_prompts/bad_minimal.txt
   Good sollte >70 scoren, Bad sollte <40 scoren

4. Teste Auto-Detection:
   schliff score skills/schliff/tests/fixtures/system_prompts/good_api_assistant.txt
   (ohne --format — sollte automatisch als system_prompt erkannt werden)

5. Teste dass bestehende Formate nicht betroffen sind:
   schliff score CLAUDE.md (falls vorhanden)
   Muss identischen Score liefern wie auf main

6. ruff check skills/schliff/

7. Falls Fehler: FIXEN und committen

This is a research + fix task.
```

---

## Wave 2, Terminal B: Phase 1c — MCP Tool Scoring

### Session-Start-Prompt

```
Lies zuerst diese Dateien:
1. docs/specs/2026-03-28-v8-design.md — Section 3.2 (MCP Tool Descriptions)
2. docs/specs/plans/2026-03-28-v8-master-plan.md — Phase 1c
3. skills/schliff/scripts/scoring/registry.py — Registry Pattern
4. skills/schliff/scripts/scoring/structure.py — Scorer Interface

Du arbeitest in Worktree ../schliff-phase-1c auf Branch schliff-v8/phase-1c-mcp-tool-scoring.

MCP Tool Descriptions sind JSON: {"name": "...", "description": "...", "inputSchema": {...}}.
6 Dimensionen: schema_quality (25%), trigger_alignment (20%), efficiency (15%), clarity (15%), security (15%), composability (10%).

Gleiche Arbeitsreihenfolge wie Phase 1b: Architect -> 3 parallel -> Integration -> QA.
Nutze 6 Subagents. Erstelle Test-Fixtures als JSON-Dateien.
```

Die Subagent-Prompts folgen dem gleichen Muster wie Phase 1b — angepasst auf JSON-Input und die 6 MCP-spezifischen Dimensionen. Referenziere die Spec Section 3.2 fuer die konkreten Checks.

---

## Wave 2, Terminal C: Phase 2 — Evolution Engine

### Session-Start-Prompt

```
Lies zuerst diese Dateien:
1. docs/specs/2026-03-28-v8-design.md — Section 4 (Evolution Engine) — das ist die LAENGSTE Section, lies sie VOLLSTAENDIG
2. docs/specs/plans/2026-03-28-v8-master-plan.md — Phase 2
3. skills/schliff/scripts/text_gradient.py — bestehende Gradient-Berechnung + Patch-Generierung (wird wiederverwendet)
4. skills/schliff/scripts/shared.py — build_scores(), read_skill_safe()
5. skills/schliff/scripts/scoring/composite.py — compute_composite()

Du arbeitest in Worktree ../schliff-phase-2 auf Branch schliff-v8/phase-2-evolution-engine.

Das ist Schliff's "Karpathy-Moment": schliff evolve verbessert Instruction Files autonom.
Geschlossener Loop den KEIN anderes Tool hat:
  Deterministisch scoren -> Deterministisch patchen (60-70%, $0) -> LLM verbessern -> Deterministisch verifizieren

WICHTIG:
- LiteLLM ist OPTIONAL: pip install schliff[evolve]
- Core bleibt zero-dependency — litellm wird NUR in cmd_evolve lazy-importiert
- --budget 0 = nur deterministische Patches, kein LLM noetig
- Bestehende text_gradient.py wird 1:1 wiederverwendet, NICHT geaendert

Arbeitsreihenfolge:
1. Architect: evolve/ Package scaffolden, alle Dataclasses definieren
2. Drei parallele Subagents:
   - guard.py + budget.py + plateau.py (pure logic, kein LLM)
   - llm.py + prompts.py (LiteLLM Provider Resolution, Prompt Templates)
   - Alle 6 Test-Dateien (Mock-LLM-Responses)
3. engine.py + lineage.py (Hauptloop + JSONL I/O)
4. cli.py + pyproject.toml (cmd_evolve einhaengen, optional dep)
5. QA: Full test suite

Die Spec enthaelt:
- Exakten CLI-Interface mit allen Flags
- Pseudocode fuer den Algorithmus
- LLM System- und User-Prompts (copy-paste-ready)
- JSONL Lineage-Format mit Beispiel
- Terminal-Output-Format
- Token-Schaetzungen
```

Die Subagent-Prompts fuer Phase 2 folgen der Spec Section 4 — jeder Subagent bekommt seinen Teil der Dateienliste und die relevanten Pseudocode-Bloecke aus der Spec.

---

## Wave 4: Phasen 3a, 3b, 3c

### Phase 3a Session-Start-Prompt (GitHub Action)

```
Du erstellst ein NEUES Repo: Zandereins/schliff-action.
Lies: docs/specs/2026-03-28-v8-design.md — Section 5 (GitHub Action)

Erstelle eine Composite GitHub Action die:
- Python 3.12 installiert + pip install schliff
- Alle Instruction Files im Repo findet und scored
- Codecov-Style PR Comment postet (Score, Grade, Delta, Top 3 Suggestions)
- Dynamic Badge via GitHub Gist aktualisiert
- Regressions-Detection (Score-Drop vs main > 2.0 -> Fail)

Files: action.yml, README.md, examples/minimal.yml, examples/full.yml, examples/monorepo.yml, .github/workflows/test.yml

Nutze 6 Subagents: action.yml, PR-Comment-Logik, Badge-Logik, Examples, README, Self-Test.
```

### Phase 3b Session-Start-Prompt (MCP Server)

```
Du arbeitest in Worktree ../schliff-phase-3b auf Branch schliff-v8/phase-3b-mcp-server.
Lies: docs/specs/2026-03-28-v8-design.md — Section 6 (MCP Server)

Erstelle einen MCP Server mit FastMCP (pip install mcp) der 5 Tools exponiert:
- schliff_score: Score file or inline text
- schliff_suggest: Ranked improvement suggestions
- schliff_verify: Pass/fail against threshold
- schliff_compare: Side-by-side comparison
- schliff_diff: Explain score changes vs git ref

Direkte Python-Imports (kein Subprocess). Kein schliff_fix/evolve — der Agent IST der LLM.
Entry point: schliff-mcp (pyproject.toml scripts).

Files: skills/schliff/scripts/mcp_server.py, skills/schliff/tests/test_mcp_server.py, pyproject.toml update.
```

### Phase 3c Session-Start-Prompt (Registry & Badges)

```
Du arbeitest in Worktree ../schliff-phase-3c auf Branch schliff-v8/phase-3c-registry-badges.
Lies:
1. docs/specs/2026-03-28-v8-design.md — Section 7
2. docs/specs/schliff-registry-platform.md

Nur Phase 1 der Registry: Badges mit $0 Infrastruktur.
- schliff badge --gist: Aktualisiert ein GitHub Gist mit shields.io Endpoint JSON
- Grade-to-Color Mapping (S=gold, A=brightgreen, B=green, C=yellow, D=orange, F=red)
- GitHub Action Template fuer Auto-Update bei Push
- schliff report --share: Social-Sharing-fähiger Output
```
