---
name: changelog-updater
description: Use when adding a release entry to CHANGELOG.md, before tagging a version, to keep the changelog consistent with Keep-a-Changelog format.
---

# Changelog Updater

## When to use
Use this when a release is about to be tagged and CHANGELOG.md needs a new version section.
Do NOT use for editing release notes on the GitHub releases page — that is a separate surface.

## Steps
1. Read the current `## [Unreleased]` section.
2. Create a new `## [X.Y.Z] - YYYY-MM-DD` heading below Unreleased.
3. Move entries from Unreleased into the new section, grouped under Added / Changed / Fixed / Removed.
4. Leave an empty Unreleased section for future entries.

## Example
Before:
```
## [Unreleased]
### Fixed
- Crash on empty input
```
After:
```
## [Unreleased]

## [1.4.0] - 2026-05-26
### Fixed
- Crash on empty input
```

## Edge cases
- No Unreleased entries: stop and report; do not create an empty version section.
- Date unknown: ask for the release date rather than guessing.

## Handoff
After updating, hand off to the tagging step; this skill does not run git commands.
