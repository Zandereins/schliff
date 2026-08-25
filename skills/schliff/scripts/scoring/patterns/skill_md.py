"""SKILL.md-specific patterns for scoring instruction files with SKILL.md structure."""
import re

__all__ = [
    # Structure patterns
    "_RE_FRONTMATTER_NAME",
    "_RE_FRONTMATTER_DESC",
    "_RE_REAL_EXAMPLES",
    "_RE_REFS",
    "_RE_SECTION_HEADER",
    # Composability patterns
    "_RE_POSITIVE_SCOPE",
    "_RE_NEGATIVE_SCOPE",
    "_RE_GLOBAL_STATE",
    "_RE_INPUT_SPEC",
    "_RE_OUTPUT_SPEC",
    "_RE_HANDOFF",
    "_RE_WHEN_NOT",
    "_RE_HARD_REQUIREMENTS",
    "_RE_ALTERNATIVES",
    "_RE_ERROR_BEHAVIOR",
    "_RE_IDEMPOTENCY",
    "_RE_DEPENDENCY_DECL",
    "_RE_NAMESPACE_ISOLATION",
    "_RE_VERSION_COMPAT",
    # Trigger patterns
    "_RE_CREATION_PATTERNS",
    "_RE_NEGATION_BOUNDARIES",
    "_RE_STRONG_DOMAIN_SIGNAL",
    "_RE_ANTI_DOMAIN_SIGNAL",
    # Helper function
    "_has_skill_domain_signal",
]

# --- Structure patterns (SKILL.md-specific) ---
_RE_FRONTMATTER_NAME = re.compile(r"^name:\s*\S+", re.MULTILINE)
_RE_FRONTMATTER_DESC = re.compile(r"^description:", re.MULTILINE)
# `input.{0,200}?output` (bounded, lazy) not `input.*output`: the unbounded
# greedy form is O(n^2) under findall() and lets a ~256KB single-line payload peg
# the playground CPU for ~90s (ReDoS). The 200-char window still catches genuine
# "input … output" example pairs, which sit close together.
_RE_REAL_EXAMPLES = re.compile(
    r"(?i)(example\s*[0-9:#]|input.{0,200}?output|e\.g\.|for instance|for example)"
)
# Non-capturing group so findall() yields the FULL referenced path
# (e.g. "references/patterns.md"), not just the bare resource-dir prefix.
_RE_REFS = re.compile(r"(?:references|scripts|templates)/[\w./-]+")
_RE_SECTION_HEADER = re.compile(r"^##\s")

