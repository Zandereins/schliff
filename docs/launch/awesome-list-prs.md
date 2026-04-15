# Awesome List PR Drafts

10 PR drafts for submitting Schliff to relevant awesome lists.

---

## 1. hesreallyhim/awesome-claude-code

- **Repo:** https://github.com/hesreallyhim/awesome-claude-code
- **Category:** Skills/Tools
- **PR Title:** Add Schliff — deterministic quality scorer for CLAUDE.md and skill files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Skills/Tools section.
>
> Schliff is a deterministic quality scorer purpose-built for AI agent instruction files like CLAUDE.md and SKILL.md. It scores files across 7 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity), runs as a pre-commit hook or GitHub Action, and suggests ranked fixes with estimated score impact (`schliff suggest`). Zero dependencies, Python 3.9+ stdlib only, 732 tests, MIT license.
>
> Directly relevant for anyone writing or maintaining Claude Code skills and configuration files.

---

## 2. jqueryscript/awesome-claude-code [VERIFY]

- **Repo:** https://github.com/jqueryscript/awesome-claude-code
- **Category:** Tools [VERIFY]
- **PR Title:** Add Schliff — quality scoring and linting for Claude Code files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Tools section.
>
> Schliff scores CLAUDE.md, SKILL.md, and other AI agent instruction files across 7 quality dimensions (structure, triggers, quality, edges, efficiency, composability, clarity). It integrates as a pre-commit hook or GitHub Action, catching quality regressions before they ship. `schliff suggest` provides ranked improvement suggestions with estimated point gains. Pure Python stdlib, zero dependencies, 732 tests.
>
> A natural fit for Claude Code users who want measurable, repeatable quality for their agent configuration.

---

## 3. travisvn/awesome-claude-skills

- **Repo:** https://github.com/travisvn/awesome-claude-skills
- **Category:** Development & Quality [VERIFY]
- **PR Title:** Add Schliff — 7-dimension quality scorer for skill files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Development & Quality section.
>
> Schliff is a deterministic scorer that evaluates SKILL.md and CLAUDE.md files across 7 dimensions: structure, triggers, quality, edges, efficiency, composability, and clarity. `schliff suggest` ranks concrete improvements by estimated score impact, so you fix the highest-value issues first. Ships with a GitHub Action and pre-commit hook for CI integration.
>
> Built specifically for the skill authoring workflow — catch vague triggers, missing edge cases, and structural gaps before they cause misfires.

---

## 4. analysis-tools-dev/static-analysis

- **Repo:** https://github.com/analysis-tools-dev/static-analysis
- **Category:** Writing [VERIFY]
- **PR Title:** Add Schliff — static analysis for AI agent instruction files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Writing section (or a new "AI Instruction Files" category if preferred).
>
> Schliff performs deterministic static analysis on AI agent instruction files (CLAUDE.md, .cursorrules, AGENTS.md, SKILL.md). It evaluates 7 quality dimensions and produces a 0-100 composite score. Unlike LLM-based linters, scoring is fully deterministic and reproducible. Zero external dependencies, Python 3.9+ stdlib only, MIT license, 732 tests.
>
> As AI agent configuration files become a standard part of codebases, static analysis coverage for this file class fills a gap no existing tool addresses.

---

## 5. caramelomartins/awesome-linters [VERIFY]

- **Repo:** https://github.com/caramelomartins/awesome-linters
- **Category:** Markdown [VERIFY]
- **PR Title:** Add Schliff — linter and quality scorer for AI instruction files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Markdown section (or a new AI/LLM section if the maintainers prefer).
>
> Schliff lints and scores AI agent instruction files (CLAUDE.md, .cursorrules, AGENTS.md) across 7 quality dimensions. It flags missing sections, vague constraints, absent edge-case handling, and structural issues. `schliff verify` integrates as a CI gate with configurable score thresholds. Deterministic scoring, zero dependencies, Python 3.9+ stdlib only.
>
> Fills a gap in the linting ecosystem — structured quality enforcement for the growing class of AI configuration files that live alongside code.

---

