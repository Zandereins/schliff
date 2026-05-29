# ADR-0007: Spec Versioning via ADR Addenda — No v0.4 Bump

- **Status:** Accepted
- **Date:** 2026-04-27
- **Decision-Driver:** Franz Paul (benevolent dictator)
- **Sprint:** v8.0 14-day sprint (2026-04-28 to 2026-05-11)
- **Related:** [Spec](../specs/2026-04-27-v8-product-completion.md) §13, [Vision Spec](../specs/2026-04-25-measurement-layer-vision.md) v0.3, ADR-0001..ADR-0006

## Context

The strategic decisions D1–D6 captured in ADR-0001 through ADR-0006 materially refine the master Vision Spec (`docs/specs/2026-04-25-measurement-layer-vision.md`, currently v0.3). The mechanical question: do these refinements warrant bumping the Vision Spec to v0.4?

The argument for a v0.4 bump is canonical-snapshot hygiene — one document a new reader can consume top-to-bottom to know "the current view". The argument against is process theater. At solo-maintainer scale, the cost of keeping a single living spec in sync with seven separate ADRs is non-trivial: every ADR revision becomes two edits, and the spec inevitably lags. The Challenger sparring Subagent Report (2026-04-27) flagged this exact pattern as "premature formalisation" — adopting governance scaffolding (RFC-style snapshots, mandatory reviewer-agent gates) appropriate for a 5–20 person org at a 1-person org cost.

The cultural reference points (IETF RFCs, Rust RFC process) are governance patterns for projects with many maintainers and external implementers; they encode debate and revision rituals that make sense at that scale. Hamel Husain's repeated critique of "Doc-First processes" applies: write fewer documents, write smaller documents, and let the working code carry as much canonical-state as it can.

## Decision

1. **Strategic decisions D1–D6 are encoded as individual ADRs** in `docs/adr/`. ADRs are the canonical record.
2. **The master Vision Spec stays at v0.3.** No v0.4 bump in v8.0.
3. **An addendum block** is appended to v0.3 listing pointers to the ADR set (`docs/adr/0001-...md` through `docs/adr/0007-...md`) and the v8.0 Product Completion Spec.
4. **A v0.4 bump is triggered only when** at least one of these holds:
   - **(a)** A second maintainer joins the project, requiring a canonical snapshot for onboarding without ADR-archaeology, **or**
   - **(b)** External review (Reviewer-Agent gate per Vision Spec §10) explicitly requires a snapshot bump for compliance.
5. **Reviewer-Agent gate per ADR is optional, not mandatory.** Vision Spec §10 originally implied per-ADR review; this is downgraded to "may be invoked by author for high-stakes ADRs" — flat 1-2h wall-clock per ADR compounds across 7 ADRs into a half-sprint of process.

## Consequences

**Positive:**
- ADRs are the smaller, debate-ready unit — cheaper to write, cheaper to revise, cheaper to argue about than a versioned monolith.
- Avoids the "spec lags reality" failure mode common when both ADRs and a master spec must co-evolve.
- Clear bump-trigger conditions prevent the question from re-arising at every ADR; future-proofs the decision.

**Negative:**
- New readers must follow the addendum-pointer chain to reconstruct the current view; v0.3 read alone is incomplete.
- ADR-archaeology becomes the onboarding cost when condition (a) eventually fires; mitigated by the addendum index and ADR cross-references.

## Alternatives Considered

1. **Bump Vision Spec to v0.4 now** *(rejected).* Process theater for solo-maintainer scale; ADRs already encode the same decisions in a smaller, more debate-ready format; doubles edit-surface for every future revision.
2. **No formal records, decisions live in commit messages and PRs** *(rejected).* Loses ability to debate/revise decisions later; loses external-reader trust signal that the project takes its own decisions seriously; defeats the "Datadog for AI software" measurement-layer credibility narrative.
3. **Mandatory Reviewer-Agent gate per ADR (Vision-Spec §10 as written)** *(rejected).* Adds 1–2h wall-clock per ADR which compounds across 7 ADRs into half a sprint. Optional invocation captures the value (high-stakes ADRs do get reviewed) without the flat tax.
4. **One mega-ADR for D1–D6 combined** *(rejected).* Collapses the debate-unit; revisions force editing unrelated decisions; defeats the small-unit advantage.

## References

- Challenger sparring Subagent Report (2026-04-27) — "premature formalisation" finding.
- Michael Nygard, "Documenting Architecture Decisions" (original ADR pattern) — https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- IETF RFC process and Rust RFC process — cultural background for snapshot-versioned governance at multi-maintainer scale.
- Hamel Husain, recurring critique of Doc-First processes — https://hamel.dev/blog/posts/evals-faq/
- Vision Spec v0.3 — `docs/specs/2026-04-25-measurement-layer-vision.md`
- v8.0 Product Completion Spec — `docs/specs/2026-04-27-v8-product-completion.md`