# --- Composability patterns (SKILL.md-specific) ---
_RE_POSITIVE_SCOPE = re.compile(
    r"(?i)(use this skill when|use when|trigger when|activate for)"
)
_RE_NEGATIVE_SCOPE = re.compile(
    r"(?i)(do not use|don't use|NOT for|not use for|out of scope)"
)
_RE_GLOBAL_STATE = re.compile(
    r"(?i)(must be installed globally|global config|~\/\.|modify system|"
    r"system-wide|/etc/|export\s+\w+=)"
)
_RE_INPUT_SPEC = re.compile(
    r"(?i)(input:|takes.*as input|expects|requires.*file|requires.*path|target.*skill)"
)
_RE_OUTPUT_SPEC = re.compile(
    r"(?i)(output:|produces|generates|creates|saves.*to|writes.*to|returns)"
)
_RE_HANDOFF = re.compile(
    r"(?i)(then use|hand off to|pass to|chain with|followed by|"
    r"complementary|works with|after.*use|before.*use|"
    r"skill-creator|next step)"
)
_RE_WHEN_NOT = re.compile(
    r"(?i)(if.*instead use|for.*use.*instead|suggest using)"
)
_RE_HARD_REQUIREMENTS = re.compile(
    r"(?i)(requires?\s+(?:npm|pip|brew|apt|docker|node|python)\b)"
)
_RE_ALTERNATIVES = re.compile(
    r"(?i)(alternatively|or use|if.*not available|fallback)"
)
# New composability patterns (v6.0.1 — granular scoring)
# A file that names its failure CHANNEL and exit STATUS has declared an error contract
# more precisely than one that says "on error". The phrasing alternatives below were the
# only recognised form until 2026-08-13; "Errors go to stderr as one line with a non-zero
# exit" scored nothing. See docs/specs/2026-08-13-structural-signal-detection.md.
#
# KNOWN LIMIT, measured and accepted: `\bstderr\b` detects the WORD, not the contract, so
# "Do not write to stderr in library code" is credited. Distinguishing a declared failure
# channel from a mention of the stream needs sentence-level meaning, which no regex here
# has. Measured over 186 real files: 0 where a bare `stderr` is the only thing carrying
# the point. Revisit if a field hit appears.
_RE_ERROR_BEHAVIOR = re.compile(
    r"(?i)(on\s+error|error\s+handling|if\s+\w[\w ]{0,80}\s+fails?|when\s+\w[\w ]{0,80}\s+fails?|"
    r"graceful(?:ly)?\s+(?:handle|degrad\w+|fail)|recover(?:y|s)?\s+(?:from|when)|"
    # `[ \t]` not `\s` — same reason as _RE_DEPENDENCY_DECL below, and the same defect
    # class this diff fixed there but missed here: `\s` crosses newlines, so
    # "…until the agent exits\n1. Review…" matched `exits\n1` and credited an error
    # contract that does not exist.
    r"\bstderr\b|non-?zero[ \t]+(?:exit|status)|exit[ \t]+(?:code|status)|exits?[ \t]+[1-9])"
)
_RE_IDEMPOTENCY = re.compile(
    r"(?i)(idempotent|safe to (?:re-?run|run (?:again|twice|multiple))|"
    r"running (?:again|twice)|no side.?effects?|re-?entrant)"
)
# The closed tool wordlist below dates from v6.0.1 and cannot be completed — it lacked
# `uv`, which is how this project's own skill declares its one prerequisite ("These run
# anywhere `uv` is available"). The added alternatives are tool-agnostic: they key on the
# SHAPE of a prerequisite statement, not on knowing every tool's name. Each still needs a
# declaration frame ("anywhere X is available", "requires X to be installed"), so bare
# prose like "the available options" is not credited.
_RE_DEPENDENCY_DECL = re.compile(
    r"(?i)(requires?[:\s]+(?:python|node|npm|pip|git|jq|bash|ruby|go)\b|"
    r"depends?\s+on|prerequisite|"
    r"needs?\s+(?:python|node|npm|pip|git|jq|bash|ruby|go)\b|"
    r"install\s+\w+\s+first|"
    # `[ \t]` not `\s`: `\s` crosses newlines, so "…needs them.\n5. Next step"
    # matched as "needs <tool> <version>" against a list number on the next line.
    # The tool token also may not end in a sentence period, which is what separates
    # "needs deno 2" from "needs them. 5". Found on a real installed skill.
    r"anywhere[ \t]+`?[\w.-]+`?[ \t]+is[ \t]+available|"
    r"requires?[ \t]+`?[\w.-]+`?[ \t]+to[ \t]+be[ \t]+installed|"
    # A bare trailing digit was too loose — "this step needs step 2 to have run first"
    # and "the loop needs iteration 3" read as tool-plus-version. Zero field hits, and
    # two constructed false positives, so the digit is now only allowed as an optional
    # version BETWEEN the tool and an explicit availability phrase.
    #
    # KNOWN LIMIT: the `(?i)` on this pattern makes "on the PATH" match "on the path",
    # so "needs work on the path to production" is credited. Dropping the flag for this
    # alternative alone would need the pattern split in two; the whole-pattern flag is
    # load-bearing for the wordlist branches above. Measured: 0 field hits.
    r"needs?[ \t]+`?[\w-]+(?:\.[\w-]+)*`?(?:[ \t]+v?[\d.]+)?[ \t]+on[ \t]+the[ \t]+PATH)"
)
_RE_NAMESPACE_ISOLATION = re.compile(
    r"(?i)(namespace\s+\w+|namespaced?\b|__\w+__|"
    r"@[\w-]+/[\w-]+|plugin[_-]\w+|scoped\s+to\b)"
)
# A version PIN is the compatibility statement people actually write — `tool@1.2.3` in a
# CI line says more than "minimum version". The `@\d+\.\d+` shape is what keeps an email
# address out: `user@example.com` has no digit after the `@`.
#
# The package-name run is BOUNDED. `[\w.-]+@` has no literal prefix to limit start
# positions, so the unbounded form is O(n^2) — measured 18.1 → 72.2 → 288.0ms, ratio
# 4.00x per doubling, caught by test_patterns_scale_linearly (the reason that gate
# exists). 64 covers the longest real package name by a wide margin
# (`@vercel/microfrontends` is 22); a bounded run costs O(bound) per start position
# and keeps the pattern linear.
#
# KNOWN LIMIT — an SSH target is credited as a pin: `ssh root@100.127.18.39` earns the 10
# points this signal is worth. It is recorded rather than fixed, because neither available
# discriminator is decidable, and each fails where the other does not. Counter-examples,
# not statistics, because these reproduce anywhere:
#
#   - By NUMBER SHAPE: `socket.inet_aton` resolves `127.1`, `0x7f.1` and `0000100.1.2.3`
#     to real hosts, so an octet rule is complete only until the next form is written.
#     Two attempts on this pattern closed zero-padding at three and then six characters;
#     seven was never reached.
#   - By DEPLOY COMMAND on the line: a wordlist misses `git clone git@10.0.0.5` and
#     `curl http://admin@192.168.1.1` — both caught by the shape rule — while stripping
#     the credit from an honest "Deploy over ssh; pin `ruff@0.4.2` in CI."
#
# Withholding the point from an honest file costs more than the limit does, and no
# attempted rule avoided that cost. Same treatment as the KNOWN LIMIT on
# `_RE_ERROR_BEHAVIOR` above and the option-shape limit in `base.py`: documented,
# not papered over.
#
# REVISIT IF: the scorer gains fenced-block language, which would separate a shell block
# from prose without enumerating number forms or command names. The gaming vector belongs
# in `benchmarks/anti-gaming/` and is not added yet — that harness runs in no CI job and
# `test_benchmark.py` is red today (two assertions expect 6 benchmarks where 7 exist).
_RE_VERSION_COMPAT = re.compile(
    r"(?i)(version\s*[><=!]+\s*[\d.]+|compatible\s+with\s+\w+\s+v?\d|"
    r"requires?\s+\w+\s*[><=]+\s*[\d.]+|minimum\s+version|"
    r"supported\s+versions?|works\s+with\s+\w+\s+v?\d+\.\d+|"
    r"[\w.-]{1,64}@\d+\.\d+)"
)

