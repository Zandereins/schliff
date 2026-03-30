"""System-prompt-specific regex patterns for all scoring dimensions.

Prefix: _RE_SP_ (System Prompt).
All patterns use bounded quantifiers to prevent ReDoS.
"""
import re

# ---------------------------------------------------------------------------
# structure_prompt patterns (Dimension 1)
# ---------------------------------------------------------------------------

_RE_SP_ROLE_DEFINITION = re.compile(
    r"(?i)(you are|your role is|act as|you're a|as a \w+ assistant|your purpose)",
)

_RE_SP_TASK_DESCRIPTION = re.compile(
    r"(?i)(your (task|job|goal|objective|mission) is"
    r"|you (will|should|must) \w+ (the|a|an)"
    r"|primary function)",
)

_RE_SP_CONSTRAINT_BLOCK = re.compile(
    r"(?i)(constraints?:|rules?:|limitations?:|boundaries:|guardrails:"
    r"|do not|never|must not|always)",
)

_RE_SP_OUTPUT_FORMAT = re.compile(
    r"(?i)(respond (in|with|using)"
    r"|output (format|as)"
    r"|return (a|the)"
    r"|format:"
    r"|your (response|reply|answer) (should|must|will))",
)

_RE_SP_EXAMPLES = re.compile(
    r"(?i)(examples?:|for example|e\.g\.|<example>"
    r"|input.{0,40}output"
    r"|here'?s (a|an|one))",
)

_RE_SP_SECTION_SEPARATOR = re.compile(
    r"(?m)(^##?\s+\S|<\w{1,30}>|^---$)",
)

_RE_SP_DEAD_CONTENT = re.compile(
    r"(?i)(TODO|FIXME|HACK|XXX|placeholder|TBD|to be determined|fill in)",
)


# ---------------------------------------------------------------------------
# output_contract patterns (Dimension 2)
# ---------------------------------------------------------------------------

_RE_SP_FORMAT_SPEC = re.compile(
    r"(?i)(respond (in|with|as)"
    r"|format (as|your)"
    r"|output (as|in|format)"
    r"|return (JSON|XML|YAML|markdown|plain text|HTML|CSV))",
)

_RE_SP_LENGTH_CONSTRAINT = re.compile(
    r"(?i)(max(imum)?\s+\d+\s+(words?|tokens?|sentences?|characters?|paragraphs?|lines?)"
    r"|keep.{0,20}(short|brief|concise|under \d+)"
    r"|limit.{0,20}(to \d+|length))",
)

_RE_SP_TONE_VOICE = re.compile(
    r"(?i)(tone:|voice:|style:"
    r"|speak (as|like)"
    r"|write (in|with) a"
    r"|formal|informal|professional|friendly|technical|casual|authoritative)",
)

_RE_SP_SCHEMA_DEF = re.compile(
    r'(?i)(\{[\s\S]{5,50}\}|"type":\s*"|fields?:|properties:|required:|schema:)',
)

_RE_SP_REQUIRED_FIELDS = re.compile(
    r"(?i)(must include|required fields?"
    r"|always include"
    r"|every response (must|should) (have|contain|include))",
)

_RE_SP_FORBIDDEN_CONTENT = re.compile(
    r"(?i)(never (include|mention|output|say|generate|reveal)"
    r"|do not (include|mention|output|reveal|disclose)"
    r"|forbidden:|prohibited:|exclude:)",
)

_RE_SP_RESPONSE_STRUCTURE = re.compile(
    r"(?i)(first[,.]|then[,.]|finally[,.]"
    r"|step \d"
    r"|begin (with|by)|end (with|by)|start (with|by)"
    r"|your response should (start|begin|end))",
)

_RE_SP_ERROR_RESPONSE = re.compile(
    r"(?i)(if .{0,40}(error|fail|unknown|unclear|can'?t|unable)"
    r"|when .{0,30}(error|fail)"
    r"|error (response|format|message)"
    r"|on (error|failure))",
)

_RE_SP_VALIDATION_INSTRUCTION = re.compile(
    r"(?i)(verify|validate|check|ensure|confirm)"
    r".{0,30}(before (respond|return|output)|your (response|output|answer))",
)

_RE_SP_EXAMPLE_OUTPUT = re.compile(
    r"(?i)(example (output|response)"
    r"|sample (output|response)"
    r"|here'?s what .{0,20}(look|should)"
    r"|expected (output|response))",
)


# ---------------------------------------------------------------------------
# completeness patterns (Dimension 7)
# ---------------------------------------------------------------------------

_RE_SP_ERROR_HANDLING = re.compile(
    r"(?i)(if .{0,30}(error|fail|invalid|wrong|broken|missing)"
    r"|when .{0,20}(error|fail)"
    r"|error (handling|response|behavior))",
)

