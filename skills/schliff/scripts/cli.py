#!/usr/bin/env python3
"""Schliff CLI — The finishing cut for Claude Code skills.

Usage:
    schliff score <path>             Score a SKILL.md file
    schliff compare <file_a> <file_b> Compare two files side by side
    schliff diff <path>              Explain score changes between git commits
    schliff verify <path>            CI gate — exit 0 if pass, 1 if fail
    schliff doctor                   Scan all installed skills
    schliff report <path>            Generate Markdown score report
    schliff badge <path>             Generate markdown badge
    schliff suggest <path>           Suggest ranked fixes with estimated score impact
    schliff demo                     Score a built-in bad skill
    schliff version                  Show version
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

# sys.path hack: scripts/ must be on sys.path because scripts/ is NOT a Python
# package (no __init__.py) — it's a flat collection of modules (shared.py, nlp.py)
# plus sub-packages (scoring/, evolve/).  cli.py is the sole entry point (via the
# `schliff` console_script in pyproject.toml), so this single path insertion is
# sufficient for all transitive imports.  Do NOT duplicate this in sub-packages.
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Help text for the positional path on multi-format commands. These commands
# auto-detect and score any supported instruction file, not just SKILL.md.
_PATH_HELP = "Path to instruction file (SKILL.md/CLAUDE.md/AGENTS.md/.cursorrules)"


def _resolve_version() -> str:
    """Single source of truth for the runtime version string.

    Reads from installed package metadata (importlib.metadata) so the CLI,
    the score-display header, and the --version flag can never drift from
    pyproject.toml. Falls back to "dev" when the package is not installed
    (e.g. running cli.py straight from a source checkout).
    """
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("schliff")
        except PackageNotFoundError:
            return "dev"
    except ImportError:  # importlib.metadata absent (pathological env)
        return "dev"


def _ensure_skill_path_exists(skill_path: str, exit_code: int = 1) -> None:
    """Exit with the standard error if the skill path does not exist.

    Centralizes the repeated existence check across commands. Callers must
    pass exit_code=2 for the CI verify gate to preserve its exit semantics.
    """
    from pathlib import Path

    if not Path(skill_path).exists():
        print(f"Error: file not found: {skill_path}", file=sys.stderr)
        sys.exit(exit_code)


def _load_eval_suite_from_args(args: argparse.Namespace) -> "dict | None":
    """Load eval suite from --eval-suite flag or auto-discover from skill dir."""
    from pathlib import Path

    from shared import MAX_SKILL_SIZE, load_eval_suite

    if getattr(args, "eval_suite", None):
        eval_path = Path(args.eval_suite)
        if not eval_path.exists():
            print(f"Error: eval-suite not found: {args.eval_suite}", file=sys.stderr)
            sys.exit(1)
        eval_size = eval_path.stat().st_size
        if eval_size > MAX_SKILL_SIZE:
            print(
                f"Error: eval-suite too large: {eval_size:,} bytes "
                f"exceeds the {MAX_SKILL_SIZE:,} byte limit",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            suite = json.loads(eval_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error: malformed eval-suite: {e}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(suite, dict):
            print(
                "Error: eval-suite must be a JSON object with triggers/quality/edges keys",
                file=sys.stderr,
            )
            sys.exit(1)
        return suite
    skill_path = getattr(args, "skill_path", None)
    if skill_path:
        return load_eval_suite(skill_path)
    return None


def cmd_score(args: argparse.Namespace) -> None:
    """Score a single SKILL.md file (structural + runtime when eval suite available)."""
    import tempfile
    from pathlib import Path

    from scoring import compute_composite
    from shared import build_scores, fetch_url_safe

    skill_path = getattr(args, "skill_path", None)
    url = getattr(args, "url", None)

    # Validate that exactly one of skill_path or --url is provided
    if not skill_path and not url:
        print("Error: provide a skill path or --url", file=sys.stderr)
        sys.exit(1)
    if skill_path and url:
        print("Error: skill_path and --url are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    tmp_path: "str | None" = None
    display_source: str

    try:
        if url:
            # Fetch URL content into a tempfile
            try:
                content = fetch_url_safe(url)
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                sys.exit(1)

            # Derive a filename from the URL path for format detection
            url_filename = Path(urllib.parse.urlparse(url).path).name or "SKILL.md"
            # Detect format from URL filename (not tempfile name)
            from scoring.formats import detect_format as _detect_fmt
            url_fmt = _detect_fmt(url_filename)
            suffix = Path(url_filename).suffix or ".md"
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=False, encoding="utf-8",
                prefix=Path(url_filename).stem + "_",
            )
            tmp.write(content)
            tmp.close()
            tmp_path = tmp.name
            skill_path = tmp_path
            display_source = url
        else:
            url_fmt = None
            if not Path(skill_path).exists():
                print(f"Error: file not found: {skill_path}", file=sys.stderr)
                sys.exit(1)
            display_source = skill_path

        eval_suite = _load_eval_suite_from_args(args)
        fmt_override = getattr(args, "format", None)
        # For --url, use format detected from URL filename (not tempfile name)
        effective_fmt = fmt_override or url_fmt
        scores = build_scores(skill_path, eval_suite, include_runtime=True, fmt=effective_fmt)

        # Determine the effective format for display
        if effective_fmt:
            detected_fmt = effective_fmt
        else:
            from scoring.formats import detect_format
            detected_fmt = detect_format(skill_path)

        # Weights must match the dimensions actually scored: pass the resolved
        # format (not effective_fmt, which is None for auto-detected formats) so
        # non-skill.md families (e.g. system_prompt) are weighted correctly.
        # The interactive `score` view is the ONLY caller that opts into ambient
        # calibrated weights (still gated by SCHLIFF_CALIBRATED_WEIGHTS); verify,
        # badge, diff, compare, suggest and report stay canonical for reproducibility.
        composite = compute_composite(scores, fmt=detected_fmt, use_calibrated=True)

        # Token budget check — reuse cached content from shared.read_skill_safe
        from scoring.formats import check_token_budget, estimate_tokens
        from shared import read_skill_safe
        try:
            skill_content = read_skill_safe(skill_path)
        except (OSError, ValueError) as exc:
            print(f"Error: could not read {display_source}: {exc}", file=sys.stderr)
            sys.exit(1)
        token_info = check_token_budget(skill_content, detected_fmt)

        if getattr(args, "json", False):
            # A dimension score of -1 is the sentinel for "not measured" (e.g.
            # triggers/quality/edges with no eval suite). Surface it as JSON null
            # (not -1, which looks like a poor score) and add a parallel
            # `dimension_status` map: "measured" for a real value, "unmeasured"
            # (needs eval suite) for the sentinel. Measured values are unchanged.
            def _json_dim(v):  # noqa: ANN001
                s = v["score"]
                if isinstance(s, float):
                    return None if s < 0 else round(s, 1)
                return None if s < 0 else s

            result = {
                "skill_path": display_source,
                "format": detected_fmt,
                "composite_score": composite["score"],
                "dimensions": {k: _json_dim(v) for k, v in scores.items()},
                "dimension_status": {
                    k: ("unmeasured" if v["score"] < 0 else "measured")
                    for k, v in scores.items()
                },
                "warnings": composite["warnings"],
                "token_budget": token_info,
            }
            print(json.dumps(result, indent=2))
        else:
            import text_gradient
            from terminal_art import format_score_display

            # Extract contradictions from clarity details
            clarity_data = scores.get("clarity", {})
            contradictions = clarity_data.get("details", {}).get("contradictions", [])

            # Count available deterministic fixes
            try:
                gradients = text_gradient.compute_gradients(
                    skill_path, eval_suite, include_clarity=True,
                )
                # Honest count: only patches /schliff:auto can actually apply,
                # not every diagnosed gradient (many are manual-only). Mirrors
                # evolve/engine.py so the displayed number matches what runs.
                fix_count = len(text_gradient.generate_patches(skill_path, gradients))
            except Exception as exc:
                print(f"Warning: could not compute fix count: {exc}", file=sys.stderr)
                fix_count = 0

            # Get version (single-sourced from package metadata)
            ver = _resolve_version()

            output = format_score_display(
                scores=scores,
                composite=composite,
                version=ver,
                contradictions=contradictions if contradictions else None,
                fix_count=fix_count,
            )
            print(output)

            # Token budget line
            from terminal_art import RESET, is_color_tty
            tok = token_info["tokens"]
            bud = token_info["budget"]
            if is_color_tty():
                sev = token_info["severity"]
                if sev == "ok":
                    color = "\x1b[32m"   # green
                elif sev == "warning":
                    color = "\x1b[33m"   # yellow
                else:
                    color = "\x1b[31m"   # red for over
                print(f"  Tokens: {color}{tok:,}{RESET} / {bud:,} ({sev})")
            else:
                print(f"  Tokens: {tok:,} / {bud:,} ({token_info['severity']})")

            # --tokens: section breakdown
            if getattr(args, "tokens", False):
                lines = skill_content.splitlines()
                sections: list[tuple[str, int]] = []
                current_section = "(preamble)"
                section_start = 0
                for i, line in enumerate(lines):
                    if line.startswith("# ") or line.startswith("## "):
                        if i > section_start:
                            sec_content = "\n".join(lines[section_start:i])
                            sections.append((current_section, estimate_tokens(sec_content)))
                        current_section = line.lstrip("#").strip()
                        section_start = i
                # Last section
                sec_content = "\n".join(lines[section_start:])
                sections.append((current_section, estimate_tokens(sec_content)))

                print("\n  Token Breakdown by Section:")
                for name, count in sections:
                    print(f"    {name:<40s} {count:>6,} tokens")

            if url:
                print(f"  Source: {url}")
            if detected_fmt != "skill.md":
                print(f"  Format: {detected_fmt} (normalized)")

    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def cmd_verify(args: argparse.Namespace) -> None:
    """CI gate — score a skill and exit with appropriate code."""
    from pathlib import Path

    import verify as verify_mod

    from shared import MAX_SKILL_SIZE, load_eval_suite

    _ensure_skill_path_exists(args.skill_path, exit_code=2)

    # Scores are on a 0..100 scale; a --min-score outside that range can never
    # be satisfied (or is trivially satisfied) and almost always indicates a
    # typo (e.g. --min-score 500). Fail fast with a clear message.
    if not 0.0 <= args.min_score <= 100.0:
        print(
            f"Error: --min-score must be between 0 and 100 (got {args.min_score:g})",
            file=sys.stderr,
        )
        sys.exit(2)

    eval_suite = None
    if args.eval_suite:
        eval_path = Path(args.eval_suite)
        if not eval_path.exists():
            print(f"Error: eval-suite not found: {args.eval_suite}", file=sys.stderr)
            sys.exit(2)
        eval_size = eval_path.stat().st_size
        if eval_size > MAX_SKILL_SIZE:
            print(
                f"Error: eval-suite too large: {eval_size:,} bytes "
                f"exceeds the {MAX_SKILL_SIZE:,} byte limit",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            eval_suite = json.loads(eval_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error: malformed eval-suite: {e}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(eval_suite, dict):
            print(
                "Error: eval-suite must be a JSON object with triggers/quality/edges keys",
                file=sys.stderr,
            )
            sys.exit(2)
    else:
        eval_suite = load_eval_suite(args.skill_path)

    try:
        verdict = verify_mod.run_verify(
            skill_path=args.skill_path,
            min_score=args.min_score,
            check_regression=args.regression,
            history_path=args.history,
            eval_suite=eval_suite,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if getattr(args, "json", False):
        print(json.dumps(verdict, indent=2))
    else:
        print(verify_mod.format_verdict(verdict))

    sys.exit(verdict["exit_code"])


def cmd_doctor(args: argparse.Namespace) -> None:
    """Run doctor scan across all installed skills."""
    import doctor as doctor_mod

    verbose = getattr(args, "verbose", False)
    repo_root = getattr(args, "repo", None)
    report = doctor_mod.run_doctor(
        skill_dirs=getattr(args, "skill_dirs", None),
        verbose=verbose,
        repo_root=repo_root,
    )

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        formatted = doctor_mod.format_doctor_report(report, verbose=verbose)
        print(formatted)


def cmd_badge(args: argparse.Namespace) -> None:
    """Generate a markdown badge for a skill's score."""
    import urllib.parse

    from terminal_art import score_to_grade

    from scoring import compute_composite
    from shared import build_scores

    _ensure_skill_path_exists(args.skill_path)

    eval_suite = _load_eval_suite_from_args(args)
    from scoring.formats import detect_format
    detected_fmt = detect_format(args.skill_path)
    scores = build_scores(args.skill_path, eval_suite, fmt=detected_fmt)

    composite = compute_composite(scores, fmt=detected_fmt)
    score = composite["score"]
    grade = score_to_grade(score)

    colors = {
        "S": "brightgreen", "A": "green", "B": "yellowgreen",
        "C": "yellow", "D": "orange", "E": "red", "F": "red",
    }
    color = colors.get(grade, "lightgrey")

    label = urllib.parse.quote(f"{score:.0f}/100 [{grade}]", safe="")
    badge_md = f"[![Schliff: {score:.0f} [{grade}]](https://img.shields.io/badge/Schliff-{label}-{color})](https://github.com/Zandereins/schliff)"

    print(badge_md)


