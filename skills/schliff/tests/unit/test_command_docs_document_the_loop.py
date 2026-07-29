"""The loop is documented where the loop lives — in the plugin command docs.

Why this exists: `skills/schliff/eval-suite.json` used to carry ten test cases whose
prompts were about the autonomous improvement loop (stuck detection, cross-session
history, iteration budgets, eval-suite generation, pass rates). Their assertions were
checked against SKILL.md, so the agent-facing card had to contain the loop's whole
vocabulary or the suite went red. That is backwards: the card is the CLI surface, and
the loop is reachable only through the `/schliff:*` plugin commands. When the card was
rewritten to be executable, 76 of those assertions failed — the suite was pinning the
shape of an artifact, not a property of the product.

So the coverage moved here, to the docs that actually own the behaviour. Every
assertion below was derived from one of those prompts and then checked against the
code before being written down:

  "stuck after 5 discards / parallel worktree branches"  -> auto-improve.py:283
  "cross-session learning from history"                  -> auto-improve.py:342,544
  "scoring changes over time / regression"               -> .schliff/auto-improve-state.jsonl
  "run N iterations / stopping"                          -> auto-improve.py:_should_stop
  "generate an eval suite / baseline"                    -> init-skill.py
  "which assertions pass and fail / pass rate"           -> run-eval.sh

Prompts that asked for things which do not exist got no assertion at all, here or
anywhere: there is no `discovery mode`, no `high-ROI` ranking (zero occurrences in
scripts/), and no custom-metric interface. `auto-improve.py` detects the stuck
condition but never branches, so "worktree" is asserted *absent* from the agent-facing
promise rather than present.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
COMMANDS = REPO / "commands" / "schliff"
DRIVER = REPO / "skills" / "schliff" / "scripts" / "auto-improve.py"


def _doc(name: str) -> str:
    return (COMMANDS / f"{name}.md").read_text(encoding="utf-8")


# (command doc, regex, what prompt this came from)
_DOCUMENTED = [
    ("auto", r"(?i)5\+?\s*consecutive discards", "stuck after 5 discards"),
    ("auto", r"(?i)sequential", "…and what it does instead of branching"),
    ("auto", r"auto-improve-state\.jsonl", "scoring changes over time"),
    ("auto", r"episodes\.jsonl", "cross-session learning from history"),
    ("auto", r"(?i)plateau|EMA", "run 1000 iterations overnight — stopping conditions"),
    ("auto", r"--max-iterations", "run 20 iterations"),
    ("init", r"(?i)eval[- ]suite", "generate an eval suite"),
    ("init", r"(?i)baseline", "…and establish the initial measurement"),
    ("eval", r"(?i)assertion", "which tests pass and which fail"),
    ("eval", r"(?i)pass[ -]rate", "show me the pass rate"),
    ("report", r"(?i)baseline", "improvement report for the last N experiments"),
]


@pytest.mark.parametrize(
    "name,rx,prompt", _DOCUMENTED, ids=[f"{n}:{r[:24]}" for n, r, _ in _DOCUMENTED]
)
def test_command_doc_answers_the_prompt(name: str, rx: str, prompt: str):
    assert re.search(rx, _doc(name)), (
        f"commands/schliff/{name}.md no longer answers {prompt!r} (missing /{rx}/)"
    )


_NEGATED = re.compile(r"(?i)\b(no|not|never|without|neither)\b")


def test_auto_only_mentions_worktrees_to_deny_them():
    """`_should_trigger_parallel` fires, prints, and the loop continues in-process.

    No worktree is created on this path — verified by running the driver to
    completion and finding the target repo's worktree list unchanged. So the word
    may appear here only inside a sentence that denies it; any other mention is a
    promise of work that never happens.
    """
    sentences = re.split(r"(?<=[.!?])\s+|\n\n", _doc("auto"))
    promises = [s.strip() for s in sentences if "worktree" in s.lower() and not _NEGATED.search(s)]
    assert not promises, (
        f"auto.md mentions worktrees without denying them, which the loop does not do: {promises}"
    )


def _flag_section() -> str:
    text = _doc("auto")
    start = text.index("## Flags")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def test_every_documented_flag_is_accepted_by_the_driver():
    """The defect this caught: auto.md documented `--resume`, and the driver exits 2
    with `unrecognized arguments: --resume`. Same failure mode as the card's
    `doctor <dir>` — a documented switch that argparse rejects."""
    helptext = subprocess.run(
        [sys.executable, str(DRIVER), "--help"], capture_output=True, text=True, timeout=60
    ).stdout
    documented = set(re.findall(r"`(--[a-z-]+)`", _flag_section()))
    assert documented, "auto.md lists no flags at all — the Flags section lost its content"
    unknown = sorted(f for f in documented if f not in helptext)
    assert not unknown, f"auto.md documents flags auto-improve.py rejects: {unknown}"


def test_documented_driver_path_resolves():
    """auto.md gives the driver's path from the checkout root; if that path is wrong
    the command doc points an agent at nothing."""
    m = re.search(r"`?python3 (skills/\S+auto-improve\.py)", _doc("auto"))
    assert m, "auto.md no longer shows how to invoke the loop driver"
    proc = subprocess.run(
        [sys.executable, str(REPO / m.group(1)), "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, (
        f"documented driver path does not run: {m.group(1)} (exit {proc.returncode})\n"
        f"{proc.stderr.strip()[:300]}"
    )
