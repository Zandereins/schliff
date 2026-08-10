"""The mesh compares skills against each other — never one against itself.

Two SKILL.md files carrying the same `name` are one skill found at two paths,
not two skills competing for the same triggers. The mesh used to report the
pair as a critical scope collision AND a critical trigger overlap, costing 27
health points and emitting a patch instruction — "Narrow scope: X should own
this domain" — that names the same skill on both sides and cannot be carried
out by anyone.

The case is ordinary, not exotic: a skill installed in `~/.claude/skills` and
again inside a project is the shape schliff itself is distributed in.
"""
import json

import skill_mesh

SKILL = """\
---
name: {name}
description: Improve and score a deployment skill. Use when you want to iterate
  on triggers, run an eval, or forge a better deploy skill.
---

# {name}

Run `make deploy`.
"""


def _write(root, subdir, name):
    d = root / subdir / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL.format(name=name), encoding="utf-8")
    return d / "SKILL.md"


def _same_skill_twice(tmp_path):
    _write(tmp_path, "global", "deploy-helper")
    _write(tmp_path, "project", "deploy-helper")
    return skill_mesh.discover_skills([str(tmp_path)])


def _two_distinct_skills(tmp_path):
    _write(tmp_path, "global", "deploy-helper")
    _write(tmp_path, "project", "release-helper")
    return skill_mesh.discover_skills([str(tmp_path)])


class TestOneSkillAtTwoPathsIsNotAConflict:
    def test_the_fixture_really_produces_two_entries(self, tmp_path):
        """Guard: if discovery ever deduplicates by content, the tests below
        would pass without the code under test doing anything."""
        skills = _same_skill_twice(tmp_path)

        assert len(skills) == 2
        assert {s["name"] for s in skills} == {"deploy-helper"}

    def test_it_is_not_a_scope_collision(self, tmp_path):
        skills = _same_skill_twice(tmp_path)

        assert skill_mesh.detect_scope_collisions(skills) == []

    def test_it_is_not_a_trigger_overlap(self, tmp_path):
        skills = _same_skill_twice(tmp_path)

        assert skill_mesh.detect_trigger_overlaps(skills) == []

    def test_it_is_reported_as_a_duplicate_name(self, tmp_path):
        """Silence would be the wrong fix: the same name at two paths means one
        of them is shadowed, and which one wins is not obvious."""
        skills = _same_skill_twice(tmp_path)

        dupes = skill_mesh.detect_duplicate_names(skills)

        assert len(dupes) == 1
        assert dupes[0]["type"] == "duplicate_name"
        assert dupes[0]["severity"] == "info"
        assert dupes[0]["name"] == "deploy-helper"
        assert len(dupes[0]["paths"]) == 2

    def test_it_costs_no_health(self, tmp_path):
        skills = _same_skill_twice(tmp_path)
        issues = (
            skill_mesh.detect_trigger_overlaps(skills)
            + skill_mesh.detect_scope_collisions(skills)
            + skill_mesh.detect_duplicate_names(skills)
        )

        assert skill_mesh.compute_mesh_health(issues)["score"] == 100


class TestDistinctSkillsStillCollide:
    """The discriminator. A fix that silences same-name pairs by silencing the
    detectors would pass every test above and destroy the module's purpose."""

    def test_two_different_names_still_produce_findings(self, tmp_path):
        skills = _two_distinct_skills(tmp_path)

        findings = (
            skill_mesh.detect_scope_collisions(skills)
            + skill_mesh.detect_trigger_overlaps(skills)
        )

        assert findings, "identical descriptions under different names must still collide"
        assert {f["skill_a"] for f in findings} | {f["skill_b"] for f in findings} == {
            "deploy-helper", "release-helper",
        }

    def test_and_they_are_not_reported_as_duplicates(self, tmp_path):
        skills = _two_distinct_skills(tmp_path)

        assert skill_mesh.detect_duplicate_names(skills) == []


class TestTheCacheCannotOutliveTheLogic:
    """`doctor` runs the mesh with `incremental=True`, and the cache keys on
    skill CONTENT. Upgrading schliff changes no file on the user's disk, so
    without a version stamp the cached verdict from the old detectors is
    returned forever and the fix is invisible to everyone who ran `doctor`
    before installing it. Found by running `doctor` after the fix and reading
    95/100 next to a fresh mesh run reporting 100/100.
    """

    def test_a_cache_from_older_logic_is_discarded(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "mesh-cache.json"
        _write(tmp_path, "global", "deploy-helper")
        _write(tmp_path, "project", "deploy-helper")
        monkeypatch.setattr(skill_mesh, "_MESH_CACHE_PATH", cache_path)
        skills = skill_mesh.discover_skills([str(tmp_path)])
        stale = {
            "_version": skill_mesh._MESH_CACHE_VERSION - 1,
            "_issues": [{
                "type": "scope_collision", "severity": "critical",
                "skill_a": "deploy-helper", "skill_b": "deploy-helper",
                "shared_domain": "skill", "overlap_score": 1.0,
            }],
        }
        for skill in skills:
            stale[skill["path"]] = {"content_hash": skill["content_hash"]}
        cache_path.write_text(json.dumps(stale), encoding="utf-8")

        result = skill_mesh.run_mesh_analysis([str(tmp_path)], incremental=True)

        assert result["health"]["score"] == 100, "stale verdict survived the upgrade"
        assert [i["type"] for i in result["issues"]] == ["duplicate_name"]

    def test_a_current_cache_is_still_used(self, tmp_path, monkeypatch):
        """The version stamp must not turn the cache off altogether."""
        cache_path = tmp_path / "mesh-cache.json"
        _write(tmp_path, "only", "deploy-helper")
        monkeypatch.setattr(skill_mesh, "_MESH_CACHE_PATH", cache_path)

        skill_mesh.run_mesh_analysis([str(tmp_path)], incremental=True)
        second = skill_mesh.run_mesh_analysis([str(tmp_path)], incremental=True)

        assert second.get("cache_hit") is True


class TestTheHumanSeesIt:
    """A finding that reaches the data and not the renderer is worse than none:
    the header counts it, the list omits it, and the reader concludes the tool
    is broken. The first cut of this fix did exactly that — "Issues found: 1"
    above an empty list."""

    def test_the_duplicate_is_printed_not_just_counted(self, tmp_path):
        _write(tmp_path, "global", "deploy-helper")
        _write(tmp_path, "project", "deploy-helper")

        result = skill_mesh.run_mesh_analysis([str(tmp_path)])
        rendered = skill_mesh.format_mesh_report(result)

        assert result["health"]["score"] == 100
        assert "deploy-helper" in rendered
        assert "duplicate" in rendered.lower()
        # Both paths, so the reader can tell which copy to remove.
        assert rendered.count("SKILL.md") >= 2

    def test_a_clean_mesh_still_says_so(self, tmp_path):
        _write(tmp_path, "only", "deploy-helper")

        result = skill_mesh.run_mesh_analysis([str(tmp_path)])

        assert result["issues"] == []
        assert "healthy" in skill_mesh.format_mesh_report(result).lower()
