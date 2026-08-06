# Glossary

One canonical name per concept, with the synonyms to stop using. Append across sessions;
keep entries alphabetical.

## Finding payload

What a credential finding is allowed to carry: the vendor and the line number, and nothing
else. The matched value never enters the data structure — not truncated, not prefixed, not
masked downstream. The rule lives at the structure because the transport carries the whole
object: `action.yml:210` hands the entire score JSON to the comment step as `RESULT_B64`.

_Avoid:_ "masked", "redacted output", "sanitized finding" — all three imply the value is
present and then hidden, which is the design that cannot be made safe when output sites are
not enumerable.

## Gate-effective

A change that alters an exit code without altering any score. `verify` and the GitHub Action
exit non-zero; the composite, badges, comparisons and every pinned `--min-score` threshold are
bit-identical to before.

_Avoid:_ "breaking", "score-affecting" — both blur the distinction the design depends on. A
gate-effective change is breaking in *behaviour* and neutral in *score*, and collapsing the two
is what made the credential gate look like it needed a major release and a rubric version.

## Gradient target

The file a gradient names in its `target` field, which is not always the file being patched:
eleven gradients in `text_gradient.py` target `eval-suite.json` while `apply_patches` only ever
writes `skill_path`. `generate_patches` filters on confidence and effort and never on target,
so the two are free to diverge.

_Avoid:_ "read-only eval suite" — it names a policy about one file rather than the property
that matters, which is that a gradient and its patcher can disagree about which file is being
edited. Also avoid "holdout" and "validation set" for the split: those describe a *partition*
of the suite, a separate and weaker property. SkillOpt's own names drifted here
(`replay`→`train`, `holdout`→`val`), which is the argument for fixing ours once.

## Raw file

The bytes of the file the user actually named. Distinct from the normalized content that
scorers receive: for every format except `skill.md`, `shared.py:232-241` writes normalized
content to a temp file and reassigns `skill_path` to it, so a scorer's "path" is a temp file
with synthetic frontmatter prepended.

_Avoid:_ "the skill path", "the input file" — after `shared.py:241` both name the temp file, so
neither distinguishes the two things that matter when a finding needs a true line number.

## Red-path proof

Two distinct proofs that an earlier draft collapsed into one requirement. The **engine
red path** — `verify` exits non-zero on a credential fixture — is a CLI test that runs against
the working tree today. The **wiring red path** — the Action propagates the finding and fails
— cannot run before release, because `action.yml:63` installs the engine from PyPI and every
self-test job enters via `uses: ./`.

_Avoid:_ "the red-path fixture" as a single item — it names a requirement that is only half
satisfiable at any given time, and the unsatisfiable half passes green for the wrong reason.

## Structurally valid vendor token

A credential match that carries a known vendor prefix *and* the exact shape that vendor issues
— `AKIA` plus 16 base32 characters, `gh[pousr]_` plus 20 or more, `sk-ant-` plus 20 or more.
Placeholder shapes (`sk-...`, `<your-key>`, `${VAR}`, `[REDACTED…]`) are not tokens and never
produce a finding.

_Avoid:_ "secret", "API key", "credential" on their own — none of them separates a live key
from the example in a setup snippet, and that separation is the entire false-positive defence.
