#!/usr/bin/env python3
"""Schliff Skill Mesh — Multi-Skill Conflict Detection

Scans all installed skills, detects trigger overlap, broken handoffs,
and scope collisions. Reports mesh health score.

Usage:
    python3 skill-mesh.py [--skill-dirs DIR...] [--json] [--incremental] [--severity info|warning|critical]

Default scan dirs: ~/.claude/skills/, .claude/skills/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import shared

# Import scorer functions for tokenization and description extraction
from nlp import tokenize_meaningful
from shared import EXCLUDED_DIRS, extract_description

# Bound on a single discovery walk. Module-level rather than local to
# `discover_skills`, because a caller that has to know whether the cap was hit —
# a truncated scan sorts AFTER truncating, so its contents follow filesystem
# order — cannot read a local. One home for the number.
MAX_SCAN_FILES = 1000

# Set by `discover_skills` when a walk stops at the cap; read through
# `discover_skills_with_status`, which resets it first. Module state rather than
# a changed return type, because every existing caller wants the list alone.
_last_scan_truncated = False

# --- Skill Discovery ---

def discover_skills(skill_dirs: list[str]) -> list[dict]:
    """Find all SKILL.md files in given directories.

    ``discover_skills_with_status`` returns the same list plus whether the walk
    hit ``MAX_SCAN_FILES``. Callers that must not act on a truncated set — a
    corpus freeze, say — need that fact and cannot infer it from the list: the
    cap counts CANDIDATES surviving ``EXCLUDED_DIRS``, while this list only grows
    for those that also pass symlink confinement, realpath dedup and the bounded
    read, so a short list is not evidence of truncation and a full one is not
    evidence against it.

    Returns list of skill dicts with: path, name, description, content_hash, tokens.
    """
    global _last_scan_truncated
    # Cleared here and not only in the status wrapper: `doctor` calls this
    # directly, so one truncated scan otherwise left the flag stuck True for the
    # rest of the process and every later reader saw a truncation that did not
    # happen. The walk that sets it owns clearing it.
    _last_scan_truncated = False

    skills = []
    seen_paths = set()

    file_count = 0
    scan_limit_reached = False

    for skill_dir in skill_dirs:
        if scan_limit_reached:
            break
        skill_dir_path = Path(skill_dir).expanduser()
        if not skill_dir_path.is_dir():
            continue

        scan_root = Path(os.path.realpath(str(skill_dir_path)))
        for skill_md in skill_dir_path.rglob("SKILL.md"):
            # A vendored copy is not an installed skill. doctor.py's sibling walk
            # (discover_instruction_files) has always filtered on EXCLUDED_DIRS; this
            # one did not, so virtualenvs, node_modules and cache archives were counted
            # into "skills scanned", the grade distribution and "Total context cost".
            #
            # Only segments BELOW the scan root count. The caller named the root; what
            # lies above it is their filesystem, not their tree. Matching the full path
            # made a checkout under ~/build/ or ~/.cache/ report "No skills found" and
            # exit 0 — quiet under-counting, which is worse than the loud over-counting
            # this filter was added to fix. os.walk in the sibling never had the problem
            # because pruning can only ever reach below its own root.
            #
            # Keyed on path SEGMENTS, so a skill legitimately named `cache-warmer` is
            # not collateral.
            # `[:-2]` drops the filename and the skill's OWN directory: only what lies
            # strictly above the skill folder can mark it as vendored. Without it, a
            # skill legitimately named `build`, `dist` or `.cache` excluded itself —
            # 4 of 5 such skills vanished silently, the same quiet under-count as the
            # scan-root defect, one level down.
            try:
                relative_parts = skill_md.relative_to(skill_dir_path).parts[:-2]
            except ValueError:  # pragma: no cover — rglob yields paths under the root
                relative_parts = skill_md.parts[:-2]
            if EXCLUDED_DIRS & set(relative_parts):
                continue
            # Counted AFTER the filter, deliberately: MAX_SCAN_FILES exists to bound the
            # expensive work, and the expensive work is the read + parse below, which a
            # filtered path never reaches. Iterating rglob is cheap by comparison. The
            # tradeoff is that a tree full of vendored copies no longer trips the limit
            # early — it also no longer spends the budget on files that are discarded.
            file_count += 1
            if file_count > MAX_SCAN_FILES:
                print(f"Warning: scan limit reached ({MAX_SCAN_FILES} files), stopping discovery", file=sys.stderr)
                scan_limit_reached = True
                _last_scan_truncated = True
                break
            try:
                # Use os.path.realpath() explicitly to resolve all symlinks
                real_path = os.path.realpath(str(skill_md))
                resolved = Path(real_path)
                # Prevent symlink escape outside scan root
                resolved.relative_to(scan_root)
            except (ValueError, OSError):
                continue
            if real_path in seen_paths:
                continue
            seen_paths.add(real_path)

            # The shared reader, not a local read: regular-file check, then size,
            # then read. Reading first blocks forever on a FIFO named SKILL.md
            # (measured) and raises MemoryError on a multi-gigabyte one, which
            # neither handler here catches. This is the first file doctor opens,
            # so it decides whether the scan can be hung at all — the guard in
            # `_read_bounded` is downstream of it.
            content = shared._read_bounded(resolved)
            if content is None:
                continue

            # Extract metadata
            name = "unknown"
            name_match = re.search(r"^name:\s*(.+?)$", content, re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip().strip('"').strip("'")

            description = extract_description(content)
            tokens = tokenize_meaningful(
                description.lower(), expand_reverse=True
            ) if description else []

            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            skills.append({
                "path": str(skill_md),
                "name": name,
                "description": description,
                "content_hash": content_hash,
                "tokens": tokens,
                "content": content,
            })

    # Sort by resolved path for deterministic ordering across machines/OSes
    # (rglob traversal order is filesystem-dependent and not stable).
    skills.sort(key=lambda s: s["path"])
    return skills


def discover_skills_with_status(skill_dirs: list[str]) -> tuple[list[dict], bool]:
    """``discover_skills``, plus whether the walk stopped at ``MAX_SCAN_FILES``.

    One walk, two callers with different needs. The truncation flag lives here
    because the walk owns it; a caller comparing ``len(result)`` against the cap
    is comparing a filtered count to an unfiltered bound, which is wrong in both
    directions — it misses a truncated scan whose candidates were mostly dropped,
    and it rejects a complete scan of exactly ``MAX_SCAN_FILES`` files, since the
    break is ``>`` and not ``>=``.
    """
    skills = discover_skills(skill_dirs)
    return skills, _last_scan_truncated


# --- TF-IDF Cosine Similarity ---

def _compute_tfidf_vectors(skills: list[dict]) -> tuple[dict, dict]:
    """Compute TF-IDF vectors for all skills.

    Returns:
        (tfidf_vectors, document_frequencies)
        tfidf_vectors: {skill_index: {term: tfidf_weight}}
        document_frequencies: {term: num_skills_containing_term}
    """
    n_docs = len(skills)
    if n_docs == 0:
        return {}, {}

    # Document frequency
    df = defaultdict(int)
    for skill in skills:
        unique_tokens = set(skill["tokens"])
        for token in unique_tokens:
            df[token] += 1

    # TF-IDF vectors
    vectors = {}
    for i, skill in enumerate(skills):
        tf = defaultdict(int)
        for token in skill["tokens"]:
            tf[token] += 1

        vector = {}
        for term, count in tf.items():
            tf_val = count / max(len(skill["tokens"]), 1)
            idf_val = math.log(n_docs / (df[term] + 1)) + 1
            vector[term] = tf_val * idf_val
        vectors[i] = vector

    return vectors, dict(df)


def _cosine_similarity(v1: dict, v2: dict) -> float:
    """Compute cosine similarity between two sparse TF-IDF vectors."""
    common_terms = set(v1.keys()) & set(v2.keys())
    if not common_terms:
        return 0.0

    dot = sum(v1[t] * v2[t] for t in common_terms)
    norm1 = math.sqrt(sum(v ** 2 for v in v1.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in v2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def _stable_token_hash(token: str) -> int:
    """Deterministic hash for a token string (independent of PYTHONHASHSEED).

    Uses zlib.crc32 instead of hashlib.md5 for ~5-10x better performance.
    """
    import zlib
    return zlib.crc32(token.encode("utf-8")) & 0x7FFFFFFF


def _minhash_coeffs(num_hashes: int, seed: int) -> list[tuple[int, int]]:
    """Return the (a, b) MinHash coefficient table for (num_hashes, seed).

    The table is fully determined by the seed, so it is identical across every
    call. Cache it so repeated per-skill signature computation does not
    regenerate 128 RNG pairs each time (signatures are unchanged).
    """
    cached = _MINHASH_COEFF_CACHE.get((num_hashes, seed))
    if cached is None:
        rng = random.Random(seed)
        cached = [
            (rng.randint(1, 2**31 - 1), rng.randint(0, 2**31 - 1))
            for _ in range(num_hashes)
        ]
        _MINHASH_COEFF_CACHE[(num_hashes, seed)] = cached
    return cached


_MINHASH_COEFF_CACHE: dict[tuple[int, int], list[tuple[int, int]]] = {}


def _minhash_signature(tokens: set, num_hashes: int = 128, seed: int = 42) -> list[int]:
    """Compute MinHash signature for a token set.

    Uses deterministic hashing (hashlib) instead of Python's built-in hash()
    to ensure reproducible signatures across process invocations.
    """
    if not tokens:
        return [0] * num_hashes
    # Coefficients are consistent across calls via seed — reuse the cached table.
    coeffs = _minhash_coeffs(num_hashes, seed)
    MOD = (1 << 31) - 1
    signature = []
    for a, b in coeffs:
        min_hash = min((a * _stable_token_hash(token) + b) % MOD for token in tokens)
        signature.append(min_hash)
    return signature


def _lsh_candidates(signatures: list[list[int]], bands: int = 16) -> set[tuple[int, int]]:
    """Find candidate pairs using LSH banding."""
    num_hashes = len(signatures[0]) if signatures else 0
    rows_per_band = num_hashes // bands

    candidates = set()
    for band_idx in range(bands):
        buckets: dict[int, list[int]] = {}
        start = band_idx * rows_per_band
        end = start + rows_per_band
        for skill_idx, sig in enumerate(signatures):
            band_hash = hash(tuple(sig[start:end]))
            if band_hash in buckets:
                for other_idx in buckets[band_hash]:
                    pair = (min(skill_idx, other_idx), max(skill_idx, other_idx))
                    candidates.add(pair)
                buckets[band_hash].append(skill_idx)
            else:
                buckets[band_hash] = [skill_idx]

    return candidates


def _skill_key(skill: dict) -> str:
    """Identity of a skill for pairing purposes: its declared name.

    Two SKILL.md files with the same name are one skill found at two paths —
    a global install plus a project-local copy, a vendored fixture — not two
    skills competing. Comparing such a pair produces a perfect overlap and a
    patch instruction naming the same skill on both sides ("Narrow scope: X
    should own this domain"), which nobody can carry out. Reported separately
    by `detect_duplicate_names`.
    """
    return (skill.get("name") or "").strip().lower()


def _is_same_skill(a: dict, b: dict) -> bool:
    key_a, key_b = _skill_key(a), _skill_key(b)
    # An unnamed skill parses as "unknown"; two of those are not known to be
    # the same thing, so they stay comparable.
    return bool(key_a) and key_a not in ("", "unknown") and key_a == key_b


def _detect_overlaps_bruteforce(skills: list[dict], vectors: dict) -> list[dict]:
    """O(n^2) brute-force trigger overlap detection for small skill sets."""
    overlaps = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            if i not in vectors or j not in vectors:
                continue
            if _is_same_skill(skills[i], skills[j]):
                continue

            sim = _cosine_similarity(vectors[i], vectors[j])
            if sim < 0.20:
                continue

            common = set(vectors[i].keys()) & set(vectors[j].keys())

            if sim >= 0.70:
                severity = "critical"
            elif sim >= 0.45:
                severity = "warning"
            else:
                severity = "info"

            overlaps.append({
                "type": "trigger_overlap",
                "severity": severity,
                "skill_a": skills[i]["name"],
                "skill_a_path": skills[i]["path"],
                "skill_b": skills[j]["name"],
                "skill_b_path": skills[j]["path"],
                "similarity": round(sim, 3),
                "common_terms": sorted(common)[:10],
            })
    return overlaps


def detect_trigger_overlaps(skills: list[dict]) -> list[dict]:
    """Detect pairwise trigger overlap using TF-IDF cosine similarity.

    Uses MinHash + LSH for O(n) candidate pruning when n >= 50,
    falls back to O(n^2) brute-force for smaller sets.

    Thresholds: >=0.70 critical, 0.45-0.69 warning, 0.20-0.44 info
    """
    vectors, _ = _compute_tfidf_vectors(skills)

    # Fallback: brute-force for small skill sets (LSH overhead not worth it)
    if len(skills) < 50:
        return _detect_overlaps_bruteforce(skills, vectors)

    # MinHash + LSH path for large skill sets
    # Compute MinHash signatures from token sets
    signatures = []
    for skill in skills:
        token_set = set(skill.get("tokens", []))
        signatures.append(_minhash_signature(token_set))

    # Find candidate pairs via LSH banding
    candidates = _lsh_candidates(signatures)

    # Only compute exact cosine similarity for candidate pairs
    overlaps = []
    for i, j in candidates:
        if i not in vectors or j not in vectors:
            continue
        # Same rule as the brute-force path above. Applying it to only one of
        # the two would make the finding depend on whether the machine happens
        # to hold 50 skills.
        if _is_same_skill(skills[i], skills[j]):
            continue

        sim = _cosine_similarity(vectors[i], vectors[j])
        if sim < 0.20:
            continue

        common = set(vectors[i].keys()) & set(vectors[j].keys())

        if sim >= 0.70:
            severity = "critical"
        elif sim >= 0.45:
            severity = "warning"
        else:
            severity = "info"

        overlaps.append({
            "type": "trigger_overlap",
            "severity": severity,
            "skill_a": skills[i]["name"],
            "skill_a_path": skills[i]["path"],
            "skill_b": skills[j]["name"],
            "skill_b_path": skills[j]["path"],
            "similarity": round(sim, 3),
            "common_terms": sorted(common)[:10],
        })

    return overlaps


# --- Broken Handoff Detection ---

def _levenshtein_distance(s1: str, s2: str, threshold: int = 2) -> int:
    """Simple Levenshtein distance for fuzzy matching with early exit."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1, threshold)
    if len(s2) == 0:
        return len(s1)
    # Length pruning: if length difference exceeds threshold, skip computation
    if abs(len(s1) - len(s2)) > threshold:
        return abs(len(s1) - len(s2))

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,
                prev_row[j + 1] + 1,
                prev_row[j] + cost,
            ))
        prev_row = curr_row

    return prev_row[-1]


