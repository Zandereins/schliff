"""Leaderboard durable storage + rate-limit via Upstash Redis (issues #51, #52).

The KV path is active only when the Upstash/Vercel-KV env vars are present; absent,
the endpoints use the /tmp fallback (covered by test_leaderboard_storage.py). These
tests exercise the KV logic against an in-memory fake injected at the `_kv_command`
boundary — the REST wire format itself is verified against Upstash docs and live
after provisioning. They also enforce that the helper block stays byte-identical
across the two independently-bundled serverless files.
"""
import importlib.util
import inspect
import json
from pathlib import Path

import pytest

_API = Path(__file__).resolve().parents[4] / "web" / "leaderboard" / "api"


def _load_module(mod_name, filename):
    spec = importlib.util.spec_from_file_location(mod_name, _API / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


submit = _load_module("lb_submit_kv", "submit.py")
query = _load_module("lb_query_kv", "query.py")


class FakeRedis:
    """Minimal in-memory Upstash REST stand-in (HSET / HGETALL / INCR / EXPIRE)."""

    def __init__(self):
        self.hashes = {}
        self.counters = {}
        self.raise_next = False

    def cmd(self, cfg, *args):
        if self.raise_next:
            raise RuntimeError("simulated KV transport error")
        op = str(args[0]).upper()
        if op == "HSET":
            _, key, field, value = args
            bucket = self.hashes.setdefault(key, {})
            is_new = field not in bucket
            bucket[field] = value
            return 1 if is_new else 0
        if op == "HGETALL":
            _, key = args
            flat = []
            for f, v in self.hashes.get(key, {}).items():
                flat.extend([f, v])
            return flat  # REST returns a flat [field, value, ...] array
        if op == "INCR":
            _, key = args
            self.counters[key] = self.counters.get(key, 0) + 1
            return self.counters[key]
        if op == "EXPIRE":
            return 1
        raise AssertionError(f"unhandled command: {op}")


@pytest.fixture
def kv(monkeypatch):
    monkeypatch.setenv("KV_REST_API_URL", "https://fake.upstash.io")
    monkeypatch.setenv("KV_REST_API_TOKEN", "tok")
    fake = FakeRedis()
    monkeypatch.setattr(submit, "_kv_command", fake.cmd)
    monkeypatch.setattr(query, "_kv_command", fake.cmd)
    return fake


def _entry(skill="s", repo="https://github.com/u/r"):
    return {"skill_name": skill, "repo_url": repo, "composite": 90.0, "version": "8.1.0"}


# --- config --------------------------------------------------------------------

def test_kv_config_none_when_unset(monkeypatch):
    for var in ("KV_REST_API_URL", "KV_REST_API_TOKEN",
                "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    assert submit._kv_config() is None


def test_kv_config_reads_both_env_schemes(monkeypatch):
    for var in ("KV_REST_API_URL", "KV_REST_API_TOKEN",
                "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://x.upstash.io/")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "t")
    # trailing slash trimmed
    assert submit._kv_config() == ("https://x.upstash.io", "t")


# --- upsert / dedup ------------------------------------------------------------

def test_upsert_insert_then_update_is_atomic_and_dedups(kv):
    cfg = submit._kv_config()
    assert submit._kv_upsert(cfg, _entry(skill="a")) is False   # newly inserted
    assert submit._kv_upsert(cfg, _entry(skill="a")) is True    # same identity -> update
    # exactly one stored field for that identity
    assert len(kv.hashes[submit.SUBMISSIONS_KEY]) == 1


def test_dedup_field_cross_file_and_value_stable():
    assert submit._dedup_field("r", "s") == query._dedup_field("r", "s")
    assert submit._dedup_field("r", "s") != submit._dedup_field("r", "s2")


# --- query load + seed union ---------------------------------------------------

def test_kv_load_unions_seed_rows_not_in_kv(kv, tmp_path, monkeypatch):
    seed = [_entry(skill="seed1", repo="https://github.com/u/seed1"),
            _entry(skill="shared", repo="https://github.com/u/shared")]
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    monkeypatch.setattr(query, "SEED_PATH", str(seed_file))

    cfg = query._kv_config()
    # KV holds an updated version of "shared" + a fresh "kvonly"
    submit._kv_upsert(cfg, {**_entry(skill="shared", repo="https://github.com/u/shared"),
                            "composite": 11.0})
    submit._kv_upsert(cfg, _entry(skill="kvonly", repo="https://github.com/u/kvonly"))

    loaded = query._kv_load_all(cfg)
    names = sorted(e["skill_name"] for e in loaded)
    assert names == ["kvonly", "seed1", "shared"]  # union, no duplicate "shared"
    shared = next(e for e in loaded if e["skill_name"] == "shared")
    assert shared["composite"] == 11.0  # KV wins over seed on identity conflict


def test_kv_load_empty_returns_only_seed(kv, tmp_path, monkeypatch):
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps([_entry(skill="only-seed")]), encoding="utf-8")
    monkeypatch.setattr(query, "SEED_PATH", str(seed_file))
    loaded = query._kv_load_all(query._kv_config())
    assert [e["skill_name"] for e in loaded] == ["only-seed"]


# --- rate limit ----------------------------------------------------------------

def test_rate_limit_allows_then_blocks(kv):
    cfg = submit._kv_config()
    assert submit._kv_rate_limited(cfg, "rl:test:ip", limit=2, window=60) is False  # 1
    assert submit._kv_rate_limited(cfg, "rl:test:ip", limit=2, window=60) is False  # 2
    assert submit._kv_rate_limited(cfg, "rl:test:ip", limit=2, window=60) is True   # 3 blocked


def test_rate_limit_fail_open_on_kv_error(kv):
    kv.raise_next = True
    # limiter must never block (or raise) when the KV backend errors
    assert submit._kv_rate_limited(submit._kv_config(), "rl:x", limit=1, window=60) is False


# --- cross-file sync guard -----------------------------------------------------

@pytest.mark.parametrize("fn", ["_kv_config", "_kv_command", "_dedup_field",
                                "_client_ip", "_kv_rate_limited"])
def test_shared_kv_helpers_byte_identical_across_files(fn):
    """The two serverless files duplicate this block by hand (Vercel can't share a
    module). Guard against drift between the copies."""
    assert inspect.getsource(getattr(submit, fn)) == inspect.getsource(getattr(query, fn))


def test_submissions_key_matches_across_files():
    assert submit.SUBMISSIONS_KEY == query.SUBMISSIONS_KEY
