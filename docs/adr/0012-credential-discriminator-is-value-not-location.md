# ADR 0012: A credential is identified by its value, not by where it sits

- Status: accepted
- Date: 2026-08-06
- Superseded by ADR 0020 on 2026-08-10: the premise below — *"shape carries all of it"* — is
  refuted by measurement. The decisions in this ADR stand; only their stated reason does not.

## Context

`scoring/security.py` carries two false-positive mitigations, and they work in **opposite
directions** — a distinction an earlier draft of this ADR got wrong.

The **code-block rule is opt-out**: `security.py:215` reads
`if cat_name != "obfuscation" and _in_code_block(...)`, so every category is suppressed inside
a fenced block and `obfuscation` alone is exempt.

The **negation rule is opt-in**: `security.py:220` reads
`if cat_name in _NEGATION_ELIGIBLE and _preceded_by_negation(...)`, and `:48` defines that set
as `{"dangerous_cmd", "overpermission", "boundaries"}` — three of the six categories at
`:29-36`. `injection`, `exfil` and `obfuscation` are all already negation-exempt, by absence
from the set rather than by special case.

The consequence for a new `credential` category: it inherits the code-block suppression
automatically and would be blind exactly where keys live — `export ANTHROPIC_API_KEY=sk-ant-…`
inside a setup snippet. It inherits **no** negation suppression, because it would not be in
`_NEGATION_ELIGIBLE`. So the concern that *"**never** commit your `sk-ant-abc123…` key"*
would be swallowed is unfounded; only the code-block rule needs an explicit exemption.

## Decision

Credential patterns are exempt from the code-block suppression, as `obfuscation` already is,
and are kept out of `_NEGATION_ELIGIBLE` so no negation suppression applies. The detector
scans the whole document.

A finding carries the **vendor and the line number, never any character of the matched
value** — see ADR 0014 for why that rule has to hold at the data-structure level rather than
at each output site.

A finding requires a **structurally valid vendor token**: the vendor prefix plus the exact
shape that vendor issues — `AKIA` followed by 16 base32 characters, `gh[pousr]_` followed by
at least 20, `sk-ant-` followed by at least 20, and so on. Placeholder shapes never fire:
`sk-...`, `sk-xxx`, `<your-key>`, `${VAR}`, `sk-REPLACE_ME`, and anything already carrying a
`[REDACTED…]` marker.

## Why

Location carries no information about whether a token is real; shape carries all of it. Moving
the discriminator from position to value turns the false-positive question from a judgment
call — "is this documentation or a leak?" — into a deterministic one — "is this a placeholder
or a valid token?". Determinism is the property schliff sells, so this is the only form of the
check that belongs in it.

The base rate makes it safe: `AKIA` followed by exactly 16 base32 characters does not occur by
accident in prose. SkillOpt's own patterns have the same property, and additionally carry
`(?!\[REDACTED…\])` lookaheads — the same idea of excluding known-fake values.

## Rejected

**Inherit the code-block suppression.** Systematically skips the most likely location. The
detector would be loudest where risk is lowest.

**Add `credential` to `_NEGATION_ELIGIBLE`.** Would introduce a suppression that does not
apply today, so that *"never commit your `sk-ant-…` key"* stops firing. The key is still in
the file; the sentence around it does not change that.

**Exempt from suppression with no value test.** Every document showing an example goes red.

**Two severities, one for in-block and one for out-of-block matches.** Two severities mean two
gate thresholds and an argument about which one turns the build red. Under a hard-fail gate
(ADR 0011) exactly one class is wanted.
