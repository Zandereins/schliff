"""Format-agnostic regex patterns shared across all scoring dimensions."""
import re

__all__ = [
    # Efficiency
    "_RE_ACTIONABLE_LINES",
    "_RE_DOCUMENTED_COMMAND",
    "normalize_command",
    "_RE_WHY_COUNT",
    "_RE_VERIFICATION_CMDS",
    "_RE_FILLER_PHRASES",
    "_RE_OBVIOUS_INSTRUCTIONS",
    "_RE_SCOPE_BOUNDARY",
    # Clarity
    "_RE_ALWAYS_PATTERNS",
    "_RE_NEVER_PATTERNS",
    "_RE_VAGUE_REF",
    "_RE_BACKTICK_REF",
    "_RE_SPECIFIC_REF",
    "_RE_AMBIGUOUS_PRONOUN",
    "_RE_RUN_PATTERN",
    "_RE_CONCEPTUAL",
    "_RE_CONCRETE_CMD",
    "_RE_CODE_BLOCK_START",
    # General structure
    "_RE_HEDGING",
    "_RE_CODE_BLOCKS",
    "_RE_HEADERS",
    "_RE_TODO",
    "_RE_CODE_BLOCK_REGION",
    # Security
    "_RE_SEC_PROMPT_INJECTION",
    "_RE_SEC_INSTRUCTION_OVERRIDE",
    "_RE_SEC_DATA_EXFIL",
    "_RE_SEC_ENV_LEAK",
    "_RE_SEC_DANGEROUS_CMD",
    "_RE_SEC_BASE64_CMD",
    "_RE_SEC_ZERO_WIDTH",
    "_RE_SEC_HEX_ESCAPE",
    "_RE_SEC_OVERPERMISSION",
    "_RE_SEC_BOUNDARY_VIOLATION",
    # Diff
    "_RE_DIFF_SIGNAL",
    "_RE_DIFF_EXAMPLE",
    "_RE_DIFF_NOISE",
    # Coherence
    "_RE_IMPERATIVE_INSTRUCTION",
]

# ---------------------------------------------------------------------------
# Efficiency patterns
# ---------------------------------------------------------------------------
# Leading list marker: numbered ("1. ", "12. ") OR bullet ("- ", "* ", "+ ").
# Applied as an optional prefix so bare imperatives still match.
_LIST_MARKER = r"(?:\d+\.\s*|[-*+]\s+)?"

_RE_ACTIONABLE_LINES = re.compile(
    r"^" + _LIST_MARKER + r"(?:Read|Run|Check|Create|Add|Remove|Move|Use|Set|"
    r"Install|Configure|Deploy|Test|Verify|Build|Start|Stop|Open|Save|"
    r"Copy|Delete|Write|Edit|Update|Generate|Execute|Validate|Parse|"
    r"Extract|Transform|Import|Export|Send|Fetch|Call|Return|"
    r"Confirm|Document|List|Show|Print|Log|Review|Apply|Enable|Disable|"
    r"Ensure|Define|Specify|Register|Mount|Scan|Inspect|Monitor)\b",
    re.MULTILINE,
)
# ---------------------------------------------------------------------------
# Documented command lines.
#
# `_RE_ACTIONABLE_LINES` above recognises an English imperative at line start, so a
# line that *is* an executable command scores nothing — the most actionable line a
# reference document can contain. This pattern closes that gap, but deliberately only
# for a command that carries its explanation: `- `tool sub <arg>` — what it does`.
#
# Measured rationale (docs/specs/2026-08-13-structural-signal-detection.md): counting
# every command-bearing line ranks a dump of `ls -la` / `pwd -P` ABOVE a documented
# command list, because efficiency divides signal by word count and the dump is
# shorter. Requiring the explanation is the only variant where the documented file wins.
#
# Structure, not a wordlist of tool names: a list marker, a backticked command whose
# first token looks like a program and which has at least one further token, a
# separator, and at least 10 characters of explanation.
#
# KNOWN LIMIT, measured and accepted: this is a shape, so a two-token option or field
# entry in the same shape is credited — `- `max_tokens int` — the maximum number of
# tokens`. There is no structural signal that separates that from `- `make test` — run
# the suite`, and inventing one would mean a wordlist of tool names, which is the design
# this detector replaced. Measured over 186 real files: 39 hits, 39 of them genuine
# commands, 0 option-list false positives — the two-token minimum already excludes the
# common single-token option form (`- `max_tokens` — …`). Revisit if a field hit appears.
_RE_DOCUMENTED_COMMAND = re.compile(
    # `[ \t]` not `\s` — third instance of the same class in this changeset. It was
    # swept out of _RE_ERROR_BEHAVIOR and _RE_DEPENDENCY_DECL and then reintroduced
    # here: `\s` after the list marker crosses a newline, so a bare "1." on its own
    # line credited the backticked command on the NEXT line as documented.
    r"^(?:\d+\.[ \t]*|[-*+][ \t]+)"     # list marker — a documented command is a list item
    # Backticked: program-like head + at least one REAL argument. The `[^\s`]` is
    # load-bearing — a dependency list aligns its entries with trailing spaces
    # (`` `coverlet.collector     ` : Coverlet is a … library ``), which otherwise
    # reads as "program + argument" and credits a package name as a command.
    r"`([a-z][\w.@/-]*[ \t]+[^\s`][^`\n]*)`"
    r"[ \t]*[—–:-][ \t]+"               # separator between command and explanation
    r"(\S[^\n]{9,})",                   # the explanation itself, on the same line
    re.MULTILINE,
)

