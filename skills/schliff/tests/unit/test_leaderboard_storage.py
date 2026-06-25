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


# --- homograph / invisible-char identity defense (LB-2) -----------------------
import unicodedata  # noqa: E402


@pytest.mark.parametrize("cp", [
    0xE0001,   # Unicode Tag char (category Cf) — escaped the old enumerated denylist
    0x115F, 0x1160, 0x3164, 0xFFA0,  # blank-rendering Hangul fillers (category Lo)
    0x180E,    # Mongolian vowel separator
    0x200B,    # ZWSP (was in the old list — must still reject)
    0x202E,    # RLO bidi override
    0x034F,    # combining grapheme joiner (Mn) — invisible, look-identical (council)
    0x2028, 0x2029,  # LINE / PARAGRAPH separator (Zl/Zp) — newline-class (council)
    0x09, 0x0A, 0x0D,  # TAB/CR/LF — a single-line identity field rejects these now
])
def test_has_unsafe_chars_rejects_invisible_and_homograph(submit, cp):
    s = unicodedata.normalize("NFKC", "ok" + chr(cp) + "name")
    assert submit._has_unsafe_chars(s) is True


@pytest.mark.parametrize("name", [
    "my-skill", "Code Reviewer", "skill_v2.1", "café-linter",
    "日本語スキル", "skill 🚀", "a.b-c_d",
])
def test_has_unsafe_chars_allows_legit_identity_names(submit, name):
    assert submit._has_unsafe_chars(unicodedata.normalize("NFKC", name)) is False


# --- reserved-identity gate on the live /tmp (cfg=None) path (LB-3) ------------
import io  # noqa: E402
import json as _json  # noqa: E402


def _drive_post(submit_mod, body):
    """Drive the real do_POST handler over the /tmp path (cfg=None, set by the
    `submit` fixture which leaves KV env unset). Captures the JSON response."""
    raw = _json.dumps(body).encode("utf-8")
    captured = {}

    class _H(submit_mod.handler):
        def __init__(self):  # skip BaseHTTPRequestHandler socket setup
            self.rfile = io.BytesIO(raw)
            self.headers = {"Content-Length": str(len(raw))}
            self.wfile = io.BytesIO()

        def _send_json(self, status, payload):
            captured["status"] = status
            captured["payload"] = payload

    _H().do_POST()
    return captured


def _full_body(skill, repo):
    return {"skill_name": skill, "repo_url": repo, "format": "SKILL.md",
            "composite": 90, "grade": "A",
            "dimensions": {k: 90 for k in submit_module_required()},
            "version": "8.1.0"}


def submit_module_required():
    mod = _load_module("lb_submit_req", "submit.py")
    return mod.REQUIRED_DIMENSIONS


@pytest.mark.parametrize("repo", [
    "https://github.com/Zandereins/schliff",
    "https://github.com/zandereins/schliff/",
    "https://github.com/Zandereins/schliff.git",
])
def test_do_post_rejects_reserved_identity_on_tmp_path(submit, repo):
    res = _drive_post(submit, _full_body("schliff", repo))
    assert res["status"] == 403
    # The reserved gate returns before any /tmp write.
    assert not os.path.exists(submit.DATA_PATH)


def test_do_post_allows_non_reserved_on_tmp_path(submit):
    res = _drive_post(submit, _full_body("schliff", "https://github.com/someone/fork"))
    assert res["status"] == 200
    assert res["payload"]["ok"] is True
    stored = submit._load_submissions()
    assert [e["skill_name"] for e in stored] == ["schliff"]
