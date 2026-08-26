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


def test_a_symlinked_eval_suite_also_splits_two_installs(tmp_path):
    """The digest must follow the loader, not a copied guard.

    ``load_eval_suite`` follows a symlink; the first version of the digest
    copied ``estimate_token_cost``'s symlink skip and therefore did not. A
    stow/chezmoi layout was scored 7-of-7 and hashed as if it had no suite, so
    the two copies collapsed and sort order picked the grade again.

    Reinstate a ``not suite.is_symlink()`` guard in ``skill_payload_digest`` and
    this goes red.
    """
    import os

    real = tmp_path / "shared-suite.json"
    real.write_text(
        '{"assertions": [{"name": "x", "type": "contains", "value": "Usage"}]}',
        encoding="utf-8",
    )
    a = _skill(tmp_path, "no-suite", BODY)
    b = _skill(tmp_path, "symlinked", BODY)
    os.symlink(real, tmp_path / "symlinked" / "eval-suite.json")

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 2, "a symlinked suite still makes this a different install"
    assert duplicates == []


@pytest.mark.parametrize("kind", ["directory", "binary", "unreadable", "deeply-nested"])
def test_a_broken_eval_suite_degrades_instead_of_crashing_the_run(tmp_path, kind):
    """doctor scans other people's directories; it reports, never gates.

    Routing the digest through ``load_eval_suite`` moved that call out of
    ``_score_single_skill``'s ``except Exception`` and in front of the scoring
    loop. The loader caught only ``JSONDecodeError``, so one malformed suite
    anywhere under ``~/.claude`` turned the whole run into a traceback instead of
    one row marked failed (ADR 0014, ADR 0019).
    """
    import os

    _skill(tmp_path, "a", BODY)
    _skill(tmp_path, "b", BODY)
    suite = tmp_path / "b" / "eval-suite.json"
    if kind == "directory":
        suite.mkdir()
    elif kind == "binary":
        suite.write_bytes(b"\xff\xfe\x00\x01")
    elif kind == "deeply-nested":
        # json.loads recurses per level below CPython 3.14, and MAX_SKILL_SIZE
        # leaves room for ~200k of them. RecursionError is neither OSError nor
        # ValueError, so the first hardening did not catch it — and it does not
        # raise on the newest interpreter, so CI's newest leg stayed green while
        # the oldest tracebacked.
        depth = 100_000
        suite.write_text("[" * depth + "]" * depth, encoding="utf-8")
    else:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            pytest.skip("chmod 0 does not deny root; the case would pass vacuously")
        suite.write_text("{}", encoding="utf-8")
        os.chmod(suite, 0)

    try:
        report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    finally:
        if kind == "unreadable":
            # 0o600, not 0o644: this only has to let pytest's tmp_path cleanup
            # remove the file. Granting world read here is what CodeQL's
            # py/overly-permissive-file flags, and it is right to.
            os.chmod(suite, 0o600)

    assert report["skills_found"] >= 1, "a broken suite must not empty the report"


def test_a_broken_suite_is_not_the_same_install_as_no_suite(tmp_path):
    """"Absent" and "present but broken" produce different rows.

    Degrading a broken suite to ``None`` stopped the crash, but it also made the
    two look identical to the digest — so they collapsed, and the row that told
    the reader to fix the file vanished into ``also_installed_at``. The row now
    carries ``eval_suite_error`` and a different ``action``, so the failure state
    belongs to the identity.

    Drop the ``eval_suite_error`` branch from ``skill_payload_digest`` and this
    goes red.
    """
    a = _skill(tmp_path, "no-suite", BODY)
    b = _skill(tmp_path, "broken-suite", BODY)
    (tmp_path / "broken-suite" / "eval-suite.json").mkdir()

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 2, "a broken suite is not the same install as no suite"
    assert duplicates == []


def test_a_broken_suite_row_does_not_send_you_to_overwrite_it(tmp_path):
    """The emitted action must be runnable.

    With the suite degraded to ``None`` the row read ``has_eval_suite: False``
    and the action became ``/schliff:init <path>`` — which writes
    ``eval-suite.json`` over the very file that failed to load.
    """
    _skill(tmp_path, "broken", BODY)
    (tmp_path / "broken" / "eval-suite.json").mkdir()

    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    row = next(r for r in report["results"] if "broken" in r["path"])

    assert row["eval_suite_error"], "the failure must reach the report, not just stderr"
    assert "/schliff:init" not in (row["action"] or "")


def test_a_grouped_row_carries_no_runnable_action(tmp_path):
    """The counted path is sort order, not merit — and usually the plugin cache.

    ``discover_skills`` sorts by path and the first wins, so
    ``plugins/cache/…`` beats ``plugins/marketplaces/…`` and ``~/.claude/skills/…``
    every time. Emitting ``/schliff:auto <that path>`` writes ``.schliff/``
    history into a directory the next plugin update deletes. Preferring another
    member would need a path wordlist — the enumeration this key avoids — so the
    row says what to do instead.
    """
    _skill(tmp_path, "cache-copy", BODY)
    _skill(tmp_path, "user-copy", BODY)

    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    grouped = [r for r in report["results"] if "also_installed_at" in r]

    assert len(grouped) == 1
    assert "/schliff:" not in (grouped[0]["action"] or ""), (
        "a grouped row must not hand out a command against one arbitrary copy"
    )


def test_cost_and_digest_read_the_same_files(tmp_path, monkeypatch):
    """The invariant behind the whole key, gated on BOTH sides.

    Four defects in this area were a domain re-derived instead of asked for, so
    this pins the property they exist for: whatever ``estimate_token_cost``
    charges for is what ``skill_payload_digest`` hashes.

    The first version asserted only what ``_payload_files`` returns and that the
    cost path uses it. Verified false negative: giving the digest its own
    ``glob("*")`` walk left all tests green, so it gated exactly one of the two
    sides it names. Both are now observed through the same monkeypatch.
    """
    import shared

    a = _skill(tmp_path, "s", BODY, refs={"keep.md": "counted\n"})
    refs = tmp_path / "s" / "references"
    (refs / "extra.md").write_text("also counted\n", encoding="utf-8")

    real = shared._payload_files
    calls = []

    def _spy(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(shared, "_payload_files", _spy)

    cost_before = shared.estimate_token_cost(a["path"])
    digest_before = shared.skill_payload_digest(a["path"])
    assert len(calls) == 2, "both consumers must go through the shared enumeration"

    # Narrowing the shared list must move BOTH. A consumer walking the directory
    # itself would keep its old value and this goes red.
    monkeypatch.setattr(shared, "_payload_files", lambda p: real(p)[:1])
    shared.invalidate_cache(a["path"])

    assert shared.estimate_token_cost(a["path"]) < cost_before, "cost side ignored the enumeration"
    assert shared.skill_payload_digest(a["path"]) != digest_before, "digest side ignored the enumeration"


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
