#!/usr/bin/env python3
"""Take the pre-registered context-cost measurement, or refuse and say why.

One command, so that on the measurement date nothing is left to decide except
the thing that genuinely needs judgement. It does three things in order and
stops at the first that fails:

1. **Verify the freeze.** A number measured against a corpus that no longer
   matches its manifest is not reproducible, and that is the whole reason the
   freeze exists. Drift is named file by file and the run stops — re-freezing is
   a decision, not something a script should make silently.
2. **Take the three figures** from the tools that own them: `manifest` for
   `resident` and `invoke`, `doctor` for the on-disk total and the installation
   count. Nothing is recomputed here.
3. **Write a dated record** beside the freeze it was taken against, naming the
   manifest by filename so the pair cannot drift apart later.

Usage:
    python3 scripts/measurement/run_measurement.py <frozen-manifest.jsonl>
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCHLIFF = _REPO / "skills" / "schliff"


def _cli(*args: str) -> dict:
    """Run the packaged CLI and return its JSON, failing loudly rather than partially."""
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.cli", *args, "--json"],
        cwd=_SCHLIFF, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"`schliff {' '.join(args)}` exited {proc.returncode}:\n{proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"`schliff {' '.join(args)}` produced no JSON: {exc}") from exc


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().split("Usage:")[-1].strip())
        return 2
    manifest = Path(sys.argv[1]).resolve()

    freeze = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("freeze_corpus.py")), "verify", str(manifest)],
        cwd=_REPO, capture_output=True, text=True,
    )
    print(freeze.stdout.rstrip())
    if freeze.returncode != 0:
        print(
            "\nMEASUREMENT NOT TAKEN — the corpus no longer matches its freeze.\n"
            "Decide, and record which you chose:\n"
            "  * re-freeze and say so in the case study, or\n"
            "  * measure against the frozen set.\n"
            "Publishing a number whose corpus is unknown is the one option that is not open.",
            file=sys.stderr,
        )
        return 1

    man = _cli("manifest")
    doc = _cli("doctor", str(Path.home() / ".claude"))

    record = {
        "measured_on": date.today().isoformat(),
        "frozen_corpus": manifest.name,
        "headline": {"resident_tokens": man["resident_tokens"], "artifacts": man["loaded_count"]},
        "context": {
            "invoke_tokens": man["invoke_tokens"],
            "on_disk_tokens": doc["total_tokens"],
            "installations": doc["skills_found"],
            "files_discovered": doc["skills_discovered"],
            "duplicate_groups": len(doc["duplicate_copies"]),
            "digest_degraded": doc["digest_degraded"],
        },
    }
    out = manifest.parent / f"measurement-{record['measured_on']}.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\nheadline  resident {record['headline']['resident_tokens']:,} tokens "
          f"across {record['headline']['artifacts']} artifacts")
    c = record["context"]
    print(f"context   invoke {c['invoke_tokens']:,} · on disk {c['on_disk_tokens']:,} "
          f"across {c['installations']} installations")
    try:
        shown = out.relative_to(_REPO)
    except ValueError:
        shown = out
    print(f"written   {shown}")
    if c["digest_degraded"]:
        # The collapse fell back; the installation count is the pre-fix number.
        print("\nWARNING: digest_degraded — the duplicate collapse did not run. "
              "Do not publish the installation count from this run.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
