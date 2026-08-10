# ADR 0020: Shape does not separate a credential from a placeholder

- Status: supersedes ADR 0012
- Date: 2026-08-10

## Context

ADR 0012's `## Why` opens with the sentence the whole design rested on:

> Location carries no information about whether a token is real; shape carries all of it.

The first half is right. The second is false, and it is false in the simplest possible way:
`AKIA1234567890ABCDEF` and `AKIAJ7QRTUVWXY3BCDEF` are structurally identical and both satisfy
every rule ADR 0012 specifies. One belongs in a README, the other is a credential. Nothing in
the shape tells them apart, because a documentation placeholder is written by someone imitating
the shape on purpose.

Measured against `scoring/credentials.py` as it stood on `0751e45`:

| Input | What it is | Gate |
| --- | --- | --- |
| `sk-proj-Ab3d-Kf9LmQ2xR7tYu1VwZ0nBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789abcdef` | **real** OpenAI project key | **silent** |
| `AKIA0000TUVWXY3BCDEF` | **real** AWS key | **silent** |
| `AKIA1234567890ABCDEF` | documentation placeholder | **fires** |
| `ghp_abcdefghijklmnopqrstuvwxyz012345` | documentation placeholder | **fires** |

The same input set, answered the opposite way round from the intent. The placeholder heuristic
— `_PLACEHOLDER_MARKERS` plus a run of four identical characters — was the patch for the gap,
and it fails in both directions at once: it eats a real key containing `0000`, and it passes any
dummy that avoids its marker words.

A field run over this machine's real files sharpens the picture rather than softening it. In 128
instruction files: no findings. In 601 documentation files: 11 findings, **all of them
documentation about credentials**, none of them a real key. The detector's observed behaviour in
the wild is to fire on people writing about secrets.

Re-running it after this ADR was written makes the point better than the numbers do: the file
you are reading is documentation about credentials, and it now contributes seven findings of its
own. Counts reproduced later will therefore exceed the ones above, and for exactly the reason
this ADR gives.

## Decision

**The premise is withdrawn.** Shape establishes that a string *could* be a credential of a given
vendor. It establishes nothing about whether it is one.

ADR 0012's operative decisions are unchanged and stay in force, because none of them depended on
the withdrawn sentence: credential patterns remain exempt from the code-block suppression, stay
out of `_NEGATION_ELIGIBLE`, carry vendor and line only, and still require a vendor prefix plus
that vendor's issued shape before anything is reported at all.

What changes is the calibration, now that ADR 0019 has made a false positive cost a line of
output rather than someone's build:

- **The repeated-run heuristic is removed.** It suppressed real keys — `AKIA0000TUVWXY3BCDEF` is
  a legal AWS key — to catch placeholders that spell themselves with `AAAA`.
- **Marker words stay.** `example`, `your`, `replace`, `redacted` and the rest are the cheapest
  true signal available: a real key does not contain them, and they silence AWS's own published
  `AKIAIOSFODNN7EXAMPLE`, which appears in real instruction files.
- **Hyphens are allowed in the OpenAI body behind a known key prefix** (`sk-proj-`,
  `sk-svcacct-`, `sk-admin-`) and nowhere else. This is the form OpenAI has issued since 2024;
  allowing them after a bare `sk-` would fire on kebab-case prose such as
  `sk-add-credential-scanning-to-verify`, which already broke a third party's build once.
- **No JWT pattern, and no entropy scoring.** ADR 0012's reasoning holds without the gate: the
  jwt.io sample and Supabase's `anon` key are public by design and a service key is
  structurally identical to both.

The term **structurally valid vendor token** keeps its name and loses half its meaning: it
asserts form, never authenticity. `docs/specs/glossary.md` is corrected accordingly.

## Why

The measurement is not a bug report against the patterns; it is a statement about the class. A
placeholder is an imitation of a real key, authored by someone who wants it to look real. Any
test that separates them has to read something other than the string — entropy against a
corpus, a live call to the vendor, a baseline of known-accepted values. Those are what real
secret scanners are, and ADR 0010 declined that apparatus deliberately.

Removing the heuristic is a genuine trade and the evidence for it is thin in both directions:
in the field it suppressed exactly one documentation placeholder, and in the brief it
suppressed exactly one real key. One case each is a coin toss, not a calibration. The
tie-breaker is the cost asymmetry ADR 0019 created — a missed key is the expensive error now,
a noisy line is not — and the same asymmetry that ADR 0013 already established for redaction,
with the sign matching for the first time.

The field number belongs in the record precisely because it is unflattering: every finding this
detector produced on real files was documentation. It is the reason the CHANGELOG documents the
limitation instead of announcing a security feature, and the reason the honest description of
this component is "a report that sometimes helps", not "a scanner".

No further tuning round follows this one. Three passes produced ten findings each, most of them
regressions from the previous pass's fixes; a defect count that does not fall is a design
signal, and the design answer was ADR 0019.

## Rejected

**Leave the patterns as they are.** Minimal change, and it ships a report that answers two of the
four measured cases wrongly — including the direction where a real key goes unseen. The honesty
gap the decision was meant to close would survive, only more quietly.

**Widen to JWTs and generic high-entropy strings.** Maximum recall, and it fires on every
Supabase `anon` key and every published example token. A report people learn to ignore is worth
less than no report.

**Narrow to the unambiguous classes only** — `AKIA`, `gh[pousr]_`, `AIza`. Clean, and it drops
`sk-` entirely: the most common key class in exactly the Claude and OpenAI instruction files
schliff is written for.

**Replace the run heuristic with a run-*count* heuristic** — suppress only when several repeated
runs occur. It separates all five cases in hand (a real key had one run, the placeholder seven).
Rejected because five cases are not a calibration set, and because the previous three passes
were each a plausible refinement of this same heuristic. The pattern of that failure is the
reason to stop refining it, not to refine it once more.
