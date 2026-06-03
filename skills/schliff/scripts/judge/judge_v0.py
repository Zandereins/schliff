#!/usr/bin/env python3
"""Judge v0 — minimal LLM-as-judge harness for the v8.0 AI-Eval pillar.

Phase-1 SMOKE TEST, not a reliability run. Scores the human-labelled calibration
set (`benchmarks/corpus/v1/phase1-calibration/labels-v0.jsonl`) with an LLM judge
on the two solid dimensions (B verifiable_success, C assumption_completeness) and
reports per-item judge-vs-human agreement. Per the closing council: this is a
DIRECTIONAL agreement check (n too small for kappa/TNR) used to iterate the judge
prompt toward Hamel's >=90% alignment — NOT a published reliability number.

Design (spec §8 / ADR-0002/0006):
  - pinned model (default claude-sonnet-4-6), temp 0.3, N self-consistency (plurality)
    — N=5 is the *calibration-run* invariant (variance mitigation vs "Rating
    Roulette", ADR-0006 §2); the shipped CLI default is N=1 for the frozen
    Phase-1 smoke set (votes were 5/5 unanimous, so N>1 buys no variance
    reduction until probe-tier specimens split). Pass --n 5 for a calibration run.
  - binary PASS/FAIL + critique via structured output (messages.parse + Pydantic)
  - leave-one-out few-shots: an item is judged using the OTHER labelled items of its
    dim as anchors, so no specimen ever judges itself
  - rubric+anchors live in a cached system block; reproducibility via prompt SHA + JSONL log
  - gating invariant (design constraint for the v8.1 resume; the frozen v0 smoke
    harness does NOT yet enforce it): never judge an artifact below the linter
    completeness floor — see scoring/guards.py:judge_floor

Run (needs ANTHROPIC_API_KEY + `pip install anthropic`):
    python3 judge_v0.py --labels ../../benchmarks/corpus/v1/phase1-calibration/labels-v0.jsonl
Mock plumbing (no API):
    python3 judge_v0.py --labels <jsonl> --mock
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[4]
# Pinned judge model. DIVERGENCE from ADR-0006 §1 (which named Sonnet 4.5 / 4.7):
# 4.6 is newer, same-family, and supports temperature, so the same-family rationale
# of ADR-0006 still holds. ADR-0006's "model+date" reproducibility pin is only half
# met here — the model string is pinned but no date/version snapshot is recorded in
# code; the date component belongs in the (not-yet-published) methodology page. ADR
# update to record 4.6 as the shipped pin is tracked outside this module's scope.
MODEL_DEFAULT = "claude-sonnet-4-6"  # pinned judge model (ADR-0006 same-family); temp allowed on 4.6

# Locked dimension rubrics (council 2026-05-26). Binary, disclosure-/checkability-anchored.
RUBRICS: dict[str, str] = {
    "verifiable_success": (
        "Dimension: verifiable_success.\n"
        "FAIL if the skill defines success by unverifiable adjectives ('museum quality', "
        "'production-ready') or unsourced precise numbers — i.e. a triggered agent has no "
        "concrete, checkable way to know it succeeded. PASS if it gives a checkable success "
        "signal (a test, an inspectable property, a runnable verification step)."
    ),
    "assumption_completeness": (
        "Dimension: assumption_completeness (DISCLOSURE, not provisionability).\n"
        "FAIL if the documented happy path relies on a consequential precondition (external "
        "package/binary, account, credential, paid service, runtime) that is NOT disclosed in "
        "the skill text at/before first use. PASS if such deps are stated (named/paid/external "
        "but disclosed still PASSES). Harness-contract tools (file-I/O, Bash, Read, Write) need "
        "no disclosure. Whether a disclosed dep is provisionable is OUT OF SCOPE (that is the "
        "verifiable_success dimension); a declared sibling-skill handoff is composability's, not this."
    ),
}

DIM_ALIASES = {"B": "verifiable_success", "C": "assumption_completeness"}


def load_labels(path: Path) -> list[dict]:
    """Load anchors, skipping any marked status=excluded (see exclude_reason in the file)."""
    rows, excluded = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("status") == "excluded":
            excluded += 1
            continue
        rows.append(row)
    if excluded:
        print(f"({excluded} anchors excluded — see exclude_reason in {path.name})", file=sys.stderr)
    return rows


def build_system(dim: str, anchors: list[dict]) -> str:
    """Rubric + leave-one-out few-shot anchors (cacheable, stable per dim)."""
    parts = [
        "You are a deterministic skill-quality judge. Apply ONLY the dimension below; "
        "ignore all other quality aspects. Output a binary label and a one-sentence critique.",
        "",
        RUBRICS[dim],
        "",
        "Calibration anchors (human-labelled; same dimension):",
    ]
    for a in anchors:
        parts.append(f"- [{a['label']}] {a['specimen']}: {a['critique']}")
    return "\n".join(parts)


def _real_judge_factory(model: str, temp: float) -> Callable:
    import anthropic  # imported lazily so --mock works without the SDK
    from pydantic import BaseModel
    from typing import Literal

    class Verdict(BaseModel):
        label: Literal["PASS", "FAIL"]
        critique: str

    client = anthropic.Anthropic()

    def judge_once(system: str, skill_text: str) -> tuple[str, str]:
        resp = client.messages.parse(
            model=model,
            max_tokens=512,
            temperature=temp,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": (
                "Judge this SKILL.md on the dimension above. Output label (PASS/FAIL) + critique.\n\n"
                "----- SKILL.md -----\n" + skill_text)}],
            output_format=Verdict,
        )
        v = resp.parsed_output
        return v.label, v.critique

    return judge_once


def _mock_judge_factory() -> Callable:
    """Deterministic stand-in so harness plumbing (voting, agreement, IO) is testable
    without an API key. Label derived from a hash — exercises both agree/disagree paths."""
    def judge_once(system: str, skill_text: str) -> tuple[str, str]:
        h = int(hashlib.sha256((system[:64] + skill_text[:256]).encode()).hexdigest(), 16)
        return ("PASS" if h % 2 == 0 else "FAIL"), "mock critique (no API call made)"
    return judge_once


def run(labels_path: Path, model: str, n: int, temp: float, mock: bool, out_path: Path) -> int:
    rows = load_labels(labels_path)
    judge_once = _mock_judge_factory() if mock else _real_judge_factory(model, temp)

    results = []
    by_dim = collections.defaultdict(list)
    for r in rows:
        by_dim[r["dim"]].append(r)

    for r in rows:
        dim = r["dim"]
        skill_path = REPO_ROOT / r["path"]
        if not skill_path.is_file():
            print(f"WARN missing {skill_path}", file=sys.stderr)
            continue
        skill_text = skill_path.read_text(encoding="utf-8", errors="replace")
        anchors = [a for a in by_dim[dim] if a["specimen"] != r["specimen"]]  # leave-one-out
        system = build_system(dim, anchors)
        prompt_sha = hashlib.sha256((system + skill_text).encode()).hexdigest()[:12]

        votes = [judge_once(system, skill_text) for _ in range(n)]
        labels = [v[0] for v in votes]
        # Deterministic plurality: on a tie, default to the conservative label (FAIL)
        # so an even/split vote does not flip PASS<->FAIL with API sample arrival order.
        counts = collections.Counter(labels).most_common()
        if len(counts) > 1 and counts[0][1] == counts[1][1]:
            plurality = "FAIL"
        else:
            plurality = counts[0][0]
        agree = plurality == r["label"]
        results.append({
            "specimen": r["specimen"], "dim": dim, "tier": r.get("tier"),
            "human": r["label"], "judge": plurality,
            "votes": dict(collections.Counter(labels)), "agree": agree,
            "judge_critique": votes[0][1], "prompt_sha": prompt_sha,
        })

    out_path.write_text("\n".join(json.dumps(x) for x in results) + "\n", encoding="utf-8")

    # Directional agreement summary (NOT kappa — n too small, council guardrail).
    print(f"\n{'specimen':28s} {'dim':24s} human judge votes        agree")
    for x in results:
        print(f"{x['specimen']:28s} {x['dim']:24s} {x['human']:5s} {x['judge']:5s} "
              f"{str(x['votes']):16s} {'OK' if x['agree'] else 'MISS'}")
    n_ok = sum(x["agree"] for x in results)
    print(f"\nDirectional agreement: {n_ok}/{len(results)} "
          f"({100*n_ok/len(results):.0f}%) — SMOKE TEST ONLY (n too small for kappa/TNR).")
    print(f"Log: {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Judge v0 smoke test (B+C dims).")
    ap.add_argument("--labels", required=True, type=Path)
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--n", type=int, default=1, help="self-consistency samples (plurality); "
                    "N=1 default for calibration — Phase-1 votes were 5/5 unanimous, so N>1 buys "
                    "no variance reduction until probe-tier specimens actually split. Raise then.")
    ap.add_argument("--temp", type=float, default=0.3)
    ap.add_argument("--mock", action="store_true", help="no API; test harness plumbing")
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("judge_v0_results.jsonl"))
    a = ap.parse_args()
    return run(a.labels, a.model, a.n, a.temp, a.mock, a.out)


if __name__ == "__main__":
    raise SystemExit(main())
