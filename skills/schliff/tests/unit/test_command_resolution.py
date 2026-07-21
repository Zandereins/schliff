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


# --- Hardening regressions (2026-07-20) -------------------------------------
# Each test below pins a defect class that was verified live against the shipped
# 8.6.0 engine during an adversarial review. All five false-positive classes made
# the check claim a working command was broken — the exact failure the spec's
# conservative contract exists to prevent.


def test_compound_cd_is_unknown_not_dangling(tmp_path):
    """`cd pkg && npm run x` — the extractor drops the cd, so the script used to
    be resolved against the ROOT manifest and reported dangling. Standard
    monorepo idiom; a false claim here would be published on a consumer's PR."""
    (tmp_path / "package.json").write_text('{"scripts": {"build": "tsc"}}')
    api = tmp_path / "packages" / "api"
    api.mkdir(parents=True)
    (api / "package.json").write_text('{"scripts": {"lint": "eslint ."}}')
    agents = "# Agents\n\n```bash\ncd packages/api && npm run lint\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "npm run lint") == "unknown"


def test_fence_scoped_cd_taints_following_lines(tmp_path):
    """A bare `cd` persists for the rest of the shell fence."""
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# Agents\n\n```bash\ncd packages/api\nnpm run lint\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "npm run lint") == "unknown"


def test_cd_never_downgrades_a_resolved_command(tmp_path):
    """The cd demotion is one-directional: a target we DID find is still real."""
    (tmp_path / "package.json").write_text('{"scripts": {"lint": "eslint ."}}')
    agents = "# Agents\n\n```bash\ncd packages/api && npm run lint\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "npm run lint") == "resolved"


def test_subshell_parens_stripped(tmp_path):
    """`(cd x && npm run build)` left `build)` glued to the segment, which
    resolved as a script literally named "build)" and was reported dangling."""
    (tmp_path / "package.json").write_text('{"scripts": {"build": "tsc"}}')
    agents = "# Agents\n\n```bash\n(cd packages/api && npm run build)\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "build") == "resolved"


def test_bun_run_file_is_resolved(tmp_path):
    """bun resolves scripts, then FILES: `bun run index.ts` executes the file."""
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    (tmp_path / "index.ts").write_text("console.log(1)\n")
    agents = "# Agents\n\n```bash\nbun run index.ts\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "bun run index.ts") == "resolved"


def test_bun_missing_target_is_never_dangling(tmp_path):
    """Codegen'd outputs (`bun run dist/index.js`) make absence unprovable."""
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# Agents\n\n```bash\nbun run dist/index.js\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "dist/index.js") == "unknown"


def test_yarn_bareword_is_unknown(tmp_path):
    """`yarn tsc` runs node_modules/.bin/tsc — absence from `scripts` proves
    nothing, and the bin name need not match the package name."""
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# Agents\n\n```bash\nyarn tsc\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "yarn tsc") == "unknown"


def test_yarn_run_is_unknown_but_pnpm_run_is_dangling(tmp_path):
    """pnpm run hard-errors (ERR_PNPM_NO_SCRIPT) so absence is provable; every
    yarn form falls back to node_modules/.bin, so it is not."""
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# Agents\n\n```bash\nyarn run build\n```\n"
    assert _status(resolve_commands(agents, str(tmp_path)), "yarn run build") == "unknown"
    agents = "# Agents\n\n```bash\npnpm run build\n```\n"
    assert _status(resolve_commands(agents, str(tmp_path)), "pnpm run build") == "dangling"


def test_pm_run_flag_is_not_the_script_name(tmp_path):
    """`pnpm run -r build` read `-r` as the script and reported
    "script '-r' is not defined"."""
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    agents = "# Agents\n\n```bash\npnpm run -r build\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "pnpm run -r build") == "unknown"


def test_make_dash_c_directory_is_not_a_target(tmp_path):
    """`make -C build test` read the DIRECTORY as the target and reported
    "target 'build' is not defined"."""
    (tmp_path / "Makefile").write_text("test:\n\t@echo root\n")
    agents = "# Agents\n\n```bash\nmake -C build test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "build") == "unknown"


def test_make_include_fanout_is_bounded(tmp_path):
    """No visited-set meant N-way includes fanned out N**5: measured 15.0s at
    N=12 through the real CLI. Bounds the work, and pins the correct targets."""
    import time

    inc = "include " + " ".join(["a.mk"] * 20) + "\n"
    (tmp_path / "Makefile").write_text(inc + "build:\n\t@echo hi\n")
    (tmp_path / "a.mk").write_text(inc + "lint:\n\t@echo x\n")
    agents = "# Agents\n\n```bash\nmake lint\n```\n"
    start = time.monotonic()
    results = resolve_commands(agents, str(tmp_path))
    assert time.monotonic() - start < 5.0
    assert _status(results, "make lint") == "resolved"  # target from the include


def test_make_include_cycle_terminates(tmp_path):
    (tmp_path / "Makefile").write_text("include a.mk\nbuild:\n\t@echo hi\n")
    (tmp_path / "a.mk").write_text("include Makefile\nlint:\n\t@echo x\n")
    agents = "# Agents\n\n```bash\nmake lint\n```\n"
    assert _status(resolve_commands(agents, str(tmp_path)), "make lint") == "resolved"


