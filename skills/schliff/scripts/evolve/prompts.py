"""LLM prompt templates for the evolution engine.

All prompts are plain strings — no LLM dependency.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are Schliff's Evolution Engine — a specialist for improving AI agent instruction files.

Your task: improve the given instruction file to increase its quality score across multiple dimensions.

RULES:
1. Return ONLY the improved file content, wrapped in ```markdown fences
2. Preserve the file's purpose and semantic meaning
3. Do NOT add false claims, invented features, or hallucinated capabilities
4. Do NOT pad content with filler — the efficiency scorer detects this
5. Do NOT remove content that other dimensions rely on
6. Every change must be defensible — you are scored by a deterministic scorer, not a human
7. Focus on the TOP ISSUES listed below"""


def build_gradient_prompt(content: str, score: float, grade: str,
                          dim_scores: dict, gradients: list[dict],
                          target_score: float, top_n: int = 5) -> str:
    """Build user prompt for gradient strategy."""
    dim_lines = []
    for dim, result in sorted(dim_scores.items()):
        s = result.get("score", -1)
        if s >= 0:
            dim_lines.append(f"  {dim}: {s:.1f}/100")

    grad_lines = []
    for i, g in enumerate(gradients[:top_n], 1):
        grad_lines.append(f"  {i}. [{g['dimension']}] {g['issue']}: {g['instruction']}")

    return f"""CURRENT FILE ({score:.1f}/100 [{grade}]):
```markdown
{content}
```

CURRENT SCORES:
{chr(10).join(dim_lines)}

TOP ISSUES (ranked by impact):
{chr(10).join(grad_lines)}

TARGET: {target_score:.1f}/100

Address the top {top_n} issues. Return the complete improved file."""


def build_holistic_prompt(content: str, score: float, grade: str,
                          dim_scores: dict, target_score: float) -> str:
    """Build user prompt for holistic strategy."""
    # Find 3 weakest dimensions
    scored = [(dim, r.get("score", -1)) for dim, r in dim_scores.items() if r.get("score", -1) >= 0]
    scored.sort(key=lambda x: x[1])
    weakest = ", ".join(f"{dim} ({s:.1f})" for dim, s in scored[:3])

    return f"""CURRENT FILE ({score:.1f}/100 [{grade}]):
```markdown
{content}
```

WEAKEST DIMENSIONS: {weakest}

Rewrite to maximize composite score while protecting strong dimensions.
Return the complete improved file."""


def build_dimension_prompt(content: str, score: float, grade: str,
                           dim_scores: dict, target_dimension: str,
                           gradients: list[dict]) -> str:
    """Build user prompt for single-dimension strategy."""
    dim_score = dim_scores.get(target_dimension, {}).get("score", -1)
    relevant = [g for g in gradients if g["dimension"] == target_dimension]

    grad_lines = []
    for i, g in enumerate(relevant[:5], 1):
        grad_lines.append(f"  {i}. {g['issue']}: {g['instruction']}")

    return f"""CURRENT FILE ({score:.1f}/100 [{grade}]):
```markdown
{content}
```

TARGET DIMENSION: {target_dimension} (currently {dim_score:.1f}/100)

ISSUES IN {target_dimension.upper()}:
{chr(10).join(grad_lines) if grad_lines else "  No specific issues detected — improve holistically."}

Improve the {target_dimension} dimension specifically. Do not sacrifice other dimensions.
Return the complete improved file."""
