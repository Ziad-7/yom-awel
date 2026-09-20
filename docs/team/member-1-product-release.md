# Member 1 — Product, Learning Design, and Release

## Mission

Ensure Yom Awel solves a clear learner problem, teaches and measures the intended skills, communicates truthfully, and ships as a coherent release rather than a collection of disconnected technical modules.

## Owned paths

- `submission/**`
- `task_packages/**/content/**`
- product sections of `README.md`
- `docs/product/**`
- release checklists and demo scripts

Shared ownership:

- task scoring intent with Member 4;
- learner-visible Arabic copy with Members 3 and 5;
- release claims with all members.

## Inputs

- verified application behavior;
- evaluation reports from Member 4;
- feedback behavior from Member 3;
- preview deployments from Member 5;
- official hackathon/application requirements and cited evidence.

## Outputs

- product requirements and prioritized learner journeys;
- task learning objectives and task instructions;
- competency definitions and evidence expectations;
- Arabic/English content glossary;
- source register for problem and market claims;
- claim-to-evidence matrix;
- application answers;
- pitch deck source and export;
- demo script and contingency script;
- release acceptance checklist and sign-off.

## Work packages

### 1. Product contract

Define each supported learner journey using:

- actor and entry channel;
- goal;
- preconditions;
- normal flow;
- failure and retry flow;
- completion evidence;
- visible learner outcome;
- feature status: current, experimental, or roadmap.

The first journey covers onboarding, spreadsheet assignment, submission, deterministic feedback, retry, pass, and skills profile.

### 2. Learning design

For every task version, document:

- intended learner level;
- workplace context;
- measurable learning objectives;
- required artifact;
- allowed and disallowed transformations;
- deterministic pass policy;
- skills evidenced by each check;
- hints and retry guidance;
- misconceptions the feedback should address.

Member 4 converts this intent into executable scoring. Neither member changes the policy alone.

### 3. Content system

Maintain:

- persona and organization naming;
- Egyptian Arabic tone rules;
- consistent translations for technical terms;
- RTL copy review;
- error/retry/empty-state copy;
- accessibility-friendly wording;
- separation of learner-facing explanations from evaluator implementation details.

### 4. Evidence and claims

Create a source register with title, publisher, date, URL, supported claim, and usage location. Remove or qualify any number that lacks an authoritative source.

The claim-to-evidence matrix maps every deck and application capability to:

- a test;
- a screenshot or preview path;
- a demo timestamp;
- or an explicit roadmap label.

### 5. Submission package

Produce and verify:

- complete application responses;
- pitch deck source;
- PDF export below the form limit;
- public repository and demo links;
- demo recording and backup recording;
- team details and enrollment proof checklist;
- declarations and final submission record.

### 6. Release acceptance

Run the product acceptance suite from a fresh learner account. Confirm the experience is understandable without developer explanation. Log every failure as an issue rather than accepting verbal workarounds.

## Acceptance criteria

- All current capability claims are demonstrated by the release candidate.
- Every statistic has a source and accurately reflects that source.
- Every task has measurable objectives and unambiguous completion rules.
- Arabic copy is consistent, professional, and culturally appropriate.
- The deck and application label unimplemented capabilities as roadmap.
- The public preview works in an incognito browser.
- The demo can complete with Gemini unavailable.
- Submission files satisfy format, size, identity, and eligibility requirements.
- The exact verified commit is recorded in the submission documentation.

## Required tests and reviews

- Review evaluator policy pull requests from Member 4.
- Review feedback/persona pull requests from Member 3.
- Review learner-visible web/Telegram changes from Member 5.
- Run scripted product acceptance against preview deployments.
- Verify Arabic RTL, keyboard navigation, error clarity, and retry comprehension.
- Verify claim-to-evidence consistency before release.

## Pull request responsibilities

Member 1 is a required reviewer for:

- product behavior;
- task instructions and scoring intent;
- learner-facing Arabic copy;
- AI feedback behavior;
- evaluator semantics;
- submission and pitch claims.

Member 1 must not approve a claim based only on planned code or a developer explanation. Evidence must come from tests or the verified preview.

## Handoffs

- To Member 2: state descriptions, completion rules, and profile fields.
- To Member 3: persona behavior, language rules, and feedback rubric.
- To Member 4: task objectives, permitted transformations, and skill mappings.
- To Member 5: user journeys, copy, assets, accessibility expectations, and demo flow.

## Out of scope

- Implementing backend state or persistence.
- Choosing evaluator algorithms independently.
- Introducing product claims before verification.
- Waiving security, contract, migration, or cost gates for presentation reasons.
