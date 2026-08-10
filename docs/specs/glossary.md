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

A change that alters an exit code without altering any score. The distinction stays useful — it
is what separates "breaking in behaviour" from "breaking in score" — but **no credential finding
is gate-effective any more** (ADR 0019). The credential scan is score-neutral *and* exit-neutral;
the only gate-effective things left in schliff are the `--min-score` threshold and `--regression`.

_Avoid:_ "breaking", "score-affecting" — both blur the distinction the design depends on. Also
avoid calling the credential scan a **gate**: it reports, and the word was what made an
undecidable classification look like it could carry a build.

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

Two distinct proofs that an earlier draft collapsed into one requirement, of which **only the
second still exists**. The engine red path is gone with the gate (ADR 0019): `verify` no longer
exits non-zero on a credential, so the CLI test now proves the opposite — the finding is
displayed *and* the exit code is unchanged. The **wiring proof** survives as a green path: the
Action must annotate and stay green. It still cannot run before release, because `action.yml:63`
installs the engine from PyPI and every self-test job enters via `uses: ./`.

_Avoid:_ "the red-path fixture" as a single item — it names a requirement that is only half
satisfiable at any given time, and the unsatisfiable half passes green for the wrong reason.

## Reported, not gated

The contract every credential surface now holds: the finding is displayed wherever a human or a
machine looks — `score`, `score --json`, `doctor`, `verify`, the Action's annotations — and
changes no exit code anywhere. Unknown stays a third state: a file that could not be read reports
`credentials: null`, never `[]`.

_Avoid:_ "advisory", "soft fail", "warning-only gate" — the first two suggest a severity dial
that does not exist, and the third keeps the word *gate* for something that cannot fail.

## Structurally valid vendor token

A string carrying a known vendor prefix *and* the exact shape that vendor issues — `AKIA` plus
16 base32 characters, `gh[pousr]_` plus 20 or more, `sk-ant-` plus 20 or more. It asserts **form
only**. Whether the token is live, revoked, or invented for a README is not knowable from the
string, and the term must never be read as "real" (ADR 0020). Tokens naming themselves as
stand-ins (`<your-key>`, `sk-ant-EXAMPLE…`, `${VAR}`, `[REDACTED…]`) are excluded by marker word,
which is the one exclusion that never cost a real key.

_Avoid:_ "secret", "API key", "credential" on their own — each asserts authenticity the check
cannot establish. Also avoid "valid" without "structurally": the word did the entire work of the
premise that turned out to be false.