_RE_SP_EDGE_CASES = re.compile(
    r"(?i)(edge case|corner case|special case|exception"
    r"|unusual (input|case|situation)"
    r"|if (the|an?) (input|request|query) is (empty|blank|missing|malformed))",
)

_RE_SP_AMBIGUITY_HANDLING = re.compile(
    r"(?i)(if (unclear|ambiguous|vague|confusing|uncertain)"
    r"|when (you'?re?|the (intent|meaning) is) (unsure|unclear|not sure|uncertain)"
    r"|ask (for|the user for) clarification)",
)

_RE_SP_OFF_TOPIC = re.compile(
    r"(?i)(off.?topic|out of scope"
    r"|unrelated (question|request|topic)"
    r"|not (within|in) (your|the) (scope|domain)"
    r"|if (the user|someone) asks? (about|for) .{0,30}(unrelated|outside))",
)

_RE_SP_MULTI_TURN = re.compile(
    r"(?i)(follow.?up"
    r"|conversation (history|context)"
    r"|previous (message|turn|question)"
    r"|referring (back|to earlier)"
    r"|maintain context"
    r"|remember (earlier|previous|the))",
)

_RE_SP_LANGUAGE_LOCALE = re.compile(
    r"(?i)(language:"
    r"|respond in \w+"
    r"|if .{0,20}(another|different|foreign) language"
    r"|locale|translation|multilingual|english only)",
)

_RE_SP_EMPTY_INPUT = re.compile(
    r"(?i)(empty (input|message|query|request)"
    r"|blank (input|message)"
    r"|null"
    r"|no (input|message|content) (provided|given|received)"
    r"|if .{0,20}(nothing|empty))",
)

_RE_SP_RATE_LIMIT = re.compile(
    r"(?i)(rate limit"
    r"|too many (requests?|calls?)"
    r"|throttl"
    r"|quota"
    r"|if .{0,30}(exceed|limit|cap))",
)

_RE_SP_GRACEFUL_DEGRADE = re.compile(
    r"(?i)(graceful(ly)?\s+(fail|degrad|handle)"
    r"|best effort"
    r"|partial (response|result)"
    r"|if .{0,30}(can'?t fully|unable to complete|partial))",
)

_RE_SP_NONOBVIOUS_EXAMPLE = re.compile(
    r"(?i)(example|e\.g\.)",
)


# ---------------------------------------------------------------------------
# security defense patterns (Dimension 5, Part B)
# ---------------------------------------------------------------------------

_RE_SP_INSTRUCTION_HIERARCHY = re.compile(
    r"(?i)(system instructions?.{0,30}(override|take precedence|priority over)"
    r"|ignore.{0,20}user.{0,20}(if|when|that).{0,20}contradict)",
)

_RE_SP_IDENTITY_ANCHORING = re.compile(
    r"(?i)(you are .{5,50}\. (do not|never) (pretend|act as|claim to be|change your) )",
)

_RE_SP_INPUT_SANITIZATION = re.compile(
    r"(?i)(user input.{0,30}(untrusted|sanitize|validate|may contain)"
    r"|treat .{0,20}(user|external).{0,20}(as data|not as instruction))",
)

_RE_SP_OUTPUT_FILTERING = re.compile(
    r"(?i)(never (reveal|output|disclose|share).{0,30}(system prompt|these instructions|internal|private)"
    r"|do not (repeat|echo|show).{0,30}(prompt|instructions))",
)

_RE_SP_SCOPE_LIMITATION = re.compile(
    r"(?i)(only (discuss|answer|respond to|help with).{0,30}(topic|domain|subject)"
    r"|(off.?topic|out of scope|outside.{0,20}(scope|domain)).{0,30}(decline|refuse|redirect))",
)

_RE_SP_CANARY_TRIPWIRE = re.compile(
    r"(?i)(canary|tripwire"
    r"|if .{0,30}(asks? (for|about)|requests?) .{0,30}(system prompt|instructions).{0,30}(refuse|decline|ignore))",
)

_RE_SP_CONTENT_POLICY = re.compile(
    r"(?i)(content policy|usage policy"
    r"|terms of (service|use)"
    r"|acceptable use"
    r"|safety guidelines)",
)


# ---------------------------------------------------------------------------
# composability patterns (Dimension 6)
# ---------------------------------------------------------------------------

_RE_SP_SCOPE_BOUNDARIES = re.compile(
    r"(?i)(you (only|exclusively) (handle|deal with|assist with|help with)"
    r"|your (scope|domain|responsibility) is"
    r"|limited to)",
)

_RE_SP_HANDOFF_PATTERNS = re.compile(
    r"(?i)(transfer to|hand off to|escalate to|route to"
    r"|pass (the user|this) to"
    r"|redirect to"
    r"|suggest (contacting|speaking with))",
)