# Argument-like token: placeholder, flag, shell operator, or a file with an extension.
# The operator branch covers the full set, not just `|`: an unstopped `&&`, `>` or `;`
# left shell plumbing in the identity (`cd build && make`, `tool run >`), so two
# different pipelines could share one and the same command could split into two.
_RE_COMMAND_ARG = re.compile(r"^(?:<|-|\$|\||&|>|<|;|\|\||&&|[\w./-]+\.[a-z]{1,5}$)")

# An interpreter prefix is not the command's identity — `bash scripts/a.sh` and
# `bash scripts/b.sh` are different commands. Without this, the script path (a
# file-with-suffix token) stopped the walk at index 1 and both collapsed to `bash`.
_INTERPRETERS = frozenset({"bash", "sh", "zsh", "python", "python3", "node", "ruby", "perl"})


def normalize_command(command: str) -> str:
    """Reduce a command to its identity: program plus subcommands.

    Arguments, flags and version pins are not part of what a command IS, so
    ``tool score <file>``, ``tool score SKILL.md`` and ``tool@1.2.3 score`` collapse to
    ``tool score``. Without this, one command listed in a command table, an example and
    a workflow counts three times.

    Subcommands are kept: truncating to a fixed token count collapses an entire CLI
    family (``tool score`` / ``tool doctor`` / ``tool verify``) into a single signal.
    """
    tokens = command.split()
    # The program is whatever follows an interpreter prefix, so the file-with-suffix
    # shape must not be tested against it either: `bash scripts/a.sh` and
    # `bash scripts/b.sh` otherwise both reduce to `bash`, merging N distinct
    # documented commands into a single signal.
    head = 1 if len(tokens) > 1 and tokens[0] in _INTERPRETERS else 0

    parts = []
    for index, token in enumerate(tokens):
        # The head is the program — never test it against the argument shape. A program
        # name with an extension (`run-eval.sh`, `manage.py`) matches the file-with-suffix
        # branch, which broke out on token 0 and returned an empty identity, so the line
        # was dropped entirely. That is the exact line shape this detector exists to
        # credit, and the one this repo's own command docs use.
        if index > head and _RE_COMMAND_ARG.match(token):
            break
        # Strip a version pin (`tool@1.2.3`), but never on a scoped package name
        # (`@vercel/microfrontends`), where the leading `@` is the name itself —
        # splitting there yields an empty token, so `npx @a/x run` and `npx @b/y run`
        # collapse to the same identity. Found on real installed skills, not fixtures.
        parts.append(token if token.startswith("@") else token.split("@", 1)[0])
    return " ".join(parts)