def cmd_demo(_args: argparse.Namespace) -> None:
    """Score a built-in demo skill to showcase schliff's output."""
    import tempfile
    from pathlib import Path

    demo_content = '''---
name: deploy-helper
description: Helps with deployment stuff
---

# Deploy Helper

This skill probably helps with deployment. You might want to use it when deploying things.

## What It Does

- Setting up deployment configurations
- Running deploy commands
- Checking if deployment worked

## How To Use

1. Tell Claude you want to deploy something
2. It will try to help you
3. Check if it worked
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = str(Path(tmpdir) / "SKILL.md")
        Path(skill_path).write_text(demo_content, encoding="utf-8")

        # Reuse cmd_score logic
        import argparse as _ap
        fake_args = _ap.Namespace(skill_path=skill_path, json=False, eval_suite=None, url=None, format=None, tokens=False)
        cmd_score(fake_args)

    print("\n  This is a deliberately bad skill. Try schliff on your own skills!")
    print("  Usage: schliff score path/to/SKILL.md\n")


def cmd_diff(args: argparse.Namespace) -> None:
    """Explain score changes between git commits."""
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    from scoring import compute_composite
    from scoring.diff import explain_score_change, score_diff
    from shared import MAX_SKILL_SIZE, build_scores

    skill_path = args.skill_path
    if not Path(skill_path).exists():
        print(f"Error: file not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    ref = args.ref

    # Validate ref to prevent git flag injection
    if ref.startswith("-") or not re.match(r'^[a-zA-Z0-9_.~^@/\-]+$', ref):
        print(f"Error: invalid git reference: {ref}", file=sys.stderr)
        sys.exit(1)

    # Score current version
    eval_suite = _load_eval_suite_from_args(args)
    from scoring.formats import detect_format
    detected_fmt = detect_format(skill_path)
    new_scores = build_scores(skill_path, eval_suite, fmt=detected_fmt)
    new_composite = compute_composite(new_scores, fmt=detected_fmt)

    # Reconstruct old version via git show
    try:
        # Get the path relative to git root
        git_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if git_root.returncode != 0:
            print("Error: not a git repository", file=sys.stderr)
            sys.exit(1)

        abs_skill = str(Path(skill_path).resolve())
        root = git_root.stdout.strip()

        # Ensure skill path is inside the git repository
        if not abs_skill.startswith(root + os.sep):
            print("Error: skill path must be inside the git repository", file=sys.stderr)
            sys.exit(1)

        rel_path = os.path.relpath(abs_skill, root)

        old_content = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            capture_output=True, text=True, timeout=10,
        )
        if old_content.returncode != 0:
            print(f"Error: cannot read {rel_path} at ref '{ref}' — file may not exist in that commit", file=sys.stderr)
            sys.exit(1)

        # Guard against oversized content from git history
        if len(old_content.stdout) > MAX_SKILL_SIZE:
            print(
                f"Error: file at ref '{ref}' too large: {len(old_content.stdout):,} bytes "
                f"exceeds the {MAX_SKILL_SIZE:,} byte limit",
                file=sys.stderr,
            )
            sys.exit(1)
    except FileNotFoundError:
        print("Error: git not available", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: git command timed out", file=sys.stderr)
        sys.exit(1)

    # Score old version in a temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = str(Path(tmpdir) / "SKILL.md")
        Path(old_path).write_text(old_content.stdout, encoding="utf-8")
        # Use the same resolved format as the current version so both composites
        # are weighted consistently (the temp file is always named SKILL.md).
        old_scores = build_scores(old_path, eval_suite, fmt=detected_fmt)
        old_composite = compute_composite(old_scores, fmt=detected_fmt)

    # Diff analysis (signal/noise classification) — use resolved path
    diff_analysis = score_diff(abs_skill, ref)

    # Build per-dimension deltas
    old_flat = {k: v["score"] for k, v in old_scores.items() if isinstance(v, dict)}
    new_flat = {k: v["score"] for k, v in new_scores.items() if isinstance(v, dict)}
    explanations = explain_score_change(old_flat, new_flat, diff_analysis)

    if getattr(args, "json", False):
        result = {
            "skill_path": skill_path,
            "ref": ref,
            "old_composite": old_composite["score"],
            "new_composite": new_composite["score"],
            "composite_delta": round(new_composite["score"] - old_composite["score"], 1),
            "dimensions": explanations,
        }
        if diff_analysis.get("available"):
            result["diff_summary"] = diff_analysis["net_change"]
        print(json.dumps(result, indent=2))
    else:
        from terminal_art import score_to_grade

        old_score = old_composite["score"]
        new_score = new_composite["score"]
        delta = new_score - old_score

        old_grade = score_to_grade(old_score)
        new_grade = score_to_grade(new_score)

        print(f"\n  schliff diff  {ref} → current\n")
        print(f"  Composite: {old_score:.1f} [{old_grade}] → {new_score:.1f} [{new_grade}]  ({delta:+.1f})\n")

        if explanations:
            for exp in explanations:
                arrow = "+" if exp["delta"] > 0 else ""
                print(f"  {exp['dimension']:16s}  {exp['old']:6.1f} → {exp['new']:6.1f}  ({arrow}{exp['delta']:.1f})")
            print()
        else:
            print("  No significant dimension changes.\n")

        if diff_analysis.get("available"):
            net = diff_analysis["net_change"]
            print(f"  Diff: {net['signal']:+d} signal, {net['noise']:+d} noise, {net['lines']:+d} lines total\n")


def cmd_compare(args: argparse.Namespace) -> None:
    """Score two files and show a side-by-side dimension comparison."""
    from pathlib import Path

    from scoring import compute_composite
    from shared import build_scores

    path_a = args.file_a
    path_b = args.file_b

    if not Path(path_a).exists():
        print(f"Error: file not found: {path_a}", file=sys.stderr)
        sys.exit(1)
    if not Path(path_b).exists():
        print(f"Error: file not found: {path_b}", file=sys.stderr)
        sys.exit(1)

    eval_suite = _load_eval_suite_from_args(args)

    from scoring.formats import detect_format
    fmt_a = detect_format(path_a)
    fmt_b = detect_format(path_b)

    scores_a = build_scores(path_a, eval_suite, fmt=fmt_a)
    scores_b = build_scores(path_b, eval_suite, fmt=fmt_b)

    composite_a = compute_composite(scores_a, fmt=fmt_a)
    composite_b = compute_composite(scores_b, fmt=fmt_b)

    score_a = composite_a["score"]
    score_b = composite_b["score"]

    # Collect dimension names present in both scores
    dims = [k for k in scores_a if isinstance(scores_a[k], dict) and "score" in scores_a[k]]

    # Per-dimension deltas: B - A
    deltas = {}
    for dim in dims:
        val_a = scores_a[dim]["score"]
        val_b = scores_b.get(dim, {}).get("score", 0.0)
        deltas[dim] = round(val_b - val_a, 1)

    # Biggest absolute gap. When several dimensions tie for the largest gap,
    # report all of them rather than arbitrarily picking the first; when the
    # largest gap is 0.0 (identical files) there is no meaningful gap at all.
    if deltas:
        max_abs = max(abs(d) for d in deltas.values())
        biggest_dims = [d for d in dims if abs(deltas[d]) == max_abs]
        biggest_dim = biggest_dims[0]
        biggest_delta = deltas[biggest_dim]
        has_gap = max_abs > 0.0
    else:
        biggest_dims = []
        biggest_dim = ""
        biggest_delta = 0.0
        has_gap = False

    if getattr(args, "json", False):
        result = {
            "file_a": {
                "path": path_a,
                "composite": round(score_a, 1),
                "dimensions": {k: round(scores_a[k]["score"], 1) for k in dims},
            },
            "file_b": {
                "path": path_b,
                "composite": round(score_b, 1),
                "dimensions": {k: round(scores_b.get(k, {}).get("score", 0.0), 1) for k in dims},
            },
            "deltas": deltas,
            "biggest_gap": {
                "dimension": biggest_dim,
                "delta": biggest_delta,
                # All dimensions tied for the largest absolute gap (>=1 entry).
                "dimensions": biggest_dims,
                # False when files are identical (largest gap is 0.0).
                "has_gap": has_gap,
            },
        }
        print(json.dumps(result, indent=2))
        return

    from terminal_art import score_to_grade

    grade_a = score_to_grade(score_a)
    grade_b = score_to_grade(score_b)

    print()
    print("  schliff compare")
    print()
    print(f"  File A: {path_a}  [{grade_a}] {score_a:.1f}")
    print(f"  File B: {path_b}  [{grade_b}] {score_b:.1f}")
    print()

    # Column header + separator
    header = f"  {'Dimension':<16}{'A':>8}{'B':>8}{'Delta':>10}"
    separator = "  " + "─" * 41
    print(header)
    print(separator)

    for dim in dims:
        val_a = scores_a[dim]["score"]
        val_b = scores_b.get(dim, {}).get("score", 0.0)
        delta = deltas[dim]
        delta_str = f"{delta:+.1f}"
        marker = "  ← biggest gap" if (has_gap and dim in biggest_dims) else ""
        print(f"  {dim:<16}{val_a:>8.1f}{val_b:>8.1f}{delta_str:>10}{marker}")

    print(separator)

    composite_delta = round(score_b - score_a, 1)
    composite_delta_str = f"{composite_delta:+.1f}"
    print(f"  {'Composite':<16}{score_a:>8.1f}{score_b:>8.1f}{composite_delta_str:>10}")
    print()

    if not has_gap:
        # Identical scores across every dimension — a "biggest gap" marker would
        # be misleading, so state the absence of any gap instead.
        print("  No dimension differences — the files score identically.")
    elif len(biggest_dims) > 1:
        # Multiple dimensions tie for the largest gap: list them all rather than
        # arbitrarily attributing the gap to whichever sorts first.
        direction = "B" if biggest_delta > 0 else "A"
        dim_list = ", ".join(biggest_dims)
        print(
            f"  Biggest gap ({biggest_delta:+.1f}, tied): {dim_list} "
            f"— {direction} has stronger coverage"
        )
    else:
        direction = "B" if biggest_delta > 0 else "A"
        dim_label = biggest_dim
        print(f"  Biggest gap: {dim_label} ({biggest_delta:+.1f}) — {direction} has stronger {dim_label} coverage")
    print()


def cmd_suggest(args: argparse.Namespace) -> None:
    """Suggest ranked fixes with estimated score impact."""
    import text_gradient
    from terminal_art import score_to_grade

    from scoring import compute_composite
    from shared import build_scores

    _ensure_skill_path_exists(args.skill_path)

    eval_suite = _load_eval_suite_from_args(args)
    top_n = max(1, args.top)

    # Compute current score
    from scoring.formats import detect_format
    detected_fmt = detect_format(args.skill_path)
    scores = build_scores(args.skill_path, eval_suite, include_runtime=True, fmt=detected_fmt)
    composite = compute_composite(scores, fmt=detected_fmt)
    current_score = composite["score"]
    current_grade = score_to_grade(current_score)

    # Get all ranked gradients (include clarity for full picture)
    try:
        gradients = text_gradient.compute_gradients(
            args.skill_path, eval_suite, include_clarity=True,
        )
    except Exception as exc:
        print(f"Error: failed to compute gradients: {exc}", file=sys.stderr)
        sys.exit(1)

    top_gradients = gradients[:top_n]

    # Estimated score after applying all top fixes
    total_delta = sum(g["delta"] for g in top_gradients)
    estimated_score = min(100.0, current_score + total_delta)
    estimated_grade = score_to_grade(estimated_score)

    if getattr(args, "json", False):
        result = {
            "skill_path": args.skill_path,
            "current_score": round(current_score, 1),
            "current_grade": current_grade,
            "estimated_score": round(estimated_score, 1),
            "estimated_grade": estimated_grade,
            "suggestions": [
                {
                    "rank": i + 1,
                    "delta": g["delta"],
                    "delta_display": g.get("delta_display", f"+{g['delta']:.1f}"),
                    "dimension": g["dimension"],
                    "instruction": g["instruction"],
                    "confidence": g.get("confidence", "medium"),
                }
                for i, g in enumerate(top_gradients)
            ],
        }
        print(json.dumps(result, indent=2))
        return

    print()
    print(f"  schliff suggest  {args.skill_path}")
    print()
    print("  TOP FIXES (estimated impact):")

    for i, g in enumerate(top_gradients, 1):
        delta_val = g["delta"]
        delta_display = g.get("delta_display", None)
        if delta_display:
            # Range like "~2.0-5.0" — show midpoint with tilde
            delta_label = f"~{delta_val:.0f}"
        else:
            delta_label = f"+{delta_val:.0f}"
        print(f"  {i:2d}. [{delta_label:>4}] {g['instruction']}")

    print()
    print(
        f"  Current: {current_score:.1f} [{current_grade}]"
        f"  →  Estimated after fixes: ~{estimated_score:.1f} [{estimated_grade}]"
    )
    print()


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a Markdown score report, optionally upload as GitHub Gist."""
    import report as report_mod
    from terminal_art import score_to_grade

    from scoring import compute_composite
    from shared import build_scores

    _ensure_skill_path_exists(args.skill_path)

    eval_suite = _load_eval_suite_from_args(args)
    from scoring.formats import check_token_budget, detect_format
    detected_fmt = detect_format(args.skill_path)
    scores = build_scores(args.skill_path, eval_suite, include_runtime=True, fmt=detected_fmt)
    composite = compute_composite(scores, fmt=detected_fmt)
    grade = score_to_grade(composite["score"])

    # Token budget for report — reuse cached content from shared.read_skill_safe
    from shared import read_skill_safe
    try:
        skill_content = read_skill_safe(args.skill_path)
    except (OSError, ValueError) as exc:
        print(f"Error: could not read {args.skill_path}: {exc}", file=sys.stderr)
        sys.exit(1)
    token_info = check_token_budget(skill_content, detected_fmt)

    markdown = report_mod.generate_report_markdown(
        scores=scores,
        skill_path=args.skill_path,
        composite=composite,
        grade=grade,
        token_info=token_info,
    )

    if getattr(args, "gist", False):
        url = report_mod.upload_gist(markdown)
        if url:
            print(f"Gist created: {url}")
        else:
            print(markdown)
    else:
        print(markdown)


def cmd_evolve(args: argparse.Namespace) -> None:
    """Run the evolution engine on an instruction file."""
    from evolve.content import EvolutionConfig, score_to_threshold
    from evolve.engine import run_evolution

    try:
        target_score = score_to_threshold(args.target)
    except ValueError:
        print(f"Error: Unknown target '{args.target}'. Use S/A/B/C or a numeric score.", file=sys.stderr)
        raise SystemExit(1)

    config = EvolutionConfig(
        skill_path=args.skill_path,
        target_score=target_score,
        max_generations=args.generations,
        budget_tokens=args.budget,
        min_improvement=args.min_improvement,
        strategy=args.strategy,
        dimension=args.dimension,
        model=args.model,
        provider=args.provider,
        dry_run=args.dry_run,
        json_output=args.json,
        lineage_dir=args.lineage,
        no_snapshots=args.no_snapshots,
        fmt=args.fmt,
    )

    try:
        result = run_evolution(config)
    except KeyboardInterrupt:
        print("\nEvolution interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except SystemExit:
        raise
    except FileNotFoundError:
        print(f"Error: File not found: {args.skill_path}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        from evolve.sanitize import redact_exception
        print(f"Error: Evolution failed: {redact_exception(exc)}", file=sys.stderr)
        raise SystemExit(1)

    if args.json:
        import json
        from dataclasses import asdict
        print(json.dumps(asdict(result), indent=2))


def cmd_version(_args: argparse.Namespace) -> None:
    """Print version string."""
    print(f"schliff {_resolve_version()}")


# Per-command example shown when a required positional argument is missing.
_USAGE_EXAMPLES: dict[str, str] = {
    "schliff score": "schliff score path/to/SKILL.md",
    "schliff verify": "schliff verify path/to/SKILL.md --min-score 75",
    "schliff badge": "schliff badge path/to/SKILL.md",
    "schliff diff": "schliff diff path/to/SKILL.md --ref HEAD~1",
    "schliff compare": "schliff compare a/SKILL.md b/SKILL.md",
    "schliff suggest": "schliff suggest path/to/SKILL.md",
    "schliff report": "schliff report path/to/SKILL.md",
    "schliff evolve": "schliff evolve path/to/SKILL.md --target A",
}


class _ActionableArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that appends a concrete example on a missing-arg error.

    argparse's default "the following arguments are required: ..." message tells
    the user *what* is missing but not *how* to invoke the command. We keep the
    standard message + exit code (2) and add a copy-pasteable example.
    """

    def error(self, message: str) -> "None":  # type: ignore[override]
        if "are required" in message:
            example = _USAGE_EXAMPLES.get(self.prog)
            if example:
                message = f"{message}\n\nExample:\n  {example}"
        super().error(message)


def main():
    parser = _ActionableArgumentParser(
        prog="schliff",
        description="The finishing cut for Claude Code skills",
        epilog="Quick start:\n"
               "  schliff demo              See it in action instantly\n"
               "  schliff score SKILL.md    Score a skill\n"
               "  schliff doctor            Scan all installed skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"schliff {_resolve_version()}",
        help="Show version and exit",
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands",
        parser_class=_ActionableArgumentParser,
    )

    # score command
    score_parser = subparsers.add_parser("score", help="Score an instruction file")
    score_parser.add_argument(
        "skill_path", nargs="?", help=f"{_PATH_HELP} (required unless --url is given)"
    )
    score_parser.add_argument("--url", help="URL to fetch and score (HTTPS only, allowlisted hosts)")
    score_parser.add_argument("--json", action="store_true", help="JSON output")
    score_parser.add_argument("--eval-suite", help="Path to eval-suite.json")
    from scoring.registry import get_format_choices
    score_parser.add_argument(
        "--format",
        choices=get_format_choices() + ["unknown"],
        default=None,
        help="Override format detection (useful when filename doesn't match content type)",
    )
    score_parser.add_argument("--tokens", action="store_true",
                              help="Show token budget breakdown by section")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="CI gate — exit 0/1 based on score")
    verify_parser.add_argument("skill_path", help=_PATH_HELP)
    verify_parser.add_argument("--min-score", type=float, default=75.0,
                               help="Minimum passing score (default: 75)")
    verify_parser.add_argument("--regression", action="store_true",
                               help="Fail if score dropped vs previous run")
    verify_parser.add_argument("--history", default=".schliff/history.jsonl",
                               help="Path to history file (default: .schliff/history.jsonl)")
    verify_parser.add_argument("--eval-suite", help="Path to eval-suite.json")
    verify_parser.add_argument("--json", action="store_true", help="JSON output")

    # doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Scan all installed skills")
    doctor_parser.add_argument("--json", action="store_true", help="JSON output")
    doctor_parser.add_argument("--skill-dirs", nargs="+", default=None,
                               help="Directories to scan")
    doctor_parser.add_argument("--verbose", "-v", action="store_true",
                               help="Show per-skill issues")
    doctor_parser.add_argument("--repo", default=None,
                               help="Repository root for instruction file discovery")

    # badge command
    badge_parser = subparsers.add_parser("badge", help="Generate markdown badge for a skill")
    badge_parser.add_argument("skill_path", help=_PATH_HELP)
    badge_parser.add_argument("--eval-suite", help="Path to eval-suite.json")

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Explain score changes between git commits")
    diff_parser.add_argument("skill_path", help=_PATH_HELP)
    diff_parser.add_argument("--ref", default="HEAD~1",
                              help="Git ref to compare against (default: HEAD~1)")
    diff_parser.add_argument("--json", action="store_true", help="JSON output")
    diff_parser.add_argument("--eval-suite", help="Path to eval-suite.json")

    # compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two files side by side")
    compare_parser.add_argument(
        "file_a", help="First instruction file (SKILL.md/CLAUDE.md/AGENTS.md/.cursorrules)"
    )
    compare_parser.add_argument(
        "file_b", help="Second instruction file (SKILL.md/CLAUDE.md/AGENTS.md/.cursorrules)"
    )
    compare_parser.add_argument("--json", action="store_true", help="JSON output")
    compare_parser.add_argument("--eval-suite", help="Path to eval-suite.json (applied to both)")

    # suggest command
    suggest_parser = subparsers.add_parser("suggest", help="Suggest ranked fixes with estimated impact")
    suggest_parser.add_argument("skill_path", help=_PATH_HELP)
    suggest_parser.add_argument("--json", action="store_true", help="JSON output")
    suggest_parser.add_argument("--top", type=int, default=5, help="Number of suggestions (default: 5)")
    suggest_parser.add_argument("--eval-suite", help="Path to eval-suite.json")

    # report command
    report_parser = subparsers.add_parser("report", help="Generate Markdown score report")
    report_parser.add_argument("skill_path", help=_PATH_HELP)
    report_parser.add_argument("--gist", action="store_true",
                               help="Upload report as GitHub Gist (requires GITHUB_TOKEN)")
    report_parser.add_argument("--eval-suite", help="Path to eval-suite.json")

    # demo command
    subparsers.add_parser("demo", help="Score a built-in bad skill to see schliff in action")

    # version command
    subparsers.add_parser("version", help="Show version")

    # evolve command
    evolve_parser = subparsers.add_parser("evolve", help="Evolve an instruction file to improve its score")
    evolve_parser.add_argument("skill_path", help="Path to instruction file")
    evolve_parser.add_argument("--target", default="A",
                               help="Target grade (S/A/B/C) or numeric score (default: A)")
    evolve_parser.add_argument("--generations", type=int, default=10,
                               help="Max generations (default: 10)")
    evolve_parser.add_argument("--budget", type=int, default=50000,
                               help="Token budget, 0=deterministic only (default: 50000)")
    evolve_parser.add_argument("--provider", default=None,
                               help="LiteLLM provider (ollama, anthropic, openai, openrouter)")
    evolve_parser.add_argument("--model", default=None,
                               help="Specific model string (e.g., anthropic/claude-sonnet-4-20250514)")
    evolve_parser.add_argument("--min-improvement", type=float, default=0.5,
                               help="Min score improvement per gen to continue (default: 0.5)")
    evolve_parser.add_argument("--strategy", choices=["gradient", "holistic", "dimension"],
                               default="gradient", help="Evolution strategy (default: gradient)")
    evolve_parser.add_argument("--dimension", default=None,
                               help="Target dimension (with --strategy dimension)")
    evolve_parser.add_argument("--format", dest="fmt", default=None,
                               help="Override format detection")
    evolve_parser.add_argument("--json", action="store_true", help="JSON output")
    evolve_parser.add_argument("--dry-run", action="store_true",
                               help="Show plan without making changes")
    evolve_parser.add_argument("--lineage", default="~/.schliff/lineage",
                               help="Lineage directory (default: ~/.schliff/lineage)")
    evolve_parser.add_argument("--no-snapshots", action="store_true",
                               help="Disable content snapshots in lineage")

    args = parser.parse_args()

    commands = {
        "score": cmd_score,
        "compare": cmd_compare,
        "diff": cmd_diff,
        "verify": cmd_verify,
        "doctor": cmd_doctor,
        "badge": cmd_badge,
        "suggest": cmd_suggest,
        "report": cmd_report,
        "demo": cmd_demo,
        "version": cmd_version,
        "evolve": cmd_evolve,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except PermissionError:
            # A PermissionError's str() leaks the OS-resolved absolute path and
            # an "[Errno 13]" prefix (read_skill_safe reads the resolved target).
            # Report the path the user actually typed, with a clean message.
            user_path = (
                getattr(args, "skill_path", None)
                or getattr(args, "file_a", None)
                or "the file"
            )
            print(f"Error: permission denied reading {user_path}", file=sys.stderr)
            sys.exit(1)
        except (OSError, ValueError) as exc:
            # Catch-all for user-input errors that leak out of any cmd_*
            # handler (e.g. passing a directory to `score`, oversized files,
            # unreadable paths). Present a short message, no traceback.
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
