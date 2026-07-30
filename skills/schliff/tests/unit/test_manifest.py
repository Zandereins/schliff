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


class TestFrontmatterParseIsBoundedAndLinear:
    """`schliff manifest` reads third-party content, so its parser is a trust boundary.

    It walks every SKILL.md under `~/.claude/skills`, every `*.md` under
    `~/.claude/commands`, the project's `.claude/`, and the payload of every enabled
    plugin. Two defects from the 2026-07-30 audit met there:

    1. `_FM = r"^---\\s*\\n(.*?)\\n---\\s*\\n"` is O(n^2) because `\\s*` may consume
       newlines: every `\\s*` length restarts the lazy body scan. 25.6s at 64KB, 4.04x
       per doubling; ~1.9h extrapolated at 1MB.
    2. The read had no size cap at all — a raw `read_text()`, unlike every other reader
       in the engine, which goes through `read_skill_safe` at MAX_SKILL_SIZE.

    Both call sites do `fm, _ = parse_frontmatter(...)`: the body was never used. So the
    fix reads a bounded HEAD rather than capping a full read nobody needed.
    """

    def test_unterminated_frontmatter_parses_in_linear_time(self, tmp_path):
        import time

        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        prev = None
        for n in (16_000, 32_000, 64_000):
            p.write_text("---" + "\n" * n, encoding="utf-8")
            start = time.perf_counter()
            parse_frontmatter(p)
            elapsed = time.perf_counter() - start
            if prev is not None:
                assert elapsed / prev < 3.0, (
                    f"parse_frontmatter is super-linear: {prev * 1000:.1f}ms -> "
                    f"{elapsed * 1000:.1f}ms at n={n} ({elapsed / prev:.2f}x per doubling)"
                )
            prev = elapsed
        assert prev < 1.0, f"parse_frontmatter took {prev:.2f}s on a 64KB file"

    def test_oversized_file_is_not_read_whole(self, tmp_path, monkeypatch):
        """A 4MB SKILL.md must not be pulled into memory to read its frontmatter.

        This asserts the READ, not just the result. A first version of this test only
        checked that `_FM_READ_BYTES` was small and that parsing still worked — and it
        passed with the bounded read reverted to a full `read_text()`, because a full read
        produces the same mapping. A test that cannot fail on the defect it names is not a
        test. Found by mutation.
        """
        import pathlib as _pathlib

        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: big\ndescription: fine\n---\n" + "x" * (4 * 1024 * 1024),
                     encoding="utf-8")

        requested: list = []
        real_open = _pathlib.Path.open

        def recording_open(self, *args, **kwargs):
            handle = real_open(self, *args, **kwargs)
            real_read = handle.read

            def read(n=-1):
                requested.append(n)
                return real_read(n)

            handle.read = read
            return handle

        monkeypatch.setattr(_pathlib.Path, "open", recording_open)
        fm = parse_frontmatter(p)

        assert fm.get("name") == "big"
        assert fm.get("description") == "fine"
        assert requested, (
            "parse_frontmatter did not go through Path.open — a full-file read path "
            "(read_text, read_bytes) bypasses the bound entirely"
        )
        assert all(n is not None and n > 0 for n in requested), (
            f"parse_frontmatter issued an unbounded read: read({requested}). "
            f"read(-1) or read() pulls the whole 4MB file into memory."
        )
        assert max(requested) <= 64 * 1024, f"read too much at once: {max(requested)} bytes"

    # Largest frontmatter block measured across 248 real skills, commands and plugin
    # payloads (vercel's ai-sdk SKILL.md), in CHARACTERS — `read(n)` on a text handle
    # counts code points. The head read must stay above it or the
    # frontmatter of a real artifact gets truncated and its description silently reads
    # as empty — the same "calibrate the bound, do not guess it" rule as the pattern
    # bounds in PR 1, and it needs its own assertion for the same reason.
    CORPUS_MAX_FRONTMATTER_CHARS = 15_711

    def test_head_read_stays_above_the_measured_frontmatter_maximum(self):
        from manifest import _FM_READ_CHARS
        assert _FM_READ_CHARS > self.CORPUS_MAX_FRONTMATTER_CHARS, (
            f"head read {_FM_READ_CHARS} is not above the largest real frontmatter block "
            f"({self.CORPUS_MAX_FRONTMATTER_CHARS}); a real artifact would parse as if it "
            f"had no frontmatter. Re-measure before changing this."
        )
        assert _FM_READ_CHARS < 1024 * 1024, (
            "the head read must stay well under MAX_SKILL_SIZE (1MB) or it is not a bound"
        )

    def test_returns_only_the_frontmatter_mapping(self, tmp_path):
        """Both call sites discarded the body. Returning it invited a full read for
        nothing, so the signature drops it."""
        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: x\ndescription: y\n---\n\nbody text\n", encoding="utf-8")
        result = parse_frontmatter(p)
        assert isinstance(result, dict), f"expected a mapping, got {type(result).__name__}"
        assert result == {"name": "x", "description": "y"}

    # Shapes that must keep parsing byte-identically after the anchor change.
    EQUIVALENCE = [
        ("plain", "---\nname: a\ndescription: b\n---\nbody", {"name": "a", "description": "b"}),
        ("crlf", "---\r\nname: a\r\ndescription: b\r\n---\r\nbody",
         {"name": "a", "description": "b"}),
        ("trailing spaces on delimiters", "---  \nname: a\n---  \nbody", {"name": "a"}),
        ("no frontmatter", "# just a heading\n", {}),
        ("unterminated", "---\nname: a\n", {}),
        ("block scalar", "---\nname: a\ndescription: >\n  one\n  two\n---\nbody",
         {"name": "a", "description": "one two"}),
        ("quoted value", '---\nname: "a b"\n---\nbody', {"name": "a b"}),
        ("boolean", "---\nname: a\ndisable-model-invocation: true\n---\nbody",
         {"name": "a", "disable-model-invocation": True}),
    ]

    @pytest.mark.parametrize("label,text,expected", EQUIVALENCE,
                             ids=[c[0] for c in EQUIVALENCE])
    def test_real_shapes_parse_unchanged(self, tmp_path, label, text, expected):
        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        p.write_text(text, encoding="utf-8")
        assert parse_frontmatter(p) == expected, label


