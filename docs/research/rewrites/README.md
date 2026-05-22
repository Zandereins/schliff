# Advisory SKILL.md Rewrites — Failure-Mode Case Studies

These are **advisory, derivative rewrites** produced for the v8.0 Phase-0 failure-mode study
(`docs/research/2026-04-28-skill-failure-modes.md`). Each fixes the highest-severity
beyond-linter findings the 10-council pass identified, while preserving the original skill's
legitimate function (anti-overcorrection constraint).

**The originals are untouched.** These files live here as case studies only — they are not
installed, not redistributed in place, and not a claim of authorship.

| Rewrite | Source | License | Findings fixed |
|---|---|---|---|
| `02-canvas-design.SKILL.md` | Anthropic `canvas-design` | Apache-2.0 (see source `LICENSE.txt`) | `#fabricated-context` (safety), `#vague-success-criteria`, `#instructed-redundancy`, `#self-inconsistent-standard`, `#unstated-assumption` |
| `03-brand-guidelines.SKILL.md` | Anthropic `brand-guidelines` | Apache-2.0 (see source `LICENSE.txt`) | `#capability-overclaim` / `#desc-body-mismatch` (Cluster A anchor), `#unstated-precondition`, `#vague-success-criteria` |
| `09-linux-ops-cheatsheet.SKILL.md` | community `luofengmacheng/algorithms` | unspecified upstream — treat as reference only | `#unguarded-destructive` (safety), `#name-content-mismatch`, `#no-trigger`, `#missing-procedure`, copy-run hazards |

Selection rationale (Safety-Triade): these three demonstrate fixes for the three heaviest
beyond-linter findings and span the most taxonomy ground per unit effort —
`#fabricated-context` (the orthogonal axis that promoted Cluster F), `#capability-overclaim`
(the sole clean anchor of Cluster A), and `#unguarded-destructive` (the corpus's
highest-blast-radius failure). Skills 08 (stub → authoring from scratch, not a fix) and 10
(reclassify, not repair) were deliberately excluded per the council verdicts.

Per-rewrite changelogs, deliberately-kept notes, and self-checks are recorded in the
session synthesis.

## Validator verdict (Wave 2 — adversarial pentester + eval-expert pass)

| Skill | Findings fixed | Overcorrection | New defects | Frontmatter | Overall |
|---|---|---|---|---|---|
| 02 canvas-design | PASS | PASS | PASS | PASS | **PASS** |
| 03 brand-guidelines | PASS | PASS | PASS-with-nits | PASS | **PASS** (nit patched) |
| 09 linux-ops-cheatsheet | PASS | PASS | PASS | PASS | **PASS** |

- All three verified genuinely better than their originals, with no gutting of legitimate function and no new beyond-linter defects.
- **Skill 09 safety audit passed:** no destructive command left unguarded; the safe-path additions are technically correct (REISUB `s→u→b` ordering + sync-wait, timestamped `cp -a` GRUB backups, correct GRUB2 `grub2-mkconfig` path vs Legacy hand-edit).
- **03 nit (patched):** the original luminance rule presented a flat `0.5` cutoff with WCAG-formula authority it didn't have — softened to a contrast-ratio-preferred rule with the `0.5`-is-not-WCAG-accurate caveat, removing a mild false-precision (`#confident-but-unsourced`) artifact.

