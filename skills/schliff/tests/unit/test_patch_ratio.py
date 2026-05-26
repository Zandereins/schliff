"""Lock the deterministic-patch-ratio measurement methodology.

'Deterministic' is defined EXACTLY as the auto-apply gate in text_gradient.py:
    confidence == "high" AND effort <= EFFORT_SIMPLE
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from measure_patch_ratio import measure  # noqa: E402


def test_measure_returns_consistent_shape():
    m = measure()
    assert m["total"] > 0
    assert m["deterministic"] + m["llm"] == m["total"]
    assert 0.0 <= m["deterministic_ratio"] <= 1.0
    # The figure is whatever the catalog actually is — the test pins the contract, not a magic number.
    assert m["definition"] == 'confidence=="high" and effort<=EFFORT_SIMPLE'


def test_only_true_gradients_counted():
    from measure_patch_ratio import _gradient_dicts
    import ast
    from pathlib import Path
    import sys
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    src = (scripts / "text_gradient.py").read_text(encoding="utf-8")
    grads = _gradient_dicts(ast.parse(src))
    assert grads, "no gradients parsed"
    assert all("effort" in g for g in grads), "a counted dict lacks 'effort' (not a true gradient)"
