# Five-Member Delivery Team

The project uses five parallel workstreams with explicit file ownership, contracts, reviews, and acceptance criteria.

| Member | Lane | Detailed assignment |
|---|---|---|
| 1 | Product, learning design, submission, release | [Member 1](member-1-product-release.md) |
| 2 | Domain, application services, persistence, contracts | [Member 2](member-2-domain-persistence.md) |
| 3 | AI personas and pedagogical feedback | [Member 3](member-3-ai-feedback.md) |
| 4 | Deterministic evaluation and task data | [Member 4](member-4-evaluation.md) |
| 5 | Web, Telegram, integration, and Vercel | [Member 5](member-5-experience-integration.md) |

All members must follow [the collaboration and pull-request protocol](collaboration-protocol.md) and [quality gates instructions](quality-gates.md). Execute work from the [parallel delivery plan and member-specific implementation plans](../superpowers/plans/README.md).

## Parallel-start rule

After the canonical contract baseline merges:

- Member 1 works on product content, evidence, and release artifacts.
- Member 2 works on domain, use cases, contracts, and persistence.
- Member 3 works against fixed evaluation fixtures and feedback contracts.
- Member 4 works against fixed task and evaluator contracts.
- Member 5 builds all interface states against contract-compatible fakes.

No member waits for another member's entire implementation. They wait only for a required contract decision, which is resolved through a GitHub issue and the contract-change protocol.

## Shared goals

Every lane is jointly accountable for:

- deterministic progression;
- zero mandatory cost;
- learner privacy;
- Arabic-first quality;
- graceful provider failure;
- typed contract compatibility;
- test evidence before merge;
- truthful product claims.
