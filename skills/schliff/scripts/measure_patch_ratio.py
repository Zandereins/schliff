#!/usr/bin/env python3
"""Measure the real deterministic-vs-LLM patch ratio — canonical source for the README claim.

A patch is auto-applied deterministically iff text_gradient.py's apply gate accepts it:
    confidence == "high" AND effort <= EFFORT_SIMPLE   (text_gradient.py)
Everything else falls back to the LLM. This script parses the gradient catalog statically.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path

_GRADIENT = Path(__file__).resolve().parent / "text_gradient.py"
EFFORT_SIMPLE = 1
DEFINITION = 'confidence=="high" and effort<=EFFORT_SIMPLE'


def _gradient_dicts(tree: ast.AST) -> list[dict]:
    """Collect dict literals that look like gradients (have 'confidence' + 'delta' keys)."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
        if "confidence" in keys and "delta" in keys and "effort" in keys:
            d = {}
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                    d[k.value] = v.value
                elif isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                    # effort uses named constants (EFFORT_SIMPLE=1, etc.)
                    d[k.value] = {"EFFORT_SIMPLE": 1, "EFFORT_MODERATE": 2,
                                  "EFFORT_COMPLEX": 3, "EFFORT_MAJOR": 4}.get(v.id, 2)
            out.append(d)
    return out


def measure() -> dict:
    tree = ast.parse(_GRADIENT.read_text(encoding="utf-8"))
    grads = _gradient_dicts(tree)
    total = len(grads)
    deterministic = sum(
        1 for g in grads
        if g.get("confidence") == "high" and int(g.get("effort", 2)) <= EFFORT_SIMPLE
    )
    return {
        "total": total,
        "deterministic": deterministic,
        "llm": total - deterministic,
        "deterministic_ratio": round(deterministic / total, 3) if total else 0.0,
        "definition": DEFINITION,
    }


def main():
    m = measure()
    print(json.dumps(m, indent=2))
    print(f"\nDeterministic patches: {m['deterministic']}/{m['total']} "
          f"= {m['deterministic_ratio']:.0%}  ({m['definition']})")


if __name__ == "__main__":
    main()
