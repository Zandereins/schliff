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
    """A version pin is a compatibility FACT: a stated version, in some syntax.

    `tool@1.2.3` and the prose forms below qualify; the bare instruction
    `pin the version` does not, and that alternative was removed.

    Re-adding a phrase alternative: the negative cases below are the
    specification — run any candidate against them. Do not copy a regex out of a
    docstring; an earlier one prescribed here was wrong in both directions. The
    reasoning and both reverted attempts live in
    docs/specs/2026-08-13-structural-signal-detection.md, "Amendment 2026-08-25".
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
        # The two honest pins each attempted exclusion would have destroyed.
        # They live HERE, in the positive set, on purpose: the limit test below
        # carries an instruction to delete it once an exclusion works, and after
        # that deletion these are the only assertions left that notice a new
        # exclusion taking real pins with it. One per error direction, because
        # covering only the wordlist would leave the shape rule unguarded.
        #
        # a wordlist keyed on `ssh` would strip this:
        "Deploy over ssh; pin `ruff@0.4.2` in CI.",
        # an IPv4-shape rule would strip this — every part falls in 0-255, so it
        # is indistinguishable from an address by shape alone:
        "Bundled runtime is v8@10.2.154.26.",
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

    def test_the_phrase_with_a_version_is_currently_not_credited(self):
        """CURRENT BEHAVIOUR, not a required property. Change it if you must.

        Nothing credits "Pin the version to 1.2.3" today, and CHANGELOG says so,
        which is why this is pinned: a re-added phrase alternative would
        otherwise leave the suite green while the CHANGELOG described behaviour
        the code no longer had.

        But do not read it as a rule that the form MUST stay uncredited. The
        spec records the reverted narrowed alternative's failure to credit
        ``Pin the version to `8.8.2`.`` as one of its two error directions — so
        a genuinely correct prose alternative, crediting the backticked and the
        plain form alike, would be an improvement and would land here as a red
        test. Update this test and the CHANGELOG line together in that case.

        The form does not occur in the field: measured over the local corpus,
        every "pin the version … <version>" line without a `tool@version` beside
        it was documentation about this very defect.
        """
        assert not _RE_VERSION_COMPAT.search("Pin the version to 1.2.3.")

    def test_an_ssh_target_is_still_credited_known_limit(self):
        """Asserts behaviour this pattern deliberately does NOT fix.

        Reasoning and the two reverted discriminators: see the spec amendment
        named in this class's docstring. If a future change makes an exclusion
        work, DELETE this test — do not weaken it. The honest-pin case that a
        wordlist exclusion would break is asserted in the positive set above, so
        it survives that deletion.
        """
        assert _RE_VERSION_COMPAT.search("Deploy with `ssh root@100.127.18.39`.")
