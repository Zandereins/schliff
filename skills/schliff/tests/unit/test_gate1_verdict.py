"""The Gate 1 verdict script decides a pre-registered outcome, so each rule it
applies is pinned here against the spec's own wording."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "gate1_verdict", _REPO / "scripts" / "experiment" / "gate1_verdict.py")
g1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g1)

CUTOFF = datetime(2026, 10, 20, 23, 59, 59, tzinfo=timezone.utc)
URL = "https://github.com/acme/market/pull/7"


def _pr(merged=None, closed=None, url=URL):
    return {"html_url": url, "state": "closed" if closed else "open",
            "created_at": "2026-09-29T18:31:59Z", "merged_at": merged, "closed_at": closed}


def test_the_real_spec_yields_its_urls_and_deadline():
    spec = g1.SPEC.read_text(encoding="utf-8")
    assert g1.submission_urls(spec) == [
        "https://github.com/jeremylongshore/tons-of-skills-marketplace/pull/1588"]
    assert g1.deadline(spec) == CUTOFF


def test_a_second_submission_row_is_read_too():
    spec = ("| D0 (first submission PR opened, UTC) | **2026-09-29** |\n"
            "| First submission PR URL | <https://github.com/a/b/pull/1> |\n"
            "| Second submission PR URL (if any) | <https://github.com/c/d/pull/2> |\n")
    assert g1.submission_urls(spec) == ["https://github.com/a/b/pull/1",
                                        "https://github.com/c/d/pull/2"]


@pytest.mark.parametrize("merged,closed,verdict,status", [
    ("2026-10-20T23:55:00Z", "2026-10-20T23:55:00Z", "GREEN", "merged on time"),
    ("2026-10-20T23:59:59Z", "2026-10-20T23:59:59Z", "GREEN", "merged on time"),
    ("2026-10-21T00:05:00Z", "2026-10-21T00:05:00Z", "RED-DISTRIBUTION", "censored"),
    (None, None, "RED-DISTRIBUTION", "censored"),
    (None, "2026-10-10T00:00:00Z", "RED-DISTRIBUTION", "closed unmerged"),
    (None, "2026-10-22T00:00:00Z", "RED-DISTRIBUTION", "censored"),
])
def test_the_spec_rule(merged, closed, verdict, status):
    """23:55 on D0+21 passes and 00:05 on D0+22 does not (the spec's own example);
    open at the deadline is censored per E-4."""
    result = g1.judge([_pr(merged, closed)], CUTOFF)
    assert result["verdict"] == verdict
    assert status in result["rows"][0][2]
    assert (result["gate2"] == "NOT-REACHED") == (verdict != "GREEN")


def test_green_sets_a0_from_the_earliest_on_time_merge():
    prs = [_pr("2026-10-15T10:00:00Z", "2026-10-15T10:00:00Z"),
           _pr("2026-10-12T09:00:00Z", "2026-10-12T09:00:00Z", url="https://github.com/c/d/pull/2")]
    result = g1.judge(prs, CUTOFF)
    assert result["a0"] == "2026-10-12"
    assert "2026-11-11" in result["gate2"]


@pytest.mark.parametrize("now,marked", [
    (datetime(2026, 10, 20, 23, 59, 59, tzinfo=timezone.utc), False),
    (datetime(2026, 10, 21, 0, 0, 0, tzinfo=timezone.utc), True),
])
def test_only_a_resolved_reading_carries_the_marker(now, marked):
    """The workflow posts only text with the marker; a preview must never pass for the verdict."""
    raw = [_pr()]
    text = g1.render(g1.judge(raw, CUTOFF), CUTOFF, now, raw)
    assert (g1.MARKER in text) is marked


@pytest.mark.parametrize("merged,closed,censored", [
    (None, None, True),
    ("2026-10-21T00:05:00Z", "2026-10-21T00:05:00Z", True),
    (None, "2026-10-10T00:00:00Z", False),
    ("2026-10-20T23:55:00Z", "2026-10-20T23:55:00Z", False),
])
def test_censoring_is_in_the_same_sentence_as_the_label(merged, closed, censored):
    """E-4: an open-at-the-deadline RED is recorded as censored in the same sentence."""
    sentence = g1.outcome_sentence(g1.judge([_pr(merged, closed)], CUTOFF))
    assert ("censored (open, not rejected)" in sentence) is censored
    assert sentence.count(".") >= 1 and sentence.index("Rule outcome") == 0


def test_the_post_never_presents_itself_as_the_reported_verdict():
    """The spec forbids a bare RED or GREEN: the post defers the report to the amendment."""
    raw = [_pr()]
    text = g1.render(g1.judge(raw, CUTOFF), CUTOFF, datetime(2026, 10, 21, tzinfo=timezone.utc), raw)
    assert "not the reported verdict" in text
    assert "1 in-scope channel plus 1 out-of-scope channel" in text
    assert "Mechanical verdict" not in text
