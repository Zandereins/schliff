# Structure score reproducibility (#10) — content-only model (A′)

- Status: implemented (TDD, 1422 tests green, golden rebaselined + documented)
- Audit finding: #10 (pre-launch audit 2026-07-22)
- Branch: `fix/prelaunch-10-structure-reproducibility`

## Goal

Make the `structure` dimension score a **pure function of the file's bytes**, so
the same SKILL.md / AGENTS.md scores identically whether it is linted locally (in
its real directory) or scored in isolation (playground / badge / a pasted file).
Eliminate the reproduced local-vs-badge gap.

## Context

`structure` currently depends on the file's **on-disk neighborhood**, not just
its content. Reproduced (`scratchpad/repro_10.py`): the same 250-line SKILL.md
scores **95 in its real directory vs 80 in a bare mkdtemp** — Δ15 for identical
bytes. The badge/playground score files in isolation; the author lints locally,
so the public badge disagrees with the author's own linter. For a tool whose
pitch is "deterministic scoring," that is a credibility gap, worst on AGENTS.md
where `structure` carries weight **0.4** (→ 6-point composite swing).

Two on-disk-dependent components inside the 0–100 `structure` sum
(`skills/schliff/scripts/scoring/structure.py`):

1. **Progressive disclosure (`:141`)** — `(skill_dir/"references").is_dir() or len(lines) <= 200` → +15 else +5. On-disk dir check.
2. **Referenced-files-resolve (`:154-167`)** — declared `references|scripts|templates/` paths credited +10 only if they resolve on disk via `_ref_resolves`, else +5. On-disk existence check.

Δ15 = 10 (progressive disclosure) + 5 (ref resolution).

### Why not the alternatives

- **Option C (keep on-disk, relabel the badge as "content-only")** — rejected: the
  badge still would not match the local score for the same file. It *is* the bug.
- **Option B (drop both components, redistribute weight)** — loses the
  progressive-disclosure signal entirely and shifts the score scale the most.
- **Naive content-only (Option A)** — rejected after a Fable-5 adversarial review
  (verified against code): making "declared refs → +10 always" and "any ref
  mention → +15 disclosure" shipped a **one-token, +6-composite exploit to the
  live badge/leaderboard** (a single `references/x.md` string in a >200-line file),
  scored dangling refs *higher* than today (+10 vs +5), and turned the unanchored
  `_RE_REFS` (which misfires on URLs, build commands, and `references/..`) into
  unconditional credit. It also left `missing_refs` firing on 100% of refs in
  isolation, feeding `text_gradient.py`/`doctor.py` garbage "create the missing
  file" gradients.

**Option A′** (this spec) delivers the same byte-purity while closing those holes.

## Requirements

- **R1** — `structure` score is a pure function of content bytes. Same bytes →
  identical score in every context. Hard gate: a reproducibility test (the inverse
  of `repro_10.py`) asserting score-with-siblings == score-without-siblings.
- **R2** — progressive disclosure credited from *content* (the skill links external
  detail), not from an on-disk `references/` dir.
- **R3** — the referenced-files component credited from *content* (declared refs),
  never from on-disk existence.
- **R4** — dangling-ref / missing-file detection is **preserved as a non-scoring
  lint issue**, but emitted only when absence is **provable** from a real on-disk
  location (a `references/` dir or a `.claude-plugin`/`.git` ancestor). In an
  isolated context (mkdtemp / normalized temp copy) no `missing_refs` is claimed,
  so the *report* is honest too and `text_gradient`/`doctor` do not emit "create
  the missing file" gradients against files a paste-context cannot see.
- **R5** — anti-gaming: no single-token full credit; cap ref-stuffing; reject
  traversal tokens. (The systematic composite anti-gaming gate is B4, separate.)
- **R6** — golden rebaseline documented; ordering (good > medium > bad) and the
  self-score bands hold; field blast radius quantified.

## Technical decisions

### Component 1 — Progressive disclosure (`structure.py:141`)

Replace the on-disk `references/` dir check with a content **disclosure signal**
and a 3-tier score:

```python
disclosure = _disclosure_refs(content)     # see below
if len(lines) <= 200 or len(disclosure) >= 2:
    score += 15
elif len(disclosure) == 1:
    score += 10
    issues.append("thin_progressive_disclosure")
else:
    score += 5
    issues.append("no_progressive_disclosure")
```

