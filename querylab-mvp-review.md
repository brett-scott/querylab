# QueryLab: MVP readiness review

Reviewed against `querylab-brief.md`, 17 October 2026. This is a planning review, not approval of the proposed stack or scope. The brief remains unchanged. No implementation or technology compatibility assessment was performed.

## Assessment

The brief is strong enough to begin a bounded technical discovery and vertical slice. It is not yet a fully agreed MVP delivery specification. The central learning loop, execution constraints and grading principles are unusually well defined; the main remaining work is deciding the release boundary and converting those principles into explicit contracts and measurable release gates.

The proposed three datasets and approximately 36 challenges are a version-one recommendation, not a prerequisite for proving the product. Building that full library before validating routine execution, reset and grading would create substantial rework risk.

## Requirements already well established

The brief explicitly requires “multiple datasets; varied scenarios and difficulty; hands-on SQL, including functions and stored procedures; a usable application.” These should remain the product baseline.

Useful existing decisions and constraints include:

- A complete learner journey: select a challenge, inspect the schema, write SQL, run, submit, receive feedback, use hints and reveal an explanation.
- “Grade observable behaviour rather than matching SQL text.” Queries, functions and procedures each have meaningful grading requirements.
- Deterministic synthetic datasets, fixed reporting dates and deliberate edge cases.
- Saved work and progress separate from disposable practice databases; assisted completion is distinguished from independent success.
- Real MySQL execution, complete routine definitions, cancellation that stops database work, and resets that account for DDL implicit commits.
- A local personal-use starting point. Public hosting and AI-generated content are already deferred.
- Nine concrete acceptance criteria for the first vertical slice. These are an appropriate starting gate and should be retained.

React/TypeScript, FastAPI, Docker Compose and MySQL 8.4 are proposed working defaults. They have not been approved or verified by this review. Laravel, Livewire and FluxUI are not requirements in this brief.

## Recommended release boundary

Separate the initial proof from the first useful MVP and the larger version one. The following quantities are recommendations for discussion, not commitments.

| Stage | Suggested boundary | Purpose |
| --- | --- | --- |
| Vertical slice | One small dataset; one query, one function and one state-changing procedure | Pass all nine existing milestone criteria before expanding content |
| MVP | Two compact datasets; approximately 12 validated challenges covering queries, functions and procedures across several difficulty levels | Meet the explicit multiple-dataset requirement and provide enough variation to evaluate learning and usability |
| Expanded version one | Three datasets and approximately 36 challenges; additional transaction/debugging content | Deliver the broader library proposed in the brief after the core loop is reliable |

For the MVP, retain schema exploration, real results/errors, automatic grading, progressive hints, explained solutions, saved attempts, resume and reset. Offer a deliberately bounded free-practice sandbox using the same execution controls. Guided material can initially live inside challenge instructions and hints rather than requiring a separate lesson-authoring system.

The brief says “Start with guided lessons, standalone challenges and a free-practice sandbox”; simplifying guided lessons into challenge guidance is a scope change to confirm. Full schema-design grading, performance evaluation, connected mini projects and all five difficulty levels need not be MVP commitments. Difficulty should reflect available authored content rather than expose empty categories.

## Decisions and gaps

| Priority | Gap or unresolved decision | Recommended resolution and evidence needed |
| --- | --- | --- |
| Before implementation | Intended learner and outcome | Choose the initial learner profile, assumed SQL knowledge and the skills they should demonstrate after the MVP. This determines guidance, progression and content depth. |
| Before implementation | Release scope and content allocation | Agree the MVP boundary, dataset choices, challenge count and distribution by topic/difficulty. Treat 36 challenges as proposed version-one scope until explicitly adopted. |
| Before implementation | Supported installation environment | Specify supported operating systems, Docker prerequisite, browser, expected local resources and offline requirements. Define a clean-install verification path. Confirm the proposed stack and pin the engine configuration. |
| Before implementation | Run versus Submit semantics | Decide whether Run mutates the current workspace and how Submit uses fresh fixtures without destroying editor work. Define transaction/session lifetime, multi-statement support, multiple result sets, routine submission format and sandbox permissions. |
| Before implementation | Isolation and execution ownership | Document learner, grading and reset credentials; allowed objects/operations; hidden-fixture lifecycle; cancellation and recovery. Decide whether simultaneous tabs/submissions are rejected, queued or isolated. |
| Before implementation | Challenge contract | Create one complete specification for each core type, including exact signatures, numeric/date/NULL rules, permitted operations, visible examples, hidden fixtures and expected errors. Define technique checks only where explicitly required. |
| Before content expansion | Vertical-slice dataset mismatch | The small online-store slice does not yet specify inventory locations/stock needed by the example stock-transfer procedure. Either add the minimal entities or choose another realistic state-changing procedure and define its rollback contract. |
| Before content expansion | Progress and assistance rules | Define draft, attempt, pass and assisted completion. Decide what happens after solution reveal followed by a successful attempt; preserve assistance history so revealing an answer cannot silently become an independent pass. |
| Before content expansion | Content validation and ownership | Name who authors, reviews and approves each challenge. Require reference solutions, alternative correct approaches and plausible incorrect answers to be tested against the fixtures. Hidden tests are finite evidence, not proof that every possible wrong answer is rejected. |
| Before MVP release | Persistence and upgrades | Specify autosave timing, what resume restores, and whether database mutations persist across restarts. Define compatibility when challenge/dataset versions change and protect existing attempts from silent reinterpretation. |
| Before MVP release | Usability and accessibility | Agree a desktop browser baseline, keyboard operation, readable results/errors, status indicators and handling of wide result grids. Define minimum small-screen behavior rather than assuming the full SQL workspace must support every device equally. |
| Before MVP release | Feedback and limits | Set result and execution limits, truncation messaging, cancellation status and recoverable infrastructure error behavior. Explain visible failures without exposing hidden fixture rows. |
| Before MVP release | Product success and support | Agree what observable learner behavior makes this useful, who will trial it, and how installation/recovery issues will be recorded. Define completion evidence without inventing numerical targets before a pilot. |

