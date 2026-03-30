# Schliff v8.0 — Final Implementation Plan (Post-Review)

> Incorporates 48 findings from 7 Opus review agents: Architecture, Testing, DevOps, Prompts, Timeline, Market, Security.

**Goal:** Transform Schliff into the universal AI instruction quality standard.

**Execution model:** Multiple parallel Claude Code sessions in git worktrees. Subagents within each session for file-level parallelism.

**Timeline:** 4-5 weeks (compressed from 10 based on proven v7.0/v7.1 throughput)

**Spec:** `docs/specs/2026-03-28-v8-design.md`
**Prompts:** `docs/specs/plans/v8-session-prompts.md` (Phases 0, 1a, 1b complete; 1c, 2, 3a-c pending)
**Previous plan:** `docs/specs/plans/2026-03-28-v8-master-plan.md` (superseded by this file)

---

## Critical Corrections from Reviews

### Architecture Fixes (from Architect Review)

| # | Finding | Fix |
|---|---------|-----|
| A1 | `score_security()` exists but is NOT wired into `build_scores()` or `composite.py` | Phase 1a must wire it in. Accept score changes. Update golden test fixtures. |
| A2 | Weight format mismatch: plan says `int 15`, code uses `float 0.15` | Registry uses floats matching existing code. NO format change. |
| A3 | `clarity` is dynamically injected, not in weight dict | Registry includes clarity explicitly. Remove dynamic injection. |
| A4 | `runtime` dimension has weight 0.10 in code but missing from registry | Add runtime to registry as opt-in (matches existing behavior). |
| A5 | `build_scores()` is normalize-then-score, not dispatch-different-scorers | Phase 1a: add a dispatch branch for new formats. Keep normalize path for existing formats. |
| A6 | `patterns.py` file must be DELETED, not coexist with `patterns/` directory | Phase 1a: `git rm patterns.py`, create `patterns/` dir with `__init__.py` re-exporting all names. |
| A7 | `text_gradient.py` has hardcoded `DIM_WEIGHTS` | Phase 1a: add to MODIFY list. Import weights from registry. |
| A8 | `auto-improve.py` not in any MODIFY list, may break | Phase 1a: verify it still works after refactor. Add to test checklist. |

### Test Fixes (from Test Engineer Review)

| # | Finding | Fix |
|---|---------|-----|
| T1 | Tests live in `tests/unit/`, not `tests/` | All new tests go to `skills/schliff/tests/unit/` |
| T2 | `conftest.py` with `sys.path` hack only exists in `tests/unit/` | New tests MUST be in `tests/unit/` or a parent conftest must be created |
| T3 | Format detection ambiguity untested | Add tests: SKILL.md without frontmatter + "you are" must stay skill.md (filename precedence) |
| T4 | Float comparison inconsistent | Use `pytest.approx(expected, abs=0.1)` for all score assertions |
| T5 | No pytest markers defined | Phase 1a: add `[tool.pytest.ini_options]` to pyproject.toml with `testpaths` and markers |
| T6 | LLM mock strategy undefined | Phase 2: `llm.py` must accept a `completion_fn` parameter for dependency injection |
| T7 | No lazy-import enforcement test | Phase 2: add test that `import scoring` does NOT import `litellm` |

### DevOps Fixes (from DevOps Review)

| # | Finding | Fix |
|---|---------|-----|
| D1 | Phase 1b + 1c modify same files → merge conflicts | Run 1b THEN 1c sequentially, NOT parallel. 1c rebases on main after 1b merges. |
| D2 | Phase 2 modifies cli.py parallel to 1b/1c | Phase 2 must rebase on main after 1b+1c merge before creating PR. |
| D3 | Squash merge destroys commit history | Use merge commits (`gh pr merge --merge`) for large phases (1b, 2). Squash for small ones. |
| D4 | CI has no Python matrix or optional-dep testing | Phase 1a: update test.yml with Python 3.9+3.12 matrix and `[evolve]`/`[mcp]` extra jobs. |
| D5 | pyproject.toml as merge bottleneck | Phase 1a: scaffold empty `[project.optional-dependencies]` section. |
| D6 | Phase 0 commits directly to main (violates "never push to main" rule) | Phase 0 gets its own branch: `schliff-v8/phase-0-launch-prep` |
| D7 | No rebase steps documented | Explicit rebase checkpoints added to Wave transitions. |
| D8 | Worktree paths pollute home directory | Use `~/dev/schliff-worktrees/` instead of `../schliff-phase-X` |

