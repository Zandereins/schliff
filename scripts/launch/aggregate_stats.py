#!/usr/bin/env python3
"""Aggregate scored corpus into the headline stats cited in state-of-ai-instructions.md.

Produces:
 - docs/launch/corpus/stats.json      (full aggregation, machine-readable)
 - docs/launch/corpus/stats.md        (markdown tables to paste into report)
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "docs" / "launch" / "corpus"
SCORES_DIR = CORPUS_DIR / "scores"


def grade_for(score: float | None) -> str:
    if score is None:
        return "?"
    if score >= 95: return "S"
    if score >= 85: return "A"
    if score >= 75: return "B"
    if score >= 65: return "C"
    if score >= 50: return "D"
    if score >= 35: return "E"
    return "F"


def load_summary() -> list[dict]:
    path = SCORES_DIR / "_summary.json"
    if not path.exists():
        raise SystemExit("no scored data — run score_corpus.py first")
    return json.loads(path.read_text())


def has_no_eval(dims: dict | None) -> bool:
    if not dims: return False
    return all((dims.get(k, 0) in (0, -1)) for k in ("triggers", "quality", "edges"))


def aggregate(summary: list[dict]) -> dict:
    ok = [s for s in summary if not s.get("error") and s.get("composite") is not None]

    n = len(ok)
    stats: dict = {"n_total": len(summary), "n_scored": n, "n_errors": len(summary) - n}

    if n == 0:
        return stats

    composites = [float(s["composite"]) for s in ok]
    tokens_all = [s.get("tokens") for s in ok if s.get("tokens") is not None]

    stats["composite_mean"] = round(statistics.mean(composites), 2)
    stats["composite_median"] = round(statistics.median(composites), 2)
    stats["composite_stdev"] = round(statistics.pstdev(composites), 2)

    grades = Counter(grade_for(c) for c in composites)
    stats["grade_distribution"] = dict(sorted(grades.items()))
    stats["pct_below_c"] = round(
        100 * sum(1 for c in composites if c < 65) / n, 1
    )
    stats["pct_at_or_above_c"] = round(100 - stats["pct_below_c"], 1)

    # eval gap: triggers+quality+edges all 0 or -1
    eval_gap = sum(1 for s in ok if has_no_eval(s.get("dims")))
    stats["pct_no_eval"] = round(100 * eval_gap / n, 1)

    # token buckets
    if tokens_all:
        stats["tokens_mean"] = round(statistics.mean(tokens_all), 1)
        stats["tokens_median"] = round(statistics.median(tokens_all), 1)
        short = [float(s["composite"]) for s in ok
                 if s.get("tokens") is not None and s["tokens"] < 300]
        long_ = [float(s["composite"]) for s in ok
                 if s.get("tokens") is not None and s["tokens"] > 1000]
        stats["short_files"] = {
            "n": len(short),
            "avg_score": round(statistics.mean(short), 2) if short else None,
        }
        stats["long_files"] = {
            "n": len(long_),
            "avg_score": round(statistics.mean(long_), 2) if long_ else None,
        }

    # per-dimension averages (over files where dimension was measured, != -1)
    dim_names = ["structure", "triggers", "quality", "edges",
                 "efficiency", "composability", "clarity"]
    dim_stats: dict = {}
    for d in dim_names:
        measured = [s["dims"][d] for s in ok
                    if s.get("dims") and s["dims"].get(d) not in (None, -1)]
        dim_stats[d] = {
            "n_measured": len(measured),
            "mean": round(statistics.mean(measured), 2) if measured else None,
            "median": round(statistics.median(measured), 2) if measured else None,
        }
    stats["dimensions"] = dim_stats

    # per-format breakdown
    per_fmt: dict = defaultdict(list)
    for s in ok:
        per_fmt[s["format"]].append(float(s["composite"]))
    stats["per_format"] = {
        fmt: {
            "n": len(vals),
            "avg_composite": round(statistics.mean(vals), 2),
            "median_composite": round(statistics.median(vals), 2),
        }
        for fmt, vals in per_fmt.items()
    }

    # top/bottom
    ok_sorted = sorted(ok, key=lambda s: float(s["composite"]), reverse=True)
    stats["top5"] = [{"file": s["file"], "composite": s["composite"],
                      "grade": grade_for(float(s["composite"]))}
                     for s in ok_sorted[:5]]
    stats["bottom5"] = [{"file": s["file"], "composite": s["composite"],
                         "grade": grade_for(float(s["composite"]))}
                        for s in ok_sorted[-5:]]

    return stats


def render_markdown(stats: dict) -> str:
    lines: list[str] = []
    lines.append("# Corpus Aggregation Stats\n")
    lines.append(f"Total files processed: {stats.get('n_total')}  \n"
                 f"Successfully scored: {stats.get('n_scored')}  \n"
                 f"Errors: {stats.get('n_errors')}\n")
    lines.append("## Headline Numbers\n")
    lines.append(f"- **% below C:** {stats.get('pct_below_c')}%")
    lines.append(f"- **Mean composite:** {stats.get('composite_mean')} "
                 f"(median {stats.get('composite_median')})")
    lines.append(f"- **% with no eval suite (triggers+quality+edges all 0 or -1):** "
                 f"{stats.get('pct_no_eval')}%")
    short = stats.get("short_files", {})
    long_ = stats.get("long_files", {})
    if short and long_:
        lines.append(f"- **<300 token files (n={short.get('n')}):** "
                     f"avg {short.get('avg_score')}")
        lines.append(f"- **>1000 token files (n={long_.get('n')}):** "
                     f"avg {long_.get('avg_score')}")

    lines.append("\n## Grade Distribution\n")
    lines.append("| Grade | Count | % |")
    lines.append("|-------|-------|---|")
    n = stats.get("n_scored", 0) or 1
    for g, count in stats.get("grade_distribution", {}).items():
        lines.append(f"| {g} | {count} | {round(100*count/n,1)}% |")

    lines.append("\n## Per-Dimension Averages\n")
    lines.append("| Dimension | N measured | Mean | Median |")
    lines.append("|-----------|-----------|------|--------|")
    for d, v in stats.get("dimensions", {}).items():
        lines.append(f"| {d} | {v.get('n_measured')} | {v.get('mean')} | {v.get('median')} |")

    lines.append("\n## Per-Format Averages\n")
    lines.append("| Format | N | Avg composite | Median |")
    lines.append("|--------|---|---------------|--------|")
    for fmt, v in stats.get("per_format", {}).items():
        lines.append(f"| {fmt} | {v.get('n')} | {v.get('avg_composite')} | "
                     f"{v.get('median_composite')} |")

    lines.append("\n## Top 5 / Bottom 5\n")
    lines.append("Top:")
    for t in stats.get("top5", []):
        lines.append(f"- {t.get('composite')} [{t.get('grade')}] — {t.get('file')}")
    lines.append("\nBottom:")
    for t in stats.get("bottom5", []):
        lines.append(f"- {t.get('composite')} [{t.get('grade')}] — {t.get('file')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    summary = load_summary()
    stats = aggregate(summary)
    (CORPUS_DIR / "stats.json").write_text(json.dumps(stats, indent=2))
    (CORPUS_DIR / "stats.md").write_text(render_markdown(stats))
    print(f"[aggregate] n_scored={stats.get('n_scored')} "
          f"pct_below_c={stats.get('pct_below_c')}% "
          f"pct_no_eval={stats.get('pct_no_eval')}% "
          f"mean={stats.get('composite_mean')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
