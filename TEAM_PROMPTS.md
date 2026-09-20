# Yom Awel Team Work Instructions

The original standalone AI prompts have been replaced because they assigned files without freezing contracts, defined conflicting interfaces, concentrated integration work in one member, and allowed planned capabilities to be presented as completed.

Use the approved, reviewable work instructions below.

## Canonical documents

1. [Platform design](docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md)
2. [Team index](docs/team/README.md)
3. [Collaboration and pull-request protocol](docs/team/collaboration-protocol.md)
4. Approved implementation plan under `docs/superpowers/plans/`

## Detailed member assignments

- [Member 1 — Product, Learning Design, and Release](docs/team/member-1-product-release.md)
- [Member 2 — Domain, Application Services, and Persistence](docs/team/member-2-domain-persistence.md)
- [Member 3 — AI Personas and Pedagogical Feedback](docs/team/member-3-ai-feedback.md)
- [Member 4 — Deterministic Evaluation and Task Data](docs/team/member-4-evaluation.md)
- [Member 5 — Web, Telegram, Integration, and Vercel](docs/team/member-5-experience-integration.md)

## How each member starts

Before making changes, every member must:

1. read the canonical platform design;
2. read their complete assignment file;
3. read the collaboration protocol;
4. select a `Ready` GitHub issue assigned to their lane;
5. confirm the consumed and produced contracts;
6. branch from the latest contract baseline;
7. open a draft pull request early;
8. communicate cross-lane decisions in the issue or pull request.

## Parallel-development rule

Members work against canonical contracts and fixtures, not another member's unfinished implementation. Member 5 uses fakes immediately; Members 2–4 replace those fakes only after their contract suites pass. Member 1 develops content and release evidence against the same accepted journeys.

## Review rule

No member merges their own work. Every pull request must satisfy the review matrix, automated checks, contract compatibility, security/privacy checks, zero-cost check, and preview requirements defined in the collaboration protocol.

## Consistency rule

If a prompt, issue, comment, or implementation conflicts with the canonical design or contracts, stop and resolve the conflict through GitHub. Do not create a local variation. Material architecture changes require an ADR; shared interface changes require the contract-change protocol.

## Cost rule

No lane may introduce a required paid plan, card-backed service, paid Vercel feature, Supabase add-on, paid model, paid queue, or metered dependency. Optional future paid scaling belongs in a separate approved architecture decision and must preserve the free path.
