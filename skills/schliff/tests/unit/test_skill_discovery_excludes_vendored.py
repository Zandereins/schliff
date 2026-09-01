"""Skill discovery must not report vendored copies as installed skills.

There are two discovery walks over a repo tree. `discover_instruction_files`
(doctor.py) filters with EXCLUDED_DIRS; `discover_skills` (skill_mesh.py) does a bare
`rglob("SKILL.md")` and filters nothing. Same purpose, two implementations, one filter.

In this project's own repo that made `schliff doctor .` report 6 skills where there is
one: three copies vendored into virtualenvs and a uv cache archive, counted into
"skills scanned", into the grade distribution and into "Total context cost".

Spec: docs/specs/2026-08-13-doctor-counts-vendored-skills.md
"""
from pathlib import Path

import pytest

from skill_mesh import discover_skills

SKILL = """---
name: demo
description: A demo skill used to verify discovery filtering behaviour end to end.
---

# demo

Use when verifying discovery. Do not use for anything else.
"""


def _write(root: Path, relative: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SKILL, encoding="utf-8")
    return path


@pytest.fixture
def tree(tmp_path):
    """A repo with one real skill and four vendored copies."""
    _write(tmp_path, "skills/real/SKILL.md")
    _write(tmp_path, ".venv/lib/python3.12/site-packages/skills/vendored/SKILL.md")
    _write(tmp_path, "node_modules/some-pkg/skills/vendored/SKILL.md")
    # A uv cache archive: no `.venv` and no `site-packages` anywhere in the path.
    _write(tmp_path, ".vercel/python/cache/uv/archive-v0/AbC123/skills/vendored/SKILL.md")
    # A bare site-packages install outside any .venv directory.
    _write(tmp_path, "lib/python3.12/site-packages/skills/vendored/SKILL.md")
    return tmp_path


def test_only_the_real_skill_is_discovered(tree):
    found = {s["path"] for s in discover_skills([str(tree)])}
    assert found == {str(tree / "skills" / "real" / "SKILL.md")}, (
        f"vendored copies discovered: "
        f"{sorted(p.replace(str(tree), '') for p in found)}"
    )


@pytest.mark.parametrize("vendored", [
    ".venv/lib/python3.12/site-packages/skills/vendored/SKILL.md",
    "node_modules/some-pkg/skills/vendored/SKILL.md",
    "backups/schliff/skills.bak.20260611075414/SKILL.md",
    ".vercel/python/cache/uv/archive-v0/AbC123/skills/vendored/SKILL.md",
    "lib/python3.12/site-packages/skills/vendored/SKILL.md",
])
def test_each_vendored_location_is_excluded(tree, vendored):
    found = {s["path"] for s in discover_skills([str(tree)])}
    assert str(tree / vendored) not in found


def test_a_real_skill_named_like_a_cache_dir_still_counts(tmp_path):
    """Exclusion keys on path segments, so a skill ABOUT caching is not collateral."""
    _write(tmp_path, "skills/cache-warmer/SKILL.md")
    found = {s["path"] for s in discover_skills([str(tmp_path)])}
    assert str(tmp_path / "skills" / "cache-warmer" / "SKILL.md") in found


@pytest.mark.parametrize("ancestor", ["build", "dist", "venv", ".cache", "node_modules", "backups"])
def test_excluded_segment_above_the_scan_root_is_not_the_users_problem(tmp_path, ancestor):
    """Filtering must apply BELOW the scan root, not to the path that leads to it.

    Whoever checks their repo out under ~/build/ or ~/.cache/ has not vendored
    anything — the scan root is what the caller asked to scan, and everything above it
    is their filesystem, not their tree. Matching on the full path made
    `schliff doctor /abs/path` report "No skills found" and exit 0, silently, which is
    worse than reporting a vendored copy: the previous defect over-counted loudly, this
    one under-counts quietly.

    doctor.py's sibling walk never had this problem — os.walk prunes dirs it descends
    into, so it can only ever see segments below its own root.
    """
    root = tmp_path / ancestor / "proj" / ".claude" / "skills"
    _write(root, "real/SKILL.md")

    found = {s["path"] for s in discover_skills([str(root)])}
    assert found == {str(root / "real" / "SKILL.md")}, (
        f"a scan root under a directory named {ancestor!r} found nothing"
    )


@pytest.mark.parametrize("skill_name", ["build", "dist", "venv", ".cache", "node_modules", "backups"])
def test_a_skill_may_be_named_like_an_excluded_directory(tmp_path, skill_name):
    """The skill's OWN directory name is not a vendoring signal.

    `build` and `dist` are plausible skill names. Testing every relative segment
    included the skill's own directory, so `skills/build/SKILL.md` was dropped —
    4 of 5 such skills vanished silently, which `main` found. Only directories
    strictly ABOVE the skill's own folder can mark it as vendored.

    The earlier guard here used `cache-warmer`, a name that CONTAINS an excluded
    word but is not equal to one, so it never covered this.
    """
    _write(tmp_path, f"skills/{skill_name}/SKILL.md")
    found = {s["path"] for s in discover_skills([str(tmp_path)])}
    assert str(tmp_path / "skills" / skill_name / "SKILL.md") in found, (
        f"a skill directory named {skill_name!r} was dropped"
    )


def test_excluded_segment_below_the_scan_root_is_still_excluded(tmp_path):
    """The guard above must not reopen the door it was added to close."""
    root = tmp_path / "build" / "proj" / ".claude" / "skills"
    _write(root, "real/SKILL.md")
    _write(root, "vendor/.venv/lib/python3.12/site-packages/skills/x/SKILL.md")

    found = {s["path"] for s in discover_skills([str(root)])}
    assert found == {str(root / "real" / "SKILL.md")}


