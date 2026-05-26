"""Fail on version drift across the three places a version is declared."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # unit→tests→schliff→skills→repo root


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


def _plugin_version() -> str:
    return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def _package_version() -> str:
    import sys
    sys.path.insert(0, str(ROOT / "skills"))
    import schliff  # skills/schliff/__init__.py
    return schliff.__version__


def test_all_versions_match():
    assert _pyproject_version() == _plugin_version() == _package_version(), (
        f"version drift: pyproject={_pyproject_version()} "
        f"plugin={_plugin_version()} package={_package_version()}"
    )
