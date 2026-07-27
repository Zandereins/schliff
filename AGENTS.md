# Schliff — agent instructions

Deterministic quality scorer for AI instruction files (Python, stdlib-only core,
zero runtime dependencies). The engine lives in `skills/schliff/scripts/`; the
web playground in `playground/`; the GitHub Action in `action.yml`.

## Scope & composition

**Use when** you need to score or improve a `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, or
`.cursorrules`. **Do not use** it on a whole codebase — it grades one instruction
file, not a repo. For a brand-new skill, use skill-creator instead; schliff improves
existing files, it doesn't scaffold new ones.

- **Input:** one instruction-file path. **Output:** a deterministic per-dimension
  score plus a composite (text or `--json`); scoring writes nothing.
- **Idempotent, no side effects** — same input, same score, safe to re-run.
- Requires Python >= 3.10, no other runtime dependency; supported versions 3.10–3.13.

## Setup

```bash
pip install -e .
pip install pytest ruff
```

Optional extras: `pip install -e ".[judge]"` (LLM-judge smoke-test only — core
scoring must stay zero-dependency).

## Build

```bash
pip install build
python -m build
```

Pure-Python wheel; nothing to compile.

## Test

```bash
make test-unit          # pytest unit suite — run this before every commit
make lint               # ruff check skills/schliff/scripts/
make test-all           # unit + integration + self + proof suites
```

A single scorer test file runs fast: `python3 -m pytest skills/schliff/tests/unit/test_operational_coverage.py -q`.

Example: verify a scorer change end-to-end (score a real file with your edit):

```bash
python3 skills/schliff/scripts/cli.py score AGENTS.md --json
```

Expected output: JSON with `composite_score`, per-dimension scores, and
`format: agents.md`. If `operational_coverage` is missing, your registry
wiring is broken — check `SCORER_REGISTRY["agents.md"]`.

## Code style

- Ruff is the authority (`pyproject.toml`: E, F, W, I; line length 120). Run `make lint` before pushing.
- Core engine code (`skills/schliff/scripts/`) is stdlib-only — never add a runtime dependency there, because "pip install schliff, zero deps" is the product promise CI and the README both make.
- Scorers must be deterministic: no `time`, `random`, `os.environ` reads, or network in any scoring path, because same-input-same-score is the core guarantee. Tests pin this (`test_purity_no_forbidden_imports`).
- Prefer explicit error handling; no silent `except: pass` in scoring code.

## Gotchas

- **Never run blanket `ruff --fix`** on existing modules: F401 "unused" imports in `skills/schliff/scripts/` are real re-exports — removing them breaks the CLI (23 tests). Fix only files you authored.
- The version lives in **three lockstep sources** (`pyproject.toml`, `.claude-plugin/plugin.json`, `skills/schliff/__init__.py`), gated by `test_version_consistency.py`. Bump all three together.
- Changing any scorer re-baselines the corpus golden tests (`test_agents_md_profile.py` pins mean/median/band counts on 30 real files). Re-derive the numbers from the engine — never hand-tweak them.
- `playground/public/index.html` has its inline `<script>` pinned by a CSP `sha256-…` hash in `playground/vercel.json`. Any edit to the inline script requires recomputing the hash, or the deployed page breaks silently.
- Playground deploys are manual (`cd playground && vercel --prod`); the committed `playground/uv.lock` is the deploy source of truth. A daily drift workflow asserts live engine == pinned version.

## Pull requests

- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `security:`, `spec:`), present tense, English.
- Never push to `main` — feature branches only; PRs are squash-merged behind branch protection (lint + tests 3.10–3.13 + macOS + CodeQL must be green).
- Non-trivial changes need a spec in `docs/specs/` first; update the spec with what you learned after implementing.
- Before claiming done: run `make test-unit` and `make lint` and show the output.