`_disclosure_refs(content)` = union of two byte-verifiable "the skill points the
reader to external detail" forms:

- `_RE_MD_LINK = re.compile(r"\]\(\s*(?!https?:|#)([\w./-]+\.md)\s*\)", re.I)` —
  a markdown link to a **local** `.md` file (`](./x.md)`, `](references/x.md)`;
  not `http(s)`, not an anchor). This is the **dominant real-world disclosure
  pattern** (field-validated below).
- `_RE_REF_PATH = re.compile(r"(?:\]\(|`|\bsee\s+|\bread\s+|\bload\s+)(references/[\w./-]+)", re.I)` —
  a `references/`path in a markdown link, backtick, or see/read/load verb (covers
  non-`.md` reference resources). The anchor keeps bare build-command mentions of
  `scripts/…` from counting as disclosure.

Rationale: a long skill that links external detail is practicing progressive
disclosure *in its content*, verifiable from the bytes alone. `scripts/`/`templates/`
paths no longer count for disclosure (they are code/build mentions, not detail
splitting).

### Component 2 — Referenced files (`structure.py:154-167`)

Remove on-disk existence from the **score**; keep an anti-stuffing / traversal
guard so declaration alone cannot be farmed:

```python
refs = set(_RE_REFS.findall(content))
if not refs:
    score += 5                                   # none declared — neutral
elif any(".." in Path(r).parts for r in refs) or len(refs) > 32:
    score += 5
    issues.append("malformed_or_excessive_refs") # traversal tokens / ref-stuffing
else:
    score += 10                                  # declared, well-formed — content credit
```

The 32-ref cap follows the alias-budget precedent from #124. `_ref_resolves`
stays in the module — used only for the lint issue (Component 3), never the score.

### Component 3 — Honest dangling lint, self-determined (no param threading)

The dangling-ref lint (`missing_refs`) must stay for the local linter but must
never fire falsely in an isolated context. Rather than thread a `refs_verifiable`
flag through `build_scores` / `_call_scorer` (fragile — see the `build_scores`
note below), `structure.py` **determines verifiability itself** from the on-disk
context, following the established `command_resolution.py` doctrine: *claim
absence only when it is provable; otherwise stay silent.*

```python
def _refs_verifiable(skill_dir: Path) -> bool:
    """A reference can only be PROVEN dangling from a real on-disk location.
    Positive evidence of a real skill location: a references/ dir, or a
    .claude-plugin / .git ancestor. A bare mkdtemp (playground/badge) or a
    normalized temp copy (non-skill.md) has none → verification is impossible,
    so we never claim a dangling ref (a false dangling burns the artifact)."""
    if (skill_dir / "references").is_dir():
        return True
    for anc in [skill_dir, *skill_dir.parents]:
        if (anc / ".claude-plugin").is_dir() or (anc / ".git").exists():
            return True
    return False
```

In Component 2's `else` branch (refs present, well-formed → +10):

```python
    score += 10
    if _refs_verifiable(skill_dir):
        missing = sorted(r for r in refs if not _ref_resolves(r, skill_dir))
        if missing:
            issues.append(f"missing_refs: {missing}")
```

The **score is byte-pure regardless** — `_refs_verifiable` gates only whether the
*issue* is emitted, never a point value. No signature change, no caller updates.
This also *fixes* a pre-existing false-positive: local AGENTS.md scoring already
runs through a temp copy (below), so today it emits `missing_refs` for **every**
declared ref; the gate suppresses those.

#### `build_scores` temp-normalization (why the self-determining gate is needed)

`build_scores` (shared.py:221-230) normalizes non-`skill.md` formats
(AGENTS.md/CLAUDE.md/.cursorrules) into a `NamedTemporaryFile` and scores *that*.
So for AGENTS.md — the flagship, structure weight 0.4 — the on-disk checks
**always** fail, even locally. Two consequences:

- The reproducibility gap this spec reproduces is a **skill.md** phenomenon
  (real path vs mkdtemp); AGENTS.md is already temp-scored in every context.
- A′ is a **bigger win for AGENTS.md than framed**: the normalized temp preserves
  the *content* (disclosure links + ref declarations), so a long AGENTS.md that
  links references now earns +15/+10 from content — credit it currently cannot
  get because the temp has no siblings. This corrects a systematic under-crediting,
  not just a reproducibility gap.

