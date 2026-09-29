"""Fail on version drift across the three places a version is declared."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # unit→tests→schliff→skills→repo root
SKILL_MD = ROOT / "skills" / "schliff" / "SKILL.md"


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


def _cli_reported_version() -> str:
    import cli  # scripts/ is on sys.path via conftest
    return cli._resolve_version()


def test_all_versions_match():
    assert _pyproject_version() == _plugin_version() == _package_version(), (
        f"version drift: pyproject={_pyproject_version()} "
        f"plugin={_plugin_version()} package={_package_version()}"
    )


def test_skill_md_pins_the_current_version():
    """Every `schliff@X` / `schliff==X` pin in SKILL.md, allowed-tools included, names this release.

    SKILL.md once told users to pin 8.8.2 while 8.12.0 was released. The lookbehind skips
    `Zandereins/schliff@v1`, the GitHub Action's float tag.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"(?<![\w/])schliff(?:@v?|[=~]=v?)([0-9][0-9A-Za-z.+-]*)"
    pins = [pin.rstrip(".") for pin in re.findall(pattern, text)]
    assert pins, "SKILL.md no longer pins a version; drop this test only if that is intended"
    assert set(pins) == {_package_version()}, f"stale pin(s) in SKILL.md: {sorted(set(pins))}"


def test_reported_version_describes_the_loaded_code_not_the_installed_dist(monkeypatch):
    """The version stamped into a score must describe the engine that produced it.

    `_resolve_version()` used to read `importlib.metadata`, i.e. the *installed*
    dist-info. In a source or editable checkout that describes a different — often
    older — copy of schliff than the one actually executing, and the value is not
    cosmetic: `cli.py` stamps it into the score JSON, so it propagates into
    benchmark JSONL and leaderboard entries, attributing measurements to an engine
    version that never produced them.

    The stale metadata is injected here rather than assumed, so this discriminates
    in CI too — where the installed dist legitimately matches the tree and a plain
    equality check would pass either way.
    """
    import importlib.metadata

    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "0.0.1-stale")
    assert _cli_reported_version() == _package_version()
