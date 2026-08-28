#!/usr/bin/env python3
"""Schliff Doctor — Health Check for All Installed Skills

Scans all installed skills, scores each one, and produces a summary table
with actionable recommendations. Single command, zero arguments needed.

Usage:
    python3 doctor.py [--skill-dirs DIR...] [--repo DIR] [--json] [--verbose]

Output: Table of skills with structural scores, issues, and suggested actions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import score_skill as scorer
import skill_mesh
from terminal_art import grade_colored, score_to_grade

import shared
from scoring.formats import detect_format
from shared import EXCLUDED_DIRS, estimate_token_cost, skill_payload_digest

# Filenames to match (lowercase) for instruction file discovery
_INSTRUCTION_FILENAMES = {"claude.md", ".cursorrules", "agents.md"}

# Width of the Action column for a row that carries a repair reason. Wide
# enough for the longest action doctor can compose, which is the grouped-and-
# broken form plus the longest reason `load_eval_suite` records. Asserted by
# test_repair_action_fits_its_column rather than trusted: the previous value
# was picked by eye and silently cut "not a JSON object" to "not a JSON objec".
REPAIR_ACTION_WIDTH = 80

# The two path-free action shapes. Named, not inlined, because the width gate has
# to enumerate exactly the strings that reach the wide column — the previous gate
# derived only the repair prefix and so did not cover the grouped action, which
# was 35 characters against a 35-wide cap with zero margin.
BROKEN_ACTION_PREFIX = "Fix eval-suite.json first: "
GROUPED_ACTION = "Scored once; other paths are listed above"
GROUPED_ACTION_PREFIX = "Scored once; eval-suite.json: "


def discover_instruction_files(root_dir: str) -> list[dict]:
    """Discover all project instruction files in a directory tree.

    Finds: CLAUDE.md, .cursorrules, AGENTS.md (any case).
    Excludes: .git/, node_modules/, venv/, __pycache__/, .venv/

    Uses detect_format() from scoring.formats to classify each file.

    Returns list of dicts:
    [{"path": "/abs/path/to/CLAUDE.md", "format": "claude.md", "name": "CLAUDE.md"}, ...]
    """
    results: list[dict] = []
    for dirpath, dirs, files in os.walk(root_dir):
        # Skip excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in files:
            if fname.lower() in _INSTRUCTION_FILENAMES:
                full_path = os.path.join(dirpath, fname)
                abs_path = os.path.abspath(full_path)
                fmt = detect_format(fname)
                results.append({
                    "path": abs_path,
                    "format": fmt,
                    "name": fname,
                })
    results.sort(key=lambda r: r["path"])
    return results


def _default_skill_dirs() -> list[str]:
    """Return default skill scan directories."""
    return [
        str(Path.home() / ".claude" / "skills"),
        ".claude/skills",
    ]


def _score_single_skill(skill_path: str) -> dict:
    """Score a single skill and return summary."""
    from scoring.credentials import scan_credentials
    from shared import build_scores, load_eval_suite, read_skill_safe

    eval_suite = load_eval_suite(skill_path)
    scores = build_scores(skill_path, eval_suite)

    # Doctor reports, it never gates — as every surface now does (ADR 0019).
    # Doctor was the first place the argument held: these are usually somebody
    # else's files, and a red exit on a file you cannot edit helps nobody
    # (ADR 0014). Raw content so the line points at the real file (ADR 0016).
    # `None` means "could not scan", which is not the same as "scanned, clean".
    # verify.py got this contract; doctor did not, so an oversize file with a
    # live key printed a row with no credential line and any `--json` consumer
    # testing `if r["credentials"]:` read it as clean.
    try:
        credentials = scan_credentials(read_skill_safe(skill_path))
    except (OSError, ValueError):
        credentials = None

    composite = scorer.compute_composite(scores)

    # Collect all issues
    all_issues = []
    for dim, data in scores.items():
        for issue in data.get("issues", []):
            all_issues.append(f"[{dim}] {issue}")

    # Check for skill-specific recommendations
    recommendations = []
    structure_issues = scores.get("structure", {}).get("issues", [])
    line_count = scores.get("structure", {}).get("details", {}).get("line_count", 0)
    if "no_progressive_disclosure" in structure_issues and line_count > 300:
        recommendations.append(
            f"Consider extracting into references/ — {line_count} lines without progressive disclosure"
        )

    # Determine recommended action
    score = composite["score"]
    has_eval = eval_suite is not None

    # A suite that is present but unreadable is not the same as no suite. It was
    # degraded to None so one bad file cannot end the run, but telling the user
    # to run /schliff:init here would write eval-suite.json over the very file
    # that failed to load.
    # `shared.eval_suite_error`, not a bound alias: a later per-run reset in
    # shared would leave an import-time binding reading a dead dict, and every
    # row would silently report no suite error.
    suite_error = shared.eval_suite_error.get(str(Path(skill_path).parent / "eval-suite.json"))

    if suite_error:
        action = f"{BROKEN_ACTION_PREFIX}{suite_error}"
    elif not has_eval:
        action = f"/schliff:init {skill_path}"
    elif score < 50:
        action = f"/schliff:auto {skill_path}"
    elif score < 80:
        action = f"/schliff:auto {skill_path}"
    elif score < 95:
        action = f"/schliff:analyze {skill_path}"
    else:
        action = "Healthy"

    tokens = estimate_token_cost(skill_path)

    return {
        "composite": score,
        "score_type": composite.get("score_type", "structural"),
        "grade": score_to_grade(score),
        "measured": composite["measured_dimensions"],
        "total_dims": composite["total_dimensions"],
        "has_eval_suite": has_eval,
        "issue_count": len(all_issues),
        "issues": all_issues,
        "action": action,
        "eval_suite_error": suite_error,
        "tokens": tokens,
        "recommendations": recommendations,
        # Vendor + line only, never the value (ADR 0014).
        "credentials": credentials,
    }


def _collapse_duplicate_copies(skills: list[dict]) -> tuple[list[dict], list[dict]]:
    """Count one install per distinct payload, and report the copies.

    A plugin that is both cached and vendored appears twice on disk, so the
    count, the grades and the headline token cost were all inflated. Identity is
    ``shared.skill_payload_digest``.

    Why a digest and not another ``EXCLUDED_DIRS`` entry — the path exclusion
    was measured and rejected — plus the before/after numbers: docs/specs/2026-08-13-doctor-counts-vendored-skills.md,
    "Amendment 2026-08-26".

    Nothing is deleted; every path in a group is reported and the caller decides
    (ADR 0019). The counted copy is the first in discovery order, which sorts by
    path. Sort order is not merit, and which member it favours depends on the
    directories being scanned, so no member may be named by a runnable command:
    the row for a group carries no ``action`` that acts on a path. Preferring a
    member on any other basis would need a path wordlist — the enumeration this
    key exists to avoid.

    What the group asserts is bounded by what the digest reads. Two members can
    differ in anything outside SKILL.md, ``references/*.md`` and
    ``eval-suite.json`` — including their version, and including whether both are
    live installs. The report states the comparison and never concludes from it.

    Skills whose digest could not be computed are all kept: an empty digest is
    not an identity, so they must not collapse together.
    """
    seen: dict[str, dict] = {}
    groups: dict[str, list[str]] = {}
    unique: list[dict] = []

    for skill in skills:
        path = skill.get("path", "")
        digest = skill_payload_digest(path) if path else ""
        if not digest:
            unique.append(skill)
            continue
        if digest in seen:
            groups.setdefault(digest, [seen[digest].get("path", "")]).append(path)
            continue
        seen[digest] = skill
        unique.append(skill)

    duplicates = [
        {
            "name": seen[digest].get("name", ""),
            "payload_digest": digest,
            "counted": paths[0],
            "also_installed_at": paths[1:],
        }
        for digest, paths in groups.items()
    ]
    duplicates.sort(key=lambda d: d["name"])
    return unique, duplicates


def run_doctor(
    skill_dirs: list[str] | None = None,
    verbose: bool = False,
    repo_root: str | None = None,
) -> dict:
    """Run doctor scan across all installed skills."""
    dirs = skill_dirs or _default_skill_dirs()

    # Discover all skills
    skills = skill_mesh.discover_skills(dirs)

    if not skills:
        # Discover instruction files even when no skills found
        scan_root = repo_root or "."
        instruction_files = discover_instruction_files(scan_root)
        return {
            "skills_found": 0,
            "scored": 0,
            "failed": 0,
            "healthy": 0,
            "needs_work": 0,
            "no_eval_suite": 0,
            "total_tokens": 0,
            "skills_discovered": 0,
            "duplicate_copies": [],
            "broken_eval_suite": 0,
            "grouped_duplicates": 0,
            "grouped_broken_eval_suite": 0,
            "digest_degraded": False,
            "mesh_health": 100,
            "mesh_issue_count": 0,
            "results": [],
            "instruction_files": instruction_files,
            "drift_findings": [],
            "summary": "No skills found. Check skill directories.",
        }

    # The digest phase is the only walk that runs OUTSIDE `_score_single_skill`'s
    # handler, and `skill_payload_digest` reaches `read_skill_safe`, which reads
    # before it checks size and can therefore raise `MemoryError` — not an
    # `OSError`, not a `ValueError`, so that function's own guard does not see it.
    # `_payload_files` justifies leaving `read_skill_safe` outside the bounded
    # reader on the grounds that "its callers sit inside a handler"; this caller
    # did not, which made the premise false exactly where the run is hardest to
    # recover. Falling back to no collapsing reports every copy — an over-count,
    # which this module has repeatedly recorded as the survivable direction.
    digest_degraded = False
    try:
        unique_skills, duplicate_copies = _collapse_duplicate_copies(skills)
    except Exception as exc:  # noqa: BLE001 — one bad file must not end the run
        print(f"Warning: duplicate detection failed ({type(exc).__name__}), "
              f"reporting every copy separately", file=sys.stderr)
        unique_skills, duplicate_copies = skills, []
        digest_degraded = True
    # path -> the other install locations, so a row carries its own signal. A
    # --json consumer acting on `action` would otherwise have to join against
    # duplicate_copies to learn that the path it was handed is whichever member
    # sorted first, which is not necessarily the copy worth acting on.
    copies_by_path = {d["counted"]: d["also_installed_at"] for d in duplicate_copies}

    results = []
    healthy = 0
    needs_work = 0
    no_eval = 0
    broken_eval = 0
    grouped = 0
    grouped_broken = 0
    failed = 0

    for skill in unique_skills:
        path = skill["path"]
        name = skill["name"]

        try:
            score_result = _score_single_skill(path)
        except Exception as e:
            failed += 1
            results.append({
                "name": name,
                "path": path,
                "error": str(e),
            })
            continue

        result = {
            "name": name,
            "path": path,
            **score_result,
        }
        # Present only when this row stands for more than one install. `path` and
        # therefore `action` name whichever member sorted first, which is picked
        # by sort order and not by merit.
        if path in copies_by_path:
            result["also_installed_at"] = copies_by_path[path]
            # `path` is one member of a group, picked by sort order rather than
            # by merit, so no runnable command may name it. The action states
            # what was measured — one score and one cost — and never what the
            # reader should do to the filesystem: the digest covers SKILL.md,
            # `references/*.md` and `eval-suite.json`, so two members can differ
            # in everything else, including their version.
            reason = result.get("eval_suite_error")
            result["action"] = (
                f"{GROUPED_ACTION_PREFIX}{reason}" if reason else GROUPED_ACTION
            )
        results.append(result)

        if path in copies_by_path:
            # A grouped row's own action says to resolve the duplicate, and its
            # path was picked by sort order. Counting it as "missing an eval suite"
            # would put it in the /schliff:init recommendation below — writing
            # into a directory the next plugin update deletes, and contradicting
            # the row three lines above. Same carve-out doctor.md step 5 makes.
            #
            # The buckets stay disjoint, so `grouped_broken` is tracked beside them
            # rather than inside them: a grouped row whose suite is ALSO broken was
            # otherwise counted nowhere, and the "Recommended next steps" block is
            # gated on those counts — so the whole block vanished, taking the
            # "do NOT run /schliff:init on these, it writes over them" line with it.
            # That line is the strongest warning the report has, and it applies to
            # a grouped row exactly as much as to a lone one. It names no path, so
            # printing it cannot point the reader at a copy picked by sort order.
            grouped += 1
            if score_result.get("eval_suite_error"):
                grouped_broken += 1
        elif score_result.get("eval_suite_error"):
            # Present but unreadable. Counting it as "missing" would put it in
            # the /schliff:init recommendation below, which writes eval-suite.json
            # over the file that failed to load — contradicting this same row's
            # own action three lines above.
            broken_eval += 1
        elif not score_result["has_eval_suite"]:
            no_eval += 1
        elif score_result["composite"] >= 80:
            healthy += 1
        else:
            needs_work += 1

    # Compute total token cost across all skills
    total_tokens = sum(r.get("tokens", 0) for r in results if "error" not in r)

    # Sort by score ascending (worst first — they need attention)
    results.sort(key=lambda r: r.get("composite", 0))

    # Run mesh analysis for cross-skill issues. Reuse the skills already
    # discovered above so the tree is not walked and every SKILL.md is not read
    # a second time within a single doctor run.
    mesh_result = skill_mesh.run_mesh_analysis(dirs, incremental=True, skills=skills)
    mesh_issues = mesh_result.get("issues", [])
    mesh_health = mesh_result.get("health", {}).get("score", 100)

    discovered = len(skills)
    scanned = (
        f"{len(results)} skills scanned"
        if discovered == len(results)
        else f"{len(results)} skills scanned ({discovered} files, duplicates counted once)"
    )
    summary_parts = [scanned]
    if healthy:
        summary_parts.append(f"{healthy} healthy")
    if needs_work:
        summary_parts.append(f"{needs_work} need work")
    if no_eval:
        summary_parts.append(f"{no_eval} missing eval suite")
    if broken_eval:
        summary_parts.append(f"{broken_eval} unreadable eval suite")
    if grouped:
        # Excluded from every other bucket on purpose, so without this line these
        # rows appear in no tally at all — 20 of 138 on a real installation.
        summary_parts.append(f"{grouped} counted once")
    if failed:
        summary_parts.append(f"{failed} failed to score")
    if mesh_issues:
        summary_parts.append(f"{len(mesh_issues)} mesh issues")

    # Discover project instruction files
    scan_root = repo_root or "."
    instruction_files = discover_instruction_files(scan_root)

    # Drift analysis on discovered instruction files
    drift_findings: list[dict] = []
    if instruction_files and repo_root:
        try:
            import drift as drift_mod
            for ifile in instruction_files:
                try:
                    content = Path(ifile["path"]).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                refs = drift_mod.extract_references(content)
                if refs:
                    # References in an instruction file are conventionally
                    # relative to that file's own directory, not the repo root.
                    base_dir = os.path.dirname(ifile["path"]) or repo_root
                    findings = drift_mod.validate_references(refs, base_dir)
                    missing = [f for f in findings if f["status"] == "missing"]
                    if missing:
                        drift_findings.extend(
                            {**f, "source_file": ifile["name"]} for f in missing
                        )
        except ImportError:
            pass  # drift module not available — skip

    if drift_findings:
        summary_parts.append(f"{len(drift_findings)} stale references")

    return {
        "skills_found": len(results) - failed,
        "scored": len(results) - failed,
        "failed": failed,
        "healthy": healthy,
        "needs_work": needs_work,
        "no_eval_suite": no_eval,
        "broken_eval_suite": broken_eval,
        "grouped_duplicates": grouped,
        # A consumer that publishes `skills_found` has to be able to see that the
        # collapse did not run: without this the fallback's output is byte-shape
        # identical to a clean scan that found no duplicates, so a case study
        # generated from --json would publish the pre-fix count with no marker.
        "digest_degraded": digest_degraded,
        "grouped_broken_eval_suite": grouped_broken,
        "total_tokens": total_tokens,
        # Physical files on disk, before collapsing copies. `skills_found` is the
        # deduplicated count; without this the difference is only recoverable by
        # summing `also_installed_at`.
        "skills_discovered": len(skills),
        "duplicate_copies": duplicate_copies,
        "mesh_health": mesh_health,
        "mesh_issue_count": len(mesh_issues),
        "results": results,
        "instruction_files": instruction_files,
        "drift_findings": drift_findings,
        "scan_root": scan_root,
        "summary": " | ".join(summary_parts),
    }


def format_doctor_report(report: dict, verbose: bool = False) -> str:
    """Format doctor report as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("  Schliff Doctor — Skill Health Check")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  {report['summary']}")
    lines.append("")

    results = report.get("results", [])
    if not results:
        lines.append("  No skills found in scanned directories.")
        lines.append("")
        lines.append("  Default scan dirs:")
        for d in _default_skill_dirs():
            lines.append(f"    - {d}")
        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)

    # Total token cost
    total_tokens = report.get("total_tokens", 0)
    if total_tokens > 0:
        lines.append(f"  Total context cost: ~{total_tokens:,} tokens")
        lines.append("")

    # One scored payload found at several paths — counted once. The block states
    # what was compared and stops there. It said "installed more than once …
    # extra copies … so you can delete one", and that is a verdict about the
    # filesystem this key never measured: on the real install one group is two
    # ACTIVE plugin versions (0.1.13 and 0.1.15 of the same plugin, both present
    # in `~/.claude/plugins/installed_plugins.json`, one project-scoped and one
    # user-scoped) whose directories differ outside the digest domain, and sort
    # order names the older one as the survivor. Capped like the drift block below.
    duplicate_copies = report.get("duplicate_copies", [])
    if duplicate_copies:
        extra = sum(len(d["also_installed_at"]) for d in duplicate_copies)
        n = len(duplicate_copies)
        lines.append(
            f"  {n} {'skill has' if n == 1 else 'skills have'} an identical scored "
            f"payload at {extra + n} paths — each counted once "
            f"({extra} {'path' if extra == 1 else 'paths'} collapsed):"
        )
        lines.append(
            "    Compared: SKILL.md, references/*.md, eval-suite.json — the files "
            "the score and the cost come from. The directories themselves were "
            "NOT compared and may differ, including in version."
        )
        lines.append(
            "    The counted path is whichever sorted first, an artifact of sort "
            "order rather than a recommendation."
        )
        lines.append(
            "    Mesh findings below are counted per file, not per install, so "
            "these copies appear there too."
        )
        for d in duplicate_copies[:10]:
            lines.append(f"    {d['name']}")
            lines.append(f"      counted: {d['counted']}")
            for other in d["also_installed_at"]:
                lines.append(f"      also at: {other}")
        if len(duplicate_copies) > 10:
            lines.append(f"    ... and {len(duplicate_copies) - 10} more")
        lines.append("")

    # Table header
    lines.append(f"  {'Skill':<25s} {'Score':>6s} {'Grade':>6s} {'Dims':>6s} {'Tokens':>7s} {'Issues':>7s}  Action")
    lines.append("  " + "-" * 76)

    for r in results:
        if "error" in r:
            lines.append(f"  {r['name']:<25s}  ERROR: {r['error'][:40]}")
            continue

        name = r["name"][:24]
        score = r["composite"]
        # Right-align the Grade column on its VISIBLE width ([X] == 3 cols);
        # padding must live outside any ANSI color wrap so colored output stays
        # aligned with the (uncolored) header.
        grade_pad = " " * max(0, 6 - len(f"[{r['grade']}]"))
        grade = grade_pad + grade_colored(r["grade"])
        dims = f"{r['measured']}/{r['total_dims']}"
        tokens = r.get("tokens", 0)
        issues = r["issue_count"]
        # The reason is the whole payload of a repair action, so keep it whole
        # rather than truncating to "Fix eval-suite.json first (unreadab".
        # 70 was still too narrow for the composed grouped-and-broken form
        # (the composed grouped-and-broken prefix runs well past 35 characters
        # before the reason even starts), so it truncated the exact word it was
        # widened to preserve: "not a JSON objec". The width is not
        # a guess — test_repair_action_fits_its_column derives the longest
        # composed action from the reasons load_eval_suite can actually produce
        # and fails if it stops fitting, so a new reason cannot re-open this.
        # Path-free actions get the wide column; the narrow one exists for actions
        # that embed an absolute path (`/schliff:auto <path>`), where widening to
        # 80 would produce an 80-character clip of a path — neither whole nor
        # short. Grouped and repair actions are path-free by construction, which
        # is why the flag is the row's own shape and not a list of prefixes.
        path_free = r.get("eval_suite_error") or r.get("also_installed_at")
        action = r["action"][:REPAIR_ACTION_WIDTH] if path_free else r["action"][:35]

        lines.append(f"  {name:<25s} {score:>5.0f} {grade:s} {dims:>6s} {tokens:>7d} {issues:>7d}  {action}")

        # Credentials print unconditionally, not behind --verbose: a possible
        # leak is not a detail you opt into. Vendor and line only (ADR 0014).
        # `None` is the third state — the file could not be read, which must not
        # render as a clean row. "possible" is the same hedge `score` and
        # `verify` use, because the finding asserts shape and not authenticity
        # (ADR 0020); doctor in particular reads other people's files, where a
        # confident claim is least warranted.
        found = r.get("credentials", [])
        if found is None:
            lines.append(f"    {'':25s}  └─ credential scan: could not read the file")
        else:
            for finding in found:
                lines.append(
                    f"    {'':25s}  └─ possible credential: {finding['vendor']} "
                    f"at line {finding['line']}"
                )

        if verbose and r.get("issues"):
            for issue in r["issues"][:5]:  # Cap at 5 to avoid flooding
                lines.append(f"    {'':25s}  └─ {issue}")

    lines.append("")

    # Project instruction files
    instruction_files = report.get("instruction_files", [])
    lines.append("  Project Instruction Files")
    lines.append("  " + "-" * 25)
    if instruction_files:
        for f in instruction_files:
            rel_path = os.path.relpath(f["path"], start=report.get("scan_root", "."))
            lines.append(f"  {f['name']:<20s} {f['format']:<14s} ./{rel_path}")
    else:
        lines.append("  No project instruction files found.")
    lines.append("")

    # Drift findings
    drift_findings = report.get("drift_findings", [])
    if drift_findings:
        lines.append(f"  Stale References ({len(drift_findings)} found)")
        lines.append("  " + "-" * 25)
        for df in drift_findings[:10]:  # Cap at 10 to avoid flooding
            lines.append(f"    {df.get('source_file', '?')}: `{df['ref']}` (line {df['line']})")
        if len(drift_findings) > 10:
            lines.append(f"    ... and {len(drift_findings) - 10} more")
        lines.append("")

    # Mesh health
    mesh_health = report.get("mesh_health", 100)
    mesh_issues = report.get("mesh_issue_count", 0)
    if mesh_issues > 0:
        # "cross-skill" was accurate while every finding named a pair. A
        # duplicate name names one skill at two paths, so the summary says how
        # many findings there are and lets `/schliff:mesh` say what they are.
        noun = "finding" if mesh_issues == 1 else "findings"
        lines.append(f"  Mesh Health: {mesh_health}/100 ({mesh_issues} mesh {noun})")
        lines.append("  Run /schliff:mesh for details.")
        lines.append("")

    # Top-level recommendations
    no_eval = report.get("no_eval_suite", 0)
    broken_eval = report.get("broken_eval_suite", 0)
    needs_work = report.get("needs_work", 0)

    # The repair warning counts grouped-and-broken rows too. They are deliberately
    # absent from the disjoint buckets, and gating the block on those alone deleted
    # the only line telling the reader not to run /schliff:init over a file that
    # failed to load.
    broken_total = broken_eval + report.get("grouped_broken_eval_suite", 0)
    if no_eval > 0 or needs_work > 0 or broken_total > 0:
        lines.append("  Recommended next steps:")
        step = 0
        if no_eval > 0:
            step += 1
            lines.append(f"    {step}. Run /schliff:init on {no_eval} skills missing eval suites")
        if broken_total > 0:
            step += 1
            lines.append(
                f"    {step}. Repair {broken_total} unreadable eval-suite.json — "
                f"do NOT run /schliff:init on these, it writes over them"
            )
        if needs_work > 0:
            step += 1
            lines.append(f"    {step}. Run /schliff:auto on {needs_work} low-scoring skills")
        lines.append("")

    # Skill-specific recommendations.
    #
    # Grouped rows are carved out for the same reason the /schliff:init and
    # /schliff:auto tallies carve them out, and the same reason doctor.md step 5
    # does: the row's own `action` states that the payload was scored once, and
    # its path was picked by sort order rather than by merit. Printing
    # "extract into references/" beside that is an instruction to edit a file
    # this command did not choose — and it contradicts the row three lines up.
    skills_with_recs = [
        r for r in results
        if r.get("recommendations") and not r.get("also_installed_at")
    ]
    if skills_with_recs:
        lines.append("  Skill-specific recommendations:")
        for r in skills_with_recs:
            for rec in r["recommendations"]:
                lines.append(f"    - {r['name']}: {rec}")
        lines.append("")

    lines.append("  NOTE: Scores are STRUCTURAL — they measure file organization,")
    lines.append("  not runtime effectiveness. Runtime scoring requires an eval suite.")
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Schliff Doctor — Health Check for All Skills")
    parser.add_argument("--skill-dirs", nargs="+", default=None,
                        help="Directories to scan (default: ~/.claude/skills/, .claude/skills/)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-skill issues")
    parser.add_argument("--repo", default=None,
                        help="Repository root for instruction file discovery")
    args = parser.parse_args()

    report = run_doctor(skill_dirs=args.skill_dirs, verbose=args.verbose,
                        repo_root=args.repo)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_doctor_report(report, verbose=args.verbose))


if __name__ == "__main__":
    main()