_RE_WHY_COUNT = re.compile(
    r"\b(because|since|this enables|this prevents|this means|the reason|"
    r"this ensures|this avoids|otherwise|so that|why[:\s])\b",
    re.IGNORECASE,
)
_RE_VERIFICATION_CMDS = re.compile(r"```\s*(?:bash|sh)\b")
_RE_FILLER_PHRASES = re.compile(
    r"(?i)(it is important to note that|as mentioned (above|earlier|before)|"
    r"in other words|that is to say|keep in mind that|note that|"
    r"it should be noted|please note|remember that|be aware that|"
    r"it's worth mentioning)"
)
_RE_OBVIOUS_INSTRUCTIONS = re.compile(
    r"(?i)(make sure to save|don't forget to|always test your|"
    r"be careful when|ensure you have|make sure you|"
    r"remember to commit|use version control)"
)
_RE_SCOPE_BOUNDARY = re.compile(r"(?i)(do not|don't) use (for|when|if)")

# ---------------------------------------------------------------------------
# Clarity patterns
# ---------------------------------------------------------------------------
_RE_ALWAYS_PATTERNS = re.compile(r"(?i)\b(always|must)\s+(\w+(?:\s+\w+)?)")
_RE_NEVER_PATTERNS = re.compile(r"(?i)\b(never|must not|do not|don't)\s+(\w+(?:\s+\w+)?)")
_RE_VAGUE_REF = re.compile(
    r"\b(the\s+(?:file|script|output|result|command|path|tool|config))\b", re.IGNORECASE
)
_RE_BACKTICK_REF = re.compile(r"`[^`]+`")
# Every quantifier here is bounded, and the bounds are measured rather than guessed.
# The shape `[\w/]+` followed by a REQUIRED `\.` is O(n^2) on its own — no nesting
# and no overlapping alternation, which is why shape-based triage misses it: the run
# consumes to the end of the input, fails on the dot, and gives back one character at
# a time, once per start position. Measured 4.4s at 32KB, ratio 4.0x per doubling.
#
# Bounds come from the longest run each quantifier actually consumes across 380 real
# instruction files (installed skills, plugin payloads, benchmarks/, docs/, this
# project's own files): `[\w/]+` 58, `[\w/.-]+` 118, a backtick span 1151, `\w+`
# after the dot 50. The bounds below carry 4.4x / 2.2x / 1.7x / 2.6x headroom over those.
#
# A first guess of 120 would have sat one character above a real 118-char token and
# truncated a real 1151-char span; a first pass at the dot suffix used 64, only 1.28x
# over the measured 50. The failure mode of a guessed bound is a silent score change, so
# calibrate and keep the headroom generous — widening a bound costs nothing here, since
# the cost per start position is O(bound) either way and the pattern stays linear.
# Verified score-neutral: 0 of 250 real files move.
# See docs/specs/2026-07-30-redos-audit-fixes.md (D1).
_RE_SPECIFIC_REF = re.compile(r"(`[^`]{1,2000}`|[\w/]{1,256}\.\w{1,128}|/[\w/]{1,256})")
_RE_AMBIGUOUS_PRONOUN = re.compile(
    r"^\s*(It|This|That)\s+(is|does|will|can|should|has|was|means)\b"
)
_RE_RUN_PATTERN = re.compile(
    r"^\s*" + _LIST_MARKER + r"(?:Run|Execute|Install|Configure)\s+(.+)", re.IGNORECASE
)
_RE_CONCEPTUAL = re.compile(
    r"(?i)(baseline|all\s+\d+|VERIFY|evolution|"
    r"the\s+(?:process|workflow|pipeline|approach|system|loop|strategy)\s+(?:on|for|to|with|against))"
)
# Same shape, same bounds, same reason as _RE_SPECIFIC_REF above.
_RE_CONCRETE_CMD = re.compile(r"(`[^`]{1,2000}`|[\w/.-]{1,256}\.\w{1,128}|/[\w/]{1,256})")
_RE_CODE_BLOCK_START = re.compile(r"^```")

# ---------------------------------------------------------------------------
# General structure patterns
# ---------------------------------------------------------------------------
_RE_HEDGING = re.compile(
    r"you (might|could|should|may) (want to|consider|possibly)", re.IGNORECASE
)
_RE_CODE_BLOCKS = re.compile(r"```")
_RE_HEADERS = re.compile(r"^##\s", re.MULTILINE)
# Dead-content markers are conventionally UPPERCASE standalone tokens or an
# explicit bracketed placeholder stub. Matching the English words
# "placeholder"/"hack" case-insensitively in prose advised deleting
# load-bearing instructions ("Replace all {{...}} placeholders with resolved
# values") — field finding #93 from the hydra case study.
_RE_TODO = re.compile(
    r"\b(?:TODO|FIXME|XXX|HACK|TBD|PLACEHOLDER)\b"
    r"|\[[Pp]laceholder\]|<[Pp]laceholder>|\{\{[Pp]laceholder\}\}"
)
_RE_CODE_BLOCK_REGION = re.compile(r"```[\s\S]*?```")

