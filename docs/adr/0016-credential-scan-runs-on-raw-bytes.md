# ADR 0016: The credential scan runs always-on, on the raw bytes of the real file

- Status: accepted
- Date: 2026-08-06

## Context

Two facts about the current scoring path decided where this check can live.

**The security dimension is opt-in — for most formats.** `shared.py:250` skips it unless
`include_security` is set. Placing credential detection inside `score_security` would mean it
never runs in a plain `schliff score --json` — which is exactly the call the GitHub Action
makes (`action.yml:93`), silently defeating ADR 0014.

The exception matters: `shared.py:224-228` returns early for `system_prompt` and never
consults `include_security` at all, while `registry.py:29` lists `security` in that format's
scorer set at weight 0.15. For system prompts the dimension is therefore **always-on and
inside the composite**. So the naive placement fails in both directions at once — invisible
for the `AGENTS.md` family, and score-moving for system prompts.

**Scorers do not see the user's file.** `shared.py:232-241` normalizes every format except
`skill.md`, writes the result to a temp file, and reassigns `skill_path = tmp_path` with the
comment *"scorers now see normalized content"*. For `AGENTS.md`, `CLAUDE.md` and
`.cursorrules` the scorer therefore reads a temp file with synthetic frontmatter prepended.
The comment block at `:212-220` records that this seam already caused two real scoring bugs —
issue #168 and a 4.7–5.5 point inflation on frontmatter-less files.

SkillOpt's own fix history is dominated by one class: `redact before clipping`,
`measure refusal length after markdown stripping`, `strip refusal markers before bounding the
head`, `detect markdown-formatted refusals`, `compare dispatched store against the normalized
config value`, `share one char-bound parser between miner and validator`. Six commits, one
lesson: detection run over transformed text misses.

## Decision

Credential detection is its own always-on check, independent of the security dimension. It
reads the **raw bytes of the file the user named**, before `normalize_content` and before the
temp file exists.

**Containment is enforced at the trust boundary, which is the Action — not in the library.**
Before invoking schliff, the Action verifies that **every path it hands to schliff** resolves
inside `realpath("$GITHUB_WORKSPACE")`, and aborts otherwise. That is `$SKILL_FULL` *and*
`$EVAL_PATH` — the latter is built at `action.yml:90` and passed at `:93` today with neither a
`[ -f ]` test nor a resolve check. `read_skill_safe` keeps its documented symlink-following
behaviour unchanged.

**Second named limit:** even with both Action paths contained, `shared.py:171-177`
auto-discovers `skill_dir/eval-suite.json` and reads it with no containment guard. Inside a
contained skill directory that is reachable only via a symlinked `eval-suite.json` sitting
next to the skill file. Closing it belongs to the eval-suite loading path, not to this ADR,
and it is recorded here so the gap is not mistaken for covered.

No `--repo-root` flag ships.

**Named limit:** hand-rolled CI that calls `schliff verify` directly on a fork pull request,
without the Action, does not get this containment. That is a real gap and it is stated here
rather than papered over.

## Why

Three reasons, and the third is why this is the one place the risk was not worth taking.

**Detect before you transform.** This is SkillOpt's most-repeated correction. Searching
transformed text means searching something the user never wrote.

**Line numbers must be true.** A finding reported against the temp file points at a line
number shifted by the injected frontmatter. A security finding at the wrong position is worse
than none — it sends the reader to the wrong line and costs trust on the first encounter.

**This seam is empirically fragile here.** It has already corrupted schliff's own scores twice,
by the repo's own record. Hanging a hard-fail gate on it is the specific gamble to decline.

Consistency with the other scorers is not a virtue in this case. The others *assess structure*;
this one *finds a fact*.

**On containment.** A raw read of an attacker-nameable path in CI is an out-of-repo oracle,
and a credential detector is a strictly stronger one than a score: it answers *"is there a key
at this path"* about the runner's filesystem. `action.yml:78-79` validates the target with
`[ ! -f "$SKILL_FULL" ]`, which dereferences symlinks, and `read_skill_safe` follows them
deliberately (`shared.py:86-90`) — for good reasons that have nothing to do with CI: dotfile
managers, `claude --worktree`, shared `~/.claude/skills` layouts. schliff already defends this
exact class elsewhere: `command_resolution.py:76-81` guards every manifest read with
`_contained`, commented as preventing *"an out-of-repo content/existence oracle when the check
runs on an attacker's repo in CI"*.

The oracle requires both an attacker-controlled path and attacker-visible output. In the
Action both hold; locally neither does — you scan your own files and read your own output. So
the guard belongs where the trust actually changes, and there it costs a `realpath` comparison
in shell before the process starts. Putting it in the library would either break the symlink
support that local users depend on, or need a root that local invocation has no way to define.

## Rejected

**Inside `score_security`.** Inherits the opt-in gate, so it never runs by default and ADR 0014
becomes a no-op.

**Inside `score_security`, with the dimension forced always-on.** Changes default behaviour and
the composite for everyone — the break ADR 0011 was built to avoid.

**Own check, but over normalized content.** Buys alignment with the other scorers and pays for
it with wrong line numbers and exposure to the seam that has already failed twice.

**Reject symlinks outright for the scan.** Closes the oracle, and breaks stow, chezmoi and
`claude --worktree` users locally — where no oracle exists in the first place.

**Containment in the library, behind a `--repo-root` flag.** Would also cover hand-rolled CI.
Rejected because a security control that only works when the operator knows to switch it on is
the same failure shape as the opt-out flag ADR 0011 declined, with the sign reversed: anyone
who has not heard of the flag is unprotected and has no way to notice.