### Security Fixes (from Security Review)

| # | Finding | Fix |
|---|---------|-----|
| S1 | Secrets in lineage snapshots (CRITICAL) | Phase 2: add `evolve/sanitize.py` with secret-pattern scanning + `--no-snapshots` flag |
| S2 | API keys in error messages/stack traces | Phase 2: key-sanitizer in `llm.py`, top-level exception handler in `cmd_evolve` |
| S3 | Path traversal in MCP server | Phase 3b: `os.path.realpath()` + `startswith(cwd)` check on all path inputs |
| S4 | LLM-injected malicious content | Phase 2: security scorer MUST run on every evolved output, drop > 0 = reject |
| S5 | Supply chain risk via pip install | Phase 3a: version pinning in action.yml, 2FA on PyPI, document hash verification |
| S6 | Secret leakage in PR comments | Phase 3a: PR comments show only dimension names + scores, never raw file content |
| S7 | LiteLLM transitive dependencies | Phase 2: upper-bound pin `litellm>=1.40.0,<2.0.0`, `pip-audit` in CI |
| S8 | MCP server DoS via large input | Phase 3b: max 1MB text input, consistent with existing `MAX_SKILL_SIZE` |
| S9 | ReDoS in new regex patterns | Phase 1b/1c: test all new patterns against `"a" * 10000` |
| S10 | Lineage directory permissions | Phase 2: create `~/.schliff/lineage/` with `chmod 700` |

### Prompt Fixes (from Prompt Review)

| # | Finding | Fix |
|---|---------|-----|
| P1 | 5 of 8 phases have NO subagent prompts | Must be written before execution. Phases 1c, 2, 3a, 3b, 3c need full prompts. |
| P2 | Phase 1c has no detail spec for regex patterns | Must write `docs/specs/mcp-tool-scoring-spec.md` before Phase 1c starts. |
| P3 | Phase 0 Subagent 1 says "WRITE task" for README (should be EDIT) | Fix in prompts file. |
| P4 | Phase 1b QA has no commit message | Add: "fix: resolve QA findings in system prompt scoring" |
| P5 | Lazy-import pattern not explained in Phase 2 prompts | Must be explicit in Impl B prompt. |

### Timeline Fixes (from PM Review)

| # | Finding | Fix |
|---|---------|-----|
| TL1 | 10 weeks is 2.5-3x too long | Compress to 4-5 weeks. |
| TL2 | Phase 0 can be done in 2-3 hours, not 2 weeks | Compress to 1 day. |
| TL3 | Phase 3a (GitHub Action) can start earlier | Start parallel to Wave 2 (separate repo, no code deps). |
| TL4 | Wave 3 is unnecessary | Phase 2 continues from Wave 2, no separate wave. |

### Market Fixes (from DevRel Review)

| # | Finding | Fix |
|---|---------|-----|
| M1 | v7.1 is already stronger than all competitors — launch NOW | Two-phase launch: v7.2 soft launch (Week 1), v8.0 major launch (Week 5). |
| M2 | Social sharing feature missing | Add `schliff report --share` to Phase 0 or Phase 3c. |
| M3 | "State of AI Instructions" report is critical path for launch | Automate with `schliff score --url` + GitHub Code Search. 50 files minimum. |

---

## Backup Strategy

### Before ANY Code Changes

```bash
# 1. Tag the current state
cd /Users/franzpaul/schliff
git tag v7.1.0-pre-v8-baseline

# 2. Create a full backup branch
git branch backup/v7.1.0-complete

# 3. Export current test output as golden file
pytest skills/schliff/tests/ -v --tb=short > docs/golden/v7.1.0-test-output.txt

# 4. Record scores for regression comparison
schliff score skills/schliff/SKILL.md --json > docs/golden/v7.1.0-skill-score.json
schliff score --format claude.md CLAUDE.md --json > docs/golden/v7.1.0-claude-score.json 2>/dev/null || true

# 5. Verify backup
git log --oneline backup/v7.1.0-complete -1
git tag -l v7.1.0-pre-v8-baseline
```

### Per-Phase Safety

```bash
# Before each phase starts: verify main is clean
git status  # must be clean
pytest skills/schliff/tests/ -v  # must pass

# Before each merge: verify no regression
schliff score skills/schliff/SKILL.md --json | diff - docs/golden/v7.1.0-skill-score.json
# (for phases that should NOT change existing scores)
```

