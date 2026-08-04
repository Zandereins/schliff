# ADR 0009: EU AI Act — schliff imposes no transparency obligation on itself, and why

- Status: accepted
- Date: 2026-08-04

## Context

Article 50 of the EU AI Act became applicable on **2026-08-02**. The Digital Omnibus on AI
(in force 2026-07-27) postponed the high-risk timelines — Annex III to 2027-12-02, Annex I to
2028-08-02 — but **did not postpone Article 50**. The only grace period it granted there is for
the Art. 50(2) machine-readable marking of systems already on the market at 2026-08-02, which
runs to 2026-12-02. Article 4 (AI literacy) survived as an obligation of effort rather than of
result and carries no fine, being absent from the Art. 99 ceilings.

schliff is affected by none of it, and this ADR records *why* — because "it does not apply" is
a claim that decays. Two days after Art. 50 started applying, a reader is entitled to ask, and
the answer should not have to be reconstructed from the source tree.

What schliff actually is, verified against the tree on 2026-08-04:

- **The score is rule-based.** `pyproject.toml` declares no `dependencies` at all. Every
  dimension is a readable scorer under `skills/schliff/scripts/scoring/`; the weights are a
  dict. Nothing infers, nothing learns, nothing is trained.
- **Two optional extras call a model**: `[evolve]` pulls `litellm`, `[judge]` pulls
  `anthropic`. Both are opt-in installs. Without them the paths exit non-zero with an install
  hint rather than degrading, and `schliff evolve --budget 0` never imports the LLM path at all
  (`budget.py:49` → `engine.py:247`).
- **Where they do run, they run on the user's machine with the user's own credentials**,
  against a provider the user configures. This project ships no model, hosts no inference,
  holds no key, and receives nothing that is scored.
- **schliff publishes no text.** Its output is a score, and — for `evolve` — an edited file on
  the user's own disk. Since 2026-08-04 it also operates no public service at all
  (see ADR 0008).

## Decision

Record that no Article 50 obligation attaches to schliff, on the reasoning below, and state
the AI-use facts in the README so a reader does not have to take that on trust. Do **not**
add a disclosure banner, a machine-readable marking, or an AI-transparency page.

## Why

**Primary reason: the scored artefact is not produced by an AI system.** Art. 3(1) requires a
machine-based system that infers. A regex-and-arithmetic scorer with a published weight dict
does not, so the Regulation does not reach the part of schliff that everything else depends on.
This is the strongest available argument and it is deliberately placed first — "Art. 50 barely
applies" would have been the weaker claim, because it concedes the framework applies at all.

**Art. 50(4) subpara. 2 cannot bite, on its own terms.** That clause — the one that does reach
a blog, and the reason fpaul.dev is getting a transparency page — obliges deployers to disclose
AI-generated or manipulated **text published to inform the public on matters of public
interest**, unless the content had human review and a named person holds editorial
responsibility (Recital 134 uses the same wording). schliff publishes no text to anyone. The
`evolve` output is a file edit delivered to the person who invoked it, which is neither
publication nor an address to the public.

**Art. 50(1) does not apply.** It covers systems intended to interact directly with natural
persons, which must disclose that the interaction is with an AI. A CLI that prints a number is
not that, and on the one path where a model *is* involved the user installed an extra named
`[evolve]` and configured a provider to get there. The README states it regardless, which is
the cheap and honest thing to do whether or not it is owed.

**Neither provider nor deployer for the optional paths.** schliff places no model on the market
and operates none. `litellm` is a client library; the model, the endpoint and the credentials
are the user's. On the reading taken here the user is the deployer of whatever they configure,
and this project is a caller. This is the least settled point in the assessment and is named as
such below rather than buried.

**Chapter III and Chapter V are not in scope.** schliff is not an Annex III use case — it
scores text files, not people — and its high-risk timelines moved to 2027-12-02 in any event.
Chapter V concerns general-purpose model providers; schliff trains and ships no model.

**Art. 4 is satisfied by the same README text.** If it applies at all it is now an obligation
of effort and not fineable, and naming which paths call a model and which do not is that effort.

## Where this is least certain

Two points, named so they are not mistaken for settled:

1. **Whether distributing software that calls a third-party model makes the distributor a
   provider.** Taken here as no. It is the point on which the optional-path reasoning would
   turn if a supervisory authority read the roles more broadly.
2. **Art. 50(2) machine-readable marking of synthetic output.** Taken here as an obligation of
   the generating system's provider rather than of a client that requests a completion. If that
   is wrong, `evolve` output would be in scope — and the grace period for systems already on the
   market ran to 2026-12-02.

Neither changes the primary reason: the deterministic score, which is the product, involves no
AI system at all.

## Rejected

- **Publishing nothing at all.** The position taken in the earlier work on this: a wrong
  published self-classification becomes evidence against its author, so publish only verifiable
  facts. That argument stands against a *guessed* classification, not against a sourced one —
  and leaving the question unanswered while Art. 50 is live invites the reader to assume the
  worse answer.
- **A disclosure banner or an AI-transparency page.** Both would assert an obligation that does
  not exist here and imply the score is model-derived, which is the exact misunderstanding
  the project exists to avoid.
- **Machine-readable marking of `evolve` output.** Not owed on this reading, and marking a file
  the user asked to have edited on their own disk communicates nothing to anyone.

## Sources and scope

The regulatory facts above — the 2026-08-02 Art. 50 date, the Digital Omnibus outcome and what
it did and did not postpone, the Art. 50(4) subpara. 2 wording, the Art. 4 downgrade, the Art.
99(4)(g) and 99(6) penalty structure, and the KI-MIG assigning central market surveillance in
Germany to the Bundesnetzagentur — come from a primary-source verification dated 2026-08-04
against `artificialintelligenceact.eu` (Art. 50, Recital 134, Art. 99) and the Bundestag
record, and were not re-derived here.

**This is an assessment by the maintainer, not legal advice and not a legal opinion.** No
lawyer was consulted. It states a reading, names where that reading is weakest, and is dated so
a later reader can see what it was based on. If something after August 2026 is at stake,
re-check the sources rather than citing this document.
