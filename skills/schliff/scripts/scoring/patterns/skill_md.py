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
_RE_REAL_EXAMPLES = re.compile(
    r"(?i)(example\s*[0-9:#]|input.*output|e\.g\.|for instance|for example)"
)
_RE_REFS = re.compile(r"(references|scripts|templates)/[\w./-]+")
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
_RE_ERROR_BEHAVIOR = re.compile(
    r"(?i)(on\s+error|error\s+handling|if\s+\w[\w ]{0,80}\s+fails?|when\s+\w[\w ]{0,80}\s+fails?|"
    r"graceful(?:ly)?\s+(?:handle|degrad\w+|fail)|recover(?:y|s)?\s+(?:from|when))"
)
_RE_IDEMPOTENCY = re.compile(
    r"(?i)(idempotent|safe to (?:re-?run|run (?:again|twice|multiple))|"
    r"running (?:again|twice)|no side.?effects?|re-?entrant)"
)
_RE_DEPENDENCY_DECL = re.compile(
    r"(?i)(requires?[:\s]+(?:python|node|npm|pip|git|jq|bash|ruby|go)\b|"
    r"depends?\s+on|prerequisite|"
    r"needs?\s+(?:python|node|npm|pip|git|jq|bash|ruby|go)\b|"
    r"install\s+\w+\s+first)"
)
_RE_NAMESPACE_ISOLATION = re.compile(
    r"(?i)(namespace\s+\w+|namespaced?\b|__\w+__|"
    r"@[\w-]+/[\w-]+|plugin[_-]\w+|scoped\s+to\b)"
)
_RE_VERSION_COMPAT = re.compile(
    r"(?i)(version\s*[><=!]+\s*[\d.]+|compatible\s+with\s+\w+\s+v?\d|"
    r"requires?\s+\w+\s*[><=]+\s*[\d.]+|minimum\s+version|"
    r"supported\s+versions?|works\s+with\s+\w+\s+v?\d+\.\d+)"
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


def _has_skill_domain_signal(prompt: str) -> float:
    """Check if prompt is about skills (not generic code/config).

    Returns a multiplier: 1.8 for strong signal, 1.0 for neutral, 0.2 for anti-signal.
    Anti-signal is set to 0.2 (not 0.4) so that high-scoring generic-action prompts
    (e.g. 'optimize my database queries') cannot accumulate enough TF-IDF weight to
    exceed the 4.5 threshold even when they contain multiple skill-adjacent verbs.
    """
    prompt_lower = prompt.lower()

    if _RE_STRONG_DOMAIN_SIGNAL.search(prompt_lower):
        return 1.8

    if "skill" in prompt_lower:
        return 1.2

    if _RE_ANTI_DOMAIN_SIGNAL.search(prompt_lower):
        return 0.2

    return 1.0
