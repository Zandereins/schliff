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
import os
import stat
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "schliff" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import manifest as manifest_mod  # noqa: E402  (path set above)
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
    # `_payload_files` rejects symlinked references — a shipped security decision
    # for the cost path. `manifest.invoke_cost_chars` follows them and charges the
    # target, so one of the three published numbers reads a file that enumeration
    # deliberately omits. Measured: rewriting a symlink target moved `invoke` from
    # 10,010 to 100,010 with `verify` reporting 0 drifted. The freeze is a superset
    # of every reader by design, so it takes them; it does not follow the link,
    # it hashes the link's target bytes exactly as the charge does.
    refs = skill_md.parent / "references"
    if refs.is_dir() and not refs.is_symlink():
        files.extend(f for f in sorted(refs.glob("*.md")) if f.is_symlink())
    suite = shared.eval_suite_path(str(skill_md))
    if suite.exists():
        files.append(suite)
    return files


# Exit codes carry the verdict, so no caller has to pattern-match this file's
# prose. `run_measurement` used to classify drift by prefix-matching stdout, and
# adding two labels here silently turned every resolution flip into "the freeze
# check itself failed" — the opposite verdict. 0 clean, 1 drift, 2 the check
# could not run.
EXIT_CLEAN, EXIT_DRIFT, EXIT_BROKEN = 0, 1, 2


def _fail(message: str) -> None:
    """Refuse with EXIT_BROKEN — a failed check is not a drift verdict."""
    print(message, file=sys.stderr)
    sys.exit(EXIT_BROKEN)


def _read_bounded_bytes(path: Path) -> bytes | None:
    """The raw bytes, with `_read_bounded_with_reason`'s discipline.

    Deliberately the same shape and not a call: that function decodes with
    `errors="replace"`, and a hash over replaced text is not a byte fingerprint.
    What is borrowed is the discipline, which this script needs for the same
    reason `shared` does — it reads `references/*.md` under third-party plugin
    caches, files discovery never pre-screened. A plain `read_bytes` there hangs
    forever on a FIFO (measured in `shared`: still blocked after six seconds) and
    raises `MemoryError` on a multi-gigabyte target, which is not an `OSError`
    and so escapes the handler below.
    """
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > shared.MAX_SKILL_SIZE:
            return None
        with os.fdopen(fd, "rb") as handle:
            fd = None
            return handle.read()
    except (OSError, ValueError):
        return None
    finally:
        if fd is not None:
            os.close(fd)


def _manifest_inputs() -> list[Path]:
    """Every file the `manifest` figures are computed from.

    The headline this measurement publishes is `manifest`'s `resident`, and
    `build_manifest` reads more than the skills do: `commands/**/*.md` for every
    enabled plugin, plus `settings.json`, whose `enabledPlugins` gates the whole
    artifact set. Freezing only what `doctor` reads covered the number this study
    demotes and left the chosen one open — measured, 21 of 106 artifacts and 830
    of 7,975 resident tokens sat outside the freeze.

    Asked for, not re-derived: `build_manifest` is called and its artifact paths
    taken. Anything it reports outside the corpus root (a project's `.claude/`)
    cannot be frozen by a manifest keyed on that root, and is named rather than
    dropped silently.
    """
    settings = CORPUS_ROOT / "settings.json"
    out = [settings] if settings.exists() else []
    outside = []
    # Which of several coexisting version directories is active is decided by
    # `_resolve_plugin_dir` on directory MTIME, and mtime is not content. Three
    # plugins here have two directories sharing one mtime, so the winner falls to
    # `iterdir()` order. Red proof, flipping nothing but an mtime: the resolved
    # supabase description went 790 -> 498 characters, which moves `resident`
    # directly — while every frozen path stayed present and unchanged, because
    # BOTH versions are in the freeze. Recording which paths were resolved is the
    # only thing that makes that flip visible.
    for artifact in manifest_mod.build_manifest(CORPUS_ROOT).loaded:
        # expanduser, not a replace: `manifest._tilde` only abbreviates a LEADING
        # home prefix and returns anything else untouched, so an unanchored
        # first-occurrence replace rewrote a `~` sitting anywhere in an absolute
        # path — and the guard below then tested a path that does not exist.
        path = Path(str(artifact.path)).expanduser()
        try:
            path.relative_to(CORPUS_ROOT)
        except ValueError:
            outside.append(str(path))
            continue
        out.append(path)
    for path in sorted(set(outside)):
        print(f"outside the corpus root, not frozen: {path}")
    return out