_DOMAIN_KEYWORDS = {
    "devops": ["deploy", "docker", "kubernetes", "ci/cd", "pipeline", "infrastructure", "terraform", "helm"],
    "testing": ["test", "spec", "assertion", "mock", "fixture", "coverage", "jest", "pytest"],
    "quality": ["lint", "format", "quality", "review", "audit", "standards", "convention"],
    "backend": ["api", "server", "database", "endpoint", "rest", "graphql", "microservice"],
    "frontend": ["react", "component", "css", "html", "ui", "layout", "style", "tailwind"],
    "security": ["auth", "security", "vulnerability", "credential", "encrypt", "token", "permission"],
    "data": ["data", "analytics", "pipeline", "etl", "transform", "schema", "migration"],
    "docs": ["documentation", "readme", "guide", "tutorial", "api-doc", "changelog"],
    "ai": ["llm", "prompt", "model", "embedding", "agent", "ai", "ml", "inference"],
    "skill": ["skill", "improve", "trigger", "eval", "score", "iterate", "forge"],
}


def _classify_domain(skill: dict) -> dict[str, float]:
    """Classify a skill into domains based on keyword matching.

    Returns dict of domain -> relevance score.
    """
    text = (skill.get("description", "") + " " + skill.get("name", "")).lower()
    tokens = set(tokenize_meaningful(text, expand_reverse=True))

    domains = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        overlap = sum(1 for kw in keywords if kw in tokens or any(kw in t for t in tokens))
        if overlap > 0:
            domains[domain] = overlap / len(keywords)

    return domains