### Consumer alignment

- `text_gradient.py:131` (missing-refs gradient) fires only on the now-verified
  `missing_refs` issue (never emitted in isolated/temp contexts → no garbage
  create-gradients).
- `text_gradient.py:92` instruction updated: "…extract detail into `references/`
  files **and link them from SKILL.md**" (linking is what now earns the credit).
- `doctor.py:87` unchanged (consumes `no_progressive_disclosure`;
  `thin_progressive_disclosure` is a new, neutral issue).

## Field validation (115 real installed skills)

`scratchpad/validate_aprime.py` compares the current vs A′-v2 structure score
across every installed SKILL.md under `~/.claude/plugins/cache` + `~/.claude/skills`
(the two changed components isolated; the rest of `structure` is unchanged, so
component-delta == score-delta):

- **11/115 changed, mean |Δ| = 0.6.** Tiny footprint.
- **2 drops (−10)** — both are the *same* skill (`vercel/workflow`, two cached
  copies): it ships a `references/` dir it **never links in prose** (0 links, 0
  ref paths). Under byte-purity an unlinked reference dir is invisible to the
  reader, so −10 is a correct tightening, not a false positive.
- **1 gain (+10)** — `subagent-driven-development` links 3 flat-sibling `.md`
  files but has no `references/` dir; the old on-disk check missed its disclosure,
  A′-v2 credits it correctly.
- **Fable's `references/`-anchored regex was refuted here**: it false-penalized
  `nextjs` (435 lines, textbook disclosure via `See [x.md](./x.md)` links whose
  targets omit the `references/` prefix) by −10. The broadened `_RE_MD_LINK`
  (any local `.md` link) fixes it. This is the "green fixtures ≠ field-ready"
  lesson — Fable validated on one file (schliff's own, which happens to use
  `references/…` paths).

## Golden rebaseline

Golden fixtures (`test_golden.py`) are scored in `tmp_path` (no siblings):

- `GOOD_SKILL` declares `scripts/score-skill.py` → ref component +5 (5→10);
  progressive disclosure unchanged (≤200 lines). Structure +5; bands `>=80` and
  composite `30-42` expected to hold.
- `MEDIUM_SKILL` / `BAD_SKILL` declare no matching paths → unchanged.
- Self-score tests run at the **real** path → schliff's own SKILL.md stays 100
  (240 lines, links ≥2 references) and, crucially, now also scores 100 in
  isolation — the reproducibility win.

Recompute the exact fixture scores during implementation and rebaseline any band
that moves with a documented value. Ordering (good > medium > bad) and the
reproducibility test are hard gates.

## Open questions (resolved)

- **`vercel/workflow` −10** (dead `references/` dir; discloses via a
  `node_modules/**/*.mdx` glob) → **accept**. Byte-purity cannot credit an
  unlinked on-disk dir; the node_modules-glob pattern is rare/exotic and out of
  scope for the reproducible structural signal.
- **≥2 threshold docks legit single-reference long skills to +10 (thin)** (e.g.
  `skill-creator`, one reference) → **accept**. The anti-gaming benefit (halving
  the single-link exploit) outweighs a rare −5, and the `thin` tier softens it.

## Testing

- **Reproducibility (R1):** same bytes scored with vs without a `references/`
  sibling → identical structure score (inverse of `repro_10.py`).
- **Disclosure signal:** `](./detail.md)` link → counts; `scripts/build` build
  command → does not; a URL containing `scripts/…` → does not; `references/..`
  → `malformed_or_excessive_refs`.
- **Issue context (R4):** a dangling ref in a bare mkdtemp (no `references/` dir,
  no `.git`/`.claude-plugin` ancestor) → **no** `missing_refs`; the same dangling
  ref in a real skill dir (with a `.git` ancestor) → `missing_refs` emitted.
- **Golden:** rebaselined bands + ordering + self-score, all green.
- **Field regressions (optional):** pin `nextjs` (no penalty), `subagent-driven-
  development` (+10), and the `vercel/workflow` dead-dir −10 as named cases.

## Out of scope

- B4 (composite anti-gaming coherence gate) — separate batch.
- Badge manifest via the GitHub tree API at the scored SHA (Fable's follow-up):
  would let the badge run *verifiable* ref resolution deterministically per SHA,
  but adds a network dependency to the badge path. Deferred; separate decision.
