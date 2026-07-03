"""Scorer-level tests for the AGENTS.md operational_coverage (opcov) dimension.

Spec: docs/specs/agents-md-operational-coverage.md (§4 detection + hardening,
§7 determinism). These tests pin the anti-gaming gates (G1-G5, D, C, A), the
recall rescues (PNNL code_style fallback, kudu test, MacroGraph negation guard),
and the determinism invariants (raw == normalized, purity, byte-identity for
other formats).

Fixtures are inlined (copied from the scratchpad red-team / repro suite) so the
module is self-contained.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scoring.composite import compute_composite
from scoring.operational_coverage import score_operational_coverage
from scoring.registry import (
    _INSTRUCTION_FILE_SCORERS,
    WEIGHT_PROFILES,
    get_scorers,
    get_weights,
)
from shared import build_scores

_CORPUS = Path(__file__).resolve().parents[4] / "docs" / "launch" / "corpus" / "agents"
_MODULE_SRC = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "scoring" / "operational_coverage.py"
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _op(tmp_path: Path, content: str) -> dict:
    p = tmp_path / "AGENTS.md"
    p.write_text(content, encoding="utf-8")
    return score_operational_coverage(str(p))


def _comp(tmp_path: Path, content: str) -> float:
    # Unique filename per content: read_skill_safe caches by resolved path, so a
    # shared name would return stale content on the second call in a comparison.
    import hashlib

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    p = tmp_path / f"{digest}_AGENTS.md"
    p.write_text(content, encoding="utf-8")
    scores = build_scores(str(p), None, fmt="agents.md")
    return compute_composite(scores, fmt="agents.md")["score"]


# --------------------------------------------------------------------------- #
# Fixtures (inlined)
# --------------------------------------------------------------------------- #

A_hollow = """---
name: acme-web
description: Context for the Acme web application monorepo
---

# Acme Web

Acme Web is the customer-facing storefront. It is a large application that has
grown over several years and serves millions of users across many regions.

## Architecture

The application follows a layered architecture. The presentation layer renders
the UI, the service layer orchestrates business logic, and the data layer talks
to the database. Each layer is owned by a different team and they coordinate
through well-defined interfaces and regular design reviews.

## Conventions

We value readability over cleverness. We prefer explicit code to implicit magic.
We write small functions with single responsibilities. We document the why, not
the what. We try to keep modules focused and cohesive so the codebase stays
approachable for new engineers joining the various product teams.

## Testing Philosophy

Testing is important to us. We believe that good tests give us the confidence to
move quickly without breaking things. We aim for meaningful coverage rather than
chasing a number, and we treat flaky tests as bugs that must be fixed promptly.

## Notes

Please be respectful in code review. Communicate early when blocked. Ask
questions when something is unclear rather than guessing at intent.
"""

B_operational = """---
name: acme-web
description: Context for the Acme web application monorepo
---

# Acme Web

Acme Web is the customer-facing storefront monorepo managed with pnpm workspaces.

## Setup

```bash
pnpm install
cp .env.example .env.local
pnpm db:migrate
```

## Build & Run

```bash
pnpm dev          # start dev server on :3000
pnpm build        # production build, output to dist/
pnpm start        # serve the production build
```

## Test

```bash
pnpm test            # unit tests (vitest)
pnpm test:e2e        # playwright end-to-end
pnpm lint && pnpm typecheck
```

Run `pnpm test --filter @acme/checkout` to scope tests to one package.

## Conventions

Use `pnpm changeset` for every user-facing change. Imports sorted by `eslint`.
Commit messages follow Conventional Commits. Never edit `dist/` by hand.

## Gotchas

The dev server needs Redis: `docker compose up redis -d` before `pnpm dev`.
`pnpm db:reset` wipes local data — never run it against a tunneled prod DB.
"""

C_gaming = """---
name: acme-web
description: Context for the Acme web application monorepo
---

# Acme Web

## Setup

## Build

## Test

## Conventions

