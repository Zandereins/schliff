"""Lineage tracking — JSONL session logs + content snapshots.

Storage: ~/.schliff/lineage/{skill_name}/{timestamp}_{session_id}.jsonl
Security: directory created with chmod 700, warns on secret-like content.
"""
from __future__ import annotations

import json
import os
import stat
import time
import uuid
from pathlib import Path
from typing import Optional

from evolve.sanitize import contains_secrets, redact_secrets


class LineageSession:
    """Track an evolution session as JSONL entries."""

    def __init__(self, skill_path: str, lineage_dir: str = "~/.schliff/lineage",
                 no_snapshots: bool = False):
        self.skill_name = Path(skill_path).stem
        self.session_id = uuid.uuid4().hex[:8]
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.skill_path = skill_path
        self.no_snapshots = no_snapshots
        self._entries: list[dict] = []

        # Resolve and create lineage directory with secure permissions
        base_dir = Path(lineage_dir).expanduser()
        self.session_dir = base_dir / self.skill_name

        # Use restrictive umask for all directory creation
        old_umask = os.umask(0o077)
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        finally:
            os.umask(old_umask)

        # Also secure existing directories (may have been created with old umask)
        for d in (base_dir, self.session_dir):
            try:
                os.chmod(str(d), stat.S_IRWXU)
            except OSError as e:
                import sys
                print(f"Warning: Could not set permissions on {d}: {e}", file=sys.stderr)

        self.jsonl_path = self.session_dir / f"{self.timestamp}_{self.session_id}.jsonl"
        self.snapshots_dir = self.session_dir / "snapshots"
        if not no_snapshots:
            old_umask = os.umask(0o077)
            try:
                self.snapshots_dir.mkdir(exist_ok=True)
            finally:
                os.umask(old_umask)

    def log_header(self, base_score: float, target_score: float, budget_tokens: int) -> None:
        self._append({
            "type": "session_header",
            "session_id": self.session_id,
            "skill_name": self.skill_name,
            "skill_path": self.skill_path,
            "base_score": base_score,
            "target_score": target_score,
            "budget_tokens": budget_tokens,
            "timestamp": self.timestamp,
        })

    def log_generation(self, generation: int, score: float, status: str,
                       strategy: str = "none", model: str = "",
                       tokens_used: int = 0, guard_violations: Optional[list[str]] = None) -> None:
        entry = {
            "generation": generation,
            "score": score,
            "status": status,
            "strategy": strategy,
            "tokens_used": tokens_used,
        }
        if model:
            entry["model"] = model
        if guard_violations:
            entry["guard_violations"] = guard_violations
        self._append(entry)

    def save_snapshot(self, generation: int, content: str) -> Optional[str]:
        """Save a content snapshot for an accepted generation.

        Returns snapshot path, or None if snapshots disabled or content contains secrets.
        """
        if self.no_snapshots:
            return None

        # Warn about secrets in content
        secrets_found = contains_secrets(content)
        if secrets_found:
            import sys
            print(
                f"Warning: Content contains secret-like patterns ({', '.join(secrets_found)}). "
                f"Snapshot will be redacted. Use --no-snapshots to skip snapshots entirely.",
                file=sys.stderr,
            )
            content = redact_secrets(content)

        path = self.snapshots_dir / f"{self.session_id}_gen{generation}.md"
        path.write_text(content, encoding="utf-8")
        try:
            os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR)  # 600
        except OSError:
            pass
        return str(path)

    def log_footer(self, final_score: float, delta: float, tokens_total: int,
                   cost_usd: float, stop_reason: str) -> None:
        self._append({
            "type": "session_footer",
            "final_score": final_score,
            "delta": delta,
            "tokens_total": tokens_total,
            "cost_usd": round(cost_usd, 4),
            "stop_reason": stop_reason,
        })

    def _append(self, entry: dict) -> None:
        self._entries.append(entry)
        # Redact any secrets before writing
        line = redact_secrets(json.dumps(entry, ensure_ascii=False))
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Secure the JSONL file (first write creates it)
        if len(self._entries) == 1:
            try:
                os.chmod(str(self.jsonl_path), stat.S_IRUSR | stat.S_IWUSR)  # 600
            except OSError:
                pass

    @property
    def path(self) -> str:
        return str(self.jsonl_path)
