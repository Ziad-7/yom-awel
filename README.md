# Yom Awel (يوم أول)

Arabic-first workplace simulation for task-based digital skills training.

## Project status

The repository is in the **approved architecture and delivery-planning stage**. It does not yet contain a working application. Runtime code, datasets, migrations, tests, and deployment configuration will be added through the reviewed implementation plan.

This status statement is intentional: documentation must not describe planned capabilities as already implemented.

## Product concept

Learners join a simulated Egyptian workplace through a web experience or Telegram. They receive realistic work assignments, submit actual artifacts, and receive two complementary forms of assessment:

1. **Deterministic evaluation** checks correctness, schema, data quality, and task-specific rules.
2. **Generative coaching** explains the deterministic result in culturally authentic Egyptian Arabic and provides targeted guidance.

Only deterministic results control task completion and progression. Generative feedback cannot override grades.

## Approved architecture

The target is a modular Python monolith with ports and adapters:

- Next.js web experience on Vercel Hobby;
- FastAPI application and transport on Vercel Python Functions;
- Telegram webhook adapter;
- domain and application services independent of frameworks;
- versioned deterministic evaluators;
- provider-neutral pedagogical feedback with Gemini free-tier and deterministic fallback;
- Supabase Free for Postgres and private artifact storage;
- SQLite and local files for development and cloud-free fallback.

No approved capability requires a paid plan, billing account, paid add-on, or metered overage.

Read the complete [platform design](docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md).

## Five-member team

| Member | Responsibility |
|---|---|
| 1 | Product, learning design, evidence, submission, and release |
| 2 | Domain, application services, contracts, persistence, and Supabase |
| 3 | AI personas, feedback, safety, and deterministic fallback |
| 4 | Deterministic evaluation, task data, and evaluator QA |
| 5 | Next.js, FastAPI transport, Telegram, integration, and Vercel |

Detailed assignments are indexed in [the team guide](docs/team/README.md).

## Collaboration

GitHub issues and pull requests are the technical system of record. Contract changes, reviewer requirements, merge gates, branch rules, database review, integration handoffs, and release sign-off are defined in the [collaboration protocol](docs/team/collaboration-protocol.md).

Every pull request must use the repository template and provide:

- acceptance evidence;
- exact verification commands;
- contract impact;
- security and privacy impact;
- zero-cost impact;
- required reviewers;
- preview evidence for user-facing changes.

## Documentation map

- [Canonical platform design](docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md)
- [Architecture guide](docs/architecture/README.md)
- [Team ownership index](docs/team/README.md)
- [Pull request and review protocol](docs/team/collaboration-protocol.md)
- [Member 1 assignment](docs/team/member-1-product-release.md)
- [Member 2 assignment](docs/team/member-2-domain-persistence.md)
- [Member 3 assignment](docs/team/member-3-ai-feedback.md)
- [Member 4 assignment](docs/team/member-4-evaluation.md)
- [Member 5 assignment](docs/team/member-5-experience-integration.md)
- [Parallel delivery and implementation plans](docs/superpowers/plans/README.md)
- [Hackathon guidelines](HACKATHON_GUIDELINES.md)
- [Application requirements](APPLICATION_REQUIREMENTS.md)

## Planned delivery sequence

1. Review and approve the written platform design.
2. Produce and approve the detailed implementation plan.
3. Merge the contract baseline and shared fixtures.
4. Start all five member lanes in parallel.
5. Integrate real modules through contract-tested ports.
6. Verify pull-request previews and the complete release candidate.
7. Promote the exact verified artifact and tag its commit.

Implementation must not begin from the older standalone prompts. The approved design, implementation plan, member assignments, and collaboration protocol are the authoritative sources.