## Gotchas
"""

D_fence_gaming = """---
name: acme-web
description: Context for the Acme web application monorepo
---

# Acme Web

## Setup

```bash
echo "hello"
ls -la
pwd
echo "setting up"
```

## Build

```bash
echo "building"
cat README.md
ls
echo "done"
```

## Test

```bash
echo "testing"
true
ls -la
echo "ok"
```

## Conventions

```bash
echo "be nice"
whoami
date
```

## Gotchas

```bash
echo "careful"
ls
```
"""

E_inline_useful = """---
name: acme-web
description: Context for the Acme web application monorepo
---

# Acme Web

Acme Web is a pnpm-workspace monorepo for the storefront.

## Setup

Install with `pnpm install`, then copy `.env.example` to `.env.local` and run
`pnpm db:migrate` to create the local schema. Redis is required: start it with
`docker compose up redis -d` before anything else.

## Build & Run

Start the dev server on port 3000 with `pnpm dev`. Produce a production build
into `dist/` with `pnpm build`, and serve it with `pnpm start`.

## Test

Unit tests run via `pnpm test` (vitest); end-to-end via `pnpm test:e2e`
(playwright). Always run `pnpm lint` and `pnpm typecheck` before pushing. Scope
to one package with `pnpm test --filter @acme/checkout`.

## Conventions

Every user-facing change needs a `pnpm changeset`. Commit messages follow
Conventional Commits. Never edit `dist/` by hand.

## Gotchas

`pnpm db:reset` wipes local data — never point it at a tunneled prod DB.
"""

# Red-team gaming fixtures
G1_minimal_max = """# My Project

## Setup
Get started quickly.
```bash
git status
```

## Build
Then build it.
```bash
git status
```

## Test
And test it.
```bash
git status
```

## Conventions
You should write good code. Always be consistent. Never be sloppy.

## Pull Requests
Always commit with a clear message. You must follow the branch naming.

## Gotchas
Be careful. This is important. Note that things can break.
"""

G2_inline_word = """# My Project

## Setup
We use `npm` for everything here, it is great.

## Build
The `make` system is documented elsewhere in our wiki.

## Testing
Our `pytest` philosophy values readability above all.

## Style
You should prefer clarity. Always document your code well.

## Commits
You must write good commit messages and follow convention.

## Notes
Be respectful and communicate early. This is important.
"""

G3_platitude = """# Guidelines

## Quick Start
```sh
npm install
```

## Usage
```sh
npm install
```

## Quality
```sh
npm install
```

## Best Practices
We value good code. You should always do your best. Never give up.

## Contributing
Please be kind. Always communicate. We require respect.

## Important Notes
Remember to be careful. Note that this matters a lot to us.
"""

G4_prose_verbs = """# Project

## Setup
First, `go to the dashboard` and sign in.

## Build
`make sure to` save your work before continuing.

## Test
`just check it` works in the browser manually.
"""

G5_directive_only = """# Project

## Code Style
Always prefer readability. You should keep functions small.

## Commit Rules
You must write clear commits. Always squash before merge.

## Gotchas
Be careful with the cache. This is important to remember.
"""

_NEGATION_ONLY_TEST = """# Project