def test_make_include_outside_repo_is_not_followed(tmp_path):
    """`include ../outside.mk` was opened, giving an attacker-authored Makefile a
    read primitive outside the checkout. Now contained -> unresolved -> unknown."""
    (tmp_path / "outside.mk").write_text("lint:\n\t@echo leak\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Makefile").write_text("include ../outside.mk\nbuild:\n\t@echo hi\n")
    agents = "# Agents\n\n```bash\nmake lint\n```\n"
    results = resolve_commands(agents, str(repo))
    # The out-of-tree target must NOT be ingested, and absence is unprovable.
    assert _status(results, "make lint") == "unknown"


def test_deeply_nested_package_json_does_not_crash(tmp_path):
    """RecursionError is a RuntimeError, not a ValueError, so it escaped the
    handler: a ~20KB nested package.json crashed the whole check."""
    (tmp_path / "package.json").write_text("[" * 5000 + "]" * 5000)
    agents = "# Agents\n\n```bash\nnpm run build\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "npm run build") == "unknown"


def test_include_regex_has_no_quadratic_backtracking(tmp_path):
    """A lazy `(.+?)[ \\t]*$` backtracked quadratically on a long whitespace run:
    15.7s for one 800KB line of attacker-authored Makefile."""
    import time

    payload = "include " + ("a" + " " * 4000) * 200 + "\n"
    (tmp_path / "Makefile").write_text("lint:\n\t@echo hi\n" + payload)
    agents = "# Agents\n\n```bash\nmake lint\n```\n"
    start = time.monotonic()
    resolve_commands(agents, str(tmp_path))
    assert time.monotonic() - start < 5.0


def test_variable_expanded_make_target_is_unknown(tmp_path):
    """`$(TARGETS): build test lint` defines targets via variable expansion; the
    target regex cannot see them, so `make test` was falsely dangling."""
    (tmp_path / "Makefile").write_text("TARGETS := build test lint\n$(TARGETS):\n\t@echo $@\n")
    agents = "# Agents\n\n```bash\nmake test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make test") == "unknown"


def test_pattern_rule_makefile_is_unknown(tmp_path):
    """A Makefile with a `%.o: %.c` pattern rule has non-enumerable targets."""
    (tmp_path / "Makefile").write_text("%.o: %.c\n\t@echo compile\nbuild:\n\t@echo hi\n")
    agents = "# Agents\n\n```bash\nmake test\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make test") == "unknown"


def test_static_makefile_still_reports_dangling(tmp_path):
    """The dynamic-target guard must not over-trigger: a purely static Makefile
    (even with `:=` assignments containing `$` and `:`) still proves absence."""
    (tmp_path / "Makefile").write_text(
        "VAR := $(shell echo hi)\nURL := http://example.com\nbuild:\n\t@echo hi\n"
    )
    agents = "# Agents\n\n```bash\nmake test\nmake build\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "make test") == "dangling"
    assert _status(results, "make build") == "resolved"


# --- Field regressions: real repos where shipped 8.6.0 emitted false danglings.
# Per feedback_field_test_over_fixtures, each real-world false positive is pinned
# by a test named after the repo that produced it. Verified 2026-07-21 against
# fresh clones: 8.6.0 reported these dangling, the hardened engine does not.


def test_field_blueprint_pnpm_nx_binary_is_unknown(tmp_path):
    """palantir/blueprint AGENTS.md: `pnpm nx compile @blueprintjs/core`. `nx` is
    a node_modules/.bin workspace tool, not a package.json script — 8.6.0 reported
    "script 'nx' is not defined" (false)."""
    (tmp_path / "package.json").write_text('{"scripts": {"build": "tsc"}}')
    agents = "# Agents\n\n```bash\npnpm nx compile @blueprintjs/core\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "pnpm nx compile") == "unknown"


def test_field_remotion_bun_run_dev_is_unknown(tmp_path):
    """remotion-dev/remotion AGENTS.md: `bun run dev`. bun resolves scripts, then
    files, then binaries — 8.6.0 reported "script 'dev' is not defined" (false)."""
    (tmp_path / "package.json").write_text('{"scripts": {"build": "tsc"}}')
    agents = "# Agents\n\n```bash\nbun run dev\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    assert _status(results, "bun run dev") == "unknown"


def test_field_swc_subshell_cd_path_is_unknown(tmp_path):
    """swc-project/swc AGENTS.md: `(cd crates/... && ./scripts/test.sh)`. 8.6.0
    reported "path './scripts/test.sh)' does not exist" — wrong name (glued paren)
    AND a false claim. The paren strip removes the `)`; the `cd` then makes the
    path's location unprovable, so it degrades to unknown, not a false dangling."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "test.sh").write_text("#!/bin/sh\necho hi\n")
    agents = "# Agents\n\n```bash\n(cd crates/swc && ./scripts/test.sh)\n```\n"
    results = resolve_commands(agents, str(tmp_path))
    # The credibility-critical property: the path must NOT be a false dangling.
    # (It resolves to the root script; the cd only demotes dangling->unknown, never
    # resolved->dangling, so the safe direction is preserved either way.)
    assert not any(r["status"] == "dangling" for r in results)
    assert _status(results, "test.sh") in ("resolved", "unknown")