### Recovery

```bash
# If a phase goes wrong: abandon worktree, main is untouched
git worktree remove ~/dev/schliff-worktrees/phase-X --force
git branch -D schliff-v8/phase-X

# If main is broken: restore from backup
git reset --hard backup/v7.1.0-complete
```

---

## Updated Worktree Setup

```bash
# Create dedicated worktree directory
mkdir -p ~/dev/schliff-worktrees

# Worktree pattern (example for Phase 1a):
cd /Users/franzpaul/schliff
git worktree add ~/dev/schliff-worktrees/phase-1a -b schliff-v8/phase-1a-scorer-registry
cd ~/dev/schliff-worktrees/phase-1a
claude

# Cleanup pattern:
git worktree remove ~/dev/schliff-worktrees/phase-1a
git worktree prune  # always run after remove
```

---

## Revised Timeline: 4-5 Weeks

### Two-Phase Launch Strategy

```
v7.2 SOFT LAUNCH (Week 1):
  README restructure + State of AI report + Show HN with EXISTING features
  → Establishes market position immediately

v8.0 MAJOR LAUNCH (Week 4-5):
  System Prompt Scoring + Evolution Engine + MCP Tool Scoring
  → "Major Update" announcement wave
```

### Week-by-Week

```
WEEK 1 (2 sessions, 1 day each):
  Day 1: Session A — Phase 0 (Launch Prep: README, Report, Drafts)
         Session B — Phase 1a (Scorer Registry refactor)
  Day 2: Phase 1a continues + QA
  Day 3: Phase 1a merge → v7.2 Soft Launch (Show HN + Social)

WEEK 2 (3 sessions):
  Session A — Phase 1b (System Prompt Scoring)
  Session B — Phase 2 (Evolution Engine starts)
  Session C — Phase 3a (GitHub Action, separate repo)

WEEK 3:
  Phase 1b merge → Phase 1c starts (MCP Tool Scoring, rebased on main)
  Phase 2 continues
  Phase 3a continues

WEEK 4:
  Phase 1c merge
  Phase 2 → rebase on main → finalize + merge
  Phase 3b + 3c start (MCP Server + Badges)

WEEK 5:
  Phase 3b + 3c merge
  v8.0 Release + Major Launch (second announcement wave)
```

### Merge Order (Sequential, No Conflicts)

```
1. Phase 0 → main (docs only, no conflicts)
2. Phase 1a → main (CRITICAL PATH, registry refactor)
3. Phase 1b → main (system prompt scoring)
   ↓ Phase 1c REBASES on main here
4. Phase 1c → main (MCP tool scoring)
   ↓ Phase 2 REBASES on main here
5. Phase 2 → main (evolution engine)
6. Phase 3a → separate repo (GitHub Action)
7. Phase 3b → main (MCP server)
8. Phase 3c → main (badges)
```

---

## Phase 0: Launch Prep + v7.2 Soft Launch

**Duration:** 1 day (2-3 hours actual work)
**Branch:** `schliff-v8/phase-0-launch-prep` (NOT direct to main)
**Sessions:** 1 terminal

### Subagent Tasks (6 parallel)

1. README restructure → `README.md`
2. Show HN draft → `docs/launch/show-hn-draft.md`
3. Twitter thread → `docs/launch/twitter-thread.md`
4. Reddit posts → `docs/launch/reddit-posts.md`
5. Awesome-list PRs → `docs/launch/awesome-list-prs.md`
6. State of AI Instructions skeleton → `docs/launch/state-of-ai-instructions.md`

**After merge:** Score 50+ public skills with `schliff score --url`, fill report, then LAUNCH.

### v7.2 Soft Launch Checklist

- [ ] README restructured and merged
- [ ] 50+ public skills scored, report filled with real data
- [ ] Show HN posted (Tuesday 08:30 ET)
- [ ] Twitter thread posted (same day)
- [ ] r/ClaudeAI posted (+2 hours)
- [ ] r/Python posted (next day)

---

## Phase 1a: Scorer Registry + Patterns Split (CRITICAL PATH)

**Duration:** 1-2 days
**Branch:** `schliff-v8/phase-1a-scorer-registry`
**Worktree:** `~/dev/schliff-worktrees/phase-1a`

### Corrected Scope (from Architecture Review)

This phase is larger than originally planned. It must:

