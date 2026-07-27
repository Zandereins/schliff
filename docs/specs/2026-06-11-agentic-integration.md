# Spec: Schliff als fester Bestandteil von Franz' Agentic Engineering

- **Status:** In Progress (Phase 1)
- **Datum:** 2026-06-11
- **Branch:** `feat/agentic-integration-phase1`
- **Herkunft:** 17-Agent ultracode-Evaluation (Run `wf_b8cf8cc5-985`), Gewinner-Proposal „Honest Signal, One Hook" (Council Ø 8.0/10), veredelt mit Grafts der unterlegenen Proposals.

## Ziel

Schliff von „nice demo" zu einem Werkzeug machen, dessen Wert Franz im täglichen Loop **spürt** — Qualitätsregressionen in Instruction-Files (SKILL.md / CLAUDE.md / AGENTS.md / .cursorrules) werden ambient sichtbar und korrigierbar, ohne Ritual, ohne Nagging. Architekturprinzip: **Trust → Signal → Automation.** Nichts wird ambient, bevor das Signal ehrlich ist; nichts wird automatisiert, bevor der Fix-Pfad nachweislich funktioniert.

## Kontext (alle Zahlen live verifiziert 2026-06-11, Engine 8.1.0)

Drei Vertrauensbrüche, die erklären, warum Schliff bisher keinen gefühlten Mehrwert lieferte — **alle drei vor der Arbeit live bestätigt**:

1. **Stale Toolchain (BEHOBEN in K1):** `which schliff` meldete **7.2.0** aus jedem Verzeichnis außerhalb des Repos, **8.1.0** nur aus dem Repo-Root. Root Cause: cwd-abhängiger `importlib.metadata`-Konflikt zwischen einer stale `schliff-7.2.0.dist-info` (alter `uv pip install -e .`) im venv und einer Legacy-`schliff.egg-info` (8.1.0, setuptools) im Repo-Root. Plugin-Kopie in `~/.claude/skills/schliff` war zusätzlich vom 24. April (6 Wochen stale).
2. **Alle Franz-Skills an der F-Wall:** grill-me **22.9**, handoff **25.7**, hydra **27.7**, carl-manager **30.2**. Ursache ist **nicht** schlechte Skill-Qualität, sondern der 42%-Composite-Cap: ohne Eval-Suite sind die Dimensionen `triggers`/`quality`/`edges` = `None`, der Composite ist gedeckelt. Der Score ist dadurch bedeutungslos.
3. **`evolve` lügt über Fix-Anzahl:** `cli.py:228` setzt `fix_count = len(gradients)` (zählt Diagnosen, nicht anwendbare Patches). `evolve/engine.py:_apply_single_patch` (Zeilen ~140-153) verwirft `append`/`remove_regex`-Ops still. Patch-Output injiziert teils `TODO:`-Platzhalter, die den Score heben und den Skill verschlechtern.

Zusätzlicher Befund während K1: **`install.sh` backupt nach `~/.claude/skills/schliff.bak.<ts>`** — dieser Pfad liegt im Claude-Code-Skill-Scan-Verzeichnis, wodurch der gesamte `/schliff:*`-Command-Namespace dupliziert wird (`schliff.bak.<ts>:auto` etc.). Temporär behoben durch Verschieben nach `~/.claude/backups/`; permanenter Fix gehört in PR-A.

### Verifizierte Einzelwerte

- hydra SKILL.md: 11.976 Tokens / Budget 1.000 (Ratio **11,97×**, `severity: over`). Dims: structure 75, efficiency 49, composability 56, clarity 92; triggers/quality/edges = `None`.
- Globale `~/.claude/CLAUDE.md`: composite 25.0, Token-Budget 602/2.000 (`ok`). → Bestätigt: CLAUDE.md ist regression-only, keine Fake-Eval-Suite (skill-shaped Dims sind dort Rauschen).
- Franz-eigene SKILL.md: grill-me, handoff, hydra, carl-manager. (carl-help, learned haben keine SKILL.md.)

## Anforderungen

### K1 — Toolchain-Reparatur ✅ ERLEDIGT (2026-06-11)

- [x] Stale 7.2.0-Metadata entfernt (`schliff.egg-info` gelöscht, `uv pip install -e . --reinstall` → 8.1.0).
- [x] `schliff version` konsistent 8.1.0 aus Repo-Root **und** `/tmp`.
- [x] Plugin-Kopie via `bash install.sh` auf 8.1.0 refresht (Copy-Mode, Auto-Backup).
- [x] history.jsonl (pytest-vergiftet, 637 Zeilen) archiviert → `.schliff/history.jsonl.bak.20260611`.
- [x] install.sh-Backup aus Skill-Scan-Pfad entfernt → `~/.claude/backups/schliff-skill-backups/`.

