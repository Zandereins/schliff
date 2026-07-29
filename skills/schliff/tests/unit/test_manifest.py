"""`schliff manifest` — resolved agent state, built against synthetic installs.

Both regressions pinned here were found by RUNNING the resolver against a live
Claude Code install, not by reading it:

1. The plugin payload is not at `plugins/<package>`. It is
   `plugins/cache/<marketplace>/<package>`, sometimes with an extra version or
   content-hash segment. The first guess reported thirteen working plugins as
   "not present on disk".
2. Resident cost and invoke cost are different numbers. What a plugin charges on
   every turn is its DESCRIPTION; the body is charged only when it fires. Summing
   bodies and calling it a per-turn cost overstated the bill ~45x on a real install.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from manifest import build_manifest, format_manifest, manifest_to_dict


def _skill(root: Path, name: str, description: str = "does a thing",
           body: str = "# Body\n", extra_fm: str = "") -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n{extra_fm}---\n\n{body}",
        encoding="utf-8")
    return d


@pytest.fixture
def install(tmp_path: Path) -> Path:
    (tmp_path / "skills").mkdir()
    _skill(tmp_path / "skills", "alpha", description="x" * 40, body="B" * 4000)
    return tmp_path


def test_resident_and_invoke_costs_are_not_the_same_number(install: Path):
    """The bug that nearly shipped: body size reported as a per-turn charge."""
    m = build_manifest(claude_dir=install)
    assert len(m.loaded) == 1
    art = m.loaded[0]
    assert art.resident_tokens == 10          # 40 description chars / 4
    assert art.tokens > 900                   # ~4000-char body
    assert m.resident_tokens < m.invoke_tokens / 10, (
        "resident cost must not be conflated with invoke cost"
    )


def test_disabled_artifact_is_reported_not_loaded(install: Path):
    _skill(install / "skills", "muted", extra_fm="disable-model-invocation: true\n")
    m = build_manifest(claude_dir=install)
    assert "muted" not in {a.name for a in m.loaded}
    assert any(f.kind == "disabled" and f.subject == "muted" for f in m.findings)


def test_directory_without_skill_md_never_loads(install: Path):
    (install / "skills" / "empty-dir").mkdir()
    m = build_manifest(claude_dir=install)
    assert any(f.kind == "no-skill-md" and f.subject == "empty-dir" for f in m.findings)


def test_nested_skill_md_is_reported(install: Path):
    nested = install / "skills" / "alpha" / "upstream"
    nested.mkdir()
    (nested / "SKILL.md").write_text("---\nname: n\n---\n", encoding="utf-8")
    m = build_manifest(claude_dir=install)
    assert any(f.kind == "nested" for f in m.findings)


def test_plugin_payload_is_found_under_cache_marketplace_package(install: Path):
    """The layout that the first implementation got wrong."""
    (install / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"acme@some-market": True}}), encoding="utf-8")
    pkg = install / "plugins" / "cache" / "some-market" / "acme"
    _skill(pkg / "skills", "widget")
    m = build_manifest(claude_dir=install)
    assert "acme:widget" in {a.name for a in m.loaded}, (
        f"plugin payload not resolved; loaded={[a.name for a in m.loaded]}"
    )


def test_plugin_payload_is_found_under_a_version_segment(install: Path):
    """`cache/<market>/<pkg>/1.2.3/skills` — the shape codex and vault-sync use."""
    (install / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"acme@some-market": True}}), encoding="utf-8")
    pkg = install / "plugins" / "cache" / "some-market" / "acme" / "1.2.3"
    _skill(pkg / "skills", "widget")
    m = build_manifest(claude_dir=install)
    assert "acme:widget" in {a.name for a in m.loaded}


def test_enabled_but_absent_plugin_is_a_finding(install: Path):
    (install / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"ghost@some-market": True}}), encoding="utf-8")
    m = build_manifest(claude_dir=install)
    assert any("ghost" in f.subject for f in m.findings)


def test_disabled_plugin_contributes_nothing(install: Path):
    (install / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"acme@some-market": False}}), encoding="utf-8")
    pkg = install / "plugins" / "cache" / "some-market" / "acme"
    _skill(pkg / "skills", "widget")
    m = build_manifest(claude_dir=install)
    assert "acme:widget" not in {a.name for a in m.loaded}
    assert not any("acme" in f.subject for f in m.findings)


def test_output_is_renderable_and_serialisable(install: Path):
    m = build_manifest(claude_dir=install)
    assert "resident every turn" in format_manifest(m)
    d = manifest_to_dict(m)
    assert d["loaded_count"] == len(m.loaded)
    assert "resident_tokens" in d and "invoke_tokens" in d
    json.dumps(d)  # must round-trip


def test_empty_install_says_so(tmp_path: Path):
    out = format_manifest(build_manifest(claude_dir=tmp_path))
    assert "0 artifacts loaded" in out
