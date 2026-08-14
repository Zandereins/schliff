"""Every flag a command doc tells the agent to type must exist in the script.

`/schliff:analyze` step 7 and `/schliff:bench` step 5 both documented
`run-eval.sh <skill> --eval-suite <suite>`. The script takes the suite
positionally and rejects that flag:

    $ bash scripts/run-eval.sh SKILL.md --eval-suite eval-suite.json
    Error: unknown option --eval-suite

Two docs, one wrong signature, and schliff ships `check-commands` precisely to catch
this class in other people's files. The docs are what an agent copies verbatim, so a
flag that does not parse is a broken instruction, not a typo.

Spec: docs/specs/2026-08-13-structural-signal-detection.md (follow-up section)
"""
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_COMMANDS = _ROOT / "commands" / "schliff"
_SCRIPTS = _ROOT / "skills" / "schliff" / "scripts"

# `bash scripts/<name>.sh` or `python3 scripts/<name>.py` … to the end of the block.
#
# The first version matched only `bash`, which left the majority of flag-bearing
# invocations in commands/schliff/ — the `python3 scripts/*.py` ones — outside the
# guard entirely. A live defect (`init-skill.py --goal`, a flag argparse does not
# have) sat in that blind spot while this test reported green.
_INVOCATION = re.compile(
    r"(?:bash|python3)\s+scripts/(?P<script>[\w.-]+\.(?:sh|py))"
    r"(?P<args>(?:[^\n`]|\\\n)*(?:\n\s+[^\n`]*)*)"
)
_FLAG = re.compile(r"(?<![\w-])--[a-z][\w-]*")


def _documented_invocations():
    for doc in sorted(_COMMANDS.glob("*.md")):
        text = doc.read_text(encoding="utf-8")
        for match in _INVOCATION.finditer(text):
            flags = set(_FLAG.findall(match.group("args")))
            if flags:
                yield doc.name, match.group("script"), frozenset(flags)


# A `case` branch in a bash argument parser: `        --flag)` or `        --a|--b)`.
_CASE_BRANCH = re.compile(r"^[ \t]+(--[\w-]+(?:\|--[\w-]+)*)\)", re.MULTILINE)
# An argparse declaration in a Python script: `add_argument("--flag"` / `'--flag'`.
_ADD_ARGUMENT = re.compile(r"add_argument\(\s*[\"'](--[\w-]+)[\"']")
# A CLI wrapper delegating to the real module: `from text_gradient import main`.
_DELEGATE = re.compile(r"^from\s+([\w]+)\s+import\s+main", re.MULTILINE)


def _flags_accepted_by(script: str) -> set[str]:
    """Flags the script's argument parser actually declares.

    Not every `--flag` appearing in the source: `run-eval.sh` PASSES `--eval-suite`
    through to score-skill.py on line 180 and names it in a jq error string, so
    scanning the whole file reports it as accepted and the check silently passes.
    That version of this test stayed green with the defect restored — the red proof
    is what caught it.
    """
    source = (_SCRIPTS / script).read_text(encoding="utf-8")
    if script.endswith(".py"):
        # The hyphenated CLI names are six-line wrappers that delegate to the
        # underscored module (`from text_gradient import main`); the argparse lives
        # there. Reading the wrapper found zero flags and reported working ones as
        # unknown — `skill-mesh.py --json` exits 0 while the check called it broken.
        delegate = _DELEGATE.search(source)
        if delegate:
            module = _SCRIPTS / f"{delegate.group(1)}.py"
            if module.exists():
                source = module.read_text(encoding="utf-8")
        return set(_ADD_ARGUMENT.findall(source))
    accepted: set[str] = set()
    for branch in _CASE_BRANCH.findall(source):
        accepted.update(branch.split("|"))
    return accepted


CASES = list(_documented_invocations())


def test_the_scan_finds_invocations():
    """Guard the guard: an empty scan would make every assertion below vacuous."""
    assert CASES, "no documented script invocations with flags found — regex is broken"


@pytest.mark.parametrize("doc,script,flags", CASES, ids=[f"{d}:{s}" for d, s, _ in CASES])
def test_documented_flags_are_accepted_by_the_script(doc, script, flags):
    accepted = _flags_accepted_by(script)
    unknown = sorted(f for f in flags if f not in accepted)
    assert not unknown, (
        f"{doc} tells the agent to run `{script} {' '.join(unknown)}`, "
        f"which the script does not parse"
    )
