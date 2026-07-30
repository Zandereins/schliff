"""Resolve what a Claude Code install actually loads, and what it costs per turn.

Every other tool in this space lints a FILE. This reads the resolved state:
`settings.json` x `installed_plugins.json` x on-disk skill and command roots x
frontmatter, and answers three questions nobody else answers —

  * which artifacts are actually loaded right now,
  * what they charge against the context window on every single turn,
  * which ones are installed but silently never load.

Design constraints, each one learned the hard way:

* **No hardcoded roster of harness built-ins.** A prototype carried one, hand-copied
  from a single live session and marked "undocumented upstream, will drift". A tool
  that reports resolved state and misclassifies silently is worse than no tool. Only
  artifacts found on disk under a known root are reported; nothing is inferred.
* **Cost is the SKILL.md plus its `references/*.md`, never the directory.** One real
  skill directory here holds a 200 MB virtualenv; measuring the tree would report
  tens of millions of tokens for a file that charges a few hundred.
* **No scoring.** This command emits no grade. It reports state.
* **Read-only, local, and quiet about identity.** Paths print relative to `~`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()

# `[^\S\n]*`, not `\s*`: the quadratic came from `\s` matching the newline ITSELF, so
# every possible `\s*` length restarted the lazy `(.*?)` body scan — O(n^2) on a file that
# opens the delimiter and never closes it. Measured 25.6s at 64KB, 4.04x per doubling,
# ~1.9h extrapolated at 1MB. A class that cannot span the record separator cannot restart
# that scan: 1.5ms at 64KB, linear.
#
# `[^\S\n]` is "whitespace except newline" and is deliberately NOT the narrower
# `[ \t]*\r?`. The first attempt at this fix used `[ \t]*\r?` and lost four shapes 8.8.2
# parsed: form feed, vertical tab, NBSP and em space. Not cosmetic here — this tool
# reports resolved state, so frontmatter it fails to parse makes a
# `disable-model-invocation: true` skill read as LOADED. Enumerating the whitespace
# dimension instead of sampling it is what caught it; the enumeration lives in
# tests/unit/test_manifest.py and covers all 14 shapes with 0 divergence from 8.8.2.
#
# The `\r` that `[^\S\n]` admits is NOT load-bearing on this path: the read below opens
# in universal-newline mode, so CR is translated to LF before the regex sees it. It is
# kept because removing a class member for no measured reason is how the first attempt
# went wrong. `TestUniversalNewlineContract` pins the translation, since `newline=""`
# would make CR reachable and change which separators are equivalent.
#
# This parser reads THIRD-PARTY content: `schliff manifest` walks every SKILL.md under
# ~/.claude/skills, every command under ~/.claude/commands, the project's .claude/, and
# the payload of every enabled plugin. See docs/specs/2026-07-30-redos-audit-fixes.md (D3).
_FM = re.compile(r"^---[^\S\n]*\n(.*?)\n---[^\S\n]*\n", re.S)
_KV = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$")

# Frontmatter lives at the top of the file, so only a head read is needed — and a head
# read is what keeps a hostile or merely huge artifact from being pulled into memory.
# Every other reader in the engine goes through `read_skill_safe` at MAX_SKILL_SIZE (1MB);
# this one used a raw `read_text()` with no cap at all.
#
# Calibrated, not guessed: across 248 real skills, commands and plugin payloads the
# frontmatter block runs a median of 694 characters, p95 4,476, max 15,711 (vercel's
# ai-sdk skill). 65,536 carries 100% of them with 4x headroom over the largest.
#
# CHARACTERS, not bytes — `read(n)` on a text handle counts code points, so on CJK
# frontmatter this reads up to 4x as many bytes. Still bounded, and named for what it
# actually limits: the first version of this constant was called `_FM_READ_BYTES`, which
# promised a guarantee the call does not make.
_FM_READ_CHARS = 64 * 1024

# Rough chars-per-token. schliff uses the same approximation elsewhere; the number
# only needs to be stable and honest about being an estimate.
_CHARS_PER_TOKEN = 4


def _tilde(p: str | Path) -> str:
    s = str(p)
    h = str(HOME)
    return "~" + s[len(h):] if s.startswith(h) else s


def parse_frontmatter(path: Path) -> dict:
    """Flat-key frontmatter parse with block-scalar support. Returns the mapping only.

    Deliberately regex-based rather than pyyaml: pyyaml is absent from a stock
    Python and from schliff's own environment, and schliff parses frontmatter this
    way everywhere else. A silent ImportError here would make findings vanish.

    Returns the mapping and nothing else. It used to return `(mapping, body)` and both
    call sites discarded the body with `fm, _ = ...` — so the body was the only reason a
    whole file had to be in memory. Dropping it is what makes the bounded head read below
    a simplification rather than a truncation.
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(_FM_READ_CHARS)
    except OSError:
        return {}
    m = _FM.match(text)
    if not m:
        return {}

    out: dict[str, object] = {}
    block_key: str | None = None
    block: list[str] = []
    for line in m.group(1).split("\n"):
        if block_key is not None:
            if line.strip() and line[:1] in (" ", "\t"):
                block.append(line.strip())
                continue
            out[block_key] = " ".join(block)
            block_key, block = None, []
        kv = _KV.match(line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val in (">", "|", ">-", "|-"):
            block_key, block = key, []
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if val.lower() in ("true", "false"):
            out[key] = val.lower() == "true"
        else:
            out[key] = val
    if block_key is not None:
        out[block_key] = " ".join(block)
    return out


def invoke_cost_chars(skill_md: Path) -> int:
    """Characters pulled into context when this artifact loads.

    The SKILL.md itself plus any `references/*.md` beside it — not the directory.
    """
    total = 0
    try:
        total += skill_md.stat().st_size
    except OSError:
        return 0
    refs = skill_md.parent / "references"
    if refs.is_dir() and not refs.is_symlink():
        for f in sorted(refs.iterdir()):
            if f.suffix == ".md" and f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    return total


@dataclass
class Artifact:
    name: str
    kind: str          # "skill" | "command"
    source: str        # "user" | "project" | plugin name
    path: str          # tilde-relative
    chars: int         # body + references: charged only when the artifact FIRES
    desc_chars: int    # the description: charged on EVERY turn, for selection
    fm_name: str | None = None

    @property
    def tokens(self) -> int:
        """Invoke cost — what it costs when this artifact actually fires."""
        return self.chars // _CHARS_PER_TOKEN

    @property
    def resident_tokens(self) -> int:
        """Resident cost — the description, carried on every single turn."""
        return self.desc_chars // _CHARS_PER_TOKEN


@dataclass
class Finding:
    kind: str          # "disabled" | "no-skill-md" | "nested" | "duplicate-name"
    subject: str
    detail: str


@dataclass
class Manifest:
    loaded: list[Artifact] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def resident_tokens(self) -> int:
        """What this install charges the context window on every turn."""
        return sum(a.resident_tokens for a in self.loaded)

    @property
    def invoke_tokens(self) -> int:
        """What it would cost if every loaded artifact fired. Not a per-turn cost —
        conflating the two overstates the bill by ~45x on a real install."""
        return sum(a.tokens for a in self.loaded)


def _scan_skill_root(root: Path, prefix: str, source: str, out: Manifest) -> None:
    if not root.is_dir():
        return
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.is_symlink():
            continue
        skill_md = entry / "SKILL.md"
        name = f"{prefix}{entry.name}"
        if not skill_md.is_file():
            out.findings.append(Finding(
                "no-skill-md", name, "directory has no SKILL.md — it never loads"))
            continue
        fm = parse_frontmatter(skill_md)
        if fm.get("disable-model-invocation") is True:
            out.findings.append(Finding(
                "disabled", name, "frontmatter disable-model-invocation: true"))
            continue
        out.loaded.append(Artifact(
            name=name, kind="skill", source=source, path=_tilde(skill_md),
            chars=invoke_cost_chars(skill_md),
            desc_chars=len(str(fm.get("description", ""))),
            fm_name=fm.get("name") if isinstance(fm.get("name"), str) else None,
        ))
        # A SKILL.md nested deeper than one level never registers.
        for sub in entry.rglob("SKILL.md"):
            if sub != skill_md:
                out.findings.append(Finding(
                    "nested", _tilde(sub),
                    "nested below a skill directory — it never registers"))


def _scan_command_root(root: Path, prefix: str, source: str, out: Manifest) -> None:
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).with_suffix("")
        segments = list(rel.parts)
        if segments[-1].startswith("_"):
            continue  # leading underscore is the partial/include convention
        name = prefix + ":".join(segments)
        fm = parse_frontmatter(path)
        if fm.get("disable-model-invocation") is True:
            out.findings.append(Finding(
                "disabled", name, "frontmatter disable-model-invocation: true"))
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        out.loaded.append(Artifact(
            name=name, kind="command", source=source, path=_tilde(path), chars=size,
            desc_chars=len(str(fm.get("description", "")))))


