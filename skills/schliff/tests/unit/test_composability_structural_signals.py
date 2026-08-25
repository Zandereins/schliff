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
        # Four-part pins are real — V8 numbers them this way — and the SSH
        # discriminator below must not swallow them. `288` is not a valid
        # octet, so this cannot be an address.
        "Built against v8@6.7.288.46.",
        # Five parts is not an address either. This one guards the trailing
        # `(?!\\.?\\d)` in _IPV4: delete that guard and the lookahead matches
        # `1.2.3.4` here and drops a legal pin. Without this case the whole
        # suite stays green through that mutation.
        "Requires pkg@1.2.3.4.5.",
        # The discriminator is the command, not the number: with no deploy
        # command on the line, a version keeps its credit whatever it looks
        # like — including shapes that are valid addresses.
        "Pin the version in CI: `uvx schliff@8.8.2`.",
        "Bundled runtime is v8@10.2.154.26.",
    ])
    def test_states_compatibility(self, text):
        assert _RE_VERSION_COMPAT.search(text), f"not recognised: {text!r}"

    @pytest.mark.parametrize("text", [
        "Email the maintainer at user@example.com for access.",
        "The versioning policy is documented separately.",
        # An SSH target is a host, not a compatibility fact. Measured on the
        # 8.12.0 scorer: these lifted composability 20 -> 30 for free.
        "Deploy with `ssh root@100.127.18.39` once the build is green.",
        "Copy it over: `scp deploy@10.0.0.5:/srv/app .`",
        # Every one of these resolves and connects, and no shape rule catches
        # them all — which is the point of keying on the command instead.
        # inet_aton: 010.1.2.3 -> 8.1.2.3, 0100.1.2.3 -> 64.1.2.3,
        # 00010.1.2.3 -> 8.1.2.3, 127.1 -> 127.0.0.1, 0x7f.1 -> 127.0.0.1.
        "Deploy with `ssh root@010.1.2.3`.",
        "Run `ssh root@01.02.03.04` on the jump host.",
        "Deploy with `ssh root@0100.1.2.3`.",
        "Deploy with `ssh root@00010.1.2.3`.",
        "Reach it at `ssh root@0000100.1.2.3`.",
        # Two- and three-part forms resolve too, and an octet rule that only
        # knows the four-part shape never sees them.
        "Reach it at `ssh root@127.1`.",
        "Reach it at `ssh root@10.0.1`.",
        # Other transports carry the same target.
        "Copy it over: `scp deploy@10.0.0.5:/srv/app .`",
        "Sync with `rsync deploy@10.0.0.5:/srv/ .`",
    ])
    def test_addresses_are_not_version_pins(self, text):
        assert not _RE_VERSION_COMPAT.search(text), f"false positive: {text!r}"

    @pytest.mark.parametrize("text", [
        # An instruction to pin is not a pin — it names no version at all.
        # The alternative that used to credit this phrase is gone entirely:
        # narrowing it missed quoted versions and credited step numbers.
        "Pin the version.",
        "Pin the version before release.",
        "Pin the version in step 2.1.",
    ])
    def test_bare_imperative_is_not_a_version_pin(self, text):
        assert not _RE_VERSION_COMPAT.search(text), f"false positive: {text!r}"

    def test_a_version_on_a_deploy_line_still_counts_elsewhere(self):
        """The exclusion is per line, not per document.

        A SKILL.md that documents a deploy command AND states a version must
        keep its credit — otherwise the fix would punish honest files that
        happen to mention `ssh`.
        """
        body = (
            "Deploy with `ssh root@10.0.0.5`.\n"
            "Requires node >= 18.0.\n"
        )
        assert _RE_VERSION_COMPAT.search(body)
