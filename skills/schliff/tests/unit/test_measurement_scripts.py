"""Guards for the two measurement scripts, which had none.

Every refusal in `freeze_corpus.py` and `run_measurement.py` was itself a defect
found in review — a freeze that covered the wrong file set, a drift verdict for a
typo'd path, a record written for a run the script declared failed. They are
load-bearing for a one-shot, date-pinned measurement, and nothing exercised them.

The drift classifier deserves particular attention: it is a string-prefix
heuristic over another process's stdout, so renaming a label in
`freeze_corpus.verify` would silently turn every drift into "the freeze check
itself failed" — the opposite verdict, with no test to notice.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_MEASUREMENT = _REPO / "scripts" / "measurement"
sys.path.insert(0, str(_MEASUREMENT))
from freeze_corpus import DRIFT_LABELS  # noqa: E402  (the labels the log tests parse)

SKILL = """---
name: demo
description: A demo skill used by the measurement script guards, long enough to be scored.
---

# demo

Use when verifying the measurement scripts. Do not use for anything else.
"""


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    """A miniature `~/.claude` with one skill and one reference."""
    root = tmp_path / ".claude"
    skill = root / "skills" / "demo"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (skill / "references" / "notes.md").write_text("# notes\n\nshort\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(_MEASUREMENT))
    monkeypatch.delitem(sys.modules, "freeze_corpus", raising=False)
    import freeze_corpus as fc
    monkeypatch.setattr(fc, "CORPUS_ROOT", root)
    return root, fc


def test_a_changed_reference_is_drift(corpus, tmp_path, capsys):
    """The defect that started this: freezing SKILL.md alone missed the references."""
    root, fc = corpus
    manifest = tmp_path / "m.jsonl"
    fc.write(manifest)
    assert fc.verify(manifest) == 0
    assert "added," not in capsys.readouterr().out, "no drift, no per-label totals"

    (root / "skills" / "demo" / "references" / "notes.md").write_text("# notes\n\nlonger\n")
    assert fc.verify(manifest) == 1, "a reference the token cost reads must count as drift"
    # The per-label totals are exact and ASCII, so a drift report can be quoted
    # and survives a C-locale stdout.
    out = capsys.readouterr().out
    assert "  0 added, 0 removed, 1 changed, 0 no longer resolved, 0 newly resolved\n" in out, out
    assert "changed: " in out, "the per-path lines carry the same labels as the totals"
    assert out.isascii(), out
    # Unequal counters, so a swapped pair of labels cannot hide behind zeros.
    (root / "skills" / "demo" / "references" / "more.md").write_text("# more\n")
    assert fc.verify(manifest) == 1
    assert "  1 added, 0 removed, 1 changed, 0 no longer resolved, 0 newly resolved\n" in capsys.readouterr().out


def test_write_refuses_an_empty_or_shrinking_corpus(corpus, tmp_path, capsys):
    """`discover_skills` skips a missing directory, so a wrong HOME truncated the artifact."""
    root, fc = corpus
    # Date-stamped names, as in the repository: the baseline is the siblings.
    manifest = tmp_path / "corpus-2026-01-01.jsonl"
    fc.write(manifest)

    fc.CORPUS_ROOT = tmp_path / "nowhere"
    with pytest.raises(SystemExit) as empty:
        fc.write(tmp_path / "corpus-2026-01-02.jsonl")
    assert empty.value.code == fc.EXIT_BROKEN
    assert "empty manifest" in capsys.readouterr().err

    fc.CORPUS_ROOT = root
    (root / "skills" / "demo" / "references" / "notes.md").unlink()
    with pytest.raises(SystemExit) as shrink:
        fc.write(tmp_path / "corpus-2026-01-03.jsonl")
    assert shrink.value.code == fc.EXIT_BROKEN
    assert "refusing to write" in capsys.readouterr().err


def test_an_interrupted_write_leaves_no_manifest(corpus, tmp_path, monkeypatch):
    """A truncated dated manifest would be protected by the overwrite refusal forever."""
    root, fc = corpus
    target = tmp_path / "corpus-2026-01-01.jsonl"
    real_dumps = fc.json.dumps
    calls = []

    def dumps_then_die(obj, **kw):
        calls.append(obj)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return real_dumps(obj, **kw)

    monkeypatch.setattr(fc.json, "dumps", dumps_then_die)
    with pytest.raises(KeyboardInterrupt):
        fc.write(target)
    assert not target.exists(), "a partial manifest must not survive the interruption"
    assert list(tmp_path.glob("corpus-*")) == [], "no leftover temporary file either"
    monkeypatch.setattr(fc.json, "dumps", real_dumps)
    fc.write(target)
    assert fc.verify(target) == 0


def test_the_shrink_baseline_is_the_fullest_sibling_not_the_newest(corpus, tmp_path, capsys):
    """A newer but smaller sibling must not lower the bar a wrong-HOME run is measured against."""
    root, fc = corpus
    full = tmp_path / "corpus-2026-01-01.jsonl"
    fc.write(full)
    rows = full.read_text().splitlines()
    assert len(rows) == 2
    (tmp_path / "corpus-2026-01-02.jsonl").write_text(rows[0] + "\n")
    (root / "skills" / "demo" / "references" / "notes.md").unlink()
    with pytest.raises(SystemExit) as exc:
        fc.write(tmp_path / "corpus-2026-01-03.jsonl")
    assert exc.value.code == fc.EXIT_BROKEN
    assert "corpus-2026-01-01.jsonl holds 2" in capsys.readouterr().err


def test_write_refuses_to_overwrite_a_manifest(corpus, tmp_path, capsys):
    """A manifest is named by measurement records; a re-freeze is a new dated file."""
    root, fc = corpus
    manifest = tmp_path / "m.jsonl"
    fc.write(manifest)
    before = manifest.read_bytes()
    (root / "skills" / "demo" / "references" / "more.md").write_text("# more\n")
    with pytest.raises(SystemExit) as exc:
        fc.write(manifest)
    assert exc.value.code == fc.EXIT_BROKEN
    assert "already exists" in capsys.readouterr().err
    assert manifest.read_bytes() == before, "the refusal must leave the file untouched"


def test_write_refuses_a_file_it_cannot_freeze(corpus, tmp_path, monkeypatch, capsys):
    """An unfreezable file is read by a published number; dropping it was silent."""
    root, fc = corpus
    monkeypatch.setattr(fc.shared, "MAX_SKILL_SIZE", 200)
    (root / "skills" / "demo" / "references" / "notes.md").write_text("x" * 500)

    with pytest.raises(SystemExit) as exc:
        fc.write(tmp_path / "m.jsonl")
    assert exc.value.code == fc.EXIT_BROKEN, "a check that could not run is not drift"
    assert "cannot be frozen" in capsys.readouterr().err


def test_a_resolution_flip_is_drift_even_when_no_file_changed(corpus, tmp_path, capsys):
    """Which plugin version is active is decided by mtime, which is not content.

    Both versions sit in the freeze, so every path stays present and unchanged
    when the active one flips — measured on the real corpus, the resolved
    description went 790 to 498 characters with `verify` reporting no drift.
    """
    root, fc = corpus
    manifest = tmp_path / "m.jsonl"
    fc.write(manifest)

    entries = [json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    assert any(e.get("resolved") for e in entries), "nothing was marked as resolved"
    for entry in entries:
        entry.pop("resolved", None)
    manifest.write_text("\n".join(json.dumps(e, sort_keys=True) for e in entries) + "\n")

    assert fc.verify(manifest) == 1, "a change in which paths resolve must count as drift"
    # The flip is reported under its own label, so the resolution pair cannot
    # be swapped unnoticed: every path stays, so added/removed/changed are 0.
    out = capsys.readouterr().out
    assert "newly resolved: " in out and "no longer resolved: " not in out, out
    assert "  0 added, 0 removed, 0 changed, 0 no longer resolved, 1 newly resolved\n" in out, out


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_MEASUREMENT / "run_measurement.py"), *args],
        cwd=_REPO, capture_output=True, text=True,
    )


def test_a_broken_check_is_not_reported_as_drift(tmp_path):
    """A typo'd path announced that the corpus no longer matches its freeze."""
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json at all\n", encoding="utf-8")
    broken = _run(str(bad))
    assert broken.returncode == 1
    assert "the freeze check itself failed" in broken.stderr
    assert "no longer matches its freeze" not in broken.stderr, (
        "a failed check must not be announced as a drift verdict"
    )

    missing = _run(str(tmp_path / "nope.jsonl"))
    assert "the freeze check itself failed" in missing.stderr


