"""Tests for evolve.lineage — JSONL session tracking."""
import json
import os
from pathlib import Path

from evolve.lineage import LineageSession


class TestLineageSession:
    def test_creates_directory_structure(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        assert session.session_dir.exists()
        assert session.session_dir.is_dir()

    def test_secure_permissions_on_base_dir(self, tmp_path):
        base = tmp_path / "lineage"
        LineageSession("test.md", str(base))
        mode = os.stat(str(base)).st_mode & 0o777
        assert mode == 0o700, f"Expected 700, got {oct(mode)}"

    def test_secure_permissions_on_session_dir(self, tmp_path):
        base = tmp_path / "lineage"
        session = LineageSession("test.md", str(base))
        mode = os.stat(str(session.session_dir)).st_mode & 0o777
        assert mode == 0o700, f"Expected 700, got {oct(mode)}"

    def test_jsonl_header_written(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        session.log_header(60.0, 85.0, 50000)
        content = session.jsonl_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["type"] == "session_header"
        assert entry["base_score"] == 60.0
        assert entry["target_score"] == 85.0
        assert "session_id" in entry

    def test_jsonl_header_contains_skill_path(self, tmp_path):
        session = LineageSession("/some/path/SKILL.md", str(tmp_path / "lineage"))
        session.log_header(60.0, 85.0, 50000)
        content = session.jsonl_path.read_text()
        entry = json.loads(content.strip())
        assert entry.get("skill_path") == "/some/path/SKILL.md"

    def test_log_generation(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        session.log_generation(1, 65.0, "accepted", strategy="gradient", model="test/model")
        lines = session.jsonl_path.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["generation"] == 1
        assert entry["score"] == 65.0
        assert entry["status"] == "accepted"
        assert entry["model"] == "test/model"

    def test_log_generation_with_guard_violations(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        session.log_generation(2, 50.0, "guard_rejected",
                               guard_violations=["triggers: 70 -> 55"])
        entry = json.loads(session.jsonl_path.read_text().strip())
        assert entry["guard_violations"] == ["triggers: 70 -> 55"]

    def test_save_snapshot(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        path = session.save_snapshot(1, "# Improved\n\nContent here.")
        assert path is not None
        assert Path(path).read_text() == "# Improved\n\nContent here."

    def test_save_snapshot_with_secrets_redacts(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        path = session.save_snapshot(1, "key: sk-ant-api03-secretkeyvalue1234567890")
        content = Path(path).read_text()
        assert "sk-ant-" not in content
        assert "REDACTED" in content

    def test_no_snapshots_flag(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"), no_snapshots=True)
        result = session.save_snapshot(1, "content")
        assert result is None

    def test_jsonl_redacts_secrets(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        session._append({"key": "sk-ant-api03-verylongsecretkey1234567890"})
        content = session.jsonl_path.read_text()
        assert "sk-ant-" not in content
        assert "REDACTED" in content

    def test_log_footer(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        session.log_footer(80.0, 20.0, 5000, 0.05, "target_reached")
        entry = json.loads(session.jsonl_path.read_text().strip())
        assert entry["type"] == "session_footer"
        assert entry["final_score"] == 80.0
        assert entry["stop_reason"] == "target_reached"
        assert entry["cost_usd"] == 0.05

    def test_full_session_flow(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        session.log_header(60.0, 85.0, 50000)
        session.log_generation(0, 60.0, "baseline")
        session.log_generation(1, 68.0, "accepted", strategy="deterministic")
        session.save_snapshot(1, "# Improved content")
        session.log_footer(68.0, 8.0, 0, 0.0, "target_reached")

        lines = session.jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 4
        types = [json.loads(line).get("type") for line in lines]
        assert types[0] == "session_header"
        assert types[-1] == "session_footer"

    def test_path_property(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        assert session.path.endswith(".jsonl")
        assert "test" in session.path

    def test_snapshot_file_permissions(self, tmp_path):
        session = LineageSession("test.md", str(tmp_path / "lineage"))
        path = session.save_snapshot(1, "content")
        if path:
            mode = os.stat(path).st_mode & 0o777
            assert mode == 0o600, f"Expected 600, got {oct(mode)}"
