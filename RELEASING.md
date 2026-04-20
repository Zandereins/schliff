# Releasing Schliff

## Pre-release Checklist

Run through this list before creating a new tag. Skipping a step has burned us before (see v7.1.1 badge hotfix).

1. **Bump version in `pyproject.toml`** (single source of truth).
2. **Verify `install.sh` VERSION** — it reads `pyproject.toml` dynamically; run `bash install.sh --help` and confirm.
3. **Update `CHANGELOG.md`** — use Keep-a-Changelog format, include date.
4. **Bump README PyPI badge cache-bust** — update `?v=X.Y.Z` query param in the PyPI version badge URL (GitHub camo caches for 3h).
5. **Run full test suite locally:** `pytest -q` — all tests green.
6. **Run build locally:** `python -m build && twine check dist/*`.
7. **Commit on a release branch** (`chore/release-X.Y.Z`), open PR, merge to `main`.
8. **Tag:** `git tag -a vX.Y.Z -m "vX.Y.Z" && git push --tags` — `publish.yml` fires.
9. **Verify PyPI release** — check `pip install schliff==X.Y.Z` works.
10. **Post-release:** close milestone, update memory entries that reference version.

## Dry-run

Use `git tag -a vX.Y.Z-rc1 ...` to test the publish workflow without a real release.

## Secrets / Trusted Publishing

Publishing uses OIDC Trusted Publishing via `pypa/gh-action-pypi-publish`. No API tokens in the repo. If this breaks: check PyPI Trusted Publisher config at https://pypi.org/manage/project/schliff/settings/publishing/.