_RE_SP_TOOL_AWARENESS = re.compile(
    r"(?i)(tools?:|functions?:"
    r"|available (tools|functions)"
    r"|you have access to"
    r"|you can (call|use|invoke))",
)

_RE_SP_CONTEXT_WINDOW = re.compile(
    r"(?i)(conversation history"
    r"|previous messages?"
    r"|context (window|length|limit)"
    r"|if (context|conversation) (exceeds?|too long)"
    r"|summarize (previous|earlier))",
)

_RE_SP_STATELESSNESS = re.compile(
    r"(?i)(you (do not|don't) (have|retain|remember|store) (memory|state|history)"
    r"|each (request|conversation|message) is (independent|separate)"
    r"|no (persistent|long-term) (memory|state))",
)

_RE_SP_ERROR_FALLBACK = re.compile(
    r"(?i)(if (you|the (tool|function|API)) (can'?t|fail|error)"
    r"|on (error|failure)"
    r"|fallback (to|behavior)"
    r"|graceful(ly)? (fail|degrad))",
)

_RE_SP_INPUT_CONTRACT = re.compile(
    r"(?i)(expects?|requires?"
    r"|input (format|schema|must)"
    r"|the user (will|should) provide"
    r"|accepts? (JSON|text|XML|structured))",
)

_RE_SP_OUTPUT_CONTRACT_DOWNSTREAM = re.compile(
    r"(?i)(so that (the next|downstream|another)"
    r"|for (consumption|parsing) by"
    r"|machine.?readable"
    r"|structured (for|to enable))",
)

_RE_SP_VERSIONING = re.compile(
    r"(?i)(version|v\d+\.\d+"
    r"|compat(ible|ibility)"
    r"|deprecated"
    r"|breaking change)",
)

_RE_SP_IDEMPOTENCY = re.compile(
    r"(?i)(idempotent"
    r"|safe to (re-?run|retry|call (again|multiple))"
    r"|same (input|request).{0,20}same (output|result))",
)


# ---------------------------------------------------------------------------
# __all__ — export every _RE_SP_ pattern
# ---------------------------------------------------------------------------

__all__ = [
    # structure_prompt
    "_RE_SP_ROLE_DEFINITION",
    "_RE_SP_TASK_DESCRIPTION",
    "_RE_SP_CONSTRAINT_BLOCK",
    "_RE_SP_OUTPUT_FORMAT",
    "_RE_SP_EXAMPLES",
    "_RE_SP_SECTION_SEPARATOR",
    "_RE_SP_DEAD_CONTENT",
    # output_contract
    "_RE_SP_FORMAT_SPEC",
    "_RE_SP_LENGTH_CONSTRAINT",
    "_RE_SP_TONE_VOICE",
    "_RE_SP_SCHEMA_DEF",
    "_RE_SP_REQUIRED_FIELDS",
    "_RE_SP_FORBIDDEN_CONTENT",
    "_RE_SP_RESPONSE_STRUCTURE",
    "_RE_SP_ERROR_RESPONSE",
    "_RE_SP_VALIDATION_INSTRUCTION",
    "_RE_SP_EXAMPLE_OUTPUT",
    # completeness
    "_RE_SP_ERROR_HANDLING",
    "_RE_SP_EDGE_CASES",
    "_RE_SP_AMBIGUITY_HANDLING",
    "_RE_SP_OFF_TOPIC",
    "_RE_SP_MULTI_TURN",
    "_RE_SP_LANGUAGE_LOCALE",
    "_RE_SP_EMPTY_INPUT",
    "_RE_SP_RATE_LIMIT",
    "_RE_SP_GRACEFUL_DEGRADE",
    "_RE_SP_NONOBVIOUS_EXAMPLE",
    # security defense
    "_RE_SP_INSTRUCTION_HIERARCHY",
    "_RE_SP_IDENTITY_ANCHORING",
    "_RE_SP_INPUT_SANITIZATION",
    "_RE_SP_OUTPUT_FILTERING",
    "_RE_SP_SCOPE_LIMITATION",
    "_RE_SP_CANARY_TRIPWIRE",
    "_RE_SP_CONTENT_POLICY",
    # composability
    "_RE_SP_SCOPE_BOUNDARIES",
    "_RE_SP_HANDOFF_PATTERNS",
    "_RE_SP_TOOL_AWARENESS",
    "_RE_SP_CONTEXT_WINDOW",
    "_RE_SP_STATELESSNESS",
    "_RE_SP_ERROR_FALLBACK",
    "_RE_SP_INPUT_CONTRACT",
    "_RE_SP_OUTPUT_CONTRACT_DOWNSTREAM",
    "_RE_SP_VERSIONING",
    "_RE_SP_IDEMPOTENCY",
]
