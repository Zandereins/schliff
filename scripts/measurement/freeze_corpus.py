#!/usr/bin/env python3
"""Freeze the measurement corpus, and verify a frozen one later.

The published field number ("N skills, X tokens") is measured against
`~/.claude`, which is not in any repository and which plugin updates rewrite on
their own schedule. Measured: 159 SKILL.md on 2026-08-29, 161 on 2026-08-31
after an update ran at 08:37 that morning. Without a frozen list, a number
published on 2026-09-14 cannot be reproduced by anyone, including its author.

Two domains, kept apart on purpose:

* **Which files count** belongs to the modules that own them, called here rather
  than re-derived: `skill_mesh.discover_skills` for which skills exist, and
  `shared._payload_files` plus the loader's `eval-suite.json` path for which
  files each skill's numbers are computed from.

  Getting that second half wrong is what the first version of this file did. It
  hashed SKILL.md alone, while `estimate_token_cost` and `skill_payload_digest`
  also read `references/*.md` and `eval-suite.json`. Measured: rewriting one
  reference moved a skill from 26 to 3,925 tokens and changed its payload digest
  while `verify` reported `0 drifted` and exited 0. A freeze whose domain is
  smaller than the quantity it indexes is not a freeze — the same defect this
  repository fixed in `skill_payload_digest` itself.
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

import shared  # noqa: E402  (path set above)

CORPUS_ROOT = Path.home() / ".claude"


def _payload_of(skill_md: Path) -> list[Path]:
    """Every file the published numbers for this skill are computed from.

    SKILL.md, its `references/*.md` as `_payload_files` enumerates them, and
    `eval-suite.json` when present — the same three the cost and the identity
    read. Asked for, not re-derived: a hand-mirrored copy of this list is what
    produced several defects in `shared` itself.
    """
    files = [skill_md, *shared._payload_files(str(skill_md))]
    suite = skill_md.parent / "eval-suite.json"
    if suite.exists():
        files.append(suite)
    return files


def _entries() -> list[dict]:
    """One record per file the measurement reads: relative path, sha256, size."""
    skills = skill_mesh.discover_skills([str(CORPUS_ROOT)])
    # discover_skills stops at MAX_SCAN_FILES and sorts AFTER truncating, so a
    # capped scan yields a set that depends on traversal order. Silently freezing
    # such a set would make `verify` report churn on an unchanged corpus.
    if len(skills) >= skill_mesh.MAX_SCAN_FILES:
        raise SystemExit(
            f"discovery hit its {skill_mesh.MAX_SCAN_FILES}-file cap; the frozen set "
            f"would be whatever the filesystem happened to return first"
        )

    seen: set[Path] = set()
    out = []
    for skill in skills:
        for path in _payload_of(Path(skill["path"])):
            if path in seen:
                continue
            seen.add(path)
            try:
                raw = path.read_bytes()
            except OSError as exc:
                # A file that vanished mid-run is exactly the corpus change this
                # tool exists to report. Say so; do not traceback over it.
                print(f"skipped (unreadable): {path} — {type(exc).__name__}")
                continue
            out.append({
                # Relative, so the manifest is checkable on another machine and
                # does not publish a home directory layout.
                "path": str(path.relative_to(CORPUS_ROOT)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            })
    out.sort(key=lambda e: e["path"])
    return out


def write(target: Path) -> int:
    entries = _entries()
    if not entries:
        raise SystemExit(
            f"refusing to write an empty manifest: no skills found under {CORPUS_ROOT}"
        )
    if target.exists():
        previous = sum(1 for line in target.read_text(encoding="utf-8").splitlines() if line.strip())
        if len(entries) < previous:
            # `discover_skills` skips a missing directory silently, so a run under
            # a different HOME would otherwise truncate the reproducibility
            # artifact and exit 0.
            raise SystemExit(
                f"refusing to shrink {target} from {previous} to {len(entries)} entries; "
                f"delete it deliberately if the corpus really got smaller"
            )
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