# ---------------------------------------------------------------------------
# Security patterns
# ---------------------------------------------------------------------------

# Category: injection
_RE_SEC_PROMPT_INJECTION = re.compile(
    r"<!--\s*(?:you\s+(?:must|should|will|are)|ignore|forget|disregard|override|"
    r"new\s+instructions?|system\s+prompt|act\s+as|pretend)\b[^>]{0,500}-->",
    re.IGNORECASE | re.DOTALL,
)
_RE_SEC_INSTRUCTION_OVERRIDE = re.compile(
    r"(?:ignore\s+(?:all\s+)?previous\s+instructions?|"
    r"disregard\s+(?:all\s+)?(?:above|prior|previous)|"
    r"override\s+system\s+prompt|"
    r"forget\s+(?:all\s+)?(?:your|prior|previous)\s+instructions?|"
    r"new\s+instructions?\s*:|"
    r"you\s+are\s+now\s+(?:a|an|the)\b)",
    re.IGNORECASE,
)

# Category: exfil
# The gap between a verb prefix and its terminator is bounded (`[^\n]{0,200}`, not
# greedy `[^\n]*`): the engine scores untrusted content up to the 1MB read cap, and
# a single newline-free line of a repeated verb ("curl " * N) with no terminator
# made the greedy form O(n^2) (~1h CPU at the cap; reachable ungated via a .txt that
# auto-detects as a system_prompt). A real exfil/leak command fits well inside 200
# chars between the verb and the sink. Same bound already used by _RE_DIFF_EXAMPLE.
# The verb alternations are word-boundary anchored (`\b`). Without it the short `nc`
# alternative matches the TAIL of any word ending in "nc" followed by whitespace, and
# markdown is full of them: a field scan of 670 community skills found 55 of 103 exfil
# hits were `async ops`, `sync primitives`, `CNC tool-path`, `BenchmarkMyFunc`. The
# anchor goes on the two alternatives that START with a verb, NOT in front of the whole
# group — the middle alternative starts with `$(`, and `\b` before a non-word character
# would never hold there.
#
# The sink alternation is shell syntax, but the input is MARKDOWN, which reuses the same
# characters for entirely different things: `|` separates table cells and backticks mark
# inline code. Accepting a bare `|` or any backtick span meant ordinary API documentation
# read as exfiltration — "| Fetch full transcripts for source files |" (a table row), or
# "if the response `Content-Type` is". In the 670-skill field scan those two sinks were 39
# of the 51 remaining exfil hits, and EVERY exfil hit in that corpus was adjudicated a
# false positive — including the one on the genuinely malicious fixture, whose real
# payload is caught by `obfuscation`, not here. So a pipe now only counts when it pipes
# into something that executes or transmits, and the backtick span is gone; `$(` and `<(`
# stay, since markdown does not reuse those.
#
# The interpreter does not have to sit flush against the pipe. Requiring that let two
# families of evasion straight through — and `curl … | sudo bash` is MORE dangerous than
# the form that was caught, not less:
#   * a wrapper before it   — `| sudo bash`, `| sudo -E sh`, `| env FOO=1 bash`
#   * an absolute path      — `| /bin/bash`, `| /usr/bin/env sh`
# so a bounded wrapper chain and an optional path prefix are allowed before the
# interpreter. Every quantifier here is bounded and the chain is non-nullable: this file
# has a ReDoS history and the widening must not reintroduce one.
# The wrapper set and the four shapes below were not guessed — they come from
# differencing every verb x sink combination against the pre-narrowing (8.8.0) pattern
# and keeping only the losses that are genuine exfil. The same differential showed
# `| jq`, `| grep`, `| less`, `| column -t`, `| head` no longer matching, which is the
# narrowing working as intended rather than a regression.
_RE_SEC_SINK_WRAPPER = (
    r"(?:(?:/[^\s|]{0,120}/)?(?:sudo|env|command|nohup|busybox)\s+"
    r"|(?:-{1,2}\w+|\w+=[^\s|]{0,64})\s+)*"
)
# An interpreter named through a variable (`| $SHELL`) is a command position, so the
# name itself carries no information — the position does.
_RE_SEC_SINK_EXEC = (
    r"sh|bash|zsh|dash|ksh|fish|python3?|perl|ruby|node|php|pwsh|powershell|iex|"
    r"eval|exec|source|nc|ncat|netcat|curl|wget|tee|xargs|dd|base64|openssl|"
    r"\$[A-Za-z_]\w{0,63}"
)

