# SKILL.md at the marketplace tier

Status: implemented in PR #239. Refs #198 (the plugin-channel submission).

## Goal

Submit `skills/schliff/SKILL.md` to `jeremylongshore/tons-of-skills-marketplace` as a Path B
mirror without making it worse for anyone who loads it outside that marketplace.

## Context

The marketplace validator (`scripts/validate-skills-schema.py --marketplace`) rejected the file
with 11 errors (74/100): six frontmatter fields and five body sections were missing. The file
also pinned `uvx schliff@8.8.2` while 8.12.0 was the release, and no test caught it.

## Decisions

- **Body sections are added:** Overview, Prerequisites, Output, Error Handling and Resources.
  `## Contract` is split into Output and Error Handling.
- **Frontmatter follows the Agent Skills spec, not the marketplace.** `license`, `compatibility`
  and `allowed-tools` are added. `author`, `version` and `tags` are not. As top-level keys they
  make the file invalid under Anthropic's `quick_validate.py` ("Unexpected key(s)"). Under
  `metadata:` the marketplace still reports them missing, so the two validators cannot both
  pass. Mirrors with validator errors are listed on that marketplace, so the 3 remaining errors
  do not block the submission.
- **`allowed-tools` pre-approves `uvx schliff *` and the pinned `uvx schliff@<release> *`.** The
  skill runs the first form. The second is the CI example. Other versions still prompt.
- **One test guards every exact pin in SKILL.md.** `test_skill_md_pins_the_current_version`
  covers `@`, `@v`, `==`, `===`, `~=` and extras, `allowed-tools` included. A pin needs a dotted
  version, so the Action's float tag `@v1` is not one.
- **Error Handling describes only what was executed.** A gate result (`verify` below the threshold
  or `--regression`, `check-commands` dangling) exits 1 with the finding on stdout. Other failures
  exit 1 or 2 by command. Relay stdout and stderr on any non-zero exit.

## Declined

- **Guarding the README pins:** README:58 dates its numbers to the release they were measured on.
- **Checking the pin against PyPI:** a network read in a unit test. The risk window lies between
  the release-PR merge and `release: published`.

## Learned

- Five review rounds found 10, 9, 10, 10 and 9 findings, and the count never fell. Round 4 asked
  for a tighter `allowed-tools` for security reasons. Round 5 then found the tighter form
  covered nothing the skill runs. Precise prose about CLI behaviour kept producing new claims to
  check, and removing claims ended the cycle faster than refining them did.
- schliff's own scorer reacts to the wording of the input contract. `expects` and `produces`
  satisfy `composability`, and `the result` trips `clarity`. A placeholder pin
  (`schliff@<version>`) cost 10 composability points.
- `make lint` exits 0 when ruff is missing ("Install ruff"). Run `uvx ruff@0.15.8 check` as CI
  does.
