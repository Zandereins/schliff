# Payments service

Fixture for the Action self-test. It carries a structurally valid AWS access
key ID so the credential scan has something to find — the point of the test is
that finding it does **not** turn the job red (ADR 0019).

The key is invented. It is not a placeholder in the detector's sense either: it
carries no marker word, which is deliberate, because a fixture the detector
skips would leave the self-test green for the wrong reason.

## Setup

Export the deploy credentials before running anything:

```bash
export AWS_ACCESS_KEY_ID=AKIA3XZQ7RBN2WKPLMTV
export AWS_REGION=eu-central-1
```

## Commands

- `make deploy` — ship to staging
- `make rollback` — undo the last deploy

## Conventions

- Never commit a key. This file does, on purpose, and schliff says so without
  failing the build.
