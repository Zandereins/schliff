"""Fail on version drift across the places a version is declared."""
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


def _skill_version() -> str:
    text = (ROOT / "skills" / "schliff" / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("\n---\n", 1)[0]
    return re.search(r"^version:\s*(\S+)\s*$", frontmatter, re.MULTILINE).group(1)


def test_skill_md_pins_the_current_version():
    """A pinned `uvx schliff@X.Y.Z` in SKILL.md must name this release (it once said 8.8.2 at 8.12.0)."""
    text = (ROOT / "skills" / "schliff" / "SKILL.md").read_text(encoding="utf-8")
    pins = re.findall(r"schliff@(\d+\.\d+\.\d+)", text)
    assert pins, "SKILL.md no longer pins a version; drop this test only if that is intended"
    assert set(pins) == {_package_version()}, f"stale pin(s) in SKILL.md: {sorted(set(pins))}"


def _cli_reported_version() -> str:
    import cli  # scripts/ is on sys.path via conftest
    return cli._resolve_version()


def test_all_versions_match():
    assert _pyproject_version() == _plugin_version() == _package_version() == _skill_version(), (
        f"version drift: pyproject={_pyproject_version()} plugin={_plugin_version()} "
        f"package={_package_version()} skill={_skill_version()}"
    )


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