def detect_duplicate_names(skills: list[dict]) -> list[dict]:
    """Report one skill name found at more than one path.

    This is what the overlap detectors used to call a critical conflict. It is
    a real thing worth seeing — only one of the copies wins when the agent
    resolves the name, and which one is not obvious from the file — but it is
    not a scope problem, and it is not the author's mistake to fix by rewriting
    a description. Hence `info`: visible, and costing no health.
    """
    by_name: dict[str, list[str]] = defaultdict(list)
    for skill in skills:
        key = _skill_key(skill)
        if key and key != "unknown":
            by_name[key].append(skill["path"])

    return [
        {
            "type": "duplicate_name",
            "severity": "info",
            "name": name,
            "paths": sorted(paths),
        }
        for name, paths in sorted(by_name.items())
        if len(paths) > 1
    ]


def detect_scope_collisions(skills: list[dict]) -> list[dict]:
    """Detect skills with overlapping primary domains and positive scope overlap.

    Groups skills by primary domain first, then only compares within each
    domain group — reducing comparisons from O(n^2) to O(k^2 per domain)
    where k << n.
    """
    # Group skill indices by primary domain
    domain_groups: dict[str, list[int]] = defaultdict(list)
    for i, skill in enumerate(skills):
        domains = _classify_domain(skill)
        if domains:
            primary = max(domains, key=domains.get)
            domain_groups[primary].append(i)

    collisions = []

    for domain, indices in domain_groups.items():
        # Only compare within same domain
        for a_pos in range(len(indices)):
            for b_pos in range(a_pos + 1, len(indices)):
                i, j = indices[a_pos], indices[b_pos]

                if _is_same_skill(skills[i], skills[j]):
                    continue

                # Check scope overlap via token overlap
                tokens_i = set(skills[i].get("tokens", []))
                tokens_j = set(skills[j].get("tokens", []))
                if not tokens_i or not tokens_j:
                    continue

                overlap = len(tokens_i & tokens_j)
                union = len(tokens_i | tokens_j)
                jaccard = overlap / union if union > 0 else 0

                if jaccard < 0.20:
                    continue

                severity = "critical" if jaccard >= 0.50 else "warning" if jaccard >= 0.35 else "info"

                collisions.append({
                    "type": "scope_collision",
                    "severity": severity,
                    "skill_a": skills[i]["name"],
                    "skill_a_path": skills[i]["path"],
                    "skill_b": skills[j]["name"],
                    "skill_b_path": skills[j]["path"],
                    "shared_domain": domain,
                    "overlap_score": round(jaccard, 3),
                })

    return collisions


