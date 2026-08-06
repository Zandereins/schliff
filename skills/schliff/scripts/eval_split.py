"""Split an eval suite into a train side and a val side, honestly.

The improvement loop derives its edits from one side and judges them on the
other. When the two are not disjoint, the comparison carries no information
about generalisation — and the caller must say so rather than report a delta
from it. That is what ``leaked`` is for.

Imported from SkillOpt's ``skillopt_sleep/consolidate.py:54-90`` (MIT), whose
``_split`` returns ``holdout_leaked`` for the same reason.

A case opts in by carrying ``"split": "train" | "val" | "test"``. The ``test``
split reaches neither side: it is held back from the loop entirely so it can
still answer a question the loop has not already optimised against.
"""
from __future__ import annotations

# Population keys a suite may carry. Anything else is metadata and is copied
# to both sides unchanged.
_POPULATIONS = ("triggers", "test_cases", "edge_cases")

_TRAIN, _VAL, _TEST = "train", "val", "test"


def split_eval_suite(suite: dict) -> tuple[dict, dict, bool]:
    """Return ``(train_suite, val_suite, leaked)``.

    ``leaked`` is True when the two sides are not disjoint — because the suite
    carries no split labels at all, or because a population has cases on only
    one side. A leaked split is still returned so the loop can run; the caller
    is responsible for not presenting its delta as evidence.
    """
    train: dict = {k: v for k, v in suite.items() if k not in _POPULATIONS}
    val: dict = dict(train)
    leaked = False

    for population in _POPULATIONS:
        cases = suite.get(population)
        if not isinstance(cases, list) or not cases:
            continue

        labelled = [c for c in cases if isinstance(c, dict) and c.get("split")]
        if not labelled:
            # No opt-in: the loop reads and judges the same cases. Runnable,
            # but it proves nothing about generalisation.
            train[population] = list(cases)
            val[population] = list(cases)
            leaked = True
            continue

        train_cases = [c for c in cases if _label(c) == _TRAIN]
        val_cases = [c for c in cases if _label(c) == _VAL]

        # One side empty means nothing is being held out for this population.
        if not train_cases or not val_cases:
            leaked = True

        train[population] = train_cases
        val[population] = val_cases

    return train, val, leaked


def _label(case: object) -> str:
    if not isinstance(case, dict):
        return ""
    value = case.get("split")
    return value.strip().lower() if isinstance(value, str) else ""
