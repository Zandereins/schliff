"""Leaderboard scoring-model epoch versioning (Hydra PR #42 finding C-2 / #5).

v8.0's full-denominator composite is a breaking scale change, so a v7-and-earlier
composite must never co-rank with a v8+ one. These tests lock the epoch helper and
the query-side selection that keeps a single ranking within one comparable scale.

The leaderboard endpoints are standalone serverless files under web/leaderboard/api
(stdlib-only, no relative imports), loaded here directly by path.
"""
import importlib.util
from pathlib import Path

import pytest

_API = Path(__file__).resolve().parents[4] / "web" / "leaderboard" / "api"


def _load(mod_name, filename):
    spec = importlib.util.spec_from_file_location(mod_name, _API / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


submit = _load("lb_submit", "submit.py")
query = _load("lb_query", "query.py")


@pytest.mark.parametrize("version,expected", [
    ("8.0.0", 2), ("8.1.3", 2), ("v8.0", 2), ("10.2.1", 2), ("9.0.0", 2),
    ("7.0.0", 1), ("7.2.0", 1), ("2.1.0", 1), ("6.1.0", 1), ("V7.0.0", 1),
    ("", 1), ("garbage", 1), ("x.y.z", 1),
])
def test_score_model_for(version, expected):
    assert submit._score_model_for(version) == expected
    # The two serverless copies must agree (kept in sync by hand).
    assert query._score_model_for(version) == expected


def test_current_score_model_constants_match():
    assert submit.CURRENT_SCORE_MODEL == query.CURRENT_SCORE_MODEL == 2


def test_resolve_backfills_legacy_rows_from_version():
    entries = [{"version": "7.0.0"}, {"version": "8.0.0"}]
    filtered, active, available = query._resolve_score_model(entries, None)
    # every row got an epoch
    assert all("score_model" in e for e in entries)
    assert available == [2, 1]


def test_resolve_default_picks_latest_epoch_and_excludes_other_scale():
    v7 = {"version": "7.0.0", "composite": 99.0}
    v8 = {"version": "8.0.0", "composite": 41.0}
    filtered, active, available = query._resolve_score_model([v7, v8], None)
    assert active == 2
    assert filtered == [v8]  # the high v7 score does NOT pollute the v8 ranking


def test_resolve_default_never_empty_when_only_legacy_present():
    v7a = {"version": "7.0.0"}
    v7b = {"version": "2.1.0"}
    filtered, active, available = query._resolve_score_model([v7a, v7b], None)
    assert active == 1
    assert len(filtered) == 2  # seed-only data still shows, all comparable


def test_resolve_explicit_request_overrides_default():
    v7 = {"version": "7.0.0"}
    v8 = {"version": "8.0.0"}
    filtered, active, available = query._resolve_score_model([v7, v8], 1)
    assert active == 1
    assert filtered == [v7]


def test_resolve_empty_input_defaults_to_current_model():
    filtered, active, available = query._resolve_score_model([], None)
    assert filtered == [] and active == query.CURRENT_SCORE_MODEL and available == []


def test_submit_entry_dict_would_carry_score_model():
    # The stamped epoch is derived from the submitted version string.
    assert submit._score_model_for("8.0.0") == 2
    assert submit._score_model_for("7.2.0") == 1
