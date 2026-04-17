#!/usr/bin/env python3
"""Collect public AI instruction files for state-of-ai-instructions.md data.

Uses `gh search code` to find public files by filename, then fetches raw content
via `gh api`. Saves to docs/launch/corpus/<format>/<owner>__<repo>__<path>.<ext>.

Designed to be re-runnable: skips files already present.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "docs" / "launch" / "corpus"

FORMATS = {
    "skill": {"filename": "SKILL.md", "language": "markdown", "ext": ".md"},
    "claude": {"filename": "CLAUDE.md", "language": "markdown", "ext": ".md"},
    "agents": {"filename": "AGENTS.md", "language": "markdown", "ext": ".md"},
    "cursor": {"filename": ".cursorrules", "language": None, "ext": ".cursorrules"},
}


def sh(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def gh_search(filename: str, language: str | None, limit: int) -> list[dict]:
    cmd = [
        "gh", "search", "code",
        "--filename", filename,
        "--limit", str(limit),
        "--json", "repository,path,url",
    ]
    if language:
        cmd.extend(["--language", language])
    try:
        r = sh(cmd)
    except subprocess.CalledProcessError as e:
        print(f"[collect] gh search failed for {filename}: {e.stderr}", file=sys.stderr)
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"[collect] gh search returned non-JSON for {filename}", file=sys.stderr)
        return []


def gh_fetch(owner: str, repo: str, path: str) -> str | None:
    cmd = ["gh", "api", f"repos/{owner}/{repo}/contents/{path}"]
    try:
        r = sh(cmd)
    except subprocess.CalledProcessError:
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def collect_format(fmt_key: str, fmt_spec: dict, target: int) -> list[Path]:
    out_dir = CORPUS_DIR / fmt_key
    out_dir.mkdir(parents=True, exist_ok=True)
    results = gh_search(fmt_spec["filename"], fmt_spec["language"], limit=max(target * 2, 30))
    saved: list[Path] = []
    seen_repos: set[str] = set()
    for item in results:
        if len(saved) >= target:
            break
        repo_info = item.get("repository", {})
        owner = repo_info.get("owner", {}).get("login") or repo_info.get("nameWithOwner", "").split("/")[0]
        repo_name = repo_info.get("name") or repo_info.get("nameWithOwner", "").split("/")[-1]
        path = item.get("path")
        if not (owner and repo_name and path):
            continue
        repo_key = f"{owner}/{repo_name}"
        if repo_key in seen_repos:
            continue
        seen_repos.add(repo_key)
        safe_path = sanitize(path)
        out_file = out_dir / f"{sanitize(owner)}__{sanitize(repo_name)}__{safe_path}{fmt_spec['ext']}"
        if out_file.exists():
            saved.append(out_file)
            continue
        content = gh_fetch(owner, repo_name, path)
        if content is None:
            continue
        if len(content) < 50:
            continue
        out_file.write_text(content, encoding="utf-8")
        meta = {
            "owner": owner, "repo": repo_name, "path": path,
            "format": fmt_key, "url": item.get("url", ""),
            "bytes": len(content.encode("utf-8")),
        }
        out_file.with_suffix(out_file.suffix + ".meta.json").write_text(json.dumps(meta, indent=2))
        saved.append(out_file)
        time.sleep(0.3)
    return saved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-format", type=int, default=30,
                    help="target files per format (default 30, total up to 120)")
    ap.add_argument("--format", choices=list(FORMATS.keys()),
                    help="collect only one format (default: all)")
    args = ap.parse_args()

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    formats = {args.format: FORMATS[args.format]} if args.format else FORMATS

    for fmt_key, fmt_spec in formats.items():
        print(f"[collect] gathering up to {args.per_format} {fmt_spec['filename']} files...")
        saved = collect_format(fmt_key, fmt_spec, args.per_format)
        print(f"[collect]   -> saved {len(saved)} to {CORPUS_DIR / fmt_key}")
        manifest.append({"format": fmt_key, "count": len(saved)})

    (CORPUS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(m["count"] for m in manifest)
    print(f"[collect] done. total={total} across {len(manifest)} formats.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
