"""Dedicated unit coverage for the episodic memory store (audit finding #1)."""
import importlib
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import episodic_store as es  # noqa: E402


def _isolate(tmp_path, monkeypatch):
    """Point the store at a temp JSONL and clear the module TF-IDF cache."""
    p = tmp_path / "episodes.jsonl"
    monkeypatch.setattr(es, "EPISODES_PATH", p)
    es._tfidf_cache.update({"mtime": 0.0, "filesize": 0, "index": None, "episodes": None})
    return p


def test_store_then_recall_roundtrip(tmp_path, monkeypatch):
    p = _isolate(tmp_path, monkeypatch)
    es.store_episode("skill-a", "trigger_expansion", "keep", 5.0,
                     "Adding synonyms improved trigger accuracy", domain="skill")
    assert p.exists()
    results = es.recall("trigger accuracy", top_k=5)
    assert results and results[0]["relevance"] > 0
    assert results[0]["strategy"] == "trigger_expansion"


def test_persistence_across_fresh_load(tmp_path, monkeypatch):
    """Written episodes survive a cache-less reload (cross-process surrogate)."""
    _isolate(tmp_path, monkeypatch)
    es.store_episode("skill-b", "noise_reduction", "discard", -1.0,
                     "Removing hedges hurt clarity", domain="skill")
    # simulate a second process: drop the in-memory cache, reload from disk
    es._tfidf_cache.update({"mtime": 0.0, "filesize": 0, "index": None, "episodes": None})
    assert es.get_stats()["total"] == 1
    assert es.recall("clarity", top_k=3)


def test_ranking_orders_by_relevance(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    es.store_episode("s1", "trigger_expansion", "keep", 3.0,
                     "trigger keyword overlap synonyms description", domain="skill")
    es.store_episode("s2", "example_addition", "keep", 2.0,
                     "completely unrelated output formatting examples", domain="testing")
    results = es.recall("trigger keyword synonyms", top_k=2)
    assert results[0]["strategy"] == "trigger_expansion"
    assert results[0]["relevance"] >= results[-1]["relevance"]


def test_atomic_rewrite_on_consolidation(tmp_path, monkeypatch):
    """_enforce_size_cap rewrites via temp+rename and preserves recent episodes."""
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr(es, "MAX_EPISODES", 5)
    monkeypatch.setattr(es, "CONSOLIDATION_BATCH", 3)
    for i in range(8):
        es.store_episode(f"s{i}", "strat", "keep", float(i), f"learning number {i}", domain="d")
    es._enforce_size_cap()
    total = es.get_stats()["total"]
    assert total <= 8  # consolidated, not lost
    assert not (tmp_path / "episodes.tmp").exists()  # temp cleaned up by rename


def test_self_test_passes():
    assert es._run_self_test() is True
