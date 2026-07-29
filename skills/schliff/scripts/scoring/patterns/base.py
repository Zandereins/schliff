"""Format-agnostic regex patterns shared across all scoring dimensions."""
import re

__all__ = [
    # Efficiency
    "_RE_ACTIONABLE_LINES",
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
_RE_SPECIFIC_REF = re.compile(r"(`[^`]+`|[\w/]+\.\w+|/[\w/]+)")
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
_RE_CONCRETE_CMD = re.compile(r"(`[^`]+`|[\w/.-]+\.\w+|/[\w/]+)")
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
_RE_SEC_DATA_EXFIL = re.compile(
    r"(?:\b(?:curl|wget|fetch|nc|ncat|netcat)\s+[^\n]{0,200}(?:\$\(|`[^`]*`|<\(|\|)|"
    r"\$\(cat\s[^\)]+\)\s*\|\s*(?:curl|wget|nc|netcat)|"
    r"\b(?:curl|wget)\s+[^\n]{0,200}(?:--data|--upload|-d\s|-F\s|-T\s)[^\n]{0,200}(?:https?://|ftp://))",
    re.IGNORECASE,
)
_RE_SEC_ENV_LEAK = re.compile(
    r"(?:(?:echo|print|cat|send|post|curl|wget|log)\s[^\n]{0,200}(?:\$[A-Z_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)|"
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
_RE_SEC_DANGEROUS_CMD = re.compile(
    r"(?:rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(?![A-Za-z0-9_.-])|"
    r"rm\s+-[a-z]*f[a-z]*r[a-z]*\s+/(?![A-Za-z0-9_.-])|"
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
