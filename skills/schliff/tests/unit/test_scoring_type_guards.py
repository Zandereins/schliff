"""Type-safety guards across all scoring modules.

Follow-up to UR-002 (score_edges assertions-guard). The same bug-class — trusting
user-authored eval-suite JSON to contain list-valued fields — exists across all
scoring modules. Each scorer must return the sentinel score -1 (not crash) when
its list-valued eval-suite field is present but not actually a list.

Covers:
- score_edges (edge_cases non-list)
- score_triggers (triggers non-list)
- score_quality (test_cases non-list, inner assertions non-list)
- score_runtime (test_cases non-list, inner assertions non-list)
- score_coherence (test_cases non-list, inner assertions non-list)

Each non-list input type is tested because the failure modes differ:
- int / bool → TypeError from len() or iteration
- non-empty string → iteration yields chars, then .get() crashes on str char
- dict → iteration yields keys, then .get() crashes on str key
"""
import pytest

from scoring.coherence import score_coherence
from scoring.edges import score_edges
from scoring.quality import score_quality
from scoring.runtime import score_runtime
from scoring.triggers import score_triggers


NON_LIST_VALUES = [
    pytest.param(42, id="int"),
    pytest.param(True, id="bool"),
    pytest.param("a-non-empty-string", id="non-empty-str"),
    pytest.param({"0": {"category": "minimal_input"}}, id="dict"),
]


# ---------------------------------------------------------------------------
# score_edges — edge_cases field
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_edges_non_list_edge_cases_returns_sentinel(bad):
    """score_edges must return sentinel -1 (not crash) when edge_cases is
    present but not a list."""
    result = score_edges("dummy.md", {"edge_cases": bad})
    assert isinstance(result, dict)
    assert result["score"] == -1


# ---------------------------------------------------------------------------
# score_triggers — triggers field
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_triggers_non_list_triggers_returns_sentinel(bad):
    """score_triggers must return sentinel -1 when triggers is present but
    not a list. Pre-fix: `not eval_suite["triggers"]` passed on truthy
    non-list values; iteration then crashed with AttributeError."""
    result = score_triggers("dummy.md", {"triggers": bad})
    assert isinstance(result, dict)
    assert result["score"] == -1


# ---------------------------------------------------------------------------
# score_quality — test_cases field
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_quality_non_list_test_cases_returns_sentinel(bad):
    """score_quality must return sentinel -1 when test_cases is present but
    not a list. Pre-fix: iteration crashed on non-dict items."""
    result = score_quality("dummy.md", {"test_cases": bad})
    assert isinstance(result, dict)
    assert result["score"] == -1


@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_quality_non_list_inner_assertions_does_not_crash(bad):
    """score_quality iterates `tc.get('assertions', [])` in two places. A
    non-list assertions field in ONE test case must not crash the whole
    scorer; it just shouldn't contribute credit for that case."""
    suite = {
        "test_cases": [
            {"id": "bad", "prompt": "x", "assertions": bad},
            {"id": "good", "prompt": "y", "assertions": [
                {"type": "contains", "value": "z"}
            ]},
        ]
    }
    result = score_quality("dummy.md", suite)
    assert isinstance(result, dict)
    assert isinstance(result["score"], int)


# ---------------------------------------------------------------------------
# score_coherence — test_cases field
# ---------------------------------------------------------------------------

_COHERENCE_SKILL_MD = (
    "---\n"
    "name: dummy\n"
    "description: Test skill for coherence guard\n"
    "---\n\n"
    "# Usage\n\n"
    "- Validate user input before processing files.\n"
    "- Verify output matches format specification.\n"
    "- Extract configuration values from header.\n"
)


@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_coherence_non_list_test_cases_returns_zero_bonus(bad, tmp_path):
    """score_coherence must return bonus=0 (not crash) when test_cases is
    present but not a list."""
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(_COHERENCE_SKILL_MD, encoding="utf-8")

    result = score_coherence(str(skill_path), {"test_cases": bad})
    assert isinstance(result, dict)
    assert result["bonus"] == 0


@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_coherence_non_list_inner_assertions_does_not_crash(bad, tmp_path):
    """score_coherence iterates inner assertions. Non-list assertions in one
    test case must not crash the whole scorer."""
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(_COHERENCE_SKILL_MD, encoding="utf-8")

    suite = {
        "test_cases": [
            {"id": "bad", "assertions": bad},
            {"id": "good", "assertions": [{"type": "contains", "value": "input"}]},
        ]
    }
    result = score_coherence(str(skill_path), suite)
    assert isinstance(result, dict)
    assert "bonus" in result


# ---------------------------------------------------------------------------
# score_runtime — test_cases field + inner assertions
# ---------------------------------------------------------------------------

def _mock_claude_ok(*args, **kwargs):
    """Pretend `claude --version` succeeded so the runtime gate opens."""
    class _R:
        returncode = 0
        stdout = "claude 1.0.0\n"
        stderr = ""
    return _R()


@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_runtime_non_list_test_cases_returns_sentinel(bad, tmp_path, monkeypatch):
    """score_runtime must return sentinel -1 when test_cases is present but
    not a list. Pre-fix: iteration at line 48 crashed."""
    from scoring import runtime as runtime_mod

    monkeypatch.setattr(runtime_mod.subprocess, "run", _mock_claude_ok)

    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("---\nname: x\n---\nbody\n", encoding="utf-8")

    result = score_runtime(
        str(skill_path), {"test_cases": bad}, enabled=True
    )
    assert isinstance(result, dict)
    assert result["score"] == -1


@pytest.mark.parametrize("bad", NON_LIST_VALUES)
def test_score_runtime_non_list_inner_assertions_does_not_crash(bad, tmp_path, monkeypatch):
    """score_runtime builds `runtime_asserts = [a for a in assertions if ...]`.
    If inner assertions is non-list, the comprehension crashes — unless
    guarded. This tests the inner-field guard."""
    from scoring import runtime as runtime_mod

    monkeypatch.setattr(runtime_mod.subprocess, "run", _mock_claude_ok)

    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("---\nname: x\n---\nbody\n", encoding="utf-8")

    suite = {
        "test_cases": [
            {"id": "bad", "prompt": "q", "assertions": bad},
        ]
    }
    result = score_runtime(str(skill_path), suite, enabled=True)
    assert isinstance(result, dict)
    # No valid runtime asserts anywhere → sentinel.
    assert result["score"] == -1
