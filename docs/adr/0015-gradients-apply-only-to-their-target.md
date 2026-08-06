# ADR 0015: A gradient is applied only to the file it targets

- Status: accepted
- Date: 2026-08-06

## Context

`auto-improve.py` accepts an edit when schliff's composite rises. The composite is produced by
the same rubric `text_gradient.py` inverts to generate the edit, so the loop grades its own
homework. The proposed fix was a train/val split of `eval-suite.json`, imported from
SkillOpt's `consolidate.py:54-90`.

Two earlier drafts of this ADR got the diagnosis wrong, in opposite directions. The first said
a split was enough. The second said the loop *rewrites the exam it is measured against* — and
that is not supported by the code. There is no write path: every writer in the loop targets
`skill_path` alone (`text_gradient.py:845`, `auto-improve.py:424/474/493`), and the only
writer of `eval-suite.json` anywhere under `skills/schliff/scripts/` is `init-skill.py:898`,
driven by `/schliff:init`. `auto-improve.py` mentions `claude -p` in its docstring but makes
no such call.

What the code does support is narrower and sharper. **Eleven** gradients carry
`"target": "eval-suite.json"` — lines 155, 368, 382, 393, 404, 415, 435, 453, 467, 480, 491 —
spanning **three** dimensions: `triggers`, `quality` (`:359-360`, *"targets eval-suite.json,
not SKILL.md"*) and `edges` (`:427`), the last two called together at `:612-613`.

And **`generate_patches` never looks at `target`**. Its filter is
`if g.get("confidence") != "high" or g.get("effort", 2) > EFFORT_SIMPLE: continue` — confidence
and effort only. Two of the eleven already satisfy it: `:480` and `:491`, both `dimension:
edges`, `op: add`, with instructions such as *"Add assertions to all edge cases in
eval-suite.json"*. They produce no patch today **only because `generate_patches` has no branch
for their issue strings** — an accident of handler coverage, documented nowhere as a guard.

So a file-A instruction sits one handler away from being handed to a patcher that only knows
file B (`apply_patches(skill_path, patches)`).

Suite sizes are a separate constraint, and there are three populations. The shipped
`skills/schliff/eval-suite.json` holds 44 `triggers`, 4 `test_cases` and 14 `edge_cases`. A
22/22 split on triggers is meaningful and a 7/7 split on edge cases is workable; a 2/2 split on
test cases is not.

## Decision

**A gradient is only ever applied to the file its `target` names.** `generate_patches` gains a
target check alongside its confidence and effort filter; a gradient aimed at anything other
than the file being patched is passed through as a manual suggestion and never turned into a
patch.

Separately, and on its own merits: a train/val split where the case count supports it, and an
explicit leak flag where it does not — reporting "this comparison carries no information"
instead of a clean win.

## Why

The guard belongs at the filter because that is where the defect is. A policy of the form
"eval-suite gradients are never auto-applied" describes one symptom of a filter that is missing
a dimension; a target check closes the class — for every handler someone adds later, and for
every future gradient that happens to be high-confidence and simple-effort. It is also
smaller: one condition next to two that already exist.

The current safety is an accident. Nothing in the code says "these two must not be patched";
they are inert because nobody wrote the branch that would make them active. Relying on that is
relying on a gap staying open.

The split stands on its own. It raises the signal where enough cases exist, and the leak flag
is what replaces it on a 4-case suite: naming a 2-versus-2 comparison as uninformative is the
honest output, and silently reporting a delta from it is its own defect.

## Rejected

**A "never auto-apply eval-suite gradients" policy.** Fixes the two known instances and leaves
the filter blind. The next gradient with `high`/`simple` and a foreign target is unprotected
again.

**Split only** — the original spec proposal. It defends against overfitting to a fixed set and
says nothing about a gradient reaching the wrong file.

**Rely on the existing behaviour.** The two qualifying gradients already produce nothing.
But they are stopped by a missing handler, not by a rule, and `auto-improve.py:435` (`applied
== 0` → skip) would quietly absorb a patch that matched nothing rather than report a gradient
aimed at the wrong file.

**Drop the suite-measuring dimensions from the gate entirely** — `triggers`, `quality` and
`edges`, all three. They measure the suite rather than the skill, so the reasoning is tempting
— but removing dimensions changes the composite definition, which is precisely the
compatibility break ADR 0011 was designed to avoid. It would also be mislabelling: the
dimensions stay in the published score either way.
