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
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_MEASUREMENT = _REPO / "scripts" / "measurement"

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


def test_a_changed_reference_is_drift(corpus, tmp_path):
    """The defect that started this: freezing SKILL.md alone missed the references."""
    root, fc = corpus
    manifest = tmp_path / "m.jsonl"
    fc.write(manifest)
    assert fc.verify(manifest) == 0

    (root / "skills" / "demo" / "references" / "notes.md").write_text("# notes\n\nlonger\n")
    assert fc.verify(manifest) == 1, "a reference the token cost reads must count as drift"


def test_write_refuses_an_empty_or_shrinking_corpus(corpus, tmp_path):
    """`discover_skills` skips a missing directory, so a wrong HOME truncated the artifact."""
    root, fc = corpus
    manifest = tmp_path / "m.jsonl"
    fc.write(manifest)

    fc.CORPUS_ROOT = tmp_path / "nowhere"
    with pytest.raises(SystemExit, match="empty manifest"):
        fc.write(tmp_path / "other.jsonl")

    fc.CORPUS_ROOT = root
    (root / "skills" / "demo" / "references" / "notes.md").unlink()
    with pytest.raises(SystemExit, match="refusing to write"):
        fc.write(manifest)


def test_write_refuses_a_file_it_cannot_freeze(corpus, tmp_path, monkeypatch):
    """An unfreezable file is read by a published number; dropping it was silent."""
    root, fc = corpus
    monkeypatch.setattr(fc.shared, "MAX_SKILL_SIZE", 200)
    (root / "skills" / "demo" / "references" / "notes.md").write_text("x" * 500)

    with pytest.raises(SystemExit, match="cannot be frozen"):
        fc.write(tmp_path / "m.jsonl")


def test_a_resolution_flip_is_drift_even_when_no_file_changed(corpus, tmp_path):
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
    assert all(line.startswith("[freeze ") for line in text.splitlines()
               if line.strip() and "drifted" in line or line.startswith("added:")), (
        "every freeze line needs its label, not only the first"
    )