1. **DELETE** `scoring/patterns.py`, CREATE `scoring/patterns/` directory
2. Create `scoring/registry.py` with **float** weights (matching existing code)
3. Include `clarity` as explicit weight (remove dynamic injection from composite.py)
4. Include `runtime` as opt-in entry
5. Wire `score_security()` into `build_scores()` (currently orphaned)
6. Update `text_gradient.py` to import weights from registry
7. Scaffold empty `[project.optional-dependencies]` in pyproject.toml
8. Add `[tool.pytest.ini_options]` with `testpaths` and markers
9. Update `test.yml` CI with Python matrix

### File Map (Corrected)

```
DELETE:
  skills/schliff/scripts/scoring/patterns.py      # REPLACED by directory

CREATE:
  skills/schliff/scripts/scoring/registry.py
  skills/schliff/scripts/scoring/patterns/__init__.py   # re-exports all names
  skills/schliff/scripts/scoring/patterns/base.py
  skills/schliff/scripts/scoring/patterns/skill_md.py
  skills/schliff/tests/unit/test_registry.py
  skills/schliff/tests/unit/test_patterns_split.py
  docs/golden/v7.1.0-skill-score.json             # regression snapshot

MODIFY:
  skills/schliff/scripts/shared.py                 # build_scores() dispatch branch for new formats
  skills/schliff/scripts/scoring/composite.py      # explicit clarity weight, registry integration
  skills/schliff/scripts/cli.py                    # --format choices from registry
  skills/schliff/scripts/text_gradient.py           # import weights from registry
  pyproject.toml                                   # optional-deps scaffold, pytest config
  .github/workflows/test.yml                       # Python matrix

VERIFY (no changes, must produce identical scores):
  skills/schliff/scripts/scoring/structure.py
  skills/schliff/scripts/scoring/triggers.py
  skills/schliff/scripts/scoring/quality.py
  skills/schliff/scripts/scoring/edges.py
  skills/schliff/scripts/scoring/efficiency.py
  skills/schliff/scripts/scoring/composability.py
  skills/schliff/scripts/scoring/clarity.py
  skills/schliff/scripts/scoring/security.py
  skills/schliff/scripts/auto-improve.py           # verify still works
```

### Regression Strategy

```bash
# BEFORE starting Phase 1a:
schliff score skills/schliff/SKILL.md --json > /tmp/pre-1a-score.json

# AFTER Phase 1a complete:
schliff score skills/schliff/SKILL.md --json > /tmp/post-1a-score.json
diff /tmp/pre-1a-score.json /tmp/post-1a-score.json
# MUST be identical (security dimension was already 0/unmeasured, now it's measured but composite shouldn't change if security weight was 0 in composite)
```

**Decision: Security wiring.**
Option A: Wire security into composite with weight 0.08 → changes ALL scores → update all golden fixtures.
Option B: Wire security as opt-in only (current `--security` flag behavior) → no score change → easier regression.
**Recommendation: Option B for Phase 1a. Option A in Phase 1a.5 (separate commit, separate test update).**

### Merge Criteria

- [ ] All 732+ tests pass
- [ ] New registry + patterns tests pass
- [ ] `schliff score SKILL.md` → identical composite score to pre-refactor
- [ ] `ruff check skills/schliff/` passes
- [ ] `auto-improve.py` still works (manual check)
- [ ] CI updated with Python matrix
- [ ] PR: `gh pr create --base main --head schliff-v8/phase-1a-scorer-registry`

---

## Phase 1b: System Prompt Scoring

**Duration:** 2-3 days
**Branch:** `schliff-v8/phase-1b-system-prompt-scoring`
**Worktree:** `~/dev/schliff-worktrees/phase-1b`
**Prerequisite:** Phase 1a merged to main
**Detail Spec:** `docs/specs/system-prompt-scoring-spec.md` (exists, written by subagent)

### Corrected File Map

```
CREATE:
  skills/schliff/scripts/scoring/structure_prompt.py
  skills/schliff/scripts/scoring/output_contract.py
  skills/schliff/scripts/scoring/completeness.py
  skills/schliff/scripts/scoring/patterns/system_prompt.py
  skills/schliff/tests/unit/test_system_prompt_scoring.py    # NOTE: tests/unit/, not tests/
  skills/schliff/tests/unit/fixtures/system_prompts/good_api_assistant.txt
  skills/schliff/tests/unit/fixtures/system_prompts/mediocre_chatbot.txt
  skills/schliff/tests/unit/fixtures/system_prompts/bad_minimal.txt
  skills/schliff/tests/unit/fixtures/system_prompts/xml_tags_prompt.txt  # Anthropic-style
  skills/schliff/tests/unit/fixtures/system_prompts/looks_like_skill.txt  # format detection edge case

MODIFY:
  skills/schliff/scripts/scoring/registry.py
  skills/schliff/scripts/scoring/formats.py
  skills/schliff/scripts/scoring/patterns/__init__.py
  skills/schliff/scripts/shared.py
  skills/schliff/scripts/scoring/composite.py
```

