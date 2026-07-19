"""Tests for the dangling-command check (command_resolution).

Spec: docs/specs/2026-07-19-command-resolution.md. Pins the core behavior
(dangling detection for make/npm/path) and the conservative / false-positive-safe
contract: absent a manifest, a command is `unknown`, never `dangling`.
"""
from __future__ import annotations

from scoring.command_resolution import resolve_commands


def _status(results: list[dict], needle: str) -> str | None:
    for r in results:
        if needle in r["command"]:
            return r["status"]
    return None


def test_make_target_dangling_and_resolved(tmp_path):
    (tmp_path / "Makefile").write_text("lint:\n\truff check .\n")
    agents = "# Agents\n\n```bash\nmake lint\nmake test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make test") == "dangling"  # no `test` target
    assert _status(results, "make lint") == "resolved"   # target exists


def test_make_unknown_without_makefile(tmp_path):
    # No Makefile on disk -> cannot prove absence -> conservative `unknown`.
    agents = "# Agents\n\n```bash\nmake test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make test") == "unknown"


def test_npm_script_dangling_and_resolved(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {"build": "tsc"}}')
    agents = "# Agents\n\n```bash\nnpm run build\nnpm run test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "build") == "resolved"
    assert _status(results, "test") == "dangling"  # not in package.json scripts


def test_missing_script_path_is_dangling(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# Agents\n\n```bash\nbash scripts/setup.sh\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "scripts/setup.sh") == "dangling"


def test_existing_script_path_is_resolved(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "setup.sh").write_text("#!/bin/sh\n")
    agents = "# Agents\n\n```bash\nbash scripts/setup.sh\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "scripts/setup.sh") == "resolved"


def test_deterministic(tmp_path):
    (tmp_path / "Makefile").write_text("lint:\n\truff check .\n")
    agents = "# Agents\n\n```bash\nmake test\n```\n"
    a = resolve_commands(agents, str(tmp_path))
    b = resolve_commands(agents, str(tmp_path))
    assert a == b
