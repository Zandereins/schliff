# Hydra Findings Fix — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** Fix all validated Hydra findings: Evolution Engine hardening (F4a/F4b/F4c + budget pricing), Registry unification (F2 + composite alignment), Dead code cleanup (F3 + performance).

**Architecture:** Three independent worktrees targeting non-overlapping file sets. Merge order: WT1 (evolve/) → WT3 (dead files) → WT2 (scoring/ + shared.py). F1 (sys.path) deferred — too invasive for parallel work, needs its own branch.

**Tech Stack:** Python 3.9+ stdlib, pytest, no new dependencies.

---

## Worktree 1: Evolution Engine Hardening

**Branch:** `fix/evolve-hardening`
**Files:** `evolve/llm.py`, `evolve/plateau.py`, `evolve/budget.py`, `evolve/engine.py`
**Tests:** `tests/unit/test_evolve_llm.py`, `tests/unit/test_evolve_plateau.py`, `tests/unit/test_evolve_budget.py`, `tests/unit/test_evolve_engine.py`

### Task 1.1: LLM Retry with Exponential Backoff (F4a)

- [ ] Write failing tests in `test_evolve_llm.py`:
  - `test_retry_on_transient_error`: completion_fn raises on first call, succeeds on second → returns result
  - `test_retry_exhausted_raises`: completion_fn raises 3 times → SystemExit
  - `test_no_retry_on_keyboard_interrupt`: KeyboardInterrupt propagates immediately
  - `test_timeout_parameter_passed`: verify litellm.completion gets timeout kwarg

- [ ] Implement retry in `evolve/llm.py:call_llm()`:
  - Add `max_retries=3` parameter
  - Wrap litellm.completion in retry loop with delays [1, 2, 4] seconds
  - Only retry on Exception (not KeyboardInterrupt/SystemExit)
  - Add `timeout=120` to litellm.completion call
  - SystemExit only after all retries exhausted

- [ ] Run full test suite, commit

### Task 1.2: Plateau Tracks Rejections (F4b)

- [ ] Write failing tests in `test_evolve_plateau.py`:
  - `test_record_rejection_increments_counter`: after N rejections, `consecutive_rejections` == N
  - `test_rejection_threshold_triggers_plateau`: 10 consecutive rejections → is_plateau
  - `test_acceptance_resets_rejection_counter`: rejection streak broken by acceptance
  - `test_rejection_plateau_uses_escape_sequence`: same strategy_switch → temp_bump → stop

- [ ] Add `record_rejection()` method to `PlateauDetector`:
  - Increment `consecutive_rejections` counter
  - If >= `max_consecutive_rejections` (default 10): set `stale_count = window` (force plateau)
  - Acceptance resets `consecutive_rejections = 0`

- [ ] Wire into `evolve/engine.py`: call `plateau.record_rejection()` at lines 301, 325, 336 (all rejection paths)

- [ ] Run full test suite, commit

### Task 1.3: Improved Token Estimation (F4c)

- [ ] Write test in `test_evolve_budget.py`:
  - `test_estimate_tokens_uses_prompt_length`: verify estimation accounts for prompt overhead

- [ ] In `evolve/engine.py`, move token estimation AFTER prompt construction (line ~264→~290):
  ```python
  estimated = int((len(user_prompt.split()) + len(best_content.split())) * 1.3 + 800)
  ```

- [ ] Run full test suite, commit

### Task 1.4: Dynamic Model Pricing (Volta Finding)

- [ ] Write tests in `test_evolve_budget.py`:
  - `test_cost_estimate_with_model_pricing`: different models produce different costs
  - `test_cost_estimate_default_sonnet`: backward-compat with current behavior

- [ ] Add `MODEL_PRICING` dict to `evolve/budget.py`:
  ```python
  MODEL_PRICING = {
      "anthropic/claude-sonnet-4-20250514": (3.0, 15.0),
      "anthropic/claude-opus-4-20250514": (15.0, 75.0),
      "anthropic/claude-haiku-4-5-20251001": (0.80, 4.0),
      "openai/gpt-4o": (2.50, 10.0),
      "ollama/llama3": (0.0, 0.0),
  }
  ```
  Update `estimate_cost_usd()` to accept optional `model` param, lookup pricing.

- [ ] Run full test suite, commit

---

## Worktree 2: Registry Unification (F2)

**Branch:** `fix/registry-unification`
**Files:** `shared.py`, `scoring/composite.py`, `scoring/registry.py`
**Tests:** `tests/unit/test_registry.py`, `tests/unit/test_composite_weights.py`, `tests/unit/test_scoring.py`