# --- Trigger patterns (SKILL.md-specific) ---
_RE_CREATION_PATTERNS = re.compile(
    r"(?i)(from scratch|brand new|new\b.{0,20}\bskill|create\b.{0,20}\bskill|"
    r"build\b.{0,20}\bskill|write\b.{0,20}\bskill|design\b.{0,20}\bskill)"
)
_RE_NEGATION_BOUNDARIES = re.compile(
    r"(?:do not|don't|NOT|never)\s+(?:use\s+)?(?:for|when|if|with)?\s*(.+?)(?:\.|,|$)",
    re.IGNORECASE,
)

# Domain signal patterns
_RE_STRONG_DOMAIN_SIGNAL = re.compile(
    r"skill\.md|skill\s*forge|my\s+skill|this\s+skill|the\s+skill|"
    r"skill\s+(?:trigger|description|improvement|quality|needs|work)|"
    r"improve\s+(?:my|this|the)\s+skill|"
    r"(?:trigger|eval)\s+(?:accuracy|suite|test)|"
    r"skill\s+(?:and|but|needs|is|has)",
    re.IGNORECASE,
)
_RE_ANTI_DOMAIN_SIGNAL = re.compile(
    r"python\s+function|rest\s+api|docker|"
    r"security\s+vulnerab|\.py\b|\.ts\b|\.js\b|"
    r"open\s+source\s+project|readme|prompt\s+template|"
    r"database\s+quer|sql\s+quer|db\s+quer|"
    r"(?:my|the)\s+(?:database|sql|postgres|mysql|sqlite|mongo)\b",
    re.IGNORECASE,
)
# "skill" used as the object being acted on (e.g. "my database skill",
# "the migration skill") is a genuine in-domain signal, not an incidental
# mention. When this is present the anti-domain suppression must NOT fire,
# otherwise legitimate skill-improvement prompts that name a domain
# ("improve the composability of my database skill") get wrongly suppressed.
# Bounded quantifiers: the SECOND alternative starts with `[\w-]+` and therefore has
# no literal prefix to limit start positions, so an unbounded run before the required
# `\s+` was O(n^2) — measured 2.8s at 16KB, ratio 4.1x per doubling. This pattern is
# fed eval-suite trigger prompts, i.e. untrusted JSON, so the input is attacker-chosen
# on any `score --eval-suite` / `run-eval.sh` / Action `eval-suite` path.
#
# Bound 64 against a measured longest real run of 19 chars across 494 trigger and test
# prompts (3.4x headroom). Verified identical on the two cases this pattern exists to
# protect ("improve the composability of my database skill", "the migration skill") and
# on the anti-signal it must keep rejecting ("optimize my database queries").
# Found by tests/unit/test_patterns_scale_linearly.py, not by the audit's fix list —
# which is the reason that gate exists.
_RE_SKILL_AS_OBJECT = re.compile(
    r"(?i)(?:my|this|the|our|your|a|an)\s+(?:[\w-]{1,64}\s+){0,3}skills?\b|"
    r"[\w-]{1,64}\s+skills?\b\s+(?:conflicts?|needs?|works?|is\b|when\b|that\b)"
)


def _has_skill_domain_signal(prompt: str) -> float:
    """Check if prompt is about skills (not generic code/config).

    Returns a multiplier: 1.8 for strong signal, 1.0 for neutral, 0.2 for anti-signal.
    Anti-signal is set to 0.2 (not 0.4) so that high-scoring generic-action prompts
    (e.g. 'optimize my database queries') cannot accumulate enough TF-IDF weight to
    exceed the 4.5 threshold even when they contain multiple skill-adjacent verbs.

    The anti-domain check is evaluated BEFORE the bare 'skill' substring boost so an
    incidental 'skill' mention inside an otherwise generic-action prompt cannot lift
    it to 1.2. A genuine in-domain prompt that names 'skill' as the object being acted
    on (e.g. 'improve the composability of my database skill') is exempted from anti-
    domain suppression via _RE_SKILL_AS_OBJECT so true positives are preserved.
    """
    prompt_lower = prompt.lower()

    if _RE_STRONG_DOMAIN_SIGNAL.search(prompt_lower):
        return 1.8

    if _RE_ANTI_DOMAIN_SIGNAL.search(prompt_lower) and not _RE_SKILL_AS_OBJECT.search(
        prompt_lower
    ):
        return 0.2

    if "skill" in prompt_lower:
        return 1.2

    return 1.0