## Test
Never run `pytest` in this repository; it corrupts the fixtures.
"""


# --------------------------------------------------------------------------- #
# Details contract
# --------------------------------------------------------------------------- #

def test_details_contract(tmp_path):
    r = _op(tmp_path, B_operational)
    assert isinstance(r["score"], int)
    assert "details" in r
    cats = r["details"]["categories"]
    for cat in ("setup", "build", "test", "code_style", "gotchas", "pr"):
        assert cat in cats
        assert isinstance(cats[cat]["credited"], bool)
        assert isinstance(cats[cat]["reason"], str)
    assert isinstance(r["details"]["distinct_commands"], int)


# --------------------------------------------------------------------------- #
# Anti-gaming
# --------------------------------------------------------------------------- #

def test_G1_git_status_farm(tmp_path):
    r = _op(tmp_path, G1_minimal_max)
    cats = r["details"]["categories"]
    assert r["score"] <= 15
    assert cats["setup"]["credited"] is False
    assert cats["build"]["credited"] is False
    assert cats["test"]["credited"] is False
    assert _comp(tmp_path, G1_minimal_max) < _comp(tmp_path, B_operational)


def test_G2_inline_name_drop(tmp_path):
    r = _op(tmp_path, G2_inline_word)
    assert r["score"] == 0


def test_G3_npm_install_farm(tmp_path):
    r = _op(tmp_path, G3_platitude)
    cats = r["details"]["categories"]
    assert r["details"]["distinct_commands"] == 1
    assert cats["setup"]["credited"] is True
    assert cats["build"]["credited"] is False
    assert cats["test"]["credited"] is False
    assert r["score"] <= 20
    assert _comp(tmp_path, G3_platitude) < _comp(tmp_path, B_operational)


def test_G4_prose_verbs(tmp_path):
    r = _op(tmp_path, G4_prose_verbs)
    assert r["score"] == 0


def test_G5_directive_only_no_command(tmp_path):
    r = _op(tmp_path, G5_directive_only)
    cats = r["details"]["categories"]
    assert cats["setup"]["credited"] is False
    assert cats["build"]["credited"] is False
    assert cats["test"]["credited"] is False
    assert r["score"] <= 30
    assert _comp(tmp_path, G5_directive_only) < _comp(tmp_path, B_operational)


def test_D_fence_gaming(tmp_path):
    assert _op(tmp_path, D_fence_gaming)["score"] == 0


def test_C_bare_headings(tmp_path):
    assert _op(tmp_path, C_gaming)["score"] == 0


def test_A_hollow(tmp_path):
    r = _op(tmp_path, A_hollow)
    assert r["score"] <= 15
    assert r["details"]["categories"]["code_style"]["credited"] is False


# --------------------------------------------------------------------------- #
# Recall (real operational docs)
# --------------------------------------------------------------------------- #

def test_B_operational(tmp_path):
    r = _op(tmp_path, B_operational)
    cats = r["details"]["categories"]
    assert cats["setup"]["credited"] is True
    assert cats["build"]["credited"] is True
    assert cats["test"]["credited"] is True
    assert r["score"] >= 80


def test_E_inline_useful(tmp_path):
    r = _op(tmp_path, E_inline_useful)
    cats = r["details"]["categories"]
    assert cats["setup"]["credited"] is True
    assert cats["build"]["credited"] is True
    assert cats["test"]["credited"] is True
    assert r["score"] >= 60
    assert _comp(tmp_path, E_inline_useful) > _comp(tmp_path, D_fence_gaming)


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_recall_pnnl_code_style():
    path = _CORPUS / "PNNL-CIM-Tools__CIM-Graph__AGENTS.md.md"
    r = score_operational_coverage(str(path))
    assert r["details"]["categories"]["code_style"]["credited"] is True
    assert r["score"] >= 15


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_recall_kudu_test():
    path = _CORPUS / "AdventDevInc__kudu__AGENTS.md.md"
    r = score_operational_coverage(str(path))
    assert r["details"]["categories"]["test"]["credited"] is True


@pytest.mark.skipif(not _CORPUS.is_dir(), reason="corpus fixtures not present")
def test_recall_macrograph_test_via_positive_format():
    path = _CORPUS / "Brendonovich__MacroGraph__AGENTS.md.md"
    r = score_operational_coverage(str(path))
    assert r["details"]["categories"]["test"]["credited"] is True


def test_negation_only_test_token_not_credited(tmp_path):
    r = _op(tmp_path, _NEGATION_ONLY_TEST)
    assert r["details"]["categories"]["test"]["credited"] is False


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

def _raw_eq_normalized(tmp_path, content, label):
    from scoring.formats import normalize_content

    raw_path = tmp_path / f"{label}_raw.md"
    raw_path.write_text(content, encoding="utf-8")
    a = score_operational_coverage(str(raw_path))

    norm_path = tmp_path / f"{label}_norm.md"
    norm_path.write_text(normalize_content(content, "agents.md"), encoding="utf-8")
    b = score_operational_coverage(str(norm_path))

    assert a["score"] == b["score"], label
    assert a["details"]["categories"] == b["details"]["categories"], label


def test_determinism_raw_equals_normalized(tmp_path):
    _raw_eq_normalized(tmp_path, B_operational, "B")
    _raw_eq_normalized(tmp_path, A_hollow, "A")
    if _CORPUS.is_dir():
        pnnl = (_CORPUS / "PNNL-CIM-Tools__CIM-Graph__AGENTS.md.md").read_text(
            encoding="utf-8"
        )
        _raw_eq_normalized(tmp_path, pnnl, "PNNL")


def test_determinism_repeatable(tmp_path):
    p = tmp_path / "AGENTS.md"
    p.write_text(B_operational, encoding="utf-8")
    assert score_operational_coverage(str(p)) == score_operational_coverage(str(p))


def test_purity_no_forbidden_imports():
    src = _MODULE_SRC.read_text(encoding="utf-8")
    for forbidden in (
        "import time", "import random", "import os",
        "urllib", "datetime", "environ",
    ):
        assert forbidden not in src, forbidden


# --------------------------------------------------------------------------- #
# Byte-identity for other formats
# --------------------------------------------------------------------------- #

def test_opcov_not_in_other_format_scorers():
    for fmt in ("skill.md", "claude.md", "cursorrules", "system_prompt"):
        assert "operational_coverage" not in get_scorers(fmt)
        assert "operational_coverage" not in get_weights(fmt)


def test_instruction_file_scorers_unchanged():
    assert len(_INSTRUCTION_FILE_SCORERS) == 8
    assert "operational_coverage" not in _INSTRUCTION_FILE_SCORERS


def test_opcov_in_agents_md_only():
    assert "operational_coverage" in get_scorers("agents.md")
    assert "operational_coverage" in WEIGHT_PROFILES["agents.md"]


# --------------------------------------------------------------------------- #
# Adversarial-review regressions (2026-07-03 multi-agent review of the branch)
# --------------------------------------------------------------------------- #

def test_heading_regex_no_redos():
    """A `\\s+(.*\\S)\\s*$` heading tail is quadratic on whitespace-only heading
    lines (same ReDoS class as the project's earlier content-regex fix). The
    pattern must stay linear: a 200k-space heading line completes in
    milliseconds — the quadratic pattern needs minutes at this size."""
    import time

    from scoring.operational_coverage import _HEADING_RE

    malicious = "#" + " " * 200_000
    benign = "# " + "a " * 100_000
    _HEADING_RE.match(benign)  # warm-up
    start = time.perf_counter()
    _HEADING_RE.match(malicious)
    _HEADING_RE.match(benign)
    assert time.perf_counter() - start < 0.5


def test_directive_gate_rejects_prose_homonyms(tmp_path):
    """make/go/task/just in raw prose must NOT satisfy the directive
    concreteness gate — a platitude doc farmed all 40 directive points."""
    r = _op(
        tmp_path,
        """# Project

## Conventions

You must always make sure the code is clean. Never rush your work, just take it slow.

## Gotchas

Be careful: you must always double check everything before you go further. Never assume the task is done.

## Pull Requests

Always make sure your work is reviewed. You must never merge without approval of the task owner.
""",
    )
    assert r["score"] == 0


def test_fence_info_string_no_desync(tmp_path):
    """A CommonMark opener with an info string (```bash title="x") must toggle
    fence state — otherwise the parser state inverts for the rest of the doc
    and later real command blocks are scanned as prose."""
    r = _op(
        tmp_path,
        """# P

## Example

```bash title="demo"
echo hi
```

## Setup

```bash
npm install
```
""",
    )
    assert "npm install" in r["details"]["commands"]


def test_four_backtick_fence_no_desync(tmp_path):
    r = _op(
        tmp_path,
        """# P

````markdown
```bash
placeholder-inner-fence
```
````

## Setup

```bash
pnpm install
```
""",
    )
    assert "pnpm install" in r["details"]["commands"]


def test_negation_is_sentence_scoped(tmp_path):
    """§4.2.5: 'Never commit to main. Run `pnpm test` before pushing.' keeps
    the test credit; 'don't forget to run X' is a positive instruction; and
    'use X instead of Y' positively recommends X."""
    r = _op(
        tmp_path,
        """# P

## Workflow

Never commit directly to main. Run `pnpm test` before pushing.
Don't forget to run `pnpm install` first.
Use `pnpm build` instead of `npm run build`.
""",
    )
    cmds = r["details"]["commands"]
    assert "pnpm test" in cmds
    assert "pnpm install" in cmds
    assert "pnpm build" in cmds


@pytest.mark.parametrize(
    ("segment", "inline", "family"),
    [
        # read-only refinement: -v with an operand (or on an intrinsic) is verbose
        ("pytest -v", False, "test"),
        ("pytest -v tests/", False, "test"),
        ("cargo build -v", False, "build"),
        # interpreter delegation
        ("python -m pytest", False, "test"),
        ("python3 -m pip install -r requirements.txt", False, "setup"),
        ("python -m venv .venv", False, "setup"),
        ("python -m build", False, "build"),
        ("python manage.py migrate", False, "setup"),
        # runner wrapper scripts
        ("./gradlew build", False, "build"),
        ("./gradlew test", False, "test"),
        ("./mvnw install", False, "setup"),
        # containers (spec §4.2.1 strict tier)
        ("docker build -t app .", False, "build"),
        ("docker compose build", False, "build"),
        # exec-delegation runners
        ("npx playwright test", False, "test"),
        ("npx tsc --noEmit", False, "build"),
        ("bunx vitest", False, "test"),
        ("pnpm exec vitest", False, "test"),
        ("uv pip install -e .", False, "setup"),
        # spec §4.2 setup family: cp .env* and *migrate
        ("cp .env.example .env", False, "setup"),
        ("pnpm db:migrate", False, "setup"),
        # guarded make: a flag is a qualifying command shape
        ("make -j4", False, "build"),
        # spec §4.2 puts tsc in the build family
        ("tsc", False, "build"),
        # inline $-prompt is a command-shape signal (spec §4.2.3)
        ("$ pytest", True, "test"),
    ],
)
def test_classification_recall(segment, inline, family):
    from scoring.operational_coverage import _classify

    assert _classify(segment, inline) == family


@pytest.mark.parametrize(
    ("segment", "inline"),
    [
        # git is read-only-junk or PR-directive, never a command (spec §4.2.2)
        ("git add .", False),
        ("git init", False),
        ("git status", False),
        # English prose around guarded verbs
        ("make tests pass", True),
        ("go to the dashboard", True),
        # inspection stays junk
        ("npm -v", False),
        ("ruff -h", False),
        ("pytest --version", False),
        ("docker ps", False),
    ],
)
def test_classification_still_rejects(segment, inline):
    from scoring.operational_coverage import _classify

    assert _classify(segment, inline) is None


def test_known_limit_plausible_fabrication_scores_high(tmp_path):
    """DOCUMENTED LIMIT (spec §4.4 accepted risk): a doc whose commands are
    syntactically valid but fabricated is textually indistinguishable from a
    genuine minimal AGENTS.md — no deterministic text scorer can tell them
    apart without executing the commands. opcov therefore credits it. The
    anti-gaming guarantee is scoped to WORTHLESS text (junk commands,
    platitudes, name-drops), not to plausible lies."""
    r = _op(
        tmp_path,
        """---
name: fake
description: plausible fabrication
---

# Fake Project

## Setup

```bash
npm install
```

## Test

```bash
npm test
```

## Code Style

Always follow the `eslint.config.js` rules. Never use `var` in new code.
""",
    )
    assert r["details"]["categories"]["setup"]["credited"] is True
    assert r["details"]["categories"]["test"]["credited"] is True