def _enabled_plugins(claude_dir: Path) -> dict[str, bool]:
    """`enabledPlugins` in settings.json is the authority on what is switched on.

    Not `installed_plugins.json`'s scope field: a plugin installed at project scope
    is still registered in an unrelated working directory, and a plugin present on
    disk can be switched off per project. Reading the wrong file inverts the answer.
    """
    try:
        data = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw = data.get("enabledPlugins")
    return raw if isinstance(raw, dict) else {}


def _resolve_plugin_dir(plugins_root: Path, package: str,
                        marketplace: str) -> Path | None:
    """Locate an enabled plugin's payload directory on disk.

    The layout is not `plugins/<package>` — that guess reported thirteen working
    plugins as missing on a live install. It is `plugins/cache/<marketplace>/<package>`,
    sometimes with one extra version or content-hash segment beneath it
    (`cache/openai-codex/codex/1.0.1/`, `cache/vault-sync/vault-sync/9904d91688b1/`),
    and some marketplaces instead expose `plugins/marketplaces/<marketplace>/`.
    Rather than encode which is which, descend one level while the payload is not
    yet visible.
    """
    def has_payload(d: Path) -> bool:
        return (d / "skills").is_dir() or (d / "commands").is_dir()

    candidates = []
    if marketplace:
        candidates.append(plugins_root / "cache" / marketplace / package)
        candidates.append(plugins_root / "marketplaces" / marketplace)
    candidates.append(plugins_root / package)

    for base in candidates:
        if not base.is_dir():
            continue
        if has_payload(base):
            return base
        # One extra level: a version or content-hash segment. Several may coexist —
        # a live install here holds vercel 0.44.0 AND 0.45.1. Taking the first by
        # name silently resolves the STALE one, so take the newest by mtime and let
        # the caller report the rest as superseded.
        subdirs = [d for d in base.iterdir() if d.is_dir() and has_payload(d)]
        if subdirs:
            subdirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            return subdirs[0]
    return None


