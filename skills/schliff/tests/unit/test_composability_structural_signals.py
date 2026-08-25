"""Three composability detectors miss the thing when a file states it structurally.

Each of these has one demonstrated false negative in schliff's own SKILL.md — a line
that earns the point and does not get it because the regex demands a specific English
phrasing instead of the fact itself.

`_RE_IDEMPOTENCY` and `_RE_NAMESPACE_ISOLATION` are deliberately NOT touched: measured
across benchmarks/corpus/v1 they hit 1/21 and 4/21, and neither has a demonstrated
false negative. No measurement accuses them.

Spec: docs/specs/2026-08-13-structural-signal-detection.md
"""
import pytest

from scoring.patterns import (
    _RE_DEPENDENCY_DECL,
    _RE_ERROR_BEHAVIOR,
    _RE_VERSION_COMPAT,
)


class TestErrorBehaviour:
    """An error contract is named by its channel and exit status, not by the word 'error'."""

    @pytest.mark.parametrize("text", [
        # The line from schliff's own SKILL.md that scores nothing today.
        "Errors go to stderr as one line with a non-zero exit.",
        "Any non-zero exit → report the stderr line verbatim; it names the cause.",
        "Exits 1 below the threshold.",
        "Writes diagnostics to stderr and exits with a non-zero status.",
        # Phrasings that already worked — must keep working.
        "On error, report the cause and stop.",
        "If the command fails, retry once.",
    ])
    def test_states_an_error_contract(self, text):
        assert _RE_ERROR_BEHAVIOR.search(text), f"not recognised: {text!r}"

    @pytest.mark.parametrize("text", [
        "This skill scores instruction files deterministically.",
        "The exit interview is scheduled for Friday.",
        "Standard errors in reasoning are covered in the appendix.",
        # `\s` crosses newlines, so a sentence ending in "exits" followed by a numbered
        # list read as "exits 1". Same defect class the dependency pattern fixed in the
        # same diff; this one was missed. Found by review, 0 hits in the field.
        "Run the loop until the agent exits\n1. Review the transcript",
        "sort by exit\ncode is not relevant",
    ])
    def test_prose_without_a_contract_is_not_credited(self, text):
        assert not _RE_ERROR_BEHAVIOR.search(text), f"false positive: {text!r}"


class TestDependencyDeclaration:
    """A declared prerequisite is a fact about a tool, not a member of a wordlist."""

    @pytest.mark.parametrize("text", [
        # schliff's own line: `uv` is absent from the hardcoded tool wordlist.
        "These run anywhere `uv` is available: no plugin, no checkout.",
        "Requires uvx to be installed.",
        "Needs deno 2 on the PATH.",
        "Needs deno on the PATH.",
        "Requires bun; install it first.",
        # Already-working phrasings must keep working.
        "Requires python 3.11 or newer.",
        "Depends on jq for JSON parsing.",
    ])
    def test_declares_a_prerequisite(self, text):
        assert _RE_DEPENDENCY_DECL.search(text), f"not recognised: {text!r}"

    @pytest.mark.parametrize("text", [
        "The available options are listed below.",
        "This is available to every caller.",
        # `\s` crosses newlines: this read as "needs <tool> <version>" against the
        # list number on the following line. Found on a real installed skill
        # (gpt-5-4-prompting), not on a fixture.
        "4. State the constraints the caller needs them.\n5. Return the diff only.",
        # A bare trailing digit made ordinary sequencing prose look like tool+version.
        # Found by review; zero field hits, so tightening it costs nothing.
        "This step needs step 2 to have run first.",
        "The loop needs iteration 3 before it converges.",
    ])
    def test_unrelated_availability_is_not_a_declaration(self, text):
        assert not _RE_DEPENDENCY_DECL.search(text), f"false positive: {text!r}"


class TestVersionCompatibility:
    r"""A version pin is a compatibility FACT: a stated version, in some syntax.

    `tool@1.2.3` and the prose forms below qualify. The bare instruction
    `pin the version` does not — it names no version — and that alternative was
    removed. If it is ever re-added, the ALTERNATIVE ITSELF must require a version
    token (`pin\s+the\s+version\s+(?:to|at)\s+[\d.]+`), never the bare phrase:
    an alternative matching the phrase alone hands `Pin the version.` 10 points
    again, which is the whole defect. A narrowed form was tried and reverted for
    separate reasons — see the spec — so check that history before rebuilding it.
    """
    @pytest.mark.parametrize("text", [
        # schliff's own line — a pin, in the syntax people actually use.
        "Pin the version in CI: `uvx schliff@8.8.2 verify <file> --min-score 75`.",
        "Install with `npm i tool@2.4.0`.",
        "Use imgaudit@3.4.0 in CI.",
        # Already-working phrasings must keep working.
        "Requires node >= 18.0",
        "Minimum version 3.9.",
        "Compatible with Python 3.12",
        # An honest pin on a line that also mentions a deploy command. This is
        # the counter-example the SSH limit below rests on: a command-wordlist
        # exclusion would strip this file's credit. It lives HERE, in the
        # positive set, on purpose — the limit test below carries an
        # instruction to delete it once an exclusion works, and after that
        # deletion this assertion is the only thing left that notices if the
        # new exclusion takes honest pins with it.
        "Deploy over ssh; pin `ruff@0.4.2` in CI.",
    ])
    def test_states_compatibility(self, text):
        assert _RE_VERSION_COMPAT.search(text), f"not recognised: {text!r}"

    def test_an_email_address_is_not_a_version_pin(self):
        r"""Pins the `@\d+\.\d+` digit requirement.

        The module comment on `_RE_VERSION_COMPAT` relies on exactly this: the
        digit after the `@` is what keeps an address out. Widening the alternative
        to `@[\w.]+` must break here.
        """
        assert not _RE_VERSION_COMPAT.search(
            "Email the maintainer at user@example.com for access."
        )

    def test_prose_about_versioning_is_not_a_pin(self):
        assert not _RE_VERSION_COMPAT.search(
            "The versioning policy is documented separately."
        )

    @pytest.mark.parametrize("text", [
        # An instruction to pin is not a pin: the credited thing is a stated
        # compatibility FACT, and these name no version at all. Measured on the
        # unreleased scorer this branch forked from (`main` at 922fd92), the bare
        # phrase lifted composability by 10 on an otherwise empty file.
        "Pin the version.",
        "Pin the version before release.",
        "Pin the version in step 2.1.",
    ])
    def test_bare_imperative_is_not_a_version_pin(self, text):
        assert not _RE_VERSION_COMPAT.search(text), f"false positive: {text!r}"

    def test_an_ssh_target_is_still_credited_known_limit(self):
        """Documents behaviour this pattern deliberately does NOT fix.

        `ssh root@<ipv4>` is credited as a version pin. Two discriminators were
        tried, and each cost an honest file its point:

        - number shape: `root@127.1` and `root@0000100.1.2.3` are credited and
          both resolve, so an octet rule cannot be completed — and it drops
          genuine four-part versions whose parts all fall in 0-255, such as
          `v8@10.2.154.26`;
        - command wordlist: misses `git@`/`psql`/`curl` targets, and strips the
          credit from `Deploy over ssh; pin `ruff@0.4.2` in CI.`, which is
          asserted in the positive set above precisely so it outlives this test.

        This test asserts the CURRENT behaviour. If a future change makes the
        exclusion work, delete it — do not weaken it.
        """
        assert _RE_VERSION_COMPAT.search("Deploy with `ssh root@100.127.18.39`.")