## 6. vintasoftware/python-linters-and-code-analysis [VERIFY]

- **Repo:** https://github.com/vintasoftware/python-linters-and-code-analysis
- **Category:** Linters [VERIFY]
- **PR Title:** Add Schliff — Python linter for AI agent instruction files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Linters section.
>
> Schliff is a pure-Python linter and quality scorer for AI agent instruction files. It uses only the Python 3.9+ standard library with zero external dependencies. Scores files across 7 dimensions (structure, triggers, quality, edges, efficiency, composability, clarity) and provides ranked fix suggestions with estimated point impact via `schliff suggest`. 732 tests, MIT license, available on PyPI (`pip install schliff`).
>
> A focused, stdlib-only Python tool that addresses a new file category emerging in modern development workflows.

---

## 7. ml-tooling/best-of-python-dev [VERIFY]

- **Repo:** https://github.com/ml-tooling/best-of-python-dev
- **Category:** Code Quality [VERIFY]
- **PR Title:** Add Schliff — quality scoring for AI agent configuration files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Code Quality section.
>
> Schliff is a deterministic quality scorer for AI agent instruction files (CLAUDE.md, .cursorrules, AGENTS.md, SKILL.md). It evaluates 7 dimensions, integrates as a GitHub Action and pre-commit hook, and provides ranked improvement suggestions via `schliff suggest`. Pure Python 3.9+ stdlib, zero dependencies, 732 tests, MIT license.
>
> As AI-assisted development grows, the configuration files that guide agents are becoming as important as the code itself. Schliff brings measurable quality standards to this layer.

---

## 8. rohitg00/awesome-claude-code-toolkit [VERIFY]

- **Repo:** https://github.com/rohitg00/awesome-claude-code-toolkit
- **Category:** Quality Tools [VERIFY]
- **PR Title:** Add Schliff — deterministic scorer for CLAUDE.md and skill files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Quality Tools section.
>
> Schliff scores CLAUDE.md, SKILL.md, and other AI agent instruction files across 7 quality dimensions with fully deterministic, reproducible results. It ships with a GitHub Action, pre-commit hook, and `schliff suggest` for ranked fix recommendations. `schliff doctor` scans all installed skills at once. Zero dependencies, 732 tests, MIT license.
>
> Purpose-built for the Claude Code ecosystem — ensures your project instructions and skills maintain consistent quality as they evolve.

---

## 9. wong2/awesome-mcp-servers

> **STATUS: DO NOT SUBMIT -- MCP server is not yet implemented. This is a draft for future use.**

- **Repo:** https://github.com/wong2/awesome-mcp-servers
- **Category:** Testing/Quality [VERIFY]
- **PR Title:** Add Schliff MCP Server — quality scoring for AI instruction files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Testing/Quality section.
>
> Schliff provides a Model Context Protocol server that exposes deterministic quality scoring for AI agent instruction files (CLAUDE.md, .cursorrules, AGENTS.md). Agents can request scores across 7 dimensions and receive ranked fix suggestions via MCP tool calls. Pure Python, zero dependencies, MIT license.
>
> Enables any MCP-compatible agent to lint and score its own configuration files programmatically.

---

## 10. sourcegraph/awesome-code-ai [VERIFY]

- **Repo:** https://github.com/sourcegraph/awesome-code-ai
- **Category:** Developer Tools [VERIFY]
- **PR Title:** Add Schliff — quality standard for AI agent instruction files
- **PR Body:**

> Add [Schliff](https://github.com/Zandereins/schliff) to the Developer Tools section.
>
> Schliff establishes a measurable quality standard for AI agent instruction files -- the CLAUDE.md, .cursorrules, AGENTS.md, and similar files that increasingly ship with codebases. It scores files across 7 dimensions, integrates into CI via GitHub Action and pre-commit hook, and provides ranked fix suggestions with estimated impact. Deterministic, zero dependencies, Python 3.9+ stdlib only, 732 tests.
>
> Addresses a blind spot in AI-assisted development: the quality of the instructions we give our AI tools is rarely measured or enforced. Schliff changes that.
