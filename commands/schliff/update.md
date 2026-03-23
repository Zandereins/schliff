---
name: schliff:update
description: >
  Update Schliff to the latest version from GitHub. Pulls latest changes,
  shows changelog diff, and re-installs skills + commands. Supports both
  copy and symlink installations.
---

# /schliff:update

Update Schliff to the latest version.

## Instructions

1. **Find the Schliff repo clone** — check these locations in order:
   - If `~/.claude/skills/schliff` is a symlink, follow it to find the repo root
   - Check `~/schliff/`, `~/Projects/schliff/`, `~/Code/schliff/`
   - Ask the user for the path if not found

2. **Pull latest changes:**
   ```bash
   cd <repo_root>
   git fetch origin main
   git log --oneline HEAD..origin/main  # Show what's new
   git pull origin main
   ```

3. **Show version diff** — compare the CHANGELOG.md before and after pull to highlight new features.

4. **Re-install if using copy mode** (not symlinks):
   ```bash
   bash install.sh
   ```
   If symlink mode is detected (skills dir is a symlink), skip this step — git pull already updated everything.

5. **Verify installation:**
   ```bash
   cd skills/schliff/scripts
   python3 score-skill.py ../SKILL.md --json 2>&1 | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Schliff v5.1 — Score: {d[\"composite_score\"]}/100')"
   ```

6. **Report to user:**
   - Show new version number
   - List new features from CHANGELOG
   - Confirm tests still pass
   - Show current self-score

## Notes

- If the repo is not found, guide the user to clone it first:
  `git clone https://github.com/Zandereins/schliff.git && bash schliff/install.sh`
- Symlink installations auto-update with git pull — no re-install needed
- Always run /schliff:doctor after update to verify all skills still work
