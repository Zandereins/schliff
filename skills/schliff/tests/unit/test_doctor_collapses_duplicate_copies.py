"""doctor counts one install per payload, and names the copies it did not count.

A plugin that is both cached and vendored sits on disk twice, so it was billed
twice. The measurements and the rejected alternatives live in docs/specs/2026-08-13-doctor-counts-vendored-skills.md,
"Amendment 2026-08-26".

Each test here is named after the mutation it has to survive. Two of them exist
because the first version of this file did not discriminate: they were green
against the very mutations their docstrings quoted.
"""
import pathlib

import doctor
import pytest
import shared


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


def test_two_copies_with_the_same_broken_suite_still_collapse(tmp_path):
    """The failure reason must be path-free.

    Folding the formatted exception into the digest put an absolute path in the
    identity, so two genuine copies of one broken skill got different digests and
    were billed twice — the exact double-count this key removes. Only a reason
    reaches the identity; the detail goes to stderr.
    """
    a = _skill(tmp_path, "cached", BODY)
    b = _skill(tmp_path, "vendored", BODY)
    for name in ("cached", "vendored"):
        (tmp_path / name / "eval-suite.json").mkdir()

    unique, duplicates = doctor._collapse_duplicate_copies([a, b])

    assert len(unique) == 1, "same skill, same breakage — one install"
    assert len(duplicates) == 1


def test_a_symlinked_reference_is_rejected_not_followed(tmp_path):
    """A shipped security fix, kept deliberately.

    doctor walks other people's directories, so a plugin controls what sits in
    its ``references/``. Following a link there turns a word count into a
    filesystem oracle, and reading before the size check turns a link to a huge
    file into an OOM — which is why ``estimate_token_cost`` rejected them and why
    ``skill_mesh`` confines resolved paths to the scan root.

    I reversed this once, to make a stow layout collapse with its plain twin, on
    the strength of a fixture I wrote myself. The field says 0 symlinks across
    the 41 real skills that have a ``references/``. Restore ``resolve()``-and-
    follow here and this goes red.
    """
    import os

    import shared

    outside = tmp_path / "outside.md"
    outside.write_text("word " * 900, encoding="utf-8")
    skill = _skill(tmp_path, "s", BODY, refs={"placeholder.md": ""})
    (tmp_path / "s" / "references" / "placeholder.md").unlink()
    os.symlink(outside, tmp_path / "s" / "references" / "linked.md")

    assert shared._payload_files(skill["path"]) == [], "a symlinked ref must not be read"
    # ...and the file outside the skill directory contributes nothing.
    assert shared.estimate_token_cost(skill["path"]) < 100


def test_a_symlinked_references_directory_is_rejected(tmp_path):
    """Same fix, the directory half of it."""
    import os

    import shared

    real_refs = tmp_path / "elsewhere"
    real_refs.mkdir()
    (real_refs / "guide.md").write_text("word " * 900, encoding="utf-8")
    skill = _skill(tmp_path, "s", BODY)
    os.symlink(real_refs, tmp_path / "s" / "references")

    assert shared._payload_files(skill["path"]) == []


def test_a_repaired_suite_clears_its_recorded_failure(tmp_path):
    """The registry is module state; a stale entry outlives the file.

    Only the "absent" branch cleared it, so a suite that failed once and was
    then repaired produced a self-contradictory row: 7-of-7 dimensions and an
    action saying to fix the file.
    """
    import shared

    skill = _skill(tmp_path, "s", BODY)
    suite = tmp_path / "s" / "eval-suite.json"

    suite.write_text("{ broken", encoding="utf-8")
    assert shared.load_eval_suite(skill["path"]) is None
    assert shared.eval_suite_error.get(str(suite))

    suite.write_text('{"assertions": []}', encoding="utf-8")
    assert shared.load_eval_suite(skill["path"]) is not None
    assert shared.eval_suite_error.get(str(suite)) is None, "a repaired suite must clear its entry"