### Security Requirements

- [ ] All new regex patterns tested against `"a" * 10000` (ReDoS check)
- [ ] Format detection: filename takes precedence over content heuristics
- [ ] Test: SKILL.md containing "you are" is NOT misdetected as system_prompt

### Merge: `gh pr merge --merge` (preserve commit history for large phase)

---

## Phase 1c: MCP Tool Description Scoring

**Duration:** 1-2 days
**Branch:** `schliff-v8/phase-1c-mcp-tool-scoring`
**Worktree:** `~/dev/schliff-worktrees/phase-1c`
**Prerequisite:** Phase 1b merged to main, then `git rebase origin/main`
**Detail Spec:** `docs/specs/mcp-tool-scoring-spec.md` (MUST BE WRITTEN before Phase 1c starts)

### Pre-Phase Task: Write MCP Tool Scoring Spec

Before Phase 1c can start, create `docs/specs/mcp-tool-scoring-spec.md` with concrete regex patterns for all 6 dimensions (analogous to `system-prompt-scoring-spec.md`). This can be done as a subagent task during Phase 1b.

### Security Requirements

- [ ] `json.loads()` wrapped in try/except → score 0 with issue "schema_quality:invalid_json"
- [ ] All regex patterns ReDoS-tested

---

## Phase 2: Evolution Engine

**Duration:** 3-5 days
**Branch:** `schliff-v8/phase-2-evolution-engine`
**Worktree:** `~/dev/schliff-worktrees/phase-2`
**Prerequisite:** Phase 1a merged (starts in Week 2, rebases after 1b+1c merge in Week 3-4)
**Spec reference:** Design spec Section 4

### Corrected File Map (with Security additions)

```
CREATE:
  skills/schliff/scripts/evolve/__init__.py
  skills/schliff/scripts/evolve/engine.py
  skills/schliff/scripts/evolve/llm.py              # accepts completion_fn for DI/testing
  skills/schliff/scripts/evolve/prompts.py
  skills/schliff/scripts/evolve/guard.py             # includes security-specific guard
  skills/schliff/scripts/evolve/budget.py
  skills/schliff/scripts/evolve/plateau.py
  skills/schliff/scripts/evolve/lineage.py
  skills/schliff/scripts/evolve/content.py
  skills/schliff/scripts/evolve/sanitize.py          # NEW: key redaction, secret scanning
  skills/schliff/tests/unit/test_evolve_guard.py
  skills/schliff/tests/unit/test_evolve_budget.py
  skills/schliff/tests/unit/test_evolve_plateau.py
  skills/schliff/tests/unit/test_evolve_lineage.py
  skills/schliff/tests/unit/test_evolve_engine.py
  skills/schliff/tests/unit/test_evolve_prompts.py
  skills/schliff/tests/unit/test_evolve_sanitize.py  # NEW: secret scanning tests
  skills/schliff/tests/unit/test_evolve_lazy_import.py  # NEW: verify litellm not imported by default

MODIFY:
  skills/schliff/scripts/cli.py
  pyproject.toml                                     # evolve = ["litellm>=1.40.0,<2.0.0"]
```

### Security Requirements (from Security Review)

- [ ] `sanitize.py`: redact patterns `sk-ant-*`, `sk-*`, `AKIA*`, `postgres://`, etc. from all output
- [ ] `llm.py`: top-level exception handler, never expose raw tracebacks with locals
- [ ] `llm.py`: `completion_fn` parameter for dependency injection (testability)
- [ ] `guard.py`: security dimension drop > 0 = REJECT (stricter than generic 3.0 threshold)
- [ ] `lineage.py`: create `~/.schliff/lineage/` with `chmod 700`
- [ ] `lineage.py`: `--no-snapshots` flag for sensitive files
- [ ] `lineage.py`: warn if content contains secret-like patterns
- [ ] `test_evolve_lazy_import.py`: verify `import scoring` does NOT import `litellm`
- [ ] LiteLLM pinned with upper bound: `litellm>=1.40.0,<2.0.0`

