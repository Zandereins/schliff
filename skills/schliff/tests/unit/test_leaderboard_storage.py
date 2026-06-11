"""Leaderboard submission storage: concurrency + atomicity (issue #51 / tmp-01).

The submit endpoint read-modify-writes a JSON file. Two concurrent POSTs must not
last-write-wins clobber each other, and a reader must never observe a torn file.
These tests lock the flock critical section + atomic os.replace added in
fix/leaderboard-submit-race-and-ratelimit-docs.

The leaderboard endpoints are standalone serverless files under web/leaderboard/api
(stdlib-only, no relative imports), loaded here directly by path — storage paths are
redirected to a tmp dir so the real /tmp is never touched.
"""
import importlib.util
import os
import threading
from pathlib import Path

import pytest

_API = Path(__file__).resolve().parents[4] / "web" / "leaderboard" / "api"


def _load_module(mod_name, filename):
    spec = importlib.util.spec_from_file_location(mod_name, _API / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def submit(tmp_path):
    mod = _load_module("lb_submit_storage", "submit.py")
    data_dir = tmp_path / "schliff-leaderboard"
    mod.DATA_DIR = str(data_dir)
    mod.DATA_PATH = str(data_dir / "submissions.json")
    mod.LOCK_PATH = str(data_dir / ".lock")
    # Point the seed at a nonexistent file so each test starts from an empty store.
    mod.SEED_PATH = str(tmp_path / "nonexistent-seed.json")
    return mod


def test_save_then_load_roundtrip(submit):
    submit._save_submissions([{"skill_name": "a"}])
    assert submit._load_submissions() == [{"skill_name": "a"}]


def test_save_leaves_no_temp_file(submit):
    submit._save_submissions([{"skill_name": "a"}])
    leftovers = [p for p in os.listdir(submit.DATA_DIR) if p.endswith(".tmp")]
    assert leftovers == [], f"atomic write left temp files behind: {leftovers}"


def test_concurrent_writes_no_lost_update(submit):
    """25 threads each append one unique entry under the lock. With the flock'd
    read-modify-write critical section every entry must survive; without it,
    last-write-wins would silently drop most of them."""
    n = 25
    barrier = threading.Barrier(n)  # maximize overlap to expose any race

    def worker(i):
        barrier.wait()
        with submit._exclusive_lock():
            entries = submit._load_submissions()
            entries.append({
                "skill_name": f"skill-{i}",
                "repo_url": f"https://github.com/u/r{i}",
            })
            submit._save_submissions(entries)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = submit._load_submissions()
    names = sorted(e["skill_name"] for e in final)
    assert names == sorted(f"skill-{i}" for i in range(n)), "lost update under concurrency"
