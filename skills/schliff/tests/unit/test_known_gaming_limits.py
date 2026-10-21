"""DOCUMENTED LIMITS: two gaming vectors the engine does not catch.

docs/SCORING.md ("Known gaming limits") names both. Every fix measured on 2026-10-19 was
bypassed by a trivial string and still lowered real field files, so the owner chose to
disclose rather than patch (spec: docs/specs/2026-10-19-known-gaming-limits.md).

These tests pin that the gain EXISTS. When a future change closes a vector, its test goes
red — that is intended: update SCORING.md and the spec in the same change, then delete
or invert the test. Do not loosen the assertion to keep it green.

Pinned values are literals measured on the unmodified bases. The efficiency checks compare
against the run-time base by design: that base also earns example credit (see the second test).
"""
from pathlib import Path

from scoring.efficiency import score_efficiency
from scoring.structure import score_structure
from shared import _file_cache

_REPO = Path(__file__).resolve().parents[4]
_CLEAN = _REPO / "benchmarks" / "anti-gaming" / "skills" / "clean-reference.md"
_WEBAPP = _REPO / "benchmarks" / "corpus" / "v1" / "phase0-snapshot" / "01-webapp-testing.SKILL.md"


def _score(tmp_path, name, text, scorer):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    _file_cache.clear()
    return scorer(str(path))["score"]


def test_known_limit_bare_example_tokens_earn_structure_credit(tmp_path):
    """`_RE_REAL_EXAMPLES` counts occurrences, not content: two bare "e.g." tokens
    reach the 10-point examples tier. The same counter feeds efficiency."""
    base = _CLEAN.read_text(encoding="utf-8")
    gamed = base + "\ne.g. e.g.\n"

    assert _score(tmp_path, "base.md", base, score_structure) == 85
    assert _score(tmp_path, "gamed.md", gamed, score_structure) == 95
    assert _score(tmp_path, "gamed.md", gamed, score_efficiency) > _score(
        tmp_path, "base.md", base, score_efficiency
    )


def test_known_limit_content_free_imperatives_earn_efficiency(tmp_path):
    """Efficiency credits distinct imperative lines regardless of what they say:
    ten "- Check item i" bullets lift a short real skill to the ceiling."""
    base = _WEBAPP.read_text(encoding="utf-8")
    gamed = base + "\n" + "\n".join(f"- Check item {i}" for i in range(10)) + "\n"

    # Measured 86 -> 100. The base is not pinned: it also earns example-token credit
    # (test above), so closing THAT vector moves it (81) while this one stays open.
    base_score = _score(tmp_path, "base.md", base, score_efficiency)
    gamed_score = _score(tmp_path, "gamed.md", gamed, score_efficiency)
    assert gamed_score == 100
    assert gamed_score - base_score >= 10