def _superseded_dirs(plugins_root: Path, package: str, marketplace: str,
                     active: Path) -> list[Path]:
    """Version directories of an enabled plugin that are on disk but not active."""
    base = plugins_root / "cache" / marketplace / package if marketplace else None
    if base is None or not base.is_dir() or active.parent != base:
        return []
    return [d for d in sorted(base.iterdir())
            if d.is_dir() and d != active
            and ((d / "skills").is_dir() or (d / "commands").is_dir())]


def build_manifest(claude_dir: Path | None = None,
                   project_dir: Path | None = None) -> Manifest:
    """Resolve the effective artifact set. Pure disk + config; nothing inferred."""
    claude_dir = Path(claude_dir) if claude_dir else HOME / ".claude"
    out = Manifest()

    _scan_skill_root(claude_dir / "skills", "", "user", out)
    _scan_command_root(claude_dir / "commands", "", "user", out)

    if project_dir:
        proj = Path(project_dir) / ".claude"
        _scan_skill_root(proj / "skills", "", "project", out)
        _scan_command_root(proj / "commands", "", "project", out)

    enabled = _enabled_plugins(claude_dir)
    plugins_root = claude_dir / "plugins"
    seen_packages: dict[str, str] = {}
    for key, on in sorted(enabled.items()):
        if on is not True:
            continue
        package, _, marketplace = key.partition("@")
        pdir = _resolve_plugin_dir(plugins_root, package, marketplace)
        if pdir is None:
            # Enabled in settings but absent on disk — a real, silent no-op.
            out.findings.append(Finding(
                "no-skill-md", key, "enabled in settings.json but not present on disk"))
            continue
        if package in seen_packages:
            out.findings.append(Finding(
                "duplicate-name", package,
                f"enabled twice ({seen_packages[package]} and {key}) — one wins silently"))
            continue
        seen_packages[package] = key
        _scan_skill_root(pdir / "skills", f"{package}:", package, out)
        _scan_command_root(pdir / "commands", f"{package}:", package, out)

    # A name claimed by more than one artifact: only one of them is reachable.
    by_name: dict[str, list[Artifact]] = {}
    for a in out.loaded:
        by_name.setdefault(a.name, []).append(a)
    for name, group in sorted(by_name.items()):
        if len(group) > 1:
            kinds = " + ".join(f"{a.kind} {a.chars} B" for a in group)
            out.findings.append(Finding(
                "duplicate-name", name, f"claimed {len(group)}x ({kinds})"))

    return out


