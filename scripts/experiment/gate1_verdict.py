#!/usr/bin/env python3
"""Take the plugin-channel experiment's Gate 1 reading and state the mechanical verdict.

Runs on GitHub Actions (`.github/workflows/gate1-verdict.yml`), because the Claude
Code cloud environment cannot read another repository (probed 2026-10-02, see #198).

Everything it decides comes from the spec, docs/specs/2026-08-11-plugin-channel-experiment.md:

- the submission PR URLs, from the clock table's "First/Second submission PR URL" rows;
- the deadline, 23:59:59 UTC on D0+21, from the clock table's D0 row;
- the rule: GREEN if any submission has `merged_at` at or before the deadline, else
  RED-DISTRIBUTION with Gate 2 NOT-REACHED, and a PR still open at the deadline is
  recorded as censored (open, not rejected) per E-4.

It prints the deciding reading and the rule's label, with E-4's censoring in the same
sentence. That is not the reported verdict: the spec requires the verdict to carry the
per-repo outcome and the N = 2 caveat, and the landing note, so the owner writes it as
the Gate 1 amendment. Only a resolved reading (now past the deadline) carries the marker
the workflow keys on, so a preview can never be posted.

Usage:
    python3 scripts/experiment/gate1_verdict.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

SPEC = Path(__file__).resolve().parents[2] / "docs/specs/2026-08-11-plugin-channel-experiment.md"
MARKER = "<!-- gate1-verdict -->"
_PR_URL = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)")


def submission_urls(spec: str) -> list[str]:
    """The PR URLs recorded in the clock table's submission rows, in order."""
    urls = []
    for line in spec.splitlines():
        if re.match(r"\|\s*(First|Second) submission PR URL", line):
            urls += [m.group(0) for m in _PR_URL.finditer(line)]
    return urls


def deadline(spec: str) -> datetime:
    """23:59:59 UTC on D0+21, D0 taken from the clock table's D0 row."""
    for line in spec.splitlines():
        if line.startswith("| D0 "):
            found = re.search(r"\*\*(\d{4}-\d{2}-\d{2})\*\*", line)
            if found:
                d0 = date.fromisoformat(found.group(1))
                return datetime.combine(d0 + timedelta(days=21), time(23, 59, 59), timezone.utc)
    raise ValueError("no D0 date in the spec's clock table")


def _ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def judge(prs: list[dict], cutoff: datetime) -> dict:
    """The verdict for `prs` (GitHub REST pull objects) against `cutoff`."""
    on_time = sorted(_ts(p["merged_at"]) for p in prs
                     if _ts(p.get("merged_at")) and _ts(p["merged_at"]) <= cutoff)
    rows = []
    for p in prs:
        merged, closed = _ts(p.get("merged_at")), _ts(p.get("closed_at"))
        if merged and merged <= cutoff:
            status = f"merged on time ({p['merged_at']})"
        elif merged:
            status = (f"open at the deadline: censored (open, not rejected); "
                      f"merged later ({p['merged_at']})")
        elif closed and closed <= cutoff:
            status = f"closed unmerged before the deadline ({p['closed_at']})"
        else:
            status = "open at the deadline: censored (open, not rejected)"
        rows.append((p["html_url"], p["created_at"], status))
    if on_time:
        a0 = on_time[0].date()
        return {"verdict": "GREEN", "rows": rows, "a0": a0.isoformat(),
                "gate2": f"opens: A0 = {a0}, window ends 23:59 UTC on {a0 + timedelta(days=30)}"}
    return {"verdict": "RED-DISTRIBUTION", "rows": rows, "a0": None, "gate2": "NOT-REACHED"}


def outcome_sentence(result: dict) -> str:
    """The rule's label, with E-4's censoring in the same sentence when it applies."""
    sentence = f"Rule outcome: **{result['verdict']}**"
    censored = [u for u, _, s in result["rows"] if s.startswith("open at the deadline")]
    if result["verdict"] != "GREEN" and censored:
        sentence += (", censored (open, not rejected): "
                     + ", ".join(censored) + " was open at the deadline")
    return sentence + f". Gate 2: {result['gate2']}."


def render(result: dict, cutoff: datetime, now: datetime, raw: list[dict]) -> str:
    resolved = now > cutoff
    head = (f"{MARKER}\n**Gate 1 deciding reading, taken {now:%Y-%m-%dT%H:%M:%SZ}** "
            f"(deadline {cutoff:%Y-%m-%dT%H:%M:%SZ})" if resolved else
            f"**PREVIEW, not a reading: the deadline {cutoff:%Y-%m-%dT%H:%M:%SZ} has not passed "
            f"(now {now:%Y-%m-%dT%H:%M:%SZ}).**")
    lines = [head, "", outcome_sentence(result), "",
             "This is the deciding reading and the label the spec's rule gives it, not the "
             "reported verdict. The spec requires the verdict to name the per-repo outcome as "
             "1 in-scope channel plus 1 out-of-scope channel, never a bare fraction of 2, and to "
             "carry the N = 2 caveat; that report is the Gate 1 amendment in "
             "docs/specs/2026-08-11-plugin-channel-experiment.md.", ""]
    lines += ["| Submission PR | created_at | status at the deadline |", "| --- | --- | --- |"]
    lines += [f"| {u} | {c} | {s} |" for u, c, s in result["rows"]]
    lines += ["", "Raw reading (GitHub REST):", "", "```json",
              json.dumps(raw, indent=2), "```", "",
              "The landing note (2026-09-29 amendment) is written when the verdict is written and "
              "records each qualified repo's catalog state at that time; it never changes the label."]
    return "\n".join(lines) + "\n"


def fetch(url: str) -> dict:
    owner, repo, number = _PR_URL.fullmatch(url).groups()
    out = subprocess.run(["gh", "api", f"repos/{owner}/{repo}/pulls/{number}"],
                         capture_output=True, text=True, check=True).stdout
    pr = json.loads(out)
    return {k: pr.get(k) for k in ("html_url", "state", "created_at", "merged_at", "closed_at")}


def main() -> int:
    spec = SPEC.read_text(encoding="utf-8")
    urls = submission_urls(spec)
    if not urls:
        print("::error::no submission PR URL in the spec's clock table", file=sys.stderr)
        return 1
    cutoff = deadline(spec)
    raw = [fetch(u) for u in urls]
    sys.stdout.write(render(judge(raw, cutoff), cutoff, datetime.now(timezone.utc), raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
