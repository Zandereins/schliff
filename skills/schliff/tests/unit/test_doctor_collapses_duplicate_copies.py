"""doctor counts one install per payload, and names the copies it did not count.

A plugin that is both cached and vendored sits on disk twice, so it was billed
twice. The measurements and the rejected alternatives live in docs/specs/2026-08-13-doctor-counts-vendored-skills.md,
"Amendment 2026-08-26".

Each test here is named after the mutation it has to survive. Two of them exist
because the first version of this file did not discriminate: they were green
against the very mutations their docstrings quoted.
"""
import doctor
import pytest


def _skill(tmp_path, name, body, refs=None):
    d = tmp_path / name
    (d / "references").mkdir(parents=True) if refs else d.mkdir(parents=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")
    for ref_name, ref_body in (refs or {}).items():
        (d / "references" / ref_name).write_text(ref_body, encoding="utf-8")
    return {"name": name, "path": str(d / "SKILL.md")}


BODY = "---\nname: thing\ndescription: does a thing\n---\n\n## Usage\n\nRun it.\n"


def test_identical_copies_are_counted_once(tmp_path):
    """The defect itself: same bytes in two places, billed twice."""
    a = _skill(tmp_path, "cached", BODY)
    b = _skill(tmp_path, "vendored", BODY)

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 1
    assert len(duplicates) == 1
    # Both paths are named — nothing is deleted, the reader decides (ADR 0019).
    assert duplicates[0]["counted"] == a["path"]
    assert duplicates[0]["also_installed_at"] == [b["path"]]


def test_same_skill_md_but_different_references_are_two_installs(tmp_path):
    """THE MUTATION GATE. Red against ``skill["content_hash"]``.

    The token estimate charges for SKILL.md *plus* ``references/*.md``, so a key
    hashing only SKILL.md collapses installs that cost different amounts. The
    measured pair is in the spec amendment named at the top of this file.

    Replace ``skill_payload_digest`` with a bare SKILL.md hash and this goes red.
    """
    a = _skill(tmp_path, "slim", BODY, refs={"a.md": "short\n"})
    b = _skill(tmp_path, "fat", BODY, refs={"a.md": "much longer " * 200})

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 2, "different payloads must not collapse"
    assert duplicates == []


def test_an_unreadable_skill_never_collapses_onto_another(tmp_path):
    """An empty digest is not an identity.

    Two skills that both fail to hash must stay two, or a permissions error
    silently deletes a skill from the count.
    """
    a = {"name": "gone-a", "path": str(tmp_path / "nope-a" / "SKILL.md")}
    b = {"name": "gone-b", "path": str(tmp_path / "nope-b" / "SKILL.md")}

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 2
    assert duplicates == []


def test_the_group_does_not_depend_on_iteration_order(tmp_path):
    """The published number must not move when discovery order does.

    Fixture note: the two copies get DIFFERENT references on purpose. With
    identical ones the bare-SKILL.md key groups them too, and this test passes
    against the very mutation it exists to catch — which is what the first
    version of it did.
    """
    a = _skill(tmp_path, "first", BODY, refs={"r.md": "same\n"})
    b = _skill(tmp_path, "second", BODY, refs={"r.md": "same\n"})
    c = _skill(tmp_path, "third", BODY, refs={"r.md": "different\n"})

    fwd, fwd_dupes = doctor._collapse_duplicate_copies([a, b, c])
    rev, rev_dupes = doctor._collapse_duplicate_copies([c, b, a])

    # Two distinct payloads either way, and c never joins a group.
    assert len(fwd) == len(rev) == 2
    assert len(fwd_dupes) == len(rev_dupes) == 1
    assert {fwd_dupes[0]["counted"], *fwd_dupes[0]["also_installed_at"]} == \
           {rev_dupes[0]["counted"], *rev_dupes[0]["also_installed_at"]} == \
           {a["path"], b["path"]}


def test_eval_suite_presence_splits_two_otherwise_identical_installs(tmp_path):
    """MUTATION GATE for the score, not the cost.

    ``eval-suite.json`` moves a row from 4-of-7 dimensions to 7-of-7, so ignoring
    it lets two installs collapse and path sort order decide which grade a reader
    is shown. The measured pair is in the spec amendment named at the top.

    Drop the eval-suite branch from ``skill_payload_digest`` and this goes red.
    """
    a = _skill(tmp_path, "no-suite", BODY)
    b = _skill(tmp_path, "with-suite", BODY)
    (tmp_path / "with-suite" / "eval-suite.json").write_text(
        '{"assertions": [{"name": "x", "type": "contains", "value": "Usage"}]}',
        encoding="utf-8",
    )

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 2, "a skill with an eval suite is not the same install"
    assert duplicates == []


def test_mesh_receives_every_physical_copy(tmp_path, monkeypatch):
    """Dedup is for the report, not for discovery.

    Two installs of one skill under the same name is exactly the collision mesh
    exists to flag, so it must see both. The first version of this test asserted
    on ``inspect.getsource`` strings and was a verified false negative: handing
    mesh the deduplicated list left it green.
    """
    import skill_mesh

    a = _skill(tmp_path, "cached", BODY)
    b = _skill(tmp_path, "vendored", BODY)
    seen = {}

    monkeypatch.setattr(skill_mesh, "discover_skills", lambda dirs: [a, b])
    monkeypatch.setattr(doctor.skill_mesh, "discover_skills", lambda dirs: [a, b])

    def _capture(dirs, incremental=True, skills=None):
        seen["n"] = len(skills or [])
        return {"issues": [], "health": {"score": 100}}

    monkeypatch.setattr(doctor.skill_mesh, "run_mesh_analysis", _capture)

    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])

    assert seen["n"] == 2, "mesh must see both physical copies, not the collapsed one"
    assert report["skills_found"] == 1, "the report counts one install"
    assert len(report["duplicate_copies"]) == 1