# --- Mesh Evolution Actions ---

def generate_mesh_actions(issues: list[dict], skills: list[dict]) -> list[dict]:
    """Generate concrete fix actions for mesh issues.

    For each issue type, generates a specific remediation action:
    - trigger_overlap (critical): Negative-boundary additions for both skills
    - scope_collision: Domain-ownership proposal + scope-narrowing patches

    Returns list of MeshAction dicts with: type, target_path, instruction, patch, confidence.
    """
    actions = []

    for issue in issues:
        itype = issue.get("type", "")
        severity = issue.get("severity", "info")

        if itype == "trigger_overlap" and severity == "critical":
            # Generate negative boundary additions for both skills
            skill_a = issue.get("skill_a", "")
            skill_b = issue.get("skill_b", "")
            common = issue.get("common_terms", [])

            if skill_a and skill_b:
                # For skill A: add "Do NOT use for [skill_b's domain]"
                actions.append({
                    "type": "add_negative_boundary",
                    "target_path": issue.get("skill_a_path", ""),
                    "instruction": f"Add negative boundary: 'Do NOT use for {skill_b} scenarios' "
                                   f"to disambiguate from {skill_b}",
                    "patch": {
                        "op": "append_section",
                        "content": f"\nDo NOT use for:\n- Tasks that belong to `{skill_b}` "
                                   f"(disambiguate: {', '.join(common[:5])})\n",
                    },
                    "confidence": 0.8 if severity == "critical" else 0.5,
                    "issue_ref": f"trigger_overlap:{skill_a}:{skill_b}",
                })
                # Mirror for skill B
                actions.append({
                    "type": "add_negative_boundary",
                    "target_path": issue.get("skill_b_path", ""),
                    "instruction": f"Add negative boundary: 'Do NOT use for {skill_a} scenarios' "
                                   f"to disambiguate from {skill_a}",
                    "patch": {
                        "op": "append_section",
                        "content": f"\nDo NOT use for:\n- Tasks that belong to `{skill_a}` "
                                   f"(disambiguate: {', '.join(common[:5])})\n",
                    },
                    "confidence": 0.8 if severity == "critical" else 0.5,
                    "issue_ref": f"trigger_overlap:{skill_b}:{skill_a}",
                })

        elif itype == "scope_collision":
            skill_a = issue.get("skill_a", "")
            skill_b = issue.get("skill_b", "")
            domain = issue.get("shared_domain", "")

            actions.append({
                "type": "scope_narrowing",
                "target_path": issue.get("skill_a_path", ""),
                "instruction": f"Narrow scope: {skill_a} should own '{domain}' for its specific use case. "
                               f"Add 'Scope: {domain} specifically for [specific aspect]' to description.",
                "patch": None,  # Requires human judgment
                "confidence": 0.5,
                "issue_ref": f"scope_collision:{skill_a}:{skill_b}",
            })

    return actions


