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

- `imgaudit scan <dockerfile>` — static pass over a Dockerfile, one finding per line
- `imgaudit inspect <image>` — pull the manifest and report the effective user
- `imgaudit policy <file> --profile strict` — apply a named policy profile
- `imgaudit gate <image> --max-severity medium` — CI gate; exits 1 above the ceiling
- `imgaudit diff <a> <b>` — layer-level comparison of two image tags
- `imgaudit report <image> --format sarif` — machine-readable findings for code scanning
- `imgaudit baseline <image>` — record current findings as the accepted baseline

Pin the version in CI: `imgaudit@3.4.0 gate <image> --max-severity medium`.

## Examples

Example 1 — audit a Dockerfile before the first build:

```
$ imgaudit scan Dockerfile
  high    line 1   base image tag is 'latest', not a digest
  medium  line 14  no USER directive; container runs as root
  low     line 22  no HEALTHCHECK defined
```

Example 2 — compare a rebuild against the accepted baseline:

```
$ imgaudit diff app:1.2.0 app:1.3.0
  added    layer 4   apt package 'curl' introduced
  removed  layer 7   setuid bit on /usr/local/bin/entry cleared
```

Severities run high · medium · low. A finding is reported only when the policy it
violates is decidable from the file alone; anything requiring a running container
is reported `deferred` rather than as a violation.

## Workflow

1. `imgaudit scan <dockerfile>` — find the violations before anything is built.
2. `imgaudit policy <file> --profile strict` — see which of them the profile enforces.
3. Fix the Dockerfile, then re-run the scan to confirm the delta.
4. Gate it: `imgaudit gate <image> --max-severity medium` in CI.

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