def _entries() -> list[dict]:
    """One record per file ANY published number reads: relative path, sha256, size."""
    # Ask the walk whether it truncated. Comparing `len(skills)` to the cap was
    # wrong in both directions: the cap counts candidates surviving EXCLUDED_DIRS
    # while this list only keeps those that also pass symlink confinement,
    # realpath dedup and the bounded read — so a capped scan whose candidates were
    # mostly dropped returns a short list and looks fine, and a complete scan of
    # exactly MAX_SCAN_FILES files was rejected, since the break is `>` not `>=`.
    skills, truncated = skill_mesh.discover_skills_with_status([str(CORPUS_ROOT)])
    if truncated:
        # A truncated walk sorts AFTER truncating, so its contents follow
        # filesystem traversal order; freezing that would make `verify` report
        # churn on an unchanged corpus.
        _fail(f"discovery stopped at its {skill_mesh.MAX_SCAN_FILES}-file cap; the frozen "
              f"set would be whatever the filesystem happened to return first")

    seen: set[Path] = set()
    unfreezable: list[str] = []
    out = []
    resolved = set(_manifest_inputs())
    sources = [_payload_of(Path(skill["path"])) for skill in skills]
    sources.append(sorted(resolved))
    for group in sources:
        for path in group:
            if path in seen:
                continue
            seen.add(path)
            raw = _read_bounded_bytes(path)
            if raw is None:
                # NOT a skip. `manifest` still charges an oversized SKILL.md —
                # `parse_frontmatter` head-reads 64 KB and `invoke_cost_chars`
                # uses `st_size` with no cap — so dropping it leaves a file the
                # headline reads outside the freeze, which is the one thing this
                # artifact must never do. Measured before this guard: a 1.2 MB
                # SKILL.md was dropped, `write` reported "froze 1 files" and
                # `verify` reported "0 drifted" with exit 0 while the number moved.
                unfreezable.append(str(path))
                continue
            entry = {
                # Relative, so the manifest is checkable on another machine and
                # does not publish a home directory layout.
                "path": str(path.relative_to(CORPUS_ROOT)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
            if path in resolved:
                entry["resolved"] = True
            out.append(entry)
    if unfreezable:
        _fail("these files are read by a published number and cannot be frozen "
              "(not a regular file, past the size limit, or unreadable):\n  "
              + "\n  ".join(sorted(unfreezable)))
    out.sort(key=lambda e: e["path"])
    return out


def write(target: Path) -> int:
    entries = _entries()
    if not entries:
        _fail(f"refusing to write an empty manifest: no skills found under {CORPUS_ROOT}")
    # Compare against the newest existing freeze in the directory, not against
    # `target`: the manifests are date-stamped, so a re-freeze writes a NEW path
    # and a guard keyed on `target.exists()` never fires for the workflow this
    # repository actually prescribes — which is every re-freeze.
    # The target itself counts as a baseline too. Keying only on the date-stamped
    # siblings narrowed the guard: a re-freeze to the same path under any other
    # name was unprotected, which is the case the original `target.exists()`
    # check covered before it was replaced.
    candidates = list(target.parent.glob("corpus-*.jsonl")) if target.parent.exists() else []
    if target.exists() and target not in candidates:
        candidates.append(target)
    # Largest by ENTRY COUNT, not by name. Appending the target to a list ranked
    # by filename left it unprotected whenever its name sorted below `corpus-…`:
    # measured, a 50-entry freeze was overwritten with 3 entries at exit 0, which
    # is the failure this guard exists for.
    counts = {p: sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
              for p in candidates}
    baseline = max(counts, key=counts.get, default=None)
    if baseline is not None:
        previous = counts[baseline]
        if len(entries) < previous:
            # `discover_skills` skips a missing directory silently, so a run under
            # a different HOME would otherwise truncate the reproducibility
            # artifact and exit 0.
            _fail(f"refusing to write {len(entries)} entries when {baseline.name} holds "
                  f"{previous}; delete that file deliberately if the corpus really got smaller")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"froze {len(entries)} files -> {target}")
    return 0


def verify(target: Path) -> int:
    if not target.exists():
        _fail(f"no frozen manifest at {target}")
    frozen = {}
    frozen_resolved = set()
    # Caught, because exit 1 now MEANS drift: an uncaught parse error would exit 1
    # through the interpreter and be read as a drift verdict — the very
    # misclassification the exit-code contract was introduced to remove.
    try:
        with target.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    e = json.loads(line)
                    frozen[e["path"]] = e["sha256"]
                    if e.get("resolved"):
                        frozen_resolved.add(e["path"])
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        _fail(f"{target} is not a usable freeze manifest: {type(exc).__name__}: {exc}")
    entries = _entries()
    current = {e["path"]: e["sha256"] for e in entries}
    current_resolved = {e["path"] for e in entries if e.get("resolved")}

    added = sorted(set(current) - set(frozen))
    removed = sorted(set(frozen) - set(current))
    changed = sorted(p for p in set(frozen) & set(current) if frozen[p] != current[p])
    # A version flip changes nothing in the file set — both versions are frozen —
    # so the resolved set is compared on its own.
    # Only paths that are still PRESENT: a removed file is already reported as
    # removed, and counting it again under "no longer resolved" made one missing
    # file read as two drifted problems under two labels.
    still_present = set(frozen) & set(current)
    unresolved = sorted((frozen_resolved - current_resolved) & still_present)
    newly = sorted((current_resolved - frozen_resolved) & still_present)

    for label, paths in (("added", added), ("removed", removed), ("changed", changed),
                         ("no longer resolved", unresolved), ("newly resolved", newly)):
        for p in paths:
            print(f"{label}: {p}")

    drift = len(added) + len(removed) + len(changed) + len(unresolved) + len(newly)
    print(f"{len(frozen)} frozen, {len(current)} present, {drift} drifted")
    if drift:
        # Per-label totals, so a drift report can be quoted instead of counted
        # by hand from the path lines above.
        print(f"  {len(added)} added · {len(removed)} removed · {len(changed)} changed · "
              f"{len(unresolved)} no longer resolved · {len(newly)} newly resolved")
    # Non-zero on drift: a measurement taken against a corpus that no longer
    # matches its freeze is not reproducible, and that has to be loud.
    return EXIT_DRIFT if drift else EXIT_CLEAN


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("write", "verify"):
        print(__doc__.strip().split("Usage:")[-1].strip())
        return 2
    return (write if sys.argv[1] == "write" else verify)(Path(sys.argv[2]))


if __name__ == "__main__":
    sys.exit(main())
