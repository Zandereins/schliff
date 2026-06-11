"""Pytest configuration for Schliff unit tests."""
import sys
from pathlib import Path

import pytest

# Add scripts directory to path so scoring package is importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def clear_caches():
    from shared import _file_cache
    _file_cache.clear()
    yield
    _file_cache.clear()


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """Run every test in a throwaway cwd.

    `schliff verify` writes its score history to a cwd-relative default path
    (.schliff/history.jsonl). Without this, suite runs that exercise the verify
    CLI poison the real repo history file. Tests that need files use tmp_path or
    __file__-relative fixtures, so an isolated cwd is safe.
    """
    monkeypatch.chdir(tmp_path)
    yield