def test_evidence_precedes_the_verdict_in_a_redirected_log(tmp_path):
    """stdout is block-buffered when redirected; the verdict overtook its evidence."""
    real = _REPO / "docs" / "case-studies" / "context-cost" / "corpus-2026-09-01.jsonl"
    short = tmp_path / "short.jsonl"
    short.write_text("\n".join(real.read_text().splitlines()[:-1]) + "\n", encoding="utf-8")

    # Both streams into ONE file, which is what a tee'd or redirected run does.
    # Capturing them as two pipes and concatenating cannot see the interleaving:
    # stdout would always sort first regardless of buffering, so that version of
    # this test passed with the flush removed.
    log = tmp_path / "log"
    with log.open("w") as fh:
        code = subprocess.run(
            [sys.executable, str(_MEASUREMENT / "run_measurement.py"), str(short)],
            cwd=_REPO, stdout=fh, stderr=subprocess.STDOUT,
        ).returncode
    assert code == 1
    text = log.read_text()
    assert text.index("drifted") < text.index("MEASUREMENT NOT TAKEN"), (
        f"the verdict preceded the evidence it rests on:\n{text}"
    )
    # Assert on the BARE labels: if any line still starts with `added:` or
    # `drifted` without its prefix, the labelling stopped after the first line.
    # The previous version read `line.strip() and "drifted" in line or
    # line.startswith("added:")`, which parses as `(A and B) or C` — and since
    # every line is already prefixed, C never selected anything, so dropping the
    # per-line labelling would have kept this green.
    unlabelled = [line for line in text.splitlines()
                  if (line.startswith(tuple(f"{label}:" for label in DRIFT_LABELS))
                      or re.match(r"\s*\d+ added, ", line)
                      or (line.rstrip().endswith("drifted")
                          and not line.startswith("[freeze ")))]
    assert not unlabelled, f"freeze output missing its label: {unlabelled}"
    # The per-label totals travel with the verdict, under the same prefix, and
    # add up to the drift count on the summary line.
    summary = re.search(r"\[freeze before\] (\d+) frozen, \d+ present, (\d+) drifted", text)
    totals = re.search(r"\[freeze before\]\s+" + ", ".join(rf"(\d+) {re.escape(label)}"
                                                           for label in DRIFT_LABELS) + r"$", text, re.M)
    assert summary and totals, text
    assert sum(map(int, totals.groups())) == int(summary.group(2)), text