# --- Incremental Cache ---

_MESH_CACHE_PATH = Path.home() / ".schliff" / "meta" / "mesh-cache.json"


# Bump whenever a detector's verdict changes for unchanged input. The cache
# keys on skill CONTENT, so without this an upgrade is invisible to everyone who
# has run `doctor` before: same files, same hashes, cached verdict returned, and
# the fix they installed never shows. Raised to 2 when same-name pairs stopped
# being reported as collisions.
_MESH_CACHE_VERSION = 2


def _load_mesh_cache() -> dict:
    """Load mesh analysis cache (content_hash -> analysis results)."""
    if not _MESH_CACHE_PATH.exists():
        return {}
    try:
        cache = json.loads(_MESH_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(cache, dict) or cache.get("_version") != _MESH_CACHE_VERSION:
        # Written by a different analysis. Discard rather than migrate: the
        # entries are verdicts, and a verdict from older logic is exactly what
        # must not survive.
        return {}
    return cache


def _save_mesh_cache(cache: dict) -> None:
    """Save mesh analysis cache."""
    cache["_version"] = _MESH_CACHE_VERSION
    _MESH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MESH_CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")


def _needs_recompute(skills: list[dict], cache: dict) -> tuple[bool, list[int]]:
    """Check which skill pairs need recomputation based on content hashes.

    Returns (any_changed, list_of_changed_skill_indices).
    """
    changed = []
    for i, skill in enumerate(skills):
        cache_key = skill.get("path", "")
        cached_hash = cache.get(cache_key, {}).get("content_hash", "")
        if cached_hash != skill.get("content_hash", ""):
            changed.append(i)

    return len(changed) > 0, changed


# --- Mesh Health Score ---

def compute_mesh_health(issues: list[dict]) -> dict:
    """Compute mesh health score starting from 100, subtracting penalties.

    Penalties (each capped):
    - Critical conflicts: 15 each (max 60)
    - Warnings: 5 each (max 30)
    - Broken handoffs: 8 each (max 40)
    - Critical collisions: 12 each (max 48)
    """
    score = 100

    critical_conflicts = sum(1 for i in issues if i["type"] == "trigger_overlap" and i["severity"] == "critical")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    critical_collisions = sum(1 for i in issues if i["type"] == "scope_collision" and i["severity"] == "critical")

    score -= min(critical_conflicts * 15, 60)
    score -= min(warnings * 5, 30)
    score -= min(critical_collisions * 12, 48)

    return {
        "score": max(0, score),
        "total_issues": len(issues),
        "critical_conflicts": critical_conflicts,
        "warnings": warnings,
        "critical_collisions": critical_collisions,
    }


# --- Main ---

def run_mesh_analysis(
    skill_dirs: list[str],
    severity_filter: Optional[str] = None,
    incremental: bool = False,
    skills: Optional[list[dict]] = None,
) -> dict:
    """Run full mesh analysis.

    Args:
        skills: Pre-discovered skill dicts (path/name/description/content_hash/
            tokens/content). When provided, skips the internal discover_skills()
            call so a caller that already walked the tree (e.g. doctor) does not
            re-walk and re-read every SKILL.md. Results are identical.

    Returns dict with: skills, issues, health, summary.
    """
    # Default dirs
    if not skill_dirs:
        skill_dirs = [
            str(Path.home() / ".claude" / "skills"),
            ".claude/skills",
        ]

    if skills is None:
        skills = discover_skills(skill_dirs)

    if not skills:
        return {
            "skills_found": 0,
            "issues": [],
            "health": {"score": 100, "total_issues": 0},
            "summary": "No skills found in scanned directories.",
        }

    # Incremental mode: only recompute pairs involving changed skills
    cache = {}
    if incremental:
        cache = _load_mesh_cache()
        any_changed, changed_indices = _needs_recompute(skills, cache)
        if not any_changed and cache.get("_issues") is not None:
            # No skills changed — return cached result
            cached_issues = cache.get("_issues", [])
            severity_order = {"info": 0, "warning": 1, "critical": 2}
            if severity_filter and severity_filter in severity_order:
                cached_issues = [i for i in cached_issues if severity_order.get(i.get("severity", "info"), 0) >= severity_order[severity_filter]]
            return {
                "skills_found": len(skills),
                "skill_names": [s["name"] for s in skills],
                "issues": cached_issues,
                "health": compute_mesh_health(cached_issues),
                "incremental": True,
                "cache_hit": True,
            }

    # Run all detectors
    issues = []
    issues.extend(detect_trigger_overlaps(skills))
    issues.extend(detect_scope_collisions(skills))
    issues.extend(detect_duplicate_names(skills))

    # Generate evolution actions for issues
    actions = generate_mesh_actions(issues, skills)

    # Filter by severity
    severity_order = {"info": 0, "warning": 1, "critical": 2}
    if severity_filter and severity_filter in severity_order:
        min_severity = severity_order[severity_filter]
        issues = [i for i in issues if severity_order.get(i.get("severity", "info"), 0) >= min_severity]

    # Sort by severity descending
    issues.sort(key=lambda i: severity_order.get(i.get("severity", "info"), 0), reverse=True)

    health = compute_mesh_health(issues)

    # Update cache
    if incremental:
        for skill in skills:
            cache[skill.get("path", "")] = {"content_hash": skill.get("content_hash", "")}
        cache["_issues"] = issues
        _save_mesh_cache(cache)

    result = {
        "skills_found": len(skills),
        "skill_names": [s["name"] for s in skills],
        "issues": issues,
        "health": health,
    }

    if actions:
        result["actions"] = actions
        result["actions_count"] = len(actions)

    if incremental:
        result["incremental"] = True
        result["cache_hit"] = False

    return result


def format_mesh_report(result: dict) -> str:
    """Format mesh analysis as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("  Schliff Skill Mesh — Health Report")
    lines.append("=" * 70)
    lines.append("")

    health = result.get("health", {})
    score = health.get("score", 100)
    total_issues = health.get("total_issues", 0)

    indicator = "\u2713" if score >= 80 else "\u25b3" if score >= 50 else "\u2717"
    lines.append(f"  {indicator} Mesh Health Score: {score}/100")
    lines.append(f"  Skills scanned: {result.get('skills_found', 0)}")
    lines.append(f"  Issues found: {total_issues}")
    lines.append("")

    if result.get("skill_names"):
        lines.append("  Skills in mesh:")
        for name in sorted(result["skill_names"]):
            lines.append(f"    - {name}")
        lines.append("")

    issues = result.get("issues", [])
    if issues:
        lines.append("  Issues:")
        lines.append("  " + "-" * 60)
        for issue in issues:
            sev = issue.get("severity", "info").upper()
            itype = issue.get("type", "unknown")

            if itype == "trigger_overlap":
                lines.append(
                    f"  [{sev}] Trigger overlap: {issue['skill_a']} <-> {issue['skill_b']}"
                    f" (similarity: {issue['similarity']:.1%})"
                )
                if issue.get("common_terms"):
                    lines.append(f"         Common terms: {', '.join(issue['common_terms'][:5])}")
            elif itype == "scope_collision":
                lines.append(
                    f"  [{sev}] Scope collision: {issue['skill_a']} <-> {issue['skill_b']}"
                    f" (domain: {issue['shared_domain']}, overlap: {issue['overlap_score']:.1%})"
                )
            elif itype == "duplicate_name":
                lines.append(
                    f"  [{sev}] Duplicate name: '{issue['name']}' found at "
                    f"{len(issue['paths'])} paths — only one of them resolves"
                )
                for path in issue["paths"]:
                    lines.append(f"         {path}")
            lines.append("")
    else:
        lines.append("  No issues found — mesh is healthy!")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Schliff Skill Mesh Analyzer")
    parser.add_argument("--skill-dirs", nargs="+", default=[], help="Directories to scan for SKILL.md files")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--incremental", action="store_true", help="Use content-hash cache to skip recomputation for unchanged skills")
    parser.add_argument("--severity", choices=["info", "warning", "critical"], default=None,
                        help="Minimum severity to report")
    args = parser.parse_args()

    result = run_mesh_analysis(
        skill_dirs=args.skill_dirs,
        severity_filter=args.severity,
        incremental=args.incremental,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_mesh_report(result))


if __name__ == "__main__":
    main()
