# Changelog

All notable changes to SkillForge are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [5.0.0] - 2026-03-21

### Added — The Self-Driving Engine
- **Auto-Apply** (`text-gradient.py --apply`) — deterministic patches apply themselves without LLM
- **Auto-Improve** (`auto-improve.py`) — autonomous loop driver: score → gradient → apply → keep/revert → repeat
- **Strategy Predictor** (`meta-report.py predict_best_strategy()`) — predicts P(keep) before trying
- **Runtime Scoring** (`score-skill.py --runtime`) — 7th dimension invokes Claude for behavioral validation
- **Auto-Calibration** (`meta-report.py compute_optimal_weights()`) — dimension weights from data
- **Mesh Evolution** (`skill-mesh.py generate_mesh_actions()`) — generates negative boundaries, stubs, scope fixes
- **Incremental Mesh** (`skill-mesh.py --incremental`) — content-hash caching, O(n×changed) not O(n²)
- **Episodic Memory** (`episodic-store.py`) — cross-session TF-IDF recall with auto-consolidation
- **Parallel Branching** (`parallel-runner.py`) — git worktree experiments, 3 strategies at once
- **ROI Stopping** — marginal ROI < 0.2 for 3 windows → auto-stop
- **Gap Buckets** (`progress.py`) — dimension gaps discretized for predictor input
- **Episode Emit** (`progress.py`) — auto-emit learnings to episodic store after decisions
- New subcommands: `/skillforge:auto`, `/skillforge:mesh-evolve`, `/skillforge:predict`, `/skillforge:recall`

### Changed
- Dimension weights redistributed: triggers 25%→20%, quality 25%→20%, composability 10%→5%, new runtime 15%
- `compute_composite()` auto-loads `calibrated-weights.json` when available
- Scorer test updated: 7 dimensions (6 core + runtime opt-in)

## [4.1.0] - 2026-03-21

### Fixed
- 3 critical + 4 high security issues from 4-agent code review
- CI stability with `--no-runtime-auto` in self-tests

## [3.1.0] - 2026-03-20

### Fixed
- `--since` flag now correctly scopes all 11 methods in `progress.py`
- Consistent score capping across all scoring functions

### Added
- Cost tracking: real `duration_ms`, `tokens_estimated`, `delta`, computed `status`
- 25 new integration tests (51 total)
- `explain_score_change()` wired into `--diff` output
- Security: path traversal guard, file size limit (1MB), ReDoS protection
- CHANGELOG.md, SECURITY.md, GitHub CI workflow

### Removed
- Dead code: `history/results.tsv`
- Shell expansion risk: replaced `xargs` with `sed` in `run-eval.sh`

## [3.0.0] - 2026-03-20

### Added
- Runtime evaluator — invoke Claude with test prompts
- Diff-aware scoring (`--diff` flag)
- Strategy meta-learning in `progress.py`
- Instruction clarity scorer (`--clarity` flag)
- Eval health classification
- 26-test integration suite + 12-test self-test suite

### Fixed
- 7 critical bugs found by sparring agents
- 3 assertion type mismatches
- 2 crash bugs, clarity false positives

## [2.3.0] - 2026-03-19

### Added
- Bidirectional synonym expansion, plateau guard, interaction effect detection

## [2.0.0] - 2026-03-18

### Added
- TF-IDF trigger scoring, composability analysis, 9-phase protocol
- Discovery mode, parallel experimentation, noisy metric handling

## [1.0.0] - 2026-03-17

### Added
- Initial release — 6-dimension scoring, eval runner, progress tracking
