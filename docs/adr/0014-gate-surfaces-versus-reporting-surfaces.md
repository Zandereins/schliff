# ADR 0014: Only gate surfaces change exit codes; reporting surfaces never do

- Status: accepted
- Date: 2026-08-06

## Context

ADR 0011 makes credential detection gate-effective. That raised the question of which commands
the gate applies to, and the answer was not the obvious one.

The GitHub Action **does not call `verify`**. It calls `schliff score --json` and implements
its own threshold logic (`action.yml:93-95`), swallowing the exit code with `|| true`; a
comment at `:115` notes only that its bands "stay aligned with `schliff verify`". A hard fail
added to `verify` alone would therefore bypass the most-used CI surface entirely, and the
Action would keep passing files containing live credentials.

`action.yml:22-25` also shows `schliff-version` defaulting to `''` — latest. Action users
receive new behaviour on their next run without changing anything. Pre-commit users are pinned
by `rev:` and are not affected until they bump.

## Decision

Two gate surfaces: `verify` and the GitHub Action. Both exit non-zero on a credential finding.

`score --json` carries the finding as a data field — it is the Action's only data source.

`score`, `doctor`, `compare` and `report` display the finding and **never** change their exit
code.

**The finding carries the vendor and the line number. The matched value never enters the data
structure at all.** Not truncated, not prefixed, not masked at the output site — absent. The
transport is the reason: `action.yml:210` hands the entire score JSON to the comment step as
`RESULT_B64`, so anything in that structure is already in the workflow's step outputs before
any renderer decides what to print. Base64 there is shell safety, not secrecy, and the Action
uses no `::add-mask::` anywhere. Enumerating output sites cannot work when the transport
carries the whole object; keeping the value out of the object binds every site at once,
including CI logs and the PR comment, with no list to maintain.

## Why

The split follows purpose, not convenience. `verify` and the Action exist to gate; changing
their exit code is what they are for. The others exist to report, and a reporting command that
starts exiting non-zero breaks every pipeline that legitimately just wants the number —
including, concretely, `RESULT=$(schliff score …)` inside the very Action being protected.

`doctor` deserves a note: it scans directories of skills that are usually not yours. Turning
red on somebody else's file helps nobody, because you cannot fix it. Display is the right
response there.

This makes the work larger than it sounds, and it needs **two** proofs, not one — an earlier
draft conflated them into a single unmeetable requirement.

- **Before release:** a CLI test that `verify` exits non-zero on a credential fixture. This
  runs against the working tree in the normal suite and proves the detector and the gate.
- **After release:** a fixture in `action-selftest.yml` proving the Action propagates the
  finding. It cannot run earlier: `action.yml:63` installs the engine with `pip install
  schliff` from PyPI and every self-test job enters via `uses: ./`, so a fixture added in the
  F3 PR would exercise 8.10.1 — which has no detector — and pass for the wrong reason. The
  repo already documents this degradation mode in the `old-engine` job
  (`action-selftest.yml:104-124`).

The Action must also **contain the target path** before invoking schliff: it builds
`SKILL_FULL="${GITHUB_WORKSPACE}/${INPUT_SKILL_PATH}"` and validates it with `[ ! -f ]`, which
follows symlinks. See ADR 0016.

## Rejected

**`verify` only.** Leaves the Action unprotected, which is the surface most likely to be in
use. Untenable once the `action.yml` call path was read.

**Add `doctor`.** Red on files the operator cannot edit.

**Every surface, including `score`.** Breaks the Action's own data collection and every script
that reads the score.
