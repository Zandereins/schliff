"""Train/val split of an eval suite, with an honest leak flag (ADR 0015).

Imported from SkillOpt's `skillopt_sleep/consolidate.py:54-90`, whose `_split`
returns `holdout_leaked` precisely so a non-disjoint comparison cannot be
reported as a clean win.
"""
from eval_split import split_eval_suite


def _case(name, split=None):
    case = {"prompt": name}
    if split is not None:
        case["split"] = split
    return case


class TestExplicitSplit:
    def test_partitions_each_population_by_its_split_field(self):
        suite = {
            "triggers": [_case("a", "train"), _case("b", "val"), _case("c", "test")],
            "test_cases": [_case("d", "train"), _case("e", "val")],
        }

        train, val, leaked = split_eval_suite(suite)

        assert [c["prompt"] for c in train["triggers"]] == ["a"]
        assert [c["prompt"] for c in val["triggers"]] == ["b"]
        assert [c["prompt"] for c in train["test_cases"]] == ["d"]
        assert [c["prompt"] for c in val["test_cases"]] == ["e"]
        assert leaked is False

    def test_test_split_reaches_neither_side(self):
        suite = {"triggers": [_case("a", "train"), _case("b", "val"), _case("c", "test")]}

        train, val, _ = split_eval_suite(suite)

        prompts = [c["prompt"] for c in train["triggers"] + val["triggers"]]
        assert "c" not in prompts, "the test split is held back from the loop entirely"


class TestLeakFlag:
    """A non-disjoint comparison must announce itself rather than report a win."""

    def test_unlabelled_suite_is_flagged_as_leaked(self):
        suite = {"triggers": [_case("a"), _case("b"), _case("c")]}

        train, val, leaked = split_eval_suite(suite)

        assert leaked is True, "without split labels, gradient and gate see the same cases"
        assert train["triggers"] == val["triggers"]

    def test_population_with_only_a_train_side_is_flagged(self):
        suite = {"triggers": [_case("a", "train"), _case("b", "train")]}

        _, _, leaked = split_eval_suite(suite)

        assert leaked is True, "an empty val side cannot hold anything out"

    def test_a_single_case_cannot_carry_a_split(self):
        suite = {"triggers": [_case("a", "train")]}

        _, _, leaked = split_eval_suite(suite)

        assert leaked is True


class TestShapePreserved:
    def test_unknown_keys_survive_on_both_sides(self):
        suite = {"version": 2, "triggers": [_case("a", "train"), _case("b", "val")]}

        train, val, _ = split_eval_suite(suite)

        assert train["version"] == 2
        assert val["version"] == 2

    def test_input_suite_is_not_mutated(self):
        suite = {"triggers": [_case("a", "train"), _case("b", "val")]}

        split_eval_suite(suite)

        assert len(suite["triggers"]) == 2
