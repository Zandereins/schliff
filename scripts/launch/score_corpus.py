#!/usr/bin/env python3
"""Score every collected file with schliff and dump per-file JSON results."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "docs" / "launch" / "corpus"
SCORES_DIR = CORPUS_DIR / "scores"

FORMAT_FLAG = {
    "skill": "skill.md",
    "claude": "claude.md",
    "agents": "agents.md",
    "cursor": "cursorrules",
}


def score_one(path: Path, fmt_key: str) -> dict | None:
    cmd = [
        "/usr/bin/python3", "-m", "skills.schliff.scripts.cli",
        "score", "--json",
        "--format", FORMAT_FLAG.get(fmt_key, "unknown"),
        str(path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False,
                           cwd=str(REPO_ROOT), timeout=60)
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    if r.returncode != 0:
        return {"error": f"exit {r.returncode}", "stderr": r.stderr[:500]}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": "non-json", "raw": r.stdout[:500]}


def collect_corpus_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for fmt_dir in CORPUS_DIR.iterdir():
        if not fmt_dir.is_dir() or fmt_dir.name == "scores":
            continue
        fmt_key = fmt_dir.name
        for f in sorted(fmt_dir.iterdir()):
            if f.name.endswith(".meta.json"):
                continue
            if f.suffix in {".md", ".cursorrules"}:
                files.append((f, fmt_key))
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="score at most N files (0 = all)")
    ap.add_argument("--force", action="store_true", help="re-score even if result exists")
    args = ap.parse_args()

    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    files = collect_corpus_files()
    if args.limit:
        files = files[: args.limit]

    print(f"[score] scoring {len(files)} files")
    summary: list[dict] = []
    for i, (path, fmt_key) in enumerate(files, 1):
        out_path = SCORES_DIR / f"{fmt_key}__{path.stem}.json"
        if out_path.exists() and not args.force:
            result = json.loads(out_path.read_text())
        else:
            result = score_one(path, fmt_key)
            if result is None:
                continue
            # attach file info
            result["_file"] = str(path.relative_to(REPO_ROOT))
            result["_format_key"] = fmt_key
            out_path.write_text(json.dumps(result, indent=2))
        summary.append({
            "file": str(path.relative_to(REPO_ROOT)),
            "format": fmt_key,
            "composite": result.get("composite_score"),
            "dims": result.get("dimensions"),
            "tokens": (result.get("token_budget") or {}).get("tokens"),
            "error": result.get("error"),
        })
        if i % 10 == 0:
            print(f"[score]  {i}/{len(files)}")

    (SCORES_DIR / "_summary.json").write_text(json.dumps(summary, indent=2))
    errors = sum(1 for s in summary if s.get("error"))
    print(f"[score] done. total={len(summary)} errors={errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