def test_a_backup_is_not_an_installed_skill(tmp_path):
    """`~/.claude/backups/` holds backups, and a backup is not a loadable skill.

    This completes a fix from 2026-06-11. `install.sh` used to write its backup
    to ``~/.claude/skills/schliff.bak.<ts>`` — inside the skill scan path, which
    duplicated the whole ``/schliff:*`` namespace — and was moved to
    ``~/.claude/backups/`` for that reason
    (docs/specs/2026-06-11-agentic-integration.md). That protected Claude Code's
    scan path but not a scan pointed at ``~/.claude`` itself: measured
    2026-09-01, ``doctor ~/.claude`` reported THREE rows named ``schliff``, two
    of them June backups of its own SKILL.md, contributing 18,014 of 438,597
    tokens and two of 138 counted installations.

    The mutation: drop ``backups`` from ``EXCLUDED_DIRS`` and this goes red.
    """
    _write(tmp_path, "skills/real/SKILL.md")
    _write(tmp_path, "backups/schliff/skills.bak.20260611075414/SKILL.md")
    _write(tmp_path, "backups/schliff-skill-backups/schliff.bak.20260611071745/SKILL.md")

    found = {s["path"] for s in discover_skills([str(tmp_path)])}

    assert found == {str(tmp_path / "skills" / "real" / "SKILL.md")}, (
        f"backups discovered as skills: "
        f"{sorted(p.replace(str(tmp_path), '') for p in found)}"
    )


def test_the_eval_suite_path_has_one_home():
    """A consolidation without a gate is a convention, not a fix.

    The `<skill dir>/eval-suite.json` expression had six independent derivations
    across `shared` and `doctor` — the loader, its cache wrapper, the
    invalidator, two branches of `skill_payload_digest`, and doctor's row
    builder — all keying the same module dicts on a string each of them rebuilt.
    That is the #209 shape: the defect is not the expression, it is the number of
    homes. A caller outside the module needed it as a seventh, which surfaced it.

    Keyed on the construction, not on wording: rebuild the path in either of
    these two modules instead of calling `shared.eval_suite_path` and this goes
    red.

    **Scope, stated exactly.** This covers `shared.py` and `doctor.py`, the two
    modules consolidated here. It is NOT a repository-wide uniqueness claim:
    when this gate was first written repo-wide it immediately found five more
    derivations — in `achievements.py`, `dashboard.py`, `init-skill.py`,
    `score-skill.py` and `text_gradient.py` — which is precisely why a
    consolidation needs a gate rather than an assertion that it is complete.
    Those five are a separate, mechanical change; widening this list is what
    closes them.
    """
    import re
    from pathlib import Path as _P

    scripts = _P(__file__).resolve().parents[2] / "scripts"
    # Path CONSTRUCTION, in either quoting style and through os.path.join.
    # Keyed on the double-quoted form alone, this gate passed on the very
    # mutation its docstring named — single quotes slipped straight through.
    #
    # Scope, stated rather than claimed: an f-string or a name assembled from
    # parts would still evade this. The pattern covers the shapes that exist in
    # this codebase; the point is that it now fails when someone writes the
    # obvious thing, not that it cannot be evaded.
    construction = re.compile(r"""(?:/\s*|,\s*)["']eval-suite\.json["']""")
    sites = []
    for name in ("shared.py", "doctor.py"):
        source = scripts / name
        for n, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if construction.search(line):
                sites.append(f"{name}:{n}")

    assert len(sites) == 1, (
        f"the eval-suite path is derived in {len(sites)} places across "
        f"shared.py and doctor.py, not one: {sites}"
    )
    assert sites[0].startswith("shared.py"), f"its one home should be shared.py, found {sites[0]}"


@pytest.mark.parametrize("walker", ["doctor", "sync"])
def test_backups_is_pruned_by_the_instruction_walks_too(tmp_path, walker):
    """`EXCLUDED_DIRS` has three consumers, and `backups` reaches all of them.

    `discover_skills` is only one. `doctor.discover_instruction_files` and
    `sync.discover_all_instruction_files` prune the same set from an `os.walk`
    over an arbitrary user repository, so `myrepo/backups/AGENTS.md` now drops
    out of drift analysis and out of doctor's instruction-file list as well.

    That is intended — a backup of an AGENTS.md is not the project's AGENTS.md —
    but it is blast radius beyond the `~/.claude` case the change was argued
    from, and `backups` is likelier to be a live user directory than
    `node_modules`. Pinned so the behaviour is a decision and not a side effect.
    """
    (tmp_path / "AGENTS.md").write_text("# Real\n\nSetup: `make dev`\n", encoding="utf-8")
    backup = tmp_path / "backups" / "2026-06-11"
    backup.mkdir(parents=True)
    (backup / "AGENTS.md").write_text("# Backup\n\nSetup: `make dev`\n", encoding="utf-8")

    if walker == "doctor":
        import doctor
        found = {f["path"] for f in doctor.discover_instruction_files(str(tmp_path))}
    else:
        import sync
        found = {f["path"] for f in sync.discover_all_instruction_files(str(tmp_path))}

    # Relative to tmp_path, because pytest names the temp directory after the
    # test — so an absolute-path check for "backups" matches the fixture itself
    # and fails on a correct implementation. It did.
    relative = {str(Path(p).relative_to(tmp_path)) for p in found}

    assert not any(r.startswith("backups/") for r in relative), (
        f"a backup copy reached the {walker} instruction walk: {sorted(relative)}"
    )
    assert "AGENTS.md" in relative, f"the real AGENTS.md must still be found: {sorted(relative)}"
