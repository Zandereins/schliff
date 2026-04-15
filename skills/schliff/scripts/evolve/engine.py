"""Evolution engine — the main improvement loop.

Phase 0: Score baseline
Phase 1: Deterministic patches (free, no LLM)
Phase 2: LLM-guided improvement (budgeted)
Phase 3: Finalize + write result
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from evolve.budget import BudgetTracker
from evolve.content import (
    EvolutionConfig,
    EvolutionResult,
    content_hash,
    extract_markdown_content,
    grade_from_score,
)
from evolve.guard import dimension_guard, security_guard
from evolve.lineage import LineageSession
from evolve.plateau import PlateauDetector


def _atomic_write(path: str, content: str) -> None:
    """Atomic write: write to temp file in same dir, then os.replace()."""
    target = Path(path)
    fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), suffix=".schliff-tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _score_file(skill_path: str, fmt: Optional[str] = None) -> tuple[dict, float]:
    """Score a file and return (dim_scores, composite_score)."""
    from scoring.composite import compute_composite
    from shared import build_scores

    scores = build_scores(skill_path, include_security=True, fmt=fmt)
    composite = compute_composite(scores, fmt=fmt)
    return scores, composite["score"]


def _apply_deterministic_patches(skill_path: str, config: EvolutionConfig,
                                  lineage: Optional[LineageSession],
                                  current_scores: dict, current_composite: float,
                                  verbose: bool = True) -> tuple[str, dict, float, int]:
    """Apply deterministic patches from text_gradient.

    Returns (content, scores, composite, patch_count).
    """
    import text_gradient

    from shared import load_eval_suite, read_skill_safe

    content = read_skill_safe(skill_path)
    best_content = content
    best_scores = current_scores
    best_composite = current_composite
    patch_count = 0

    eval_suite = load_eval_suite(skill_path)
    gradients = text_gradient.compute_gradients(skill_path, eval_suite, include_clarity=True)
    patches = text_gradient.generate_patches(skill_path, gradients)

    if not patches:
        return best_content, best_scores, best_composite, 0

    # Sort patches by line number descending to avoid index shifts
    def _patch_sort_key(p):
        if p.get("op") == "remove_lines":
            return max(p.get("lines", [0]))
        return p.get("line", 0)
    patches.sort(key=_patch_sort_key, reverse=True)

    for patch in patches:
        # Apply patch to content
        patched = _apply_single_patch(best_content, patch)
        if patched == best_content:
            continue

        # Write temporarily to score
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp.write(patched)
            tmp_path = tmp.name

        try:
            new_scores, new_composite = _score_file(tmp_path, fmt=config.fmt)
        finally:
            os.unlink(tmp_path)

        # Guard check (conservative threshold=2.0 for deterministic patches)
        guard = dimension_guard(best_scores, new_scores, threshold=2.0)
        sec_guard = security_guard(best_scores, new_scores)

        if not guard.passed or not sec_guard.passed:
            violations = guard.violations + sec_guard.violations
            if verbose:
                print(f"  \u2717 patch rejected: {', '.join(violations)}", file=sys.stderr)
            continue

        if new_composite > best_composite:
            best_content = patched
            best_scores = new_scores
            best_composite = new_composite
            patch_count += 1

            if verbose:
                grade = grade_from_score(new_composite)
                print(f"  Gen {patch_count}  [deterministic]   {new_composite:.1f} [{grade}]  "
                      f"+{new_composite - current_composite:.1f}")

            if lineage:
                lineage.log_generation(patch_count, new_composite, "accepted",
                                       strategy="deterministic")
                lineage.save_snapshot(patch_count, best_content)

    return best_content, best_scores, best_composite, patch_count


def _apply_single_patch(content: str, patch: dict) -> str:
    """Apply a single patch dict to content string."""
    op = patch.get("op", "")
    lines = content.split("\n")

    if op == "insert_before":
        line_idx = max(0, patch.get("line", 1) - 1)
        new_lines = patch.get("content", "").rstrip("\n").split("\n")
        lines[line_idx:line_idx] = new_lines
    elif op == "remove_lines":
        remove = set(patch.get("lines", []))
        lines = [ln for i, ln in enumerate(lines, 1) if i not in remove]
    else:
        return content  # unsupported op, skip

    return "\n".join(lines)


def run_evolution(config: EvolutionConfig,
                  completion_fn: Optional[Callable[..., Any]] = None) -> EvolutionResult:
    """Run the full evolution loop.

    Args:
        config: Evolution configuration
        completion_fn: Optional LLM completion function for testing (dependency injection)
    """
    from shared import invalidate_cache, read_skill_safe

    skill_path = config.skill_path
    verbose = not config.json_output

    # Phase 0: Score baseline
    initial_scores, initial_composite = _score_file(skill_path, fmt=config.fmt)
    initial_grade = grade_from_score(initial_composite)

    if verbose:
        print(f"\n  schliff evolve  {skill_path}")
        print(f"  Target: {config.target_score:.1f}  Budget: {config.budget_tokens:,} tokens\n")
        print(f"  Gen 0  [baseline]       {initial_composite:.1f} [{initial_grade}]")

    # Check if already at target
    if initial_composite >= config.target_score:
        if verbose:
            print(f"\n  Already at target ({initial_composite:.1f} >= {config.target_score:.1f})")
        return EvolutionResult(
            initial_score=initial_composite, final_score=initial_composite,
            initial_grade=initial_grade, final_grade=initial_grade,
            generations=0, accepted=0, rejected=0, deterministic_patches=0,
            tokens_used=0, cost_usd=0.0, stop_reason="target_reached",
        )

    # Dry run: just show baseline
    if config.dry_run:
        return EvolutionResult(
            initial_score=initial_composite, final_score=initial_composite,
            initial_grade=initial_grade, final_grade=initial_grade,
            generations=0, accepted=0, rejected=0, deterministic_patches=0,
            tokens_used=0, cost_usd=0.0, stop_reason="dry_run",
        )

    # Setup tracking
    budget = BudgetTracker(config.budget_tokens)
    plateau = PlateauDetector(min_improvement=config.min_improvement)
    plateau.update(initial_composite)

    lineage: Optional[LineageSession] = None
    if config.lineage_dir:
        lineage = LineageSession(skill_path, config.lineage_dir, config.no_snapshots)
        lineage.log_header(initial_composite, config.target_score, config.budget_tokens)
        lineage.log_generation(0, initial_composite, "baseline")

    # Phase 1: Deterministic patches
    content = read_skill_safe(skill_path)
    best_content = content
    best_scores = initial_scores
    best_composite = initial_composite

    # Backup original before any modification
    original_content = read_skill_safe(skill_path)
    backup_path = skill_path + ".schliff-backup"
    _atomic_write(backup_path, original_content)

    stop_reason = "no_improvement"
    det_count = 0
    accepted = 0
    rejected = 0
    gen_num = 0

    try:
        det_content, det_scores, det_composite, det_count = _apply_deterministic_patches(
            skill_path, config, lineage, best_scores, best_composite, verbose=verbose,
        )

        if det_count > 0:
            best_content = det_content
            best_scores = det_scores
            best_composite = det_composite
            plateau.update(best_composite)

            # Write deterministic improvements
            _atomic_write(skill_path, best_content)
            invalidate_cache(skill_path)

        gen_num = det_count

        # Check target after deterministic
        if best_composite >= config.target_score:
            stop_reason = "target_reached"
        elif budget.is_deterministic_only:
            stop_reason = "no_improvement" if det_count == 0 else "budget_exhausted"
        else:
            # Phase 2: LLM-guided improvement
            import text_gradient
            from evolve.llm import call_llm, resolve_model
            from evolve.prompts import (
                SYSTEM_PROMPT,
                build_dimension_prompt,
                build_gradient_prompt,
                build_holistic_prompt,
            )

            from shared import load_eval_suite

            model = resolve_model(config.provider, config.model) if not completion_fn else (config.model or "mock/injected")
            strategy = config.strategy
            temperature = 0.3

            for _ in range(config.max_generations - det_count):
                if best_composite >= config.target_score:
                    break

                # Build prompt based on strategy
                eval_suite = load_eval_suite(skill_path)
                gradients = text_gradient.compute_gradients(skill_path, eval_suite, include_clarity=True)

                if strategy == "dimension" and config.dimension:
                    user_prompt = build_dimension_prompt(
                        best_content, best_composite, grade_from_score(best_composite),
                        best_scores, config.dimension, gradients,
                    )
                elif strategy == "holistic":
                    user_prompt = build_holistic_prompt(
                        best_content, best_composite, grade_from_score(best_composite),
                        best_scores, config.target_score,
                    )
                else:  # gradient (default)
                    user_prompt = build_gradient_prompt(
                        best_content, best_composite, grade_from_score(best_composite),
                        best_scores, gradients, config.target_score,
                    )

                # Prompt-aware token estimation: includes both prompt and content
                estimated = int((len(user_prompt.split()) + len(best_content.split())) * 1.3 + 800)
                if not budget.can_afford(estimated):
                    break

                gen_num += 1

                # Call LLM
                llm_result = call_llm(
                    SYSTEM_PROMPT, user_prompt, model,
                    temperature=temperature,
                    completion_fn=completion_fn,
                )

                budget.record(llm_result["tokens_used"], f"gen {gen_num}")
                new_content = extract_markdown_content(llm_result["content"])

                if not new_content.strip() or content_hash(new_content) == content_hash(best_content):
                    rejected += 1
                    plateau.record_rejection()
                    if lineage:
                        lineage.log_generation(gen_num, best_composite, "rejected_identical",
                                               strategy=strategy, model=model,
                                               tokens_used=llm_result["tokens_used"])
                    continue

                # Score the new content
                with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                    tmp.write(new_content)
                    tmp_path = tmp.name

                try:
                    new_scores, new_composite = _score_file(tmp_path, fmt=config.fmt)
                finally:
                    os.unlink(tmp_path)

                # Guard checks
                threshold = 5.0 if strategy == "holistic" else 3.0
                guard = dimension_guard(best_scores, new_scores, threshold=threshold)
                sec_guard = security_guard(best_scores, new_scores)

                if not guard.passed or not sec_guard.passed:
                    rejected += 1
                    plateau.record_rejection()
                    violations = guard.violations + sec_guard.violations
                    if verbose:
                        print(f"  Gen {gen_num}  [{strategy}/{model.split('/')[-1]}]  ——.— [—]  ——    "
                              f"✗ guard: {violations[0] if violations else 'unknown'}")
                    if lineage:
                        lineage.log_generation(gen_num, new_composite, "guard_rejected",
                                               strategy=strategy, model=model,
                                               tokens_used=llm_result["tokens_used"],
                                               guard_violations=violations)
                    continue

                if new_composite <= best_composite:
                    rejected += 1
                    plateau.record_rejection()
                    if lineage:
                        lineage.log_generation(gen_num, new_composite, "rejected_no_improvement",
                                               strategy=strategy, model=model,
                                               tokens_used=llm_result["tokens_used"])
                    continue

                # Accept!
                accepted += 1
                old_composite = best_composite
                best_content = new_content
                best_scores = new_scores
                best_composite = new_composite
                plateau.update(best_composite)

                # Write to file
                _atomic_write(skill_path, best_content)
                invalidate_cache(skill_path)

                grade = grade_from_score(best_composite)
                if verbose:
                    print(f"  Gen {gen_num}  [{strategy}/{model.split('/')[-1]}]  {best_composite:.1f} [{grade}]  "
                          f"+{best_composite - old_composite:.1f}")

                if lineage:
                    lineage.log_generation(gen_num, best_composite, "accepted",
                                           strategy=strategy, model=model,
                                           tokens_used=llm_result["tokens_used"])
                    lineage.save_snapshot(gen_num, best_content)

                # Plateau detection
                if plateau.is_plateau:
                    escape = plateau.get_escape_strategy()
                    if escape == "strategy_switch":
                        strategy = "holistic" if strategy == "gradient" else "gradient"
                        if verbose:
                            print(f"  → Plateau detected, switching to {strategy}")
                    elif escape == "temperature_bump":
                        temperature = 0.6
                        if verbose:
                            print(f"  → Plateau persists, bumping temperature to {temperature}")
                    else:
                        if verbose:
                            print("  → Plateau is real, stopping")
                        break

            # Determine stop reason
            if best_composite >= config.target_score:
                stop_reason = "target_reached"
            elif budget.is_exhausted or not budget.can_afford(1):
                stop_reason = "budget_exhausted"
            elif gen_num >= config.max_generations:
                stop_reason = "max_generations"
            elif plateau.is_plateau:
                stop_reason = "plateau"
            else:
                stop_reason = "no_improvement"

    except KeyboardInterrupt:
        stop_reason = "interrupted"
        if verbose:
            print("\n  Interrupted by user.", file=sys.stderr)
    except SystemExit:
        stop_reason = "error"
    finally:
        _finalize(config, lineage, initial_composite, best_composite, budget, stop_reason, verbose,
                  det_count=det_count, accepted=accepted, rejected=rejected)
        # Remove backup on success
        if stop_reason not in ("error", "interrupted"):
            try:
                os.unlink(backup_path)
            except OSError:
                pass

    return EvolutionResult(
        initial_score=initial_composite, final_score=best_composite,
        initial_grade=initial_grade, final_grade=grade_from_score(best_composite),
        generations=gen_num, accepted=det_count + accepted, rejected=rejected,
        deterministic_patches=det_count, tokens_used=budget.used,
        cost_usd=budget.estimate_cost_usd(), stop_reason=stop_reason,
        lineage_path=lineage.path if lineage else None,
    )


def _finalize(config: EvolutionConfig, lineage: Optional[LineageSession],
              initial: float, final: float, budget: BudgetTracker,
              stop_reason: str, verbose: bool,
              det_count: int = 0, accepted: int = 0, rejected: int = 0) -> None:
    """Print summary and close lineage."""
    if lineage:
        lineage.log_footer(final, final - initial, budget.used,
                           budget.estimate_cost_usd(), stop_reason)

    if verbose:
        print(f"\n  Result: {initial:.1f} → {final:.1f} (+{final - initial:.1f})  "
              f"[{grade_from_score(initial)} → {grade_from_score(final)}]")
        total_gens = det_count + accepted + rejected
        print(f"  Generations: {total_gens} ({accepted} accepted, {rejected} rejected, {det_count} deterministic)")
        if budget.used > 0:
            print(f"  Tokens: {budget.used:,} / {budget.budget:,}  "
                  f"Cost: ${budget.estimate_cost_usd():.3f}")
        if lineage:
            print(f"  Lineage: {lineage.path}")
        print()
