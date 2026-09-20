# Architecture Documentation

The canonical platform design is:

- [Yom Awel Platform Design](../superpowers/specs/2026-09-20-yom-awel-platform-design.md)

It defines the proposed product principles, modular-monolith boundaries, domain model, contracts, state machine, submission flow, security controls, zero-cost infrastructure, Vercel deployment, quality requirements, testing strategy, and architecture governance. It becomes the merged design authority only after review and integration into `main`.

## Decision hierarchy

1. The canonical platform design governs the target system.
2. Accepted Architecture Decision Records amend specific decisions.
3. The merged implementation plan defines execution order without silently changing the design.
4. Member task files define lane ownership and acceptance criteria.

## Architecture Decision Records

Material changes require an ADR under `docs/architecture/decisions/`. Use the process in [the collaboration protocol](../team/collaboration-protocol.md). An ADR must explain context, decision, alternatives, consequences, security/privacy impact, zero-cost impact, and migration or rollback effect.

Examples of changes that require an ADR:

- replacing the modular monolith with services;
- changing Vercel/Supabase deployment boundaries;
- making a paid dependency mandatory;
- moving progression authority to a new component;
- changing artifact ownership or privacy boundaries;
- changing the contract-versioning strategy;
- adding a durable queue or background-processing platform.

Implementation details that preserve merged boundaries do not require an ADR, but still require normal pull-request review.
