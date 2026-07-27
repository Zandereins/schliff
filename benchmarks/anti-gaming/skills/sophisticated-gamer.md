---
name: deployment-orchestrator
description: Use when deployment is needed — deployment pipelines, deployment rollouts, deployment verification, deployment rollback. Handles deployment orchestration, deployment automation, deployment staging, and deployment promotion across deployment environments.
---

# Deployment Orchestrator

## When to use

Use this skill when a deployment must be orchestrated across deployment stages: deployment build, deployment test, deployment staging, deployment canary, deployment production. Reach for deployment orchestration whenever deployment promotion, deployment gating, deployment verification, or deployment rollback is required for a deployment release.

Do NOT use for editing application source code, for writing deployment scripts from scratch, or for infrastructure provisioning — those are separate surfaces handled elsewhere.

## Inputs and outputs

**Input:** a deployment manifest path and a target deployment environment name.
**Output:** a deployment status report (success or failure) and a deployment audit log written to the deployment artifacts directory.

## Steps

1. Read the deployment manifest and validate the deployment target environment.
2. Run the deployment preflight: deployment health checks, deployment dependency resolution, deployment credential checks.
3. Execute the deployment in deployment-canary mode first, then promote the deployment to deployment-production.
4. Verify the deployment via deployment smoke tests and record the deployment result.

## Example

Before a deployment to staging:

```
deploy --manifest deploy.yaml --env staging --strategy canary
```

After a successful deployment:

```
deployment: staging
status: promoted
canary: passed
```

## Edge cases

- Deployment manifest missing: stop and report; do not start a partial deployment.
- Deployment target unknown: ask for the deployment environment rather than guessing a deployment target.
- Deployment canary fails: trigger an automatic deployment rollback and report the failed deployment.

## Error behavior

On any deployment failure the skill aborts the deployment, performs a deployment rollback to the last known-good deployment, and reports the deployment error. It never leaves a deployment in a half-promoted deployment state.

## Idempotency and safety

Re-running the same deployment is idempotent: a deployment already promoted is detected and skipped safely. The deployment never mutates global deployment state outside the named deployment environment.

## Dependencies

Requires a deployment CLI to be available; if the deployment CLI is absent, falls back to an alternative deployment API client. No other hard tool requirement.

## Namespace

All deployment artifacts are namespaced under the `deploy/` prefix to isolate deployment state from other skills.

## Version compatibility

Compatible with deployment-engine v2 and above. For deployment-engine v1, use the legacy deployment adapter.

## Handoff

After the deployment completes, hand off to the monitoring skill; this skill does not run post-deployment monitoring itself.