def format_manifest(m: Manifest, top: int = 5) -> str:
    lines: list[str] = []
    lines.append(f"{len(m.loaded)} artifacts loaded · "
                 f"~{m.resident_tokens:,} tok resident every turn "
                 f"(~{m.invoke_tokens:,} tok if all fired)")
    if not m.loaded and not m.findings:
        lines.append("  nothing found — is this a Claude Code install?")
        return "\n".join(lines)

    order = {"disabled": 0, "duplicate-name": 1, "nested": 2, "no-skill-md": 3}
    label = {"disabled": "DISABLED", "duplicate-name": "DUPLICATE NAME",
             "nested": "NESTED", "no-skill-md": "NEVER LOADS"}
    for f in sorted(m.findings, key=lambda f: (order.get(f.kind, 9), f.subject)):
        lines.append(f"  {label.get(f.kind, f.kind):<15} {f.subject}")
        lines.append(f"  {'':<15}   {f.detail}")

    if m.loaded:
        lines.append("")
        lines.append("  TOP COST")
        for a in sorted(m.loaded, key=lambda a: -a.resident_tokens)[:top]:
            lines.append(f"  {'':<15} {a.name:<40} ~{a.resident_tokens:,} tok resident")
    return "\n".join(lines)


def manifest_to_dict(m: Manifest) -> dict:
    return {
        "loaded_count": len(m.loaded),
        "resident_tokens": m.resident_tokens,
        "invoke_tokens": m.invoke_tokens,
        "artifacts": [
            {"name": a.name, "kind": a.kind, "source": a.source,
             "path": a.path, "chars": a.chars, "tokens": a.tokens,
             "resident_tokens": a.resident_tokens}
            for a in sorted(m.loaded, key=lambda a: a.name)
        ],
        "findings": [
            {"kind": f.kind, "subject": f.subject, "detail": f.detail}
            for f in sorted(m.findings, key=lambda f: (f.kind, f.subject))
        ],
    }
