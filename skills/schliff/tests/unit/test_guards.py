"""Unit tests for the deterministic judge guards (scoring/guards.py).

Fixtures mirror the Phase-0 specimens that motivated each guard:
- skill 09 algorithms  -> destructive-command detector
- skill 08 Nemp-memory -> gating invariant (stub below floor)
- skill 10 GAP         -> mixed-script trigger surface (+ below floor)
"""
from shared import invalidate_cache
from scoring.guards import (
    detect_destructive_commands,
    judge_floor,
    detect_mixed_script,
    run_guards,
    MIN_BODY_WORDS,
)


def _write(tmp_path, name: str, content: str) -> str:
    d = tmp_path / name
    d.mkdir()
    f = d / "SKILL.md"
    f.write_text(content)
    invalidate_cache(str(f))
    return str(f)


# --- Fixtures ---------------------------------------------------------------

# Like skill 09: destructive commands presented as neutral tips, unguarded,
# inside a code fence (which the opt-in security scorer would EXCLUDE).
DESTRUCTIVE_UNGUARDED = """\
# Linux Ops

Force an immediate reboot:
```bash
echo b > /proc/sysrq-trigger
```

Fake available RAM persistently via grub:
```bash
mem=1G
```
"""

# Same dangerous commands but guarded by warnings/negation (educational).
DESTRUCTIVE_GUARDED = """\
---
name: safety-guide
description: How to avoid destructive commands.
---

# Safety Guide

Warning — never run the following, it forces an unsynced reboot:
```bash
echo b > /proc/sysrq-trigger
```

Do not run `rm -rf /` — it is irreversible.
"""

BENIGN = """\
---
name: format-code
description: Format source files using project conventions. Use when formatting code.
---

# Format Code

Run the formatter against the target file and verify the output matches the
style guide. This skill has nothing dangerous in it whatsoever.
"""

# Like skill 08: frontmatter only, no body.
STUB = """\
---
name: nemp-memory
description: Persistent local memory for AI agents. Save, recall, and search.
metadata: {"openclaw": {"always": true}}
---
"""

# Like skill 09/10: no YAML frontmatter at all.
NO_FRONTMATTER = """\
# algorithms

1. `free -m` shows memory
2. `iostat` shows disk io
"""

REAL_SKILL = """\
---
name: real-skill
description: A genuine skill with a real body. Use when you need to do the thing.
---

# Real Skill

## Instructions

1. Read the input file carefully and confirm it exists before proceeding.
2. Apply the transformation described below to each section in turn.
3. Verify the output against the documented acceptance criteria.

## Examples

A worked example with enough words to comfortably clear the body-length floor.
"""

# Like skill 10: tri-script headers (Thai + Chinese + English), no frontmatter.
MULTI_SCRIPT = """\
# ระบบการออกแบบ

## 设计系统概述

## Authentication Setup

Some body content describing the design system across multiple languages.
"""

ENGLISH_ONLY = """\
---
name: english-skill
description: An English-only skill for testing script detection.
---

# Design System

## Authentication Setup

## Deployment Notes
"""


# --- detect_destructive_commands -------------------------------------------

class TestDestructiveCommands:
    def test_unguarded_destructive_flags(self, tmp_path):
        res = detect_destructive_commands(_write(tmp_path, "d1", DESTRUCTIVE_UNGUARDED))
        assert res["flag"] is True
        assert res["unguarded_count"] >= 2
        kinds = {m["kind"] for m in res["matches"]}
        assert "sysrq_trigger" in kinds
        assert "grub_mem" in kinds
        assert res["recommendation"]

    def test_does_not_code_block_exclude(self, tmp_path):
        """Unlike score_security, commands inside a fence still flag (skill-09 gap)."""
        res = detect_destructive_commands(_write(tmp_path, "d2", DESTRUCTIVE_UNGUARDED))
        # the sysrq command lives inside a ```bash fence yet must still be caught
        assert any(m["kind"] == "sysrq_trigger" and not m["guarded"] for m in res["matches"])

    def test_guarded_destructive_not_flagged(self, tmp_path):
        res = detect_destructive_commands(_write(tmp_path, "d3", DESTRUCTIVE_GUARDED))
        assert res["flag"] is False
        # matches are still recorded, but all guarded
        assert res["matches"]
        assert all(m["guarded"] for m in res["matches"])

    def test_benign_no_flag(self, tmp_path):
        res = detect_destructive_commands(_write(tmp_path, "d4", BENIGN))
        assert res["flag"] is False
        assert res["matches"] == []

    def test_rm_rf_variants(self, tmp_path):
        content = "# x\n\nrun `rm -fr /data` now\nthen `dd if=/dev/zero of=/dev/sda`\n"
        res = detect_destructive_commands(_write(tmp_path, "d5", content))
        kinds = {m["kind"] for m in res["matches"]}
        assert "rm_rf" in kinds
        assert "dd_to_device" in kinds
        assert res["flag"] is True

    def test_missing_file(self):
        res = detect_destructive_commands("/nonexistent/SKILL.md")
        assert res["flag"] is False
        assert "error" in res


# --- judge_floor ------------------------------------------------------------

class TestJudgeFloor:
    def test_real_skill_above_floor(self, tmp_path):
        res = judge_floor(_write(tmp_path, "f1", REAL_SKILL))
        assert res["above_floor"] is True
        assert res["reasons"] == []
        assert res["body_words"] >= MIN_BODY_WORDS

    def test_stub_below_floor(self, tmp_path):
        res = judge_floor(_write(tmp_path, "f2", STUB))
        assert res["above_floor"] is False
        assert any(r.startswith("body_too_short") for r in res["reasons"])

    def test_no_frontmatter_below_floor(self, tmp_path):
        res = judge_floor(_write(tmp_path, "f3", NO_FRONTMATTER))
        assert res["above_floor"] is False
        assert "no_frontmatter" in res["reasons"]

    def test_missing_file_below_floor(self):
        res = judge_floor("/nonexistent/SKILL.md")
        assert res["above_floor"] is False
        assert res["reasons"]


# --- detect_mixed_script ----------------------------------------------------

class TestMixedScript:
    def test_multi_script_flags(self, tmp_path):
        res = detect_mixed_script(_write(tmp_path, "m1", MULTI_SCRIPT))
        assert res["flag"] is True
        assert "THAI" in res["trigger_surface_scripts"]
        assert "CJK" in res["trigger_surface_scripts"]
        assert "LATIN" in res["trigger_surface_scripts"]

    def test_english_only_no_flag(self, tmp_path):
        res = detect_mixed_script(_write(tmp_path, "m2", ENGLISH_ONLY))
        assert res["flag"] is False
        assert res["trigger_surface_scripts"] == ["LATIN"]

    def test_missing_file(self):
        res = detect_mixed_script("/nonexistent/SKILL.md")
        assert res["flag"] is False
        assert "error" in res


# --- run_guards -------------------------------------------------------------

def test_run_guards_shape(tmp_path):
    res = run_guards(_write(tmp_path, "g1", REAL_SKILL))
    assert set(res) == {"destructive_commands", "judge_floor", "mixed_script"}
    assert res["judge_floor"]["above_floor"] is True
