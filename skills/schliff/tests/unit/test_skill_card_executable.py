"""The agent-facing card must consist of commands that actually run.

Why this exists: for 132 days schliff shipped a 241-line SKILL.md containing zero
executable CLI invocations. Every instruction in it was either a `/schliff:*` slash
command — which exists only inside a Claude Code plugin install — or a repo-relative
`python3 scripts/…` path that exits 2 from any other directory. A real-agent probe
scored the shipped card 0/8 on executable tasks. The one external adopter wrote his
own card rather than use it.

So: every command documented in SKILL.md is executed here, and every slash command it
mentions must exist on disk. `uvx schliff X` is translated to the local module so the
test stays offline — what is being guarded is command-surface drift, not uvx itself.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
CARD = Path(__file__).resolve().parents[2] / "SKILL.md"
REPO = Path(__file__).resolve().parents[4]

CARD_TEXT = CARD.read_text(encoding="utf-8")

# `uvx schliff[@version] <args>` inside a backtick span.
_INVOCATION = re.compile(r"`uvx schliff(?:@[\w.]+)?\s+([^`]+)`")
_SLASH = re.compile(r"/schliff:([a-z-]+)")


def _placeholders(arg: str, tmp: Path, target: Path) -> list[str] | None:
    """Substitute the card's placeholders with real paths. None = not executable."""
    out = []
    for tok in arg.split():
        if tok in ("<file>", "<a>", "<b>"):
            out.append(str(target))
        elif tok in ("<dir>",):
            out.append(str(tmp))
        elif tok.startswith("<") and tok.endswith(">"):
            return None  # an unknown placeholder means the card is under-specified
        else:
            out.append(tok)
    return out


@pytest.fixture(scope="module")
def sandbox(tmp_path_factory) -> tuple[Path, Path]:
    tmp = tmp_path_factory.mktemp("card")
    target = tmp / "SKILL.md"
    target.write_text(CARD_TEXT, encoding="utf-8")
    return tmp, target


def _documented() -> list[str]:
    return _INVOCATION.findall(CARD_TEXT)


def test_card_documents_at_least_one_runnable_command():
    """The regression that started this: a card with no executable invocation."""
    assert len(_documented()) >= 5, (
        f"SKILL.md documents only {len(_documented())} runnable `uvx schliff` commands"
    )


@pytest.mark.parametrize("arg", _documented(), ids=lambda a: a.split()[0])
def test_every_documented_command_executes(arg: str, sandbox):
    tmp, target = sandbox
    argv = _placeholders(arg, tmp, target)
    assert argv is not None, f"card has an unresolvable placeholder: {arg!r}"

    # Run from the sandbox, not from the package directory. Two reasons, and the second
    # one was a real defect: the card's whole promise is that these commands work from
    # anywhere, so executing them elsewhere is the more faithful test — and `verify`
    # appends to `.schliff/history.jsonl` **relative to the working directory**, so with
    # cwd set to the package this suite wrote three throwaway entries per run into the
    # repo's own score history, each recording 32.7 [F] for a tmpdir copy of the card.
    # That is the data `progress.py`, `diff` and /schliff:report read.
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.cli", *argv],
        cwd=tmp, capture_output=True, text=True, timeout=120,
        # Prepend rather than replace — same idiom as the shell callers in scripts/.
        env={**os.environ, "PYTHONPATH": os.pathsep.join(
            p for p in (str(SCRIPTS.parent), os.environ.get("PYTHONPATH", "")) if p
        )},
    )
    # 0 = ran, 1 = ran and reported a verdict (`verify` is a gate; exiting 1 below the
    # threshold IS its documented contract). 2 = argparse rejected it, which is exactly
    # the command-surface drift this guard exists to catch.
    assert proc.returncode in (0, 1), (
        f"documented command did not run (exit {proc.returncode}): schliff {arg}\n"
        f"stderr: {proc.stderr.strip()[:400]}"
    )
    assert "Traceback" not in proc.stderr, (
        f"documented command crashed: schliff {arg}\n{proc.stderr.strip()[:400]}"
    )


@pytest.mark.parametrize("name", sorted(set(_SLASH.findall(CARD_TEXT))))
def test_every_documented_slash_command_exists(name: str):
    """Slash commands are real, but only inside a plugin install — they must at
    least exist on disk, or the card points an agent at nothing."""
    assert (REPO / "commands" / "schliff" / f"{name}.md").is_file(), (
        f"card documents /schliff:{name} but commands/schliff/{name}.md does not exist"
    )


def test_card_has_no_repo_relative_script_paths():
    """`python3 scripts/…` in the card exits 2 for every reader outside this repo —
    the exact defect that made the shipped card unusable."""
    offenders = re.findall(r"`[^`]*python3?\s+(?:\./)?scripts/[^`]*`", CARD_TEXT)
    assert not offenders, f"card documents repo-relative script paths: {offenders}"


def test_card_stays_small():
    """The shipped card was 11,700 chars / ~2,925 tokens charged on every load."""
    assert len(CARD_TEXT) < 6000, (
        f"card grew to {len(CARD_TEXT)} chars (~{len(CARD_TEXT)//4} tokens); "
        "it is loaded into context every time the skill fires"
    )
