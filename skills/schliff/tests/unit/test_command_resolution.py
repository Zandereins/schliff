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


# --- Regression tests: false-positive classes found on real repos (2026-07-19) ---

def test_env_assignment_prefix_not_a_path(tmp_path):
    # ColorlibHQ/gentelella: `BASE_PATH=/theme/gentelella/ npm run build` — the
    # env value was read as a missing path. Strip env prefix; resolve the command.
    (tmp_path / "package.json").write_text('{"scripts": {"build": "webpack"}}')
    agents = "# A\n\n```bash\nBASE_PATH=/theme/gentelella/ npm run build\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert not [r for r in results if r["status"] == "dangling"]
    assert _status(results, "build") == "resolved"


def test_inline_comment_stripped(tmp_path):
    # okTurtles/group-income: `npm run lint # run eslint` — comment must not leak
    # into resolution; `lint` really is absent (scripts has `eslint`, not `lint`).
    (tmp_path / "package.json").write_text('{"scripts": {"eslint": "eslint ."}}')
    agents = "# A\n\n```bash\nnpm run lint # run eslint\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "lint") == "dangling"
    assert "# run eslint" not in " ".join(r["evidence"] for r in results)


def test_quoted_tool_argument_not_a_path(tmp_path):
    # ViewComfy: `npx eslint "components/ui/button.tsx"` — a linter argument /
    # example, not a runnable repo artifact. Must be unknown, never dangling.
    agents = '# A\n\n```bash\nnpx eslint "components/ui/button.tsx"\n```\n'
    results = resolve_commands(agents, str(tmp_path))
    assert not [r for r in results if r["status"] == "dangling"]


def test_make_target_in_resolved_include(tmp_path):
    # authgear: `make start` where start lives in an included makefile.
    (tmp_path / "makefiles").mkdir()
    (tmp_path / "makefiles" / "common.mk").write_text("start:\n\tgo run .\n")
    (tmp_path / "Makefile").write_text("include ./makefiles/common.mk\n\nbuild:\n\tgo build .\n")
    agents = "# A\n\n```bash\nmake start\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make start") == "resolved"


def test_make_unresolvable_include_is_unknown(tmp_path):
    # An include we cannot follow (variable path) => can't prove absence => unknown.
    (tmp_path / "Makefile").write_text("include $(TOOLS)/x.mk\n\nbuild:\n\tgo build .\n")
    agents = "# A\n\n```bash\nmake test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make test") == "unknown"  # not dangling: could be in the include


def test_deterministic(tmp_path):
    (tmp_path / "Makefile").write_text("lint:\n\truff check .\n")
    agents = "# Agents\n\n```bash\nmake test\n```\n"
    a = resolve_commands(agents, str(tmp_path))
    b = resolve_commands(agents, str(tmp_path))
    assert a == b


def test_placeholder_script_is_unknown(tmp_path):
    # cssnr/cache-cleaner: `npm run *` — `*` is a prose placeholder, never dangling.
    (tmp_path / "package.json").write_text('{"scripts": {"build": "x"}}')
    agents = "# A\n\n```bash\nnpm run *\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert not [r for r in results if r["status"] == "dangling"]


def test_duplicate_command_reported_once(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# A\n\n```bash\nnpm run dev\n```\n\n## Again\n\n```bash\nnpm run dev\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert sum(1 for r in results if "dev" in r["command"]) == 1
