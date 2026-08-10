# ADR 0013: Detection and redaction keep separate pattern sets

- Status: accepted
- Date: 2026-08-06

## Context

Two places in schliff match secret-shaped strings, and the obvious economy is to share one
pattern set between them. They have opposite error costs:

| | False positive | False negative |
| --- | --- | --- |
| **Redaction** (`evolve/sanitize.py`, before an outbound LLM call) | harmless — something that was not a secret gets masked in a prompt | the secret reaches the provider |
| **Detection** (the credential gate) | breaks a third party's CI | a leak is missed |

Redaction wants to be aggressive. Detection wants to be precise. One shared set can only be
one of the two.

The corpus decides the rest. schliff scores **instruction files**, not source trees, and
instruction files legitimately carry git SHAs, UUIDs, base64 fragments and hashes. A generic
"name looks secret-ish and value has high entropy" rule over that corpus is a false-positive
machine, and under ADR 0011 a false positive turns somebody's build red.

## Decision

Two sets, in two files, each with a docstring naming its error-cost direction.

Detection carries vendor prefixes with structural validation only. Redaction additionally
carries the generic rules — the assignment-name heuristic at `sanitize.py:41`, which already
subsumes `Password=` via its `password`/`passwd` alternation, plus the ODBC `Pwd=` spelling it
does not yet cover.

`Password=` and `Pwd=` belong to redaction alone. The audit spec had assigned them to
detection; that was wrong. A later draft then listed `Password=` as something redaction still
had to gain, which was also wrong — it is already there.

## Why

The asymmetry is not a detail to be smoothed over — it is the whole reason the two call sites
exist. Encoding it as two files with two stated purposes makes the next pattern addition
self-directing: whoever adds a rule reads the docstring and knows which side it belongs on.

If `Pwd=` is adopted for redaction, carry SkillOpt's distinction with it: their pattern
separates the ODBC `Pwd=` from the conventional all-caps `PWD` working-directory variable
(`staging.py:144-150`).

**ReDoS safety is proven by timing, not by the static heuristic.** An earlier draft required
every adopted pattern to pass `validate_regex_complexity` (`shared.py:308`). That rule was
wrong twice over. The validator's only production call sites are
`runtime-evaluator.py:123` and `scoring/runtime.py:164`, both on assertion patterns supplied
by an eval suite — it is a guard against *untrusted* regexes, not an authoring standard for
first-party ones. And run over the 16 live `_SECRET_PATTERNS`, it fails one that already
ships: `sanitize.py:24` (the private-key pattern) trips the nested-quantifier heuristic on
`\s+(RSA\s+)?`. A rule that bars working production code to satisfy a heuristic has the
causality backwards.

First-party patterns in either set are therefore guarded by a **ReDoS timing test in the
suite**: a pathological input of defined length must complete within a wall-clock bound. That
measures the property that matters — catastrophic backtracking — instead of a textual
resemblance to it, and it cannot produce a heuristic false positive. See
`feedback_redos_untrusted_regex`: verify with a warm, equal-size timing discriminator.

`validate_regex_complexity` keeps its existing job on eval-suite regexes, unchanged.

SkillOpt's `_SECRET_VALUE` is a concatenated alternation; it is a reference, not something to
paste, and would have to earn its place through the timing test like anything else.

## Rejected

**One aggressive shared set.** Detection inherits the generic rules and the false positives
with them.

**One precise shared set.** Redaction loses generic coverage and starts leaking values it used
to mask — a regression in the direction where the cost is highest.

**One set with a "high-precision" subset marker.** A convention inside a shared file drifts on
the first addition by someone who did not read it. Two files with two docstrings hold longer.