def test_an_unreadable_suite_is_not_counted_as_missing(tmp_path):
    """The aggregate must not contradict the row.

    Counting it as missing put it in "Run /schliff:init on N skills missing eval
    suites" — the command that writes over the file the row three lines above
    says to repair.
    """
    _skill(tmp_path, "broken", BODY)
    (tmp_path / "broken" / "eval-suite.json").mkdir()

    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    rendered = doctor.format_doctor_report(report)

    assert report["no_eval_suite"] == 0
    assert report["broken_eval_suite"] == 1
    assert "Run /schliff:init on" not in rendered


def test_an_oversized_eval_suite_is_never_read(tmp_path, monkeypatch):
    """Size before read — the OOM-safe loading the changelog promised.

    ``read_text`` on a multi-gigabyte target raises ``MemoryError``, which is
    neither ``OSError`` nor ``ValueError`` nor ``RecursionError``. The digest
    calls this before the scoring loop and outside any handler, so one such file
    ended the whole run. ``cli._load_eval_suite_from_args`` already checked
    ``stat().st_size`` first; the shared loader never did.

    Remove the ``stat().st_size`` guard and this goes red — the file gets read.
    """
    import shared

    skill = _skill(tmp_path, "s", BODY)
    suite = tmp_path / "s" / "eval-suite.json"
    suite.write_text("{" + " " * (shared.MAX_SKILL_SIZE + 1000) + "}", encoding="utf-8")

    reads = []
    real_read = pathlib.Path.read_text

    def _spy(self, *a, **kw):
        if self.name == "eval-suite.json":
            reads.append(str(self))
        return real_read(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", _spy)
    assert shared.load_eval_suite(skill["path"]) is None
    assert reads == [], "an oversized suite must not be read into memory at all"


def test_a_grouped_row_is_not_counted_as_missing_an_eval_suite(tmp_path):
    """The footer must not contradict the row, for duplicates either.

    A grouped row's action says to resolve the duplicate and its path is the
    plugin cache. Counting it as "missing an eval suite" put it in "Run
    /schliff:init on N skills" — writing into a directory the next plugin update
    deletes. Field-measured before the fix: all 20 groups landed in that count.
    """
    _skill(tmp_path, "cached", BODY)
    _skill(tmp_path, "vendored", BODY)

    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])

    assert report["grouped_duplicates"] == 1
    assert report["no_eval_suite"] == 0, "a grouped row must not join the init recommendation"


def test_a_fifo_named_skill_md_does_not_hang_discovery(tmp_path):
    """The first file doctor opens decides whether the scan can be hung at all.

    ``discover_skills`` read SKILL.md directly, so a FIFO there blocked before
    ``_read_bounded`` was ever reached — the guard was downstream of the hazard.
    Measured: blocked past eight seconds, nothing discovered, nothing reported.
    It uses the shared reader now.

    Restore a bare ``read_text`` in ``discover_skills`` and this hangs rather
    than failing, which is the defect reproduced.
    """
    import os

    import skill_mesh

    d = tmp_path / "skills" / "s"
    d.mkdir(parents=True)
    os.mkfifo(d / "SKILL.md")

    assert skill_mesh.discover_skills([str(tmp_path)]) == []


def test_a_fifo_where_a_file_is_expected_does_not_hang(tmp_path):
    """A plugin can put a FIFO where a skill file goes; doctor must not block.

    ``read_text`` on a FIFO waits for a writer that never comes — measured, still
    blocked after six seconds — and ``st_size`` is 0, so a size gate alone lets
    it through. The digest reads these before the scoring loop, so nothing was
    reported at all. ``_read_bounded`` checks ``is_file()`` first.
    """
    import os

    import shared

    skill = _skill(tmp_path, "s", BODY, refs={"placeholder.md": ""})
    (tmp_path / "s" / "references" / "placeholder.md").unlink()
    os.mkfifo(tmp_path / "s" / "references" / "pipe.md")
    os.mkfifo(tmp_path / "s" / "eval-suite.json")

    # Both readers must return rather than block.
    assert shared.estimate_token_cost(skill["path"]) >= 0
    assert shared.load_eval_suite(skill["path"]) is None
    assert shared.skill_payload_digest(skill["path"])