### K2 — Ehrliche Baselines + erster gefühlter Gewinn (Effort: S)

- **K2a Hydra-Token-Diät:** bench-/Referenzmaterial aus dem always-loaded SKILL.md-Body in `references/` auslagern. Ziel: Token-Ratio < 2× (von 11,97×), ~10k Context-Tokens/Session zurück. **Kein** neuer Code; reine Umstrukturierung des Markdown. Akzeptanz: hydra triggert weiterhin korrekt (Trigger-Phrasen bleiben im Body), Funktionalität unverändert.
- **K2b Eval-Suites:** für die 4 Franz-Skills mit SKILL.md per Heuristik-Generator (`skills/schliff/scripts/init-skill.py`, 0.1s, kein LLM). Zielliste per **Glob** über `~/.claude/skills/*/SKILL.md`, nicht hardcoded. Durable Kopien nach `~/Projects/claude-stack/skills/`.
- **K2c Review-Gate (Pflicht, ~15 min/Suite):** selbstreferenzielle/generische Trigger umschreiben. Akzeptanzkriterium: „jeder Trigger ist ein Satz, den Franz wirklich sagen würde". Ohne dieses Gate ist der Score-Sprung (22.9 → ~64 für grill-me) Inflation, nicht Ehrlichkeit.
- **K2d Provenance-Marker:** `created_by: 'schliff-init-heuristic'` in jeder generierten Suite.
- **K2e:** CLAUDE.md/AGENTS.md bekommen **keine** Eval-Suites (regression-only).

### K3 — Der Hook: `~/.claude/hooks/schliff-watch.js` (Effort: M)

- **Eigener** PostToolUse-Eintrag mit Matcher `"Write|Edit"` in `~/.claude/settings.json` — **nicht** in den bestehenden `"Bash|Write|Edit"`-Block (sonst Node-Spawn bei jedem Bash-Call).
- Skeleton von `gsd-context-monitor.js` (debounce, fail-open, silent-fail, exit 0 immer).
- **Scope:** Pfad matcht `/(SKILL|CLAUDE|AGENTS)\.md$|\.cursorrules$/`, **nicht** unter `~/.claude/plugins` (Third-Party), nicht unter tmp/pytest-Pfaden.
- **Firing-Regeln:** SKILL.md → Composite-Drop ≥ 2 Punkte ODER `token_budget.within_budget === false`. CLAUDE.md/AGENTS.md/.cursorrules → **nur** Budget-Breach.
- **Cache:** `~/.schliff/watch-cache.json` (persistent, **nicht** `os.tmpdir()`), gekeyt auf `(file_path, engine_version)`. False-Alarm-Suppression: kein Alarm, wenn neuer Score einem früher gesehenen Wert entspricht (git revert / branch-switch).
- **Telemetrie:** bei jedem Firing durable Record nach `~/.schliff/failures.jsonl` (file, old/new composite, dimension-deltas, engine_version, `channel: "hook"`).
- **Verhalten bei Regression:** eine Zeile `additionalContext`, ehrlich formuliert: `schliff: <file> regressed 87→81 (edges -6). Fix: schliff suggest <file> (ranked, apply manually)`. Sonst: totale Stille. Max 1 Meldung/Datei/Session. 5s-Timeout.
- **Latenz-Budget:** ~0.2s cold verifiziert; jeder Fehler → exit 0.

### K4 — Failure-Loop aktivieren: `session-injector.js` (Effort: S)

- Den geshippten-aber-schlafenden `~/.claude/skills/schliff/hooks/session-injector.js` (8.1.0-Kopie) als SessionStart-Hook in `~/.claude/settings.json` registrieren.
- **Verifikationsschritt (Pflicht):** synthetischen 3-Failure-Zustand in einer `.schliff/failures.jsonl` erzeugen und bestätigen, dass die Injection feuert — nicht ungeprüft durchwinken.
- Eine Zeile in `~/.claude/CLAUDE.md`: „When a skill misfires, run /schliff:log-failure before moving on."

### K5 — Honesty-Fixes im schliff-Repo: ZWEI PRs

- **PR-A (S, dieser Branch, `fix/fix-count-honesty` als Teil von Phase 1):**
  1. `cli.py:228`: `fix_count` = Anzahl tatsächlich anwendbarer Patches (`len(generate_patches(...))`), nicht `len(gradients)`.
  2. Falsche Doku-Behauptung „All changes are git-committed" in `commands/schliff/auto.md` korrigieren.
  3. History-Path-Isolation in der Test-Suite (env var / tmp-path fixture), damit pytest nie wieder die echte `.schliff/history.jsonl` vergiftet.
  4. `install.sh`-Backup-Location: nach `~/.claude/backups/` statt `~/.claude/skills/`, damit der Skill-Scan-Pfad nicht vergiftet wird.
  - Reiner Presentation-/Test-/Tooling-Fix, **null Write-Path-Risiko**. Gate: 1.210-Test-Suite grün.