Hidden assets can be inaccessible to the learner SQL account, as required, while still being inspectable by someone who owns the local machine. Keep the threat model focused on accidental damage, SQL privilege boundaries and trustworthy practice; do not imply tamper-proof assessment.

## Suggested next steps and acceptance gates

### 1. Agree a short MVP decision record

Resolve the six “before implementation” rows above. Record approved scope, exclusions, learner profile, environment, execution behavior and unresolved assumptions beside the brief.

**Gate:** a developer can describe what ships, what is deferred, how SQL runs and what a successful attempt means without inventing product behavior. No effort or delivery-date commitment is needed before this decision record exists.

### 2. Finalize three executable challenge specifications

Complete the analysis, function and procedure examples using the agreed small dataset. Resolve the procedure/dataset mismatch. Include deterministic seeds, reference answers, alternative valid approaches, negative cases, hints and explanations.

**Gate:** every challenge has an unambiguous expected result/error/state contract; its fixtures can be recreated; each hint and explanation matches the tested behavior.

### 3. Prove execution and grading feasibility

Test complete routine definitions, repeat submissions, state-changing Run/Submit behavior, fresh hidden fixtures, DDL reset, forced cancellation and recovery using the selected MySQL configuration. Exercise permissions using the actual learner credentials.

**Gate:** core execution risks have demonstrated solutions. Reference answers pass, deliberate errors fail for useful reasons, protected data remains inaccessible through learner SQL and cancellation leaves a recoverable workspace.

### 4. Complete the learner-facing vertical slice

Connect challenge selection, schema inspection, editor, execution, grading, hints, explanations and saved progress.

**Gate:** all nine first-milestone criteria in the original brief pass through the UI. Include application restart, failed submission, cancellation and full reset; verify that reset preserves progress. Record reproducible evidence rather than relying on a demonstration of the happy path alone.

### 5. Expand only to the agreed MVP library

Add the second dataset and validated challenge coverage, then complete the bounded sandbox and installation/help material. Reuse the validated challenge format and execution controls.

**Gate:** every shipped challenge passes its content checks; a clean supported machine can start the app using the documented path; a learner can complete and resume a representative query, function and procedure without developer intervention. A pilot confirms that feedback is understandable and identifies revisions before the larger library is commissioned.

After these decisions, convert each milestone into developer-owned tasks with acceptance criteria and explicit dependencies. A granular implementation task list now would prematurely settle contracts and repository structure that remain undecided.

## Future iterations

| Iteration | Candidate additions | Dependency or reason to wait |
| --- | --- | --- |
| Broader curriculum | Third dataset, library growth toward 36 challenges, more transaction/debugging exercises, dedicated guided lessons | Reliable authoring/validation workflow and evidence of learner needs |
| Deeper practice | Schema-design grading, connected mini projects, larger performance datasets and controlled plan-based evaluation | Stable mutable-workspace lifecycle and separate grading contracts |
| Content packs | Hotel bookings and support-desk datasets | Clear business definitions, deliberate edge cases and maintained fixtures |
| Easier distribution | Desktop launcher/wrapper or installer | Proven local startup/recovery; packaging must still provide a real database engine |
| Assisted learning | AI explanations or challenge suggestions | Deterministic grading remains authoritative; validate generated content before use |
| Separate deployment initiative | Public multi-user hosting, sharing or marketplace features | New isolation, identity, operations and content-management requirements; not a routine extension of local personal use |

## Questions for the next planning discussion

1. Who is the first learner, and what SQL knowledge should they already have?
2. Does a smaller two-dataset MVP sound useful, with three datasets/36 challenges reserved for expanded version one?
3. Which operating systems must work at launch, and is Docker installation acceptable?
4. Can guided learning begin as instructions and progressive hints, or must launch include separate lessons?
5. What should resume restore: editor/progress only, or the mutated practice database as well?
6. Who will review learning content and trial the MVP before its scope expands?

The next concrete deliverable should be the approved MVP decision record and three fully specified challenges. Those unlock implementation planning without treating recommendations as settled requirements.
