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
        if op == "HEXISTS":
            _, key, field = args
            return 1 if field in self.hashes.get(key, {}) else 0
        if op == "HLEN":
            _, key = args
            return len(self.hashes.get(key, {}))
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


# --- durable-pollution cap (P1 / dos-02 bound) ---------------------------------

def test_upsert_rejects_new_identity_when_full_but_allows_updates(kv, monkeypatch):
    cfg = submit._kv_config()
    monkeypatch.setattr(submit, "MAX_SUBMISSIONS", 2)
    submit._kv_upsert(cfg, _entry(skill="a", repo="https://github.com/u/a"))
    submit._kv_upsert(cfg, _entry(skill="b", repo="https://github.com/u/b"))
    # store now holds MAX_SUBMISSIONS distinct entries -> a brand-new identity is refused
    with pytest.raises(submit.LeaderboardFullError):
        submit._kv_upsert(cfg, _entry(skill="c", repo="https://github.com/u/c"))
    # ...but updating an EXISTING identity still works (no lock-out of real users)
    assert submit._kv_upsert(
        cfg, {**_entry(skill="a", repo="https://github.com/u/a"), "composite": 1.0}) is True
    assert len(kv.hashes[submit.SUBMISSIONS_KEY]) == 2  # cap held


# --- cross-file sync guard -----------------------------------------------------

@pytest.mark.parametrize("fn", ["_kv_config", "_kv_command", "_dedup_field",
                                "_client_ip", "_kv_rate_limited",
                                "_canonical_repo_url"])
def test_shared_kv_helpers_byte_identical_across_files(fn):
    """The two serverless files duplicate this block by hand (Vercel can't share a
    module). Guard against drift between the copies."""
    assert inspect.getsource(getattr(submit, fn)) == inspect.getsource(getattr(query, fn))


def test_submissions_key_matches_across_files():
    assert submit.SUBMISSIONS_KEY == query.SUBMISSIONS_KEY


# --- repo_url canonicalization (LB-1) -----------------------------------------
def _valid_body(url):
    return {"skill_name": "x", "repo_url": url, "format": "SKILL.md",
            "composite": 50, "grade": "B",
            "dimensions": {k: 50 for k in submit.REQUIRED_DIMENSIONS},
            "version": "8.1.0"}


@pytest.mark.parametrize("url", [
    "https://github.com/Owner/Repo",
    "https://github.com/owner/repo/",
    "https://github.com/owner/repo/tree/main",
    "https://github.com/owner/repo?x=1",
    "https://github.com/owner/repo#frag",
    "https://github.com/owner/repo.git",
])
def test_validate_canonicalizes_repo_url(url):
    body = _valid_body(url)
    assert submit._validate(body) is None
    assert body["repo_url"] == "https://github.com/owner/repo"


def test_all_spellings_collapse_to_one_dedup_key():
    keys = set()
    for url in ("https://github.com/Owner/Repo", "https://github.com/owner/repo/",
                "https://github.com/owner/repo/tree/main",
                "https://github.com/owner/repo?x=1"):
        body = _valid_body(url)
        assert submit._validate(body) is None
        keys.add(submit._dedup_field(body["repo_url"], body["skill_name"]))
    assert len(keys) == 1


@pytest.mark.parametrize("url", [
    "http://github.com/owner/repo", "https://gitlab.com/o/r",
    "https://github.com/owner", "https://github.com/", 123,
])
def test_validate_rejects_non_canonicalizable_repo_url(url):
    assert submit._validate(_valid_body(url)) is not None


def test_kv_load_dedups_noncanonical_seed_against_canonical_kv(kv, tmp_path, monkeypatch):
    seed = [_entry(skill="shared", repo="https://github.com/U/Shared/")]
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed), encoding="utf-8")
    monkeypatch.setattr(query, "SEED_PATH", str(seed_file))
    cfg = query._kv_config()
    submit._kv_upsert(cfg, {**_entry(skill="shared", repo="https://github.com/u/shared"),
                            "composite": 11.0})
    loaded = query._kv_load_all(cfg)
    assert [e["skill_name"] for e in loaded] == ["shared"]
    assert loaded[0]["composite"] == 11.0


# --- reserved-identity / IDOR (LB-3) ------------------------------------------
def test_upsert_refuses_reserved_identity(kv):
    cfg = submit._kv_config()
    with pytest.raises(submit.ReservedIdentityError):
        submit._kv_upsert(cfg, _entry(skill="schliff", repo="https://github.com/Zandereins/schliff"))
    assert submit.SUBMISSIONS_KEY not in kv.hashes
    for url in ("https://github.com/zandereins/schliff/",
                "https://github.com/Zandereins/schliff/tree/main"):
        with pytest.raises(submit.ReservedIdentityError):
            submit._kv_upsert(cfg, _entry(skill="schliff", repo=url))


def test_upsert_allows_non_reserved_identity(kv):
    cfg = submit._kv_config()
    assert submit._kv_upsert(cfg, _entry(skill="other", repo="https://github.com/Zandereins/schliff")) is False
    assert submit._kv_upsert(cfg, _entry(skill="schliff", repo="https://github.com/someone/schliff")) is False
    assert len(kv.hashes[submit.SUBMISSIONS_KEY]) == 2


def test_is_reserved_identity_matches_canonical_variants():
    assert submit._is_reserved_identity("https://github.com/Zandereins/schliff", "schliff")
    assert submit._is_reserved_identity("https://github.com/zandereins/schliff?x=1", "schliff")
    assert not submit._is_reserved_identity("https://github.com/Zandereins/schliff", "other")
    assert not submit._is_reserved_identity("https://gitlab.com/zandereins/schliff", "schliff")