def test_an_oversized_reference_is_never_read(tmp_path, monkeypatch):
    """Size before read on the references side too.

    The loader got this guard first; the reference walk kept reading before
    checking, under a handler that catches neither ``MemoryError``. Since the
    digest runs before the scoring loop, one huge file ended the whole run
    instead of marking a row failed.
    """
    import shared

    skill = _skill(tmp_path, "s", BODY, refs={"big.md": "x" * (shared.MAX_SKILL_SIZE + 1000)})

    reads = []
    real_read = pathlib.Path.read_text

    def _spy(self, *a, **kw):
        if self.name == "big.md":
            reads.append(str(self))
        return real_read(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", _spy)
    shared.skill_payload_digest(skill["path"])
    shared.estimate_token_cost(skill["path"])
    assert reads == [], "an oversized reference must not be read into memory"


@pytest.mark.parametrize("content", ["null", "[1, 2, 3]", '"hello"'])
def test_a_suite_that_is_not_an_object_is_a_broken_suite(tmp_path, content):
    """`null` was indistinguishable from "no file" and routed to /schliff:init.

    A list or a string parsed fine here while `cli._load_eval_suite_from_args`
    rejects the same content outright — the auto-discovery half was the
    permissive one.
    """
    import shared

    skill = _skill(tmp_path, "s", BODY)
    (tmp_path / "s" / "eval-suite.json").write_text(content, encoding="utf-8")

    assert shared.load_eval_suite(skill["path"]) is None
    assert shared.eval_suite_error.get(str(tmp_path / "s" / "eval-suite.json")) == "not a JSON object"

    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    row = report["results"][0]
    assert "/schliff:init" not in (row["action"] or "")


def test_every_scanned_row_lands_in_exactly_one_bucket(tmp_path):
    """Grouped rows were in no tally at all — 20 of 138 on the real install."""
    _skill(tmp_path, "cached", BODY)
    _skill(tmp_path, "vendored", BODY)
    _skill(tmp_path, "solo", BODY)

    r = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    buckets = (
        r["healthy"] + r["needs_work"] + r["no_eval_suite"]
        + r["broken_eval_suite"] + r["grouped_duplicates"] + r["failed"]
    )

    assert buckets == r["skills_found"]
    assert r["skills_discovered"] - r["skills_found"] == sum(
        len(g["also_installed_at"]) for g in r["duplicate_copies"]
    )
    assert f"{r['grouped_duplicates']} duplicate install" in doctor.format_doctor_report(r)


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


# ---------------------------------------------------------------------------
# The reporting layer around the fix. Every test below is named after the
# mutation it has to survive; each one was red before the change it guards.
# ---------------------------------------------------------------------------


def _eval_suite_reasons() -> set:
    """Every reason `load_eval_suite` can put in `eval_suite_error`, from source.

    Enumerated out of the module's AST rather than hand-listed here. A hand list
    is a snapshot: it agrees with the code on the day it is written and silently
    stops covering the case someone adds next. The two shapes that produce a
    reason are an assignment into `eval_suite_error` and a return out of
    `_read_bounded_with_reason`, whose value flows straight into that dict.
    """
    import ast

    src = pathlib.Path(shared.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    reasons = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and \
                        isinstance(target.value, ast.Name) and \
                        target.value.id == "eval_suite_error":
                    reasons.add(node.value.value)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_read_bounded_with_reason":
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Tuple):
                    tail = inner.value.elts[-1]
                    if isinstance(tail, ast.Constant) and isinstance(tail.value, str) and tail.value:
                        reasons.add(tail.value)

    assert reasons, "found no reasons — the AST walk stopped matching the source"
    return reasons


def test_repair_action_fits_its_column():
    """The cap must fit the longest action doctor can actually compose.

    The mutation: lower REPAIR_ACTION_WIDTH back to 70 and this goes red naming
    the reason that no longer fits. That is what 70 did in the field — it cut
    "not a JSON object" to "not a JSON objec", truncating the exact payload the
    wide cap existed to preserve.
    """
    prefix = "Resolve the duplicate install first; eval-suite.json: "
    too_long = {r for r in _eval_suite_reasons()
                if len(prefix + r) > doctor.REPAIR_ACTION_WIDTH}
    assert not too_long, (
        f"REPAIR_ACTION_WIDTH={doctor.REPAIR_ACTION_WIDTH} truncates: "
        + ", ".join(f"{r!r} needs {len(prefix + r)}" for r in sorted(too_long))
    )


def test_a_broken_suite_reason_survives_into_the_rendered_row(tmp_path, monkeypatch):
    """End to end: the reason reaches the reader whole, not cut mid-word."""
    a = _skill(tmp_path, "cached", BODY)
    b = _skill(tmp_path, "vendored", BODY)
    for s in (a, b):
        (pathlib.Path(s["path"]).parent / "eval-suite.json").write_text("[]", encoding="utf-8")
    shared._eval_suite_cache.clear()

    monkeypatch.setattr(doctor.skill_mesh, "discover_skills", lambda dirs: [a, b])
    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    rendered = doctor.format_doctor_report(report)

    assert "not a JSON object" in rendered, rendered
    assert "not a JSON objec\n" not in rendered, "reason truncated mid-word"


def test_oversize_suite_is_not_reported_as_unreadable(tmp_path, monkeypatch):
    """A 'repair this file' verdict must not hide that the problem is size.

    The mutation: collapse the size branch of `_read_bounded_with_reason` back
    into the generic failure and this goes red — the reader is told to fix a
    file whose only defect is that it is too big.
    """
    monkeypatch.setattr(shared, "MAX_SKILL_SIZE", 200)
    a = _skill(tmp_path, "big", BODY)
    (pathlib.Path(a["path"]).parent / "eval-suite.json").write_text(
        '{"cases": [' + ",".join('"x"' for _ in range(200)) + "]}", encoding="utf-8")
    shared._eval_suite_cache.clear()

    assert shared.load_eval_suite(a["path"]) is None
    reason = shared.eval_suite_error[str(pathlib.Path(a["path"]).parent / "eval-suite.json")]
    assert reason == "too large", f"size diagnosis lost, got {reason!r}"


def test_the_size_check_runs_on_the_descriptor_that_gets_read(tmp_path):
    """The TOCTOU window, made deterministic — and measured with a clock.

    A plain FIFO is the WRONG fixture for this: `is_file()` already returns
    False for one, so the previous stat-then-read shape rejected it too and a
    FIFO test stays green against the very mutation it quotes. The defect is the
    window between the check and the open, where the path is swapped for a FIFO
    after it has already answered "regular file, 10 bytes". `_SwappedPath` is
    that window with the race taken out: it answers the path-level questions the
    old shape asked, while the object actually on disk is a FIFO.

    Under the old shape `read_text` then blocks forever. A hang raises nothing,
    so the instrument is elapsed time — an earlier test in this area passed for
    the wrong reason by asserting on a TimeoutError the code itself caught.
    """
    import os as _os
    import threading

    fifo = tmp_path / "eval-suite.json"
    _os.mkfifo(fifo)

    class _SwappedPath:
        """Answers as a small regular file; opens as the FIFO that is really there."""

        def __fspath__(self):
            return str(fifo)

        def is_file(self):
            return True

        def stat(self):
            return _os.stat_result((0o100644, 0, 0, 1, 0, 0, 10, 0, 0, 0))

        def read_text(self, **kwargs):
            with open(fifo, encoding="utf-8") as handle:
                return handle.read()

    out = {}

    def _read():
        out["result"] = shared._read_bounded_with_reason(_SwappedPath())

    worker = threading.Thread(target=_read, daemon=True)
    worker.start()
    worker.join(timeout=5)

    assert not worker.is_alive(), (
        "the read blocked: the guard trusted the path's answers instead of the "
        "descriptor it was about to read"
    )
    assert out["result"] == (None, "not a regular file"), out["result"]


def test_each_eval_suite_is_read_once_per_run(tmp_path, monkeypatch, capsys):
    """The digest pass and the scoring pass must not both open the same file.

    The mutation: drop the cache lookup from `load_eval_suite` and this goes red
    with two warnings for one broken file — which is what the field saw.
    """
    a = _skill(tmp_path, "cached", BODY)
    b = _skill(tmp_path, "vendored", BODY)
    for s in (a, b):
        (pathlib.Path(s["path"]).parent / "eval-suite.json").write_text("[]", encoding="utf-8")
    shared._eval_suite_cache.clear()
    shared.eval_suite_error.clear()

    monkeypatch.setattr(doctor.skill_mesh, "discover_skills", lambda dirs: [a, b])
    capsys.readouterr()
    doctor.run_doctor(skill_dirs=[str(tmp_path)])
    warnings = capsys.readouterr().err.count("eval-suite.json is not a JSON object")

    assert warnings == 2, f"expected one warning per distinct suite, got {warnings}"


def test_grouped_rows_get_no_skill_specific_recommendation(tmp_path, monkeypatch):
    """A recommendation to edit a file the command did not choose on merit.

    The row's own action says to resolve the duplicate install first; printing
    "extract into references/" beside it contradicts that row and points at a
    path picked by sort order. The mutation: drop the `also_installed_at` filter
    and this goes red.
    """
    long_body = BODY + "\n".join(f"- step {i}" for i in range(400)) + "\n"
    a = _skill(tmp_path, "cached", long_body)
    b = _skill(tmp_path, "vendored", long_body)
    shared._eval_suite_cache.clear()

    monkeypatch.setattr(doctor.skill_mesh, "discover_skills", lambda dirs: [a, b])
    report = doctor.run_doctor(skill_dirs=[str(tmp_path)])
    rendered = doctor.format_doctor_report(report)

    assert report["duplicate_copies"], "fixture stopped producing a duplicate group"
    body = rendered.split("Skill-specific recommendations:")
    assert len(body) == 1, f"grouped row still got a recommendation:\n{body[-1][:400]}"


def test_unserialisable_suites_do_not_share_one_identity(tmp_path, monkeypatch):
    """A constant in the digest is not an identity.

    Two skills with the same SKILL.md and DIFFERENT eval-suite.json files that
    parse but will not serialise both absorbed the literal "<unserialisable>",
    so their digests matched and the second vanished from the report as a copy
    of the first — the domain smaller than what the row reports, which is the
    failure this key exists to prevent and which the branch below it names.

    `json.dumps` is forced to raise rather than reproduced through recursion
    depth: below Python 3.14 `json.loads` recurses first and the suite never
    reaches this branch at all, so a nesting fixture would test nothing on the
    interpreter this suite usually runs on.

    The mutation: put the fixed marker back and this goes red.
    """
    a = _skill(tmp_path, "cached", BODY)
    b = _skill(tmp_path, "vendored", BODY)
    (pathlib.Path(a["path"]).parent / "eval-suite.json").write_text(
        '{"assertions": ["alpha"]}', encoding="utf-8")
    (pathlib.Path(b["path"]).parent / "eval-suite.json").write_text(
        '{"assertions": ["beta"]}', encoding="utf-8")
    shared._eval_suite_cache.clear()

    def _refuse(*args, **kwargs):
        raise ValueError("will not serialise")

    monkeypatch.setattr(shared.json, "dumps", _refuse)

    digest_a = shared.skill_payload_digest(a["path"])
    digest_b = shared.skill_payload_digest(b["path"])

    assert digest_a and digest_b, "an unserialisable suite must not void the identity"
    assert digest_a != digest_b, (
        "two different unserialisable suites collapsed onto one identity"
    )
