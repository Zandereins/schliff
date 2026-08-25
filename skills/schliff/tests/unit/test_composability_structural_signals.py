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
    """A version pin is a compatibility statement, whatever syntax expresses it."""

    @pytest.mark.parametrize("text", [
        # schliff's own line — a pin, in the syntax people actually use.
        "Pin the version in CI: `uvx schliff@8.8.2 verify <file> --min-score 75`.",
        "Install with `npm i tool@2.4.0`.",
        "Use imgaudit@3.4.0 in CI.",
        # Already-working phrasings must keep working.
        "Requires node >= 18.0",
        "Minimum version 3.9.",
        "Compatible with Python 3.12",
    ])
    def test_states_compatibility(self, text):
        assert _RE_VERSION_COMPAT.search(text), f"not recognised: {text!r}"

    @pytest.mark.parametrize("text", [
        "Email the maintainer at user@example.com for access.",
        "The versioning policy is documented separately.",
    ])
    def test_prose_without_a_pin_is_not_credited(self, text):
        assert not _RE_VERSION_COMPAT.search(text), f"false positive: {text!r}"

    @pytest.mark.parametrize("text", [
        # An instruction to pin is not a pin: the credited thing is a stated
        # compatibility FACT, and these name no version at all. Measured on the
        # 8.12.0 scorer, the bare phrase lifted composability by 10 for free.
        "Pin the version.",
        "Pin the version before release.",
        "Pin the version in step 2.1.",
    ])
    def test_bare_imperative_is_not_a_version_pin(self, text):
        assert not _RE_VERSION_COMPAT.search(text), f"false positive: {text!r}"

    def test_an_ssh_target_is_still_credited_known_limit(self):
        """Documents behaviour this pattern deliberately does NOT fix.

        `ssh root@<ipv4>` is credited as a version pin. Four review rounds
        established that no pattern separates an address from a version in
        either direction — by number shape (`127.1`, `0x7f.1` both resolve)
        or by command wordlist (which misses `git@`/`psql`/`curl` while
        destroying honest pins that merely mention ssh in prose). The limit
        is recorded, with the cost named, rather than papered over.

        This test asserts the CURRENT behaviour. If a future change makes the
        exclusion work, delete it — do not weaken it.
        """
        assert _RE_VERSION_COMPAT.search("Deploy with `ssh root@100.127.18.39`.")
