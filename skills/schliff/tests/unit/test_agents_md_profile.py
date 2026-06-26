"""Golden + regression tests for the AGENTS.md scoring profile.

Spec: docs/specs/agents-md-operational-coverage.md (supersedes the original
agents-md-scoring-profile.md 0.5/0.5 profile).

AGENTS.md is project context for coding agents, not a reusable skill. Its
headline composite is the 3-dim OPERATIONAL profile:

    0.4 * structure + 0.4 * operational_coverage + 0.2 * efficiency

operational_coverage measures whether the doc actually equips a coding agent
(runnable setup/build/test commands + code-style/PR/gotcha guidance); it
demotes efficiency, a gameable fenced-density proxy. The eval-gated dims
(triggers/quality/edges) plus the mis-fit composability and the saturated
clarity stay excluded from the headline denominator. These tests pin that
profile and guard the other four formats against regression (byte-identity).

Corpus golden values were RE-DERIVED ONCE on the hardened operational_coverage
scorer over the 30 real public AGENTS.md files in docs/launch/corpus/agents/
(spec §6) and are reproducible because the profile is deterministic (no LLM,
no calibration). The anti-gaming / recall / determinism unit tests for opcov
itself live in test_operational_coverage.py.
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
    _INSTRUCTION_FILE_SCORERS,
    _INSTRUCTION_FILE_WEIGHTS,
    WEIGHT_PROFILES,
    get_headline_excluded,
    get_scorers,
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

def test_agents_md_weight_profile_is_three_dim():
    assert WEIGHT_PROFILES["agents.md"] == {
        "structure": 0.4,
        "operational_coverage": 0.4,
        "efficiency": 0.2,
    }


def test_agents_md_headline_excludes_eval_gated_plus_composability_clarity():
    # HEADLINE_EXCLUDED is intentionally UNCHANGED by the opcov work: opcov was
    # never excluded, so it is folded into the headline via the weight profile.
    excluded = get_headline_excluded("agents.md")
    assert excluded == frozenset(
        {"security", "runtime", "triggers", "quality", "edges", "composability", "clarity"}
    )
    assert "operational_coverage" not in excluded


def test_other_formats_unchanged_byte_identity():
    # The other four formats must keep the shared instruction weights + {security,runtime}
    # and must NOT have the agents.md-only operational_coverage dimension.
    for fmt in ("skill.md", "claude.md", "cursorrules"):
        assert get_weights(fmt) == _INSTRUCTION_FILE_WEIGHTS
        assert get_headline_excluded(fmt) == frozenset({"security", "runtime"})
    for fmt in ("skill.md", "claude.md", "cursorrules", "system_prompt"):
        assert "operational_coverage" not in get_scorers(fmt)
        assert "operational_coverage" not in get_weights(fmt)

    # opcov was added to agents.md as its OWN literal, not by mutating the shared
    # instruction-file scorer list.
    assert len(_INSTRUCTION_FILE_SCORERS) == 8
    assert "operational_coverage" not in _INSTRUCTION_FILE_SCORERS


# --- Headline behavior ------------------------------------------------------

def test_well_formed_agents_md_no_eval_warning_three_dim(tmp_path):
    path = _write(tmp_path, _GOOD_AGENTS_MD)
    scores = build_scores(path, None, include_runtime=True, fmt="agents.md")
    result = compute_composite(scores, fmt="agents.md", use_calibrated=False)

    # No SKILL-only eval-suite warning, no cap.
    assert not any("eval suite" in w for w in result["warnings"])
    # Headline is over exactly the three kept dims.
    assert result["measured_dimensions"] == 3
    assert result["total_dimensions"] == 3
    # Score == 0.4*structure + 0.4*operational_coverage + 0.2*efficiency.
    expected = (
        0.4 * scores["structure"]["score"]
        + 0.4 * scores["operational_coverage"]["score"]
        + 0.2 * scores["efficiency"]["score"]
    )
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
# Numbers below were re-derived ONCE on the hardened operational_coverage scorer
# (spec §6). Do NOT reuse the pre-opcov 0.5/0.5 values (73.90/77.25/...) or the
# un-hardened prototype values — the recall fixes (PNNL/kudu/MacroGraph) and the
# command-hardening materially changed the distribution.

@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_agents_md_corpus_golden_distribution():
    rows = []
    for f in sorted(_CORPUS.glob("*.md")):
        result = _score_agents(str(f))
        rows.append((f.name, result["score"], score_to_grade(result["score"]), result["warnings"]))

    scores = [r[1] for r in rows]
    bands = Counter(r[2] for r in rows)

    assert len(rows) == 30
    assert statistics.mean(scores) == pytest.approx(60.53, abs=0.05)
    assert statistics.median(scores) == pytest.approx(62.30, abs=0.05)
    assert min(scores) == pytest.approx(25.0, abs=0.05)
    assert max(scores) == pytest.approx(91.0, abs=0.05)

    # Exact band counts (golden lock) on the hardened scorer. No file reaches S
    # (>=95); the two CJK docs floor opcov directives to 0 (English-scoped, §8.1).
    assert bands["S"] == 0
    assert bands["A"] == 1
    assert bands["B"] == 4
    assert bands["C"] == 8
    assert bands["D"] == 10
    assert bands["E"] == 6
    assert bands["F"] == 1

    # No file emits the SKILL-only eval-suite warning.
    assert not any("eval suite" in w for _, _, _, ws in rows for w in ws)


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_agents_md_top_file_is_underway_grade_a():
    # Off-by-one guard on the score >= threshold comparator. Under the hardened
    # scorer the corpus tops out at underway = 91.0 (grade A), and NO file reaches
    # the S threshold (>= 95). meltano, formerly an S-boundary file, now grades B
    # after a falsely-credited build command was removed.
    underway = _score_agents(str(_CORPUS / "maxcountryman__underway__AGENTS.md.md"))
    assert underway["score"] == pytest.approx(91.0, abs=0.05)
    assert score_to_grade(underway["score"]) == "A"

    meltano = _score_agents(str(_CORPUS / "meltano__meltano__AGENTS.md.md"))
    assert score_to_grade(meltano["score"]) == "B"

    # underway is the unique maximum and nothing reaches S.
    top = max(_score_agents(str(f))["score"] for f in sorted(_CORPUS.glob("*.md")))
    assert top == pytest.approx(91.0, abs=0.05)
    assert score_to_grade(top) != "S"
