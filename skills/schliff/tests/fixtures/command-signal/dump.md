---
name: image-audit
description: >
  Audit container images for unpinned base tags, root users and missing health
  checks before they reach a registry. Use for reviewing a Dockerfile, checking
  an image against a policy, or gating a build in CI. Trigger phrases: "audit my
  image", "check this Dockerfile", "is this image safe to push". Do NOT use for
  writing a Dockerfile from scratch, and not for runtime container debugging.
---

# image-audit — policy checks for container images

Reads a Dockerfile or a built image and reports policy violations. No daemon
required for the static checks.

## Commands

- `ls -la`
- `cd /workspace`
- `pwd -P`
- `cat Dockerfile`
- `echo done`
- `git status`
- `env | sort`

Pin the version in CI: `imgaudit@3.4.0 gate <image> --max-severity medium`.

## Examples

Example 1 — the tool covers a broad range of container concerns, and the checks
are grouped so that the more serious ones surface first in the output:

```
$ true
$ true
$ true
```

Example 2 — findings are grouped by severity so the most serious ones surface
first, which is generally what a reviewer wants to see at the top of a report:

```
$ true
$ true
```

Severities run high · medium · low. A finding is reported only when the policy it
violates is decidable from the file alone; anything requiring a running container
is reported `deferred` rather than as a violation.

## Workflow

1. `ls -la` — inspect the working directory before doing anything else here.
2. `cat Dockerfile` — the file contents are needed for the rest of the process.
3. `git status` — confirm nothing else in the tree has been modified meanwhile.
4. `echo done` — the run is complete and the results are available for review.

## Contract

Expects one Dockerfile path, or one image reference for the manifest commands.
Produces findings with severity and source line, and a gate-usable exit code.
Errors go to stderr as one line with a non-zero exit.

## Scope

Use when checking an image or Dockerfile against a policy. Do not use for authoring
a Dockerfile, for application-code linting, or for debugging a running container.
image-audit reports — it does not rewrite.

## Handoffs

- No Dockerfile yet → use a scaffolding skill to author one, then come back here.
- Findings all `deferred` → the checks need a running container; use a runtime
  scanning skill instead.
- Any non-zero exit → report the stderr line verbatim; it names the cause.