### Rebase Checkpoint

```bash
# After Phase 1b + 1c are merged to main:
cd ~/dev/schliff-worktrees/phase-2
git fetch origin main
git rebase origin/main
# Resolve any conflicts in shared.py, composite.py, cli.py
# Then continue development
```

---

## Phase 3a: GitHub Action

**Duration:** 1 day
**Location:** New repo `Zandereins/schliff-action`
**Can start:** Week 2 (parallel to 1b, no code dependency on v8)

### Security Requirements

- [ ] Default `version` input pinned to specific version, NOT `latest`
- [ ] PR comments: ONLY scores, grades, deltas, generic issue categories — NEVER raw file content
- [ ] README warns: "Never use `pull_request_target`"
- [ ] Permissions documented: `pull-requests: write` only, `contents: write` only if badge gist needed
- [ ] `<!-- schliff-report -->` marker for comment updates (no duplicate comments)

---

## Phase 3b: MCP Server

**Duration:** 1-2 days
**Branch:** `schliff-v8/phase-3b-mcp-server`
**Worktree:** `~/dev/schliff-worktrees/phase-3b`
**Prerequisite:** Phase 2 merged

### Security Requirements

- [ ] All path inputs validated: `os.path.realpath(path)` must `startswith(allowed_root)`
- [ ] `allowed_root` = `os.getcwd()` by default, configurable via env var
- [ ] Inline text input: max 1MB (consistent with `MAX_SKILL_SIZE`)
- [ ] Tool outputs: never echo raw user input in issues/suggestions
- [ ] MCP dependency pinned: `mcp>=1.0.0,<2.0.0`

---

## Phase 3c: Registry & Badges

**Duration:** 1 day
**Branch:** `schliff-v8/phase-3c-registry-badges`
**Worktree:** `~/dev/schliff-worktrees/phase-3c`

Focus: Phase 1 only (badges, $0 infrastructure). No security-critical components.

---

## Bug Prevention Checklist

### Per-Commit

- [ ] `ruff check skills/schliff/` passes
- [ ] `pytest skills/schliff/tests/ -v` passes (ALL tests, not just new ones)

### Per-Phase (before PR)

- [ ] Golden score comparison: `schliff score SKILL.md --json` matches baseline
- [ ] All 732+ pre-existing tests pass (zero regression)
- [ ] All new tests pass
- [ ] No `TODO`, `FIXME`, or placeholder code in new files
- [ ] No hardcoded paths, keys, or credentials
- [ ] All new regex patterns tested against pathological input (`"a" * 10000`)
- [ ] Import structure verified: `python -c "from scoring.patterns import _RE_FRONTMATTER_NAME"` works

### Per-Wave (before starting next wave)

- [ ] `git worktree prune` — clean up stale references
- [ ] `git worktree list` — verify only expected worktrees active
- [ ] Main branch tests pass: `cd /Users/franzpaul/schliff && pytest skills/schliff/tests/ -v`

### Pre-Release (v8.0)

- [ ] Full test suite on Python 3.9 AND 3.12
- [ ] `pip install schliff` from clean venv → `schliff demo` works
- [ ] `pip install schliff[evolve]` → `schliff evolve --budget 0 SKILL.md` works
- [ ] `pip install schliff[mcp]` → `schliff-mcp` starts without error
- [ ] `pip-audit` on all extras — no known vulnerabilities
- [ ] Self-score: `schliff score skills/schliff/SKILL.md` → S grade maintained
- [ ] Version bumped in pyproject.toml
- [ ] CHANGELOG updated
- [ ] Demo GIF re-recorded with v8 features

---

## Open Items Before Execution

| # | Item | Owner | Blocks |
|---|------|-------|--------|
| 1 | Write subagent prompts for Phases 1c, 2, 3a, 3b, 3c | Next session | Phase 1c, 2, 3a-c |
| 2 | Write `docs/specs/mcp-tool-scoring-spec.md` | During Phase 1b | Phase 1c |
| 3 | Score 50+ public skills for "State of AI Instructions" report | Phase 0 | v7.2 Launch |
| 4 | Register domain `schliff.dev` | Franz | Phase 3c (badges) |
| 5 | Verify 2FA active on PyPI account | Franz | Phase 3a (security) |
| 6 | Create `~/dev/schliff-worktrees/` directory | Franz | All phases |