### Task 2.1: Divergence Tests First

- [ ] Write tests in `test_registry.py` that verify current build_scores/registry/composite alignment:
  - `test_build_scores_keys_match_registry`: for each format, `set(build_scores(path, fmt=fmt).keys())` == `set(get_scorers(fmt))` minus opt-in
  - `test_composite_weights_cover_all_scorers`: for each format, all scorer keys have weights
  - `test_registry_weights_sum_approximately_one`: weights sum within 0.05 of 1.0

- [ ] Run tests — expect FAILURES (proving divergence exists), commit with message documenting divergence

### Task 2.2: Fix Registry Weights to Sum to 1.0

- [ ] Fix `scoring/registry.py` `_INSTRUCTION_FILE_WEIGHTS`: adjust to sum exactly 1.0 (currently 1.03)
  ```python
  _INSTRUCTION_FILE_WEIGHTS = {
      "structure": 0.15, "triggers": 0.20, "quality": 0.20,
      "edges": 0.15, "efficiency": 0.10, "composability": 0.10,
      "clarity": 0.05, "security": 0.05,
  }
  ```

- [ ] Run tests, commit

### Task 2.3: Migrate build_scores() to Use Registry

- [ ] Refactor `shared.py:build_scores()` to use `get_scorers(fmt)`:
  - Import `get_scorers` from registry
  - Build scorer function mapping: `SCORER_FUNCTIONS = {"structure": ("scoring.structure", "score_structure"), ...}`
  - Loop over `get_scorers(fmt)`, dynamically call each scorer
  - Handle eval_suite parameter for scorers that need it (triggers, quality, edges)
  - Preserve include_security/include_runtime opt-in logic

- [ ] Run full test suite including golden tests, commit

### Task 2.4: Remove Composite Fallback Weights

- [ ] In `scoring/composite.py:compute_composite()`, remove the `fmt is None` fallback weight dict (lines 71-79)
  - When `fmt is None`, default to `get_weights("skill.md")` instead of hardcoded dict
  - Remove dynamic clarity injection (line 106-114) — clarity is already explicit in registry

- [ ] Run full test suite, commit

### Task 2.5: Verify compute_composite Key Alignment (Reviewer-1 Finding)

- [ ] Write test: `test_system_prompt_keys_match_composite`:
  - Score a system prompt file with `build_scores(path, fmt="system_prompt")`
  - Pass result to `compute_composite(scores, fmt="system_prompt")`
  - Verify all scored dimensions have weights and contribute to composite

- [ ] Run full test suite, commit

---

## Worktree 3: Hygiene & Performance

**Branch:** `fix/dead-code-cleanup`
**Files:** Remove 6 files, edit `shared.py`
**Tests:** Verify existing 998 tests still pass

### Task 3.1: Remove Dead Hyphen Shim Files (F3)

- [ ] Delete 5 hyphen shim files (25 lines total):
  - `skills/schliff/scripts/episodic-store.py`
  - `skills/schliff/scripts/meta-report.py`
  - `skills/schliff/scripts/parallel-runner.py`
  - `skills/schliff/scripts/skill-mesh.py`
  - `skills/schliff/scripts/text-gradient.py`

- [ ] Delete superseded `skills/schliff/scripts/score-skill.py` (186 lines)

- [ ] Run full test suite to verify nothing breaks, commit

### Task 3.2: Hoist re.compile() to Module Level (Performance)

- [ ] In `shared.py`, move 3 regex patterns from inside `validate_regex_complexity()` to module level:
  ```python
  # Module level (after other re.compile calls)
  _RE_NESTED_QUANT = re.compile(r'[+*]\)?[+*?{]')
  _RE_OVERLAP_QUANT = re.compile(r'\((?!\?:)[^)]*\|[^)]*\)[+*]{1,2}')
  _RE_GROUP_INNER_QUANT = re.compile(r'\([^)]*[.][*+][^)]*\)[+*?{]')
  ```
  Update function body to reference module-level names.

- [ ] Run full test suite, commit

---

## Merge Order

1. Merge `fix/evolve-hardening` → main (no conflicts, only touches evolve/)
2. Merge `fix/dead-code-cleanup` → main (no conflicts, only deletes files + edits shared.py regex)
3. Merge `fix/registry-unification` → main (touches shared.py + scoring/, may need rebase after WT3)

## Deferred

- **F1 (sys.path hacks):** Too invasive for parallel work. Needs its own branch after all merges.
- **F5 (Claude Code hooks):** hooks.json format issue requires Claude Code runtime verification.
