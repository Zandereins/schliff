"""doctor counts one install per payload, and names the copies it did not count.

A plugin that is both cached and vendored sits on disk twice. Measured on a real
``~/.claude``: 159 SKILL.md, 138 distinct payloads, 57,331 tokens of double
counting in the headline figure.

Each test here is named after the mutation it has to survive. The second one is
the reason this file exists: it is red against the cheap key (SKILL.md alone),
which is what a future reader will reach for.
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

    The token estimate charges for SKILL.md *plus* ``references/*.md``. A key
    that hashes only SKILL.md has a smaller domain than the quantity it indexes,
    so it collapses installs that cost different amounts — measured at 9,013
    against 9,591 tokens on two real skills.

    Replace ``skill_payload_digest`` with a bare SKILL.md hash and this test
    fails. Nothing else in the suite does.
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


def test_the_survivor_does_not_depend_on_iteration_order(tmp_path):
    """The published number must not move when discovery order does.

    The bare-SKILL.md key failed exactly here: keep-first gave 429,006 tokens and
    keep-last 429,584 over a real installation, and keep-first discarded the live
    schliff skill in favour of a June backup — the cure authorising the defect.
    """
    a = _skill(tmp_path, "first", BODY, refs={"r.md": "same\n"})
    b = _skill(tmp_path, "second", BODY, refs={"r.md": "same\n"})

    fwd, fwd_dupes = doctor._collapse_duplicate_copies([a, b])
    rev, rev_dupes = doctor._collapse_duplicate_copies([b, a])

    assert len(fwd) == len(rev) == 1
    assert len(fwd_dupes) == len(rev_dupes) == 1
    # The survivor differs by direction — that is fine and unavoidable — but the
    # GROUP is the same, so the count and the token total cannot move.
    assert {fwd_dupes[0]["counted"], *fwd_dupes[0]["also_installed_at"]} == \
           {rev_dupes[0]["counted"], *rev_dupes[0]["also_installed_at"]}


def test_mesh_still_sees_every_physical_copy(tmp_path):
    """Dedup is for the report, not for discovery.

    ``run_mesh_analysis`` is deliberately handed the undeduplicated list: two
    installs of one skill under the same name is exactly the collision mesh
    exists to flag. Collapsing first would hide it.
    """
    import inspect
    source = inspect.getsource(doctor.run_doctor)
    assert "skills=skills" in source, (
        "mesh must receive the full discovery list, not the deduplicated one"
    )
    assert "for skill in unique_skills:" in source, (
        "scoring must run over the deduplicated list"
    )