_RE_SEC_DATA_EXFIL = re.compile(
    r"(?:\b(?:curl|wget|fetch|nc|ncat|netcat)\s+[^\n]{0,200}"
    r"(?:\$\(|<\(|\|&?\s*" + _RE_SEC_SINK_WRAPPER + r"[\"']?(?:/[^\s|]{0,120}/)?"
    r"(?:" + _RE_SEC_SINK_EXEC + r")\b)|"
    r"\$\(cat\s[^\)]+\)\s*\|\s*(?:curl|wget|nc|netcat)|"
    r"\b(?:curl|wget)\s+[^\n]{0,200}(?:--data|--upload|-d\s|-F\s|-T\s)[^\n]{0,200}(?:https?://|ftp://))",
    re.IGNORECASE,
)
# Same word-boundary anchoring as _RE_SEC_DATA_EXFIL above, and for the same reason:
# `cat` and `log` are the tails of `concat`/`logcat` and `catalog`/`changelog`/`blog`.
# This one is fixed for consistency and latent exposure, NOT for observed noise — it
# produced zero false positives in the 670-skill field scan (all 17 hits were genuine
# verbs), but that corpus carries 290 occurrences of 27 such carrier words, each one
# nearby secret token away from firing. The anchor stays off the second alternative,
# which starts with `$`.
_RE_SEC_ENV_LEAK = re.compile(
    r"(?:\b(?:echo|print|cat|send|post|curl|wget|log)\s[^\n]{0,200}(?:\$[A-Z_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)|"
    r"process\.env\.[A-Z_]+|os\.environ\[))|"
    r"(?:\$[A-Z_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)\s*[|>])",
    re.IGNORECASE,
)

# Category: dangerous_cmd
# The recursive-force `rm` alternatives require the target to be root ITSELF, via a
# negative lookahead for a path character after the slash. Without it `rm -rf /` matched
# as a prefix of `rm -rf /<any absolute path>`, so the canonical Docker layer cleanup
# `rm -rf /var/lib/apt/lists/*` was reported as a root wipe (all 13 dangerous_cmd hits in
# a 670-skill field scan were this). `rm -rf /` and `rm -rf /*` still match; a scoped
# delete no longer does.
# The three consecutive `[a-z]*` runs before a required `/` were polynomial: on
# `rm -rrrr...r` they can split the run in many ways before the match fails.
# Measured 2.7s at 16KB; bounded it is linear (12,946x faster) with 0 verdict
# differences across 380 real files. Longest real flag run is 2 chars (`rf`), so 12
# is 6x headroom.
#
# The surrounding `\s+` runs are deliberately NOT bounded. They are prefixed by the
# literal `rm`, which limits how many start positions they are reachable from, so they
# never contributed to the blowup — and bounding them to `\s{1,8}` in the first draft of
# this fix cost five detections 8.8.2 caught (`rm` + >=9 spaces or tabs + `-rf /`).
# Verified linear without the bound (1.92-2.04x per doubling on a whitespace-run
# payload). Narrowing a detector without enumerating its evasion classes is the #149
# defect; the enumeration is TestDangerousCmdWhitespaceIsNotBounded in
# tests/unit/test_security_field_false_positives.py.
#
# Reachable from the shipping CLI via the system_prompt format, where `security` is a
# core headline dimension — see the reachability pin in tests/unit/test_scoring_redos.py.
_RE_SEC_DANGEROUS_CMD = re.compile(
    r"(?:rm\s+-[a-z]{0,12}r[a-z]{0,12}f[a-z]{0,12}\s+/(?![A-Za-z0-9_.-])|"
    r"rm\s+-[a-z]{0,12}f[a-z]{0,12}r[a-z]{0,12}\s+/(?![A-Za-z0-9_.-])|"
    r"chmod\s+777\s|"
    r"dd\s+if=/dev/(?:zero|random|urandom)\s+of=/dev/|"
    r"mkfs\.\w+\s+/dev/|"
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;|"
    r"format\s+[a-z]:\s*/)",
    re.IGNORECASE,
)

