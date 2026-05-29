# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Schliff, please report it responsibly:

1. **Do not** open a public issue
2. Open a [private security advisory on GitHub](https://github.com/Zandereins/schliff/security/advisories/new)
3. Include: description, reproduction steps, potential impact

We will acknowledge receipt within 48 hours and provide a fix timeline within 7 days.

## Scope

Schliff processes skill files (SKILL.md) and eval suites (JSON). Security considerations:

- **File size limits**: Skill files are capped at 1 MB to prevent resource exhaustion
- **Path traversal**: Reference path resolution blocks `..` sequences and rejects symlinks
- **Regex safety**: Runtime evaluator uses timeout-protected regex matching
- **Local by default**: The core scoring engine is fully local — same input, same score, no data leaves your machine and no skill content is executed.
- **Opt-in features that DO use the network or a subprocess** (off by default): `score --url` fetches over HTTPS from an allowlisted set of hosts; `evolve` and `judge` send skill content to an LLM provider you configure; `report --gist` uploads to GitHub; the opt-in `--runtime` dimension invokes the local `claude` CLI. API keys are read from the environment only, never stored.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 7.x     | Yes (current) |
| 6.x     | Security fixes only |
| < 6.0   | No        |
