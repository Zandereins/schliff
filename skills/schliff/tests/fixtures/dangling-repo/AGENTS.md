# Dangling fixture

A repo-shaped fixture for the Action's check-commands selftest. Two commands
resolve; the rest are deliberately dangling, including one that carries a
markdown-link injection vector to prove the comment renderer neutralizes it.

## Setup

```bash
npm run build
make build
```

## Testing

```bash
make test
npm run evals
npm run [pwned](https://evil.example)
```
