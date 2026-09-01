#!/usr/bin/env python3
"""Freeze the measurement corpus, and verify a frozen one later.

The published field number ("N skills, X tokens") is measured against
`~/.claude`, which is not in any repository and which plugin updates rewrite on
their own schedule. Measured: 159 SKILL.md on 2026-08-29, 161 on 2026-08-31
after an update ran at 08:37 that morning. Without a frozen list, a number
published on 2026-09-14 cannot be reproduced by anyone, including its author.

Two domains, kept apart on purpose:

* **Which files count** belongs to `skill_mesh.discover_skills`. It is called
  here rather than re-derived, so the freeze covers exactly the set the tool
  measures — including its exclusions.
* **What the bytes were** belongs to this file. It hashes the raw bytes with a
  full sha256, NOT `discover_skills`' own `content_hash`, which is truncated to
  16 characters and computed over content that schliff has already decoded and
  BOM-stripped. That hash is an identity for schliff's deduplication; it is not
  a file fingerprint, and it would tie the freeze to a reader that changed twice
  in the week this was written. A freeze must not depend on the tool it freezes.

Usage:
    python3 scripts/measurement/freeze_corpus.py write  docs/.../corpus.jsonl
    python3 scripts/measurement/freeze_corpus.py verify docs/.../corpus.jsonl
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "schliff" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import skill_mesh  # noqa: E402  (path set above)

CORPUS_ROOT = Path.home() / ".claude"


def _entries() -> list[dict]:
    """One record per discovered SKILL.md: path relative to the corpus root, sha256, size."""
    out = []
    for skill in skill_mesh.discover_skills([str(CORPUS_ROOT)]):
        path = Path(skill["path"])
        raw = path.read_bytes()
        out.append({
            # Relative, so the manifest is checkable on another machine and does
            # not publish a home directory layout.
            "path": str(path.relative_to(CORPUS_ROOT)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
    out.sort(key=lambda e: e["path"])
    return out


def write(target: Path) -> int:
    entries = _entries()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"froze {len(entries)} files -> {target}")
    return 0


def verify(target: Path) -> int:
    if not target.exists():
        print(f"no frozen manifest at {target}")
        return 1
    frozen = {}
    with target.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                e = json.loads(line)
                frozen[e["path"]] = e["sha256"]
    current = {e["path"]: e["sha256"] for e in _entries()}

    added = sorted(set(current) - set(frozen))
    removed = sorted(set(frozen) - set(current))
    changed = sorted(p for p in set(frozen) & set(current) if frozen[p] != current[p])

    for label, paths in (("added", added), ("removed", removed), ("changed", changed)):
        for p in paths:
            print(f"{label}: {p}")

    drift = len(added) + len(removed) + len(changed)
    print(f"{len(frozen)} frozen, {len(current)} present, {drift} drifted")
    # Non-zero on drift: a measurement taken against a corpus that no longer
    # matches its freeze is not reproducible, and that has to be loud.
    return 1 if drift else 0


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("write", "verify"):
        print(__doc__.strip().split("Usage:")[-1].strip())
        return 2
    return (write if sys.argv[1] == "write" else verify)(Path(sys.argv[2]))


if __name__ == "__main__":
    sys.exit(main())
