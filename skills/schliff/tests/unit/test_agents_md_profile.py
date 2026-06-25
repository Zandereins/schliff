"""Golden + regression tests for the AGENTS.md scoring profile.

Spec: docs/specs/agents-md-scoring-profile.md.

AGENTS.md is project context for coding agents, not a reusable skill. Its
headline composite is therefore computed over {structure, efficiency} only
(0.5/0.5), with the eval-gated dims (triggers/quality/edges) plus the
mis-fit composability and the saturated clarity excluded from the headline
denominator. These tests pin that profile and guard the other four formats
against regression (byte-identity).

Corpus golden values were established empirically over the 30 real public
AGENTS.md files in docs/launch/corpus/agents/ and are reproducible because
the profile is deterministic (no LLM, no calibration).
"""
from __future__ import annotations

import statistics
from collections import Counter
from pathlib import Path

import pytest
import text_gradient
from terminal_art import score_to_grade

from scoring import compute_composite
from scoring.registry import (
    _INSTRUCTION_FILE_WEIGHTS,
    WEIGHT_PROFILES,
    get_headline_excluded,
    get_weights,
)
from shared import build_scores

_CORPUS = Path(__file__).resolve().parents[4] / "docs" / "launch" / "corpus" / "agents"

_GOOD_AGENTS_MD = """# AGENTS.md

This file gives coding agents the context they need to work in this repository.

## Project overview

`acme-api` is a Python FastAPI service for order management. Source lives in
`src/acme_api/`, tests in `tests/`.

## Setup

```bash
uv sync --all-extras
cp .env.example .env
```

## Build and test

Always run the full check before proposing a change:

```bash
uv run ruff check .
uv run pytest -q
```

A change is not done until `ruff` and `pytest` both pass.

## Code style

- Python 3.11+, type-hint every public function.
- Prefer stdlib; justify any new dependency in the PR description.

## Pull requests

- Title format: `feat:`, `fix:`, `chore:` (Conventional Commits).
- Every PR must update or add tests for the changed behavior.

## Gotchas

- The `orders` table uses soft-deletes — filter `deleted_at IS NULL`.
- Migrations are applied automatically in CI; never edit a shipped migration.
"""


def _write(tmp_path: Path, content: str, name: str = "AGENTS.md") -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def _score_agents(path: str) -> dict:
    scores = build_scores(path, None, include_runtime=True, fmt="agents.md")
    return compute_composite(scores, fmt="agents.md", use_calibrated=False)


# --- Profile registry shape -------------------------------------------------

def test_agents_md_weight_profile_is_structure_efficiency_5050():
    assert WEIGHT_PROFILES["agents.md"] == {"structure": 0.5, "efficiency": 0.5}


def test_agents_md_headline_excludes_eval_gated_plus_composability_clarity():
    assert get_headline_excluded("agents.md") == frozenset(
        {"security", "runtime", "triggers", "quality", "edges", "composability", "clarity"}
    )


def test_other_formats_unchanged_byte_identity():
    # The other four formats must keep the shared instruction weights + {security,runtime}.
    for fmt in ("skill.md", "claude.md", "cursorrules"):
        assert get_weights(fmt) == _INSTRUCTION_FILE_WEIGHTS
        assert get_headline_excluded(fmt) == frozenset({"security", "runtime"})


# --- Headline behavior ------------------------------------------------------

def test_well_formed_agents_md_no_eval_warning_two_dim(tmp_path):
    path = _write(tmp_path, _GOOD_AGENTS_MD)
    scores = build_scores(path, None, include_runtime=True, fmt="agents.md")
    result = compute_composite(scores, fmt="agents.md", use_calibrated=False)

    # No SKILL-only eval-suite warning, no cap.
    assert not any("eval suite" in w for w in result["warnings"])
    # Headline is over exactly the two kept dims.
    assert result["measured_dimensions"] == 2
    assert result["total_dimensions"] == 2
    # Score == 0.5*structure + 0.5*efficiency.
    expected = 0.5 * scores["structure"]["score"] + 0.5 * scores["efficiency"]["score"]
    assert result["score"] == pytest.approx(round(expected, 1))
    assert score_to_grade(result["score"]) in {"S", "A", "B", "C", "D", "E", "F"}


# --- Fix-path: suggest/evolve must not emit SKILL-only advice ----------------

def test_compute_gradients_agents_md_emits_no_skill_only_advice(tmp_path):
    path = _write(tmp_path, _GOOD_AGENTS_MD)
    gradients = text_gradient.compute_gradients(path, None, include_clarity=True, fmt="agents.md")

    # No gradient from a SKILL-only dimension.
    skill_only_dims = {"triggers", "quality", "edges", "composability", "clarity"}
    offending = [g for g in gradients if g["dimension"] in skill_only_dims]
    assert offending == [], f"AGENTS.md fix-path leaked SKILL-only dimension: {offending}"

    # No SKILL-only structure issues (frontmatter family — AGENTS.md uses none).
    skill_only_issues = {"no_frontmatter", "missing_name", "missing_description"}
    leaked = [g for g in gradients if g["issue"] in skill_only_issues]
    assert leaked == [], f"AGENTS.md fix-path leaked frontmatter advice: {leaked}"

    # And no SKILL-only phrasing anywhere in target or instruction text.
    for g in gradients:
        blob = f"{g.get('target', '')} {g.get('instruction', '')}".lower()
        for forbidden in ("frontmatter", "eval-suite", "eval suite", "this skill", "handoff"):
            assert forbidden not in blob, f"AGENTS.md fix-path leaked '{forbidden}': {g}"


# --- Corpus golden distribution --------------------------------------------

@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_agents_md_corpus_golden_distribution():
    rows = []
    for f in sorted(_CORPUS.glob("*.md")):
        result = _score_agents(str(f))
        rows.append((f.name, result["score"], score_to_grade(result["score"]), result["warnings"]))

    scores = [r[1] for r in rows]
    bands = Counter(r[2] for r in rows)

    assert len(rows) == 30
    assert statistics.mean(scores) == pytest.approx(73.90, abs=0.05)
    assert statistics.median(scores) == pytest.approx(77.25, abs=0.05)
    assert min(scores) == pytest.approx(37.5, abs=0.05)
    assert max(scores) == pytest.approx(95.0, abs=0.05)

    # Exact band counts (golden lock). F intentionally 0.
    assert bands["S"] == 2
    assert bands["A"] == 2
    assert bands["B"] == 12
    assert bands["C"] == 7
    assert bands["D"] == 6
    assert bands["E"] == 1
    assert bands["F"] == 0

    # No file emits the SKILL-only eval-suite warning.
    assert not any("eval suite" in w for _, _, _, ws in rows for w in ws)


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_agents_md_boundary_files_are_exactly_S():
    # Off-by-one guard on the score >= threshold comparator: only these two
    # files compute to exactly 95.0 and must grade S.
    for name in ("meltano__meltano__AGENTS.md.md", "maxcountryman__underway__AGENTS.md.md"):
        result = _score_agents(str(_CORPUS / name))
        assert result["score"] == pytest.approx(95.0, abs=0.05)
        assert score_to_grade(result["score"]) == "S"