# Category: obfuscation
_RE_SEC_BASE64_CMD = re.compile(
    r"(?:echo\s+[^\n]*\|\s*base64\s+-d\s*\|\s*(?:sh|bash|zsh|exec)|"
    r"base64\s+-d\s*[^\n]*\|\s*(?:sh|bash|zsh|exec|eval)|"
    r"atob\s*\([^\)]*\)\s*[^\n]*eval|"
    r"eval\s*\(\s*atob\s*\()",
    re.IGNORECASE,
)
# Zero-width / invisible characters used to hide content. A single U+FEFF at
# offset 0 is a UTF-8 byte-order mark (encoding metadata, common from
# Windows/Notepad editors), not embedded obfuscation, so it is excluded via the
# `(?<!\A)` lookbehind \u2014 only a BOM that appears mid-content is flagged. The
# other zero-width chars are never legitimate metadata and are matched anywhere.
_RE_SEC_ZERO_WIDTH = re.compile(
    r"[\u200b\u200c\u200d\u2060]|(?<!\A)\ufeff",
)
_RE_SEC_HEX_ESCAPE = re.compile(
    r"(?:\\x[0-9a-fA-F]{2}){4,}",
)

# Category: overpermission
_RE_SEC_OVERPERMISSION = re.compile(
    r"(?:run\s+as\s+root|"
    r"sudo\s+\w|"
    r"disable\s+security|"
    r"turn\s+off\s+(?:the\s+)?firewall|"
    r"allow\s+all\s+origins|"
    r"--no-verify\b|"
    r"--disable-web-security\b|"
    r"allowAll\s*[=:]\s*true)",
    re.IGNORECASE,
)

# Category: boundaries
_RE_SEC_BOUNDARY_VIOLATION = re.compile(
    r"(?:/etc/(?:passwd|shadow|sudoers)|"
    r"~/\.ssh/|"
    r"id_rsa|"
    r"\.\.(?:/|\\){2,}|"
    r"(?:cat|read|open|access)\s+[^\n]*/etc/(?:passwd|shadow))",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Diff patterns
# ---------------------------------------------------------------------------
_RE_DIFF_SIGNAL = re.compile(
    r"^" + _LIST_MARKER + r"(?:Read|Run|Check|Create|Add|Remove|Move|Use|Set|"
    r"Install|Configure|Deploy|Test|Verify|Build|Start|Stop|Open|Save|"
    r"Copy|Delete|Write|Edit|Update|Generate|Execute|Validate|Parse|"
    r"Extract|Transform|Import|Export|Send|Fetch|Call|Return)\b",
    re.IGNORECASE,
)
# Bounded `input.{0,200}?output` (not greedy `input.*output`): the unbounded form
# is O(n^2) under findall() — ReDoS on large single-line input. 200 chars still
# catches genuine "input … output" example pairs.
_RE_DIFF_EXAMPLE = re.compile(
    r"(?i)(example\s*[0-9:#]|input.{0,200}?output|e\.g\.|for instance|for example)"
)
_RE_DIFF_NOISE = re.compile(
    r"(?i)(you (might|could|should|may) (want to|consider|possibly)|"
    r"it is important to note that|as mentioned (above|earlier|before)|"
    r"in other words|keep in mind that|note that|please note|"
    r"make sure to save|don't forget to|always test your)"
)

# ---------------------------------------------------------------------------
# Coherence patterns
# ---------------------------------------------------------------------------
_RE_IMPERATIVE_INSTRUCTION = re.compile(
    r"^\s*" + _LIST_MARKER + r"(?:Run|Create|Add|Check|Remove|Move|Use|Set|Install|"
    r"Configure|Deploy|Test|Verify|Build|Start|Stop|Open|Save|Copy|Delete|"
    r"Write|Edit|Update|Generate|Execute|Validate|Parse|Extract|Transform|"
    r"Import|Export|Send|Fetch|Call|Return)\b(.+)",
    re.IGNORECASE,
)
