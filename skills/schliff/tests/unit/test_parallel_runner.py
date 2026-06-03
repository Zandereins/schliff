"""Regression tests for parallel_runner subprocess invocations.

The text-gradient CLI exposes only --apply (no --apply-top / --strategy). A prior
change invoked the nonexistent flags, which argparse rejects with exit 2, hard-failing
parallel mode. These tests pin the supported contract using AST string literals so the
explanatory comments mentioning the bad flags do not trigger false positives.
"""
import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "scripts" / "parallel_runner.py"


def _string_literals(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


class TestParallelRunnerFlags:
    def test_no_nonexistent_flags_in_code(self):
        lits = _string_literals(_SRC)
        assert "--apply-top" not in lits, "parallel_runner uses nonexistent --apply-top flag"
        assert "--strategy" not in lits, "parallel_runner uses nonexistent --strategy flag"

    def test_uses_supported_apply_flag(self):
        lits = _string_literals(_SRC)
        assert "--apply" in lits, "parallel_runner should apply via the supported --apply flag"

    def test_text_gradient_cli_rejects_apply_top(self, tmp_path):
        """Contract check: text-gradient.py must reject --apply-top (proves the flag is absent)."""
        import subprocess
        import sys

        skill = tmp_path / "SKILL.md"
        skill.write_text("---\nname: x\ndescription: y\n---\n# X\n", encoding="utf-8")
        tg = _SRC.parent / "text-gradient.py"
        rc = subprocess.run(
            [sys.executable, str(tg), str(skill), "--apply-top", "--strategy", "foo"],
            capture_output=True, text=True, timeout=60,
        ).returncode
        assert rc != 0, "text-gradient unexpectedly accepts --apply-top/--strategy"
