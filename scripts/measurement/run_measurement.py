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
    python3 scripts/measurement/run_measurement.py <frozen-manifest.jsonl> --rehearsal
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCHLIFF = _REPO / "skills" / "schliff"


def _verify(manifest: Path, when: str) -> bool:
    """Run the freeze check and report honestly which kind of failure it was.

    `freeze_corpus.py` fails for reasons that are not drift — a truncated
    discovery walk, an unfreezable file, a manifest that is not JSON, a path that
    does not exist — and it says so on stderr. Capturing that stream and printing
    only stdout announced "the corpus no longer matches its freeze" for all of
    them, with the evidence discarded: a typo in the path produced a confident
    drift verdict for a file that was never there. On the pre-registered date
    that hands the operator a re-freeze decision for an unrelated problem.
    """
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("freeze_corpus.py")), "verify", str(manifest)],
        cwd=_REPO, capture_output=True, text=True,
    )
    if proc.stdout.strip():
        # Labelled: the run verifies twice, and two identical lines with no
        # indication of which is which is not an operator-readable transcript.
        for line in proc.stdout.rstrip().splitlines():
            print(f"[freeze {when}] {line}")
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    # stdout is block-buffered whenever it is redirected, so without this the
    # verdict below lands before the evidence above it — and "see the error
    # above" pointed downward in a tee'd log. Verified both ways.
    sys.stdout.flush()
    if proc.returncode == 0:
        return True

    drifted = any(line.startswith(("added:", "removed:", "changed:")) for line in proc.stdout.splitlines())
    if drifted:
        print(
            f"\nMEASUREMENT NOT TAKEN — the corpus no longer matches its freeze ({when} measuring).\n"
            "Decide, and record which you chose:\n"
            "  * re-freeze and say so in the case study, or\n"
            "  * measure against the frozen set.\n"
            "Publishing a number whose corpus is unknown is the one option that is not open.",
            file=sys.stderr,
        )
    else:
        print(
            f"\nMEASUREMENT NOT TAKEN — the freeze check itself failed ({when} measuring); "
            "see the error above. This is NOT a drift verdict and does not call for a re-freeze.",
            file=sys.stderr,
        )
    return False


def _cli(*args: str) -> dict:
    """Run the packaged CLI and return its JSON, failing loudly rather than partially."""
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.cli", *args, "--json"],
        cwd=_SCHLIFF, capture_output=True, text=True,
    )
    if proc.stderr.strip():
        # Doctor exits 0 while warning about regex timeouts and unreadable files.
        # On the one run whose whole design is failing loudly and saying why,
        # those must not vanish because stderr was captured.
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(f"`schliff {' '.join(args)}` exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"`schliff {' '.join(args)}` produced no JSON: {exc}") from exc


def main() -> int:
    args = sys.argv[1:]
    # A rehearsal writes a differently-named file and marks itself in the record.
    # The previous guard only refused a same-day collision, so a rehearsal today
    # and the pre-registered run on another date produced two files that are
    # indistinguishable by name or content — which is the failure its own comment
    # described, still open.
    rehearsal = "--rehearsal" in args
    args = [a for a in args if a != "--rehearsal"]
    if len(args) != 1:
        print(__doc__.strip().split("Usage:")[-1].strip())
        return 2
    manifest = Path(args[0]).resolve()

    if not _verify(manifest, "before"):
        return 1

    man = _cli("manifest")
    doc = _cli("doctor", str(Path.home() / ".claude"))

    # Re-verify. Three processes walk the corpus and the README's own premise is
    # that plugin updates rewrite it unattended — one landed at 08:37 on
    # 2026-08-31 and moved the count from 159 to 161. Measured, the window here
    # is about three seconds. Small, and the whole point of this artifact is that
    # a number is never published against an unverified corpus.
    if not _verify(manifest, "after"):
        return 1

    if doc["failed"]:
        # `skills_found` is len(results) - failed and `total_tokens` sums only
        # rows without an error, so one skill that raises during scoring
        # publishes a smaller installation count and a smaller token total, with
        # `digest_degraded: false` — byte-shape identical to a clean run. doctor
        # carries the fact in `summary` and prints nothing to stderr, so nothing
        # else would have surfaced it.
        print(
            f"\nMEASUREMENT NOT TAKEN — {doc['failed']} skill(s) failed to score, so both the "
            f"installation count and the token total are short by an unknown amount.\n"
            f"doctor says: {doc.get('summary', '(no summary)')}",
            file=sys.stderr,
        )
        return 1

    if doc["digest_degraded"]:
        # Checked BEFORE writing. The drift path refuses without leaving a file;
        # this one used to write the record and complain afterwards, so an exit-1
        # run still produced an artifact indistinguishable from a good one — and
        # its `duplicate_groups: 0` reads as "none found" rather than "not
        # measured", while `installations` is the pre-fix over-count.
        print(
            "\nMEASUREMENT NOT TAKEN — `digest_degraded` is set: the duplicate collapse "
            "fell back, so the installation count is the pre-fix number by definition.",
            file=sys.stderr,
        )
        return 1

    record = {
        "measured_on": date.today().isoformat(),
        "rehearsal": rehearsal,
        "frozen_corpus": manifest.name,
        "headline": {"resident_tokens": man["resident_tokens"], "artifacts": man["loaded_count"]},
        # Recorded, not summarised: `resident` sums every loaded artifact, and
        # manifest's findings are the only place a consumer learns that one of
        # them is unreachable. Verified on this corpus that `nested` and
        # `disabled` artifacts are NOT in `loaded`, so they do not inflate the
        # headline — but `duplicate-name` and `no-skill-md` are exactly the
        # signals a published figure should carry with it.
        "manifest_findings": [{"kind": f["kind"], "subject": f["subject"]}
                              for f in man.get("findings", [])],
        "context": {
            "invoke_tokens": man["invoke_tokens"],
            "on_disk_tokens": doc["total_tokens"],
            "installations": doc["skills_found"],
            "files_discovered": doc["skills_discovered"],
            "duplicate_groups": len(doc["duplicate_copies"]),
            "broken_eval_suites": doc["broken_eval_suite"],
            "digest_degraded": doc["digest_degraded"],
            "failed_to_score": doc["failed"],
        },
    }
    prefix = "rehearsal" if rehearsal else "measurement"
    out = manifest.parent / f"{prefix}-{record['measured_on']}.json"
    if out.exists():
        # The name carries only a date, so a rehearsal and the pre-registered run
        # collide. One already did: a dry run wrote `measurement-2026-09-01.json`
        # that read exactly like a real measurement and had to be deleted by hand.
        # The sibling script guards this class; this one did not.
        raise SystemExit(
            f"{out.name} already exists. Delete it deliberately if this run is meant "
            f"to replace it — an overwritten measurement leaves no trace that it was one."
        )
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