class TestFrontmatterWhitespaceClassIsNotNarrowed:
    """The ReDoS fix replaced `\\s*` with a class that cannot span the newline. That is a
    NARROWING of the whitespace class, and the first attempt narrowed too far.

    `[ \\t]*\\r?` lost FOUR shapes 8.8.2 parsed, measured through the real read path: form
    feed, vertical tab, NBSP and em space. Material, not cosmetic: `manifest` reports
    resolved state, so frontmatter it fails to parse makes a `disable-model-invocation:
    true` skill read as LOADED, and drops the description that carries the per-turn cost.

    `[^\\S\\n]*` — whitespace except newline — is the class that keeps every shape and
    still cannot restart the lazy body scan. Enumerating the dimension rather than sampling
    it is the only way the losses became visible.

    The first count published for this was SIX, and it was wrong. That enumeration ran
    against in-memory strings while `parse_frontmatter` reads through `path.open("r")`,
    i.e. universal newlines — which collapses every CR-based shape before the regex sees
    it. A mutation test disagreed with the hand-run enumeration (four red, not six) and the
    read path was the difference. A probe against a substrate the code does not use is not
    a probe, and the error went in the direction that flattered the finding.

    The CR-bearing separators below are kept deliberately: they pin the translated
    behaviour, and `TestUniversalNewlineContract` pins the translation itself, because the
    day someone opens the file with `newline=""` those shapes stop being equivalent.
    """

    SEPARATORS = [
        ("lf", "\n"),
        ("crlf", "\r\n"),
        ("space_lf", " \n"),
        ("tab_lf", "\t\n"),
        ("two_spaces_lf", "  \n"),
        ("formfeed_lf", "\f\n"),
        ("vtab_lf", "\v\n"),
        ("cr_cr_lf", "\r\r\n"),
        ("lf_lf", "\n\n"),
        ("space_cr_lf", " \r\n"),
        ("nbsp_lf", "\u00a0\n"),
        ("emspace_lf", "\u2003\n"),
        ("tab_cr_lf", "\t\r\n"),
        ("mixed_ws_lf", "\t \r\f\v\n"),
    ]

    @pytest.mark.parametrize("label,sep", SEPARATORS, ids=[s[0] for s in SEPARATORS])
    def test_every_whitespace_separator_still_parses(self, tmp_path, label, sep):
        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        p.write_text(f"---{sep}name: a{sep}description: b{sep}---{sep}body", encoding="utf-8")
        fm = parse_frontmatter(p)
        assert fm.get("name") == "a", (
            f"separator {label!r} no longer parses — the whitespace class was narrowed "
            f"past what 8.8.2 accepted. A frontmatter this parser misses makes a disabled "
            f"skill report as loaded."
        )

    @pytest.mark.parametrize("label,sep", SEPARATORS, ids=[s[0] for s in SEPARATORS])
    def test_disabled_skill_is_never_reported_as_loaded(self, tmp_path, label, sep):
        """The consequence that makes the above material, asserted directly."""
        from manifest import build_manifest
        root = tmp_path / ".claude"
        d = root / "skills" / "off"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---{sep}name: off{sep}disable-model-invocation: true{sep}---{sep}body",
            encoding="utf-8")
        m = build_manifest(claude_dir=root)
        assert [a.name for a in m.loaded] == [], (
            f"separator {label!r}: a disabled skill was reported as LOADED because its "
            f"frontmatter did not parse"
        )
        assert any(f.kind == "disabled" for f in m.findings), f"separator {label!r}"


class TestUniversalNewlineContract:
    """`parse_frontmatter` reads through `path.open("r")`, so CR never reaches the regex.

    This is load-bearing and was invisible until a mutation test disagreed with a
    hand-run enumeration: the enumeration used in-memory strings and reported six lost
    shapes, the mutation reported four, and the read path was the difference. Pinned so
    the next person does not have to rediscover it — and so switching to `newline=""`,
    which would make CR reachable and change which separators are equivalent, fails here.
    """

    def test_carriage_returns_never_reach_the_regex(self, tmp_path):
        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        # Written as CRLF bytes on purpose — not via write_text, which would translate.
        p.write_bytes(b"---\r\nname: a\r\ndescription: b\r\n---\r\nbody")
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            seen = fh.read(4096)
        assert "\r" not in seen, (
            "a literal CR reached the reader — the file is no longer opened in universal-"
            "newline mode, so the CR-bearing separators in "
            "TestFrontmatterWhitespaceClassIsNotNarrowed are no longer equivalent to their "
            "LF forms and need re-enumerating against this substrate"
        )
        # ...and the values still parse, through the translation.
        assert parse_frontmatter(p) == {"name": "a", "description": "b"}

    def test_lone_cr_line_endings_are_translated_not_dropped(self, tmp_path):
        """Classic-Mac CR-only endings become LF, so they parse rather than reading as
        one unterminated line."""
        from manifest import parse_frontmatter
        p = tmp_path / "SKILL.md"
        p.write_bytes(b"---\rname: a\r---\rbody")
        assert parse_frontmatter(p) == {"name": "a"}
