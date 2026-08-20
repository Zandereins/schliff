#!/usr/bin/env bash
# Collects GitHub traffic + repo stats for the plugin-channel-experiment and
# appends one JSON line per UTC day to docs/experiments/plugin-channel/traffic.jsonl.
#
# Why this exists: GitHub's traffic API (views/clones/referrers/paths) only
# ever returns a rolling 14-day window. Anything older is gone. This script
# is the collector that preserves daily observations before they expire, so
# the experiment has a record to analyze later.
#
# Each line nests the RAW API payloads under named keys rather than derived
# numbers: the analysis method can change later, the observation cannot be
# retaken.
#
# Run it with `make collect-traffic` (or directly) for an ad-hoc observation.
# On a schedule it is driven by .github/workflows/collect-traffic.yml, daily at
# 12:17 and 20:17 UTC — nothing is installed on any machine, no cron job and no
# LaunchAgent. Run by hand only if that workflow is disabled or TRAFFIC_TOKEN is
# unset; the cadence floor is one run every 12 days or the un-snapshotted days
# expire for good — see the "Operating the collector" section of
# docs/specs/2026-08-11-plugin-channel-experiment.md.
#
# Idempotent per day: if the output file already has a line for today's UTC
# date, this run OVERWRITES that line in place instead of appending a
# duplicate. That makes re-running the script safe (e.g. running it twice in
# one day to be sure) — it never produces two observations for the same date.
#
# The one exception is a line carrying "note":"baseline" — a manually seeded
# historical anchor, not output from a prior run of this script. It is never
# matched or replaced by the per-day dedup, even if its date happens to
# coincide with today's run.
#
# Requires: gh (authenticated). Zero other runtime dependencies — gh's `--jq`
# flag uses gh's own embedded JSON query engine, not an external `jq` binary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_FILE="${REPO_ROOT}/docs/experiments/plugin-channel/traffic.jsonl"
REPO_SLUG="Zandereins/schliff"

if ! command -v gh >/dev/null 2>&1; then
  echo "collect-traffic.sh: 'gh' CLI not found on PATH" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "collect-traffic.sh: 'gh' is not authenticated (run 'gh auth login')" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUT_FILE}")"

collected_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
today="$(date -u +%Y-%m-%d)"

views="$(gh api "repos/${REPO_SLUG}/traffic/views")"
clones="$(gh api "repos/${REPO_SLUG}/traffic/clones")"
referrers="$(gh api "repos/${REPO_SLUG}/traffic/popular/referrers")"
paths="$(gh api "repos/${REPO_SLUG}/traffic/popular/paths")"
repo="$(gh api "repos/${REPO_SLUG}" --jq '{stargazers_count, forks_count, subscribers_count}')"

line="$(printf '{"collected_at":"%s","views":%s,"clones":%s,"referrers":%s,"paths":%s,"repo":%s}' \
  "${collected_at}" "${views}" "${clones}" "${referrers}" "${paths}" "${repo}")"

if [ -f "${OUT_FILE}" ]; then
  tmp_file="$(mktemp "${OUT_FILE}.XXXXXX")"
  # The temp file lives beside the output, inside a tracked docs directory.
  # Without this trap an interrupted or failing run strands a `traffic.jsonl.*`
  # file there; `.gitignore` covers the pattern as a second line of defence.
  trap 'rm -f "${tmp_file}"' EXIT
  replaced=0
  while IFS= read -r existing_line || [ -n "${existing_line}" ]; do
    case "${existing_line}" in
      *"\"note\":\"baseline\""*)
        # Never touch the seeded baseline anchor, even same-day.
        printf '%s\n' "${existing_line}" >>"${tmp_file}"
        ;;
      "{\"collected_at\":\"${today}"*)
        printf '%s\n' "${line}" >>"${tmp_file}"
        replaced=1
        ;;
      *)
        printf '%s\n' "${existing_line}" >>"${tmp_file}"
        ;;
    esac
  done <"${OUT_FILE}"
  if [ "${replaced}" -eq 0 ]; then
    printf '%s\n' "${line}" >>"${tmp_file}"
  fi
  mv "${tmp_file}" "${OUT_FILE}"
else
  printf '%s\n' "${line}" >>"${OUT_FILE}"
fi

echo "collect-traffic.sh: recorded observation for ${today} in ${OUT_FILE#"${REPO_ROOT}/"}" >&2