- **PR-B (M, Woche 2, separater Branch):** Patch-Applier-Unification (content-level Primitiv für CLI + evolve), Patch-Quality-Gate (nie `TODO:`-Text, nie body-gescrapte when-Klauseln), Op-Coverage-Round-Trip-Test, `remove_regex`-Sicherheitstests mit Positiv-Korpus, **Golden-Score-Byte-Identity-Gate**. Außerhalb Phase 1.

### K6 — Wöchentliche Fleet-Sicht in claude-stack (Effort: S)

- ~15 tolerante Zeilen in `~/Projects/claude-stack/bin/stack-healthcheck.py` neben dem bestehenden skill-mesh-Call: `schliff doctor --json` mit **cwd gepinnt auf `~/.claude/skills`** (Unbounded-Recursion-Bug ab `~`). Ausgabe nur zwei Zahlen: Fleet-Token-Kosten + Skills-ohne-Suite-Count. Mesh-Issue-Count ignorieren (False-Positive-Rate hoch).
- **Liveness-Check:** WARN, wenn `~/.schliff/watch-cache.json` mtime > 7 Tage trotz kürzlicher Instruction-File-Edits (toter fail-open-Hook von gesundem stillem unterscheiden).

## Technische Entscheidungen

- **uv statt pip:** venv wird mit `uv` verwaltet (kein pip drin). Editable-Reinstall via `VIRTUAL_ENV=… uv pip install -e .`. Kein paralleler pipx-Install von PyPI-8.1.0 (erzeugt nächsten Versions-Skew).
- **Copy-Mode statt Symlink** für die Plugin-Kopie (`install.sh` ohne `--link`): stabiler Snapshot, uncommittete Repo-Experimente landen nicht im Daily-Driver. Trade-off: muss periodisch refresht werden (K6-Liveness fängt Drift). Symlink-Option bleibt offen.
- **Determinismus-Vertrag (hart):** keine Komponente ändert Scorer-Semantik. PR-B läuft gegen Golden-Score-Byte-Identity-Gate. Security/Runtime bleiben separate Signale, nie im Headline-Composite. AI-Judge-Dimensionen bleiben eingefroren.
- **Hooks pinnen absolute Pfade**, fail-open, eigener Matcher (kein Bash-Tax), 5s-Timeout.
- **Cache-Keying auf `(path, engine_version)`** gegen Upgrade-False-Positives; `failures.jsonl` mit Rotation > 1 MB.

## Bewusst NICHT gebaut (Phase 1)

- `/schliff:auto` unattended (gebannt bis PR-B; wendet TODO-Platzhalter an).
- MCP-Server / SARIF / Watch-Mode / LSP (Phase 3 mit explizitem Re-Entry-Trigger; teils agnix' Heimspiel).
- Harte `--min-score`-Gates auf Franz' Files (ehrliche Scores ~60-67; rotes Dauer-Gate trainiert Ignorieren).
- Eval-Suites für CLAUDE.md/AGENTS.md, Statusline-Score, CARL/GSD-Integration (beide dormant), schliff.toml-Config-System.

## Strategischer Nebeneffekt

Jedes Hook-Firing + `/schliff:log-failure`-Eintrag landet als timestamped Record (`channel`-Feld) in `failures.jsonl` → `/schliff:triage` clustert zu Eval-Cases → nach 2-4 Wochen existiert erstmals ein realer, dokumentierter Quality-Miss-Korpus (die zweite Hälfte des eingefrorenen Judge-Kalibrierungs-Gates) als Nebenprodukt. Plus Launch-Receipts statt Pitch: „10k Tokens/Session zurück, Regression X mid-session gefangen."

## Offene Fragen

- K2a: hydra-Diät — welche Sektionen sind „always-loaded-essenziell" (Trigger, Kern-Workflow) vs. auslagerbar (bench-Tabellen, Beispiele)? → beim Umsetzen entscheiden, Trigger-Erhalt verifizieren.
- Symlink vs. Copy für Plugin-Kopie langfristig — offen, Default Copy.

## Checkpoint nach 2 Wochen (Phase-3-Gate)

Hat der Hook ≥ 1 echte Regression gefangen? Wurden suggest/evolve real genutzt? Nur dann Phase 3.
