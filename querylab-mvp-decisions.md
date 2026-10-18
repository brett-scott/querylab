# QueryLab MVP decision record

Status: Draft for discussion. Created 17 October 2026.

Sources: [Project brief](querylab-brief.md) and [MVP review](querylab-mvp-review.md).

Implementation update: three exercises run and nine remain planned. The user subsequently authorized a **hosted static frontend + local helper + learner-owned MySQL**. See [local helper](docs/local-helper.md). This supersedes the earlier zero-installation requirement and shared hosted SQL plan. Twelve validated challenges remain the MVP target; public deployment is future work.

Items marked Proposed or Open are not approved decisions. Confirmed items reflect user decisions recorded below. QueryLab is the project name used in this discussion; name availability has not been assessed.

## Product decisions

| ID | Decision to make | Proposed starting point | Status |
| --- | --- | --- | --- |
| D01 | Who is the first learner, and what do they already know? | Anyone wanting to build SQL experience who already understands filtering, joins, grouping/aggregation, subqueries and NULL handling. The product is not tailored solely to its creator. Elementary retrieval tasks such as selecting 100 customers are outside the intended challenge scope. CTEs, window functions, stored routines and transactions are skills learners can develop rather than entry requirements. | Confirmed |
| D02 | What should the learner achieve? | Independently solve realistic joins/aggregation problems, create a tested function, and create a procedure with validation and atomic changes. | Proposed |
| D03 | How much content ships? | Two datasets and 12 validated challenges. Recommended implementation sequence: first prove one query, one function and one state-changing procedure. Three datasets/~36 challenges remain a proposed expanded version-one target. | Confirmed MVP scope |
| D04 | Which datasets and topic mix? | Online store and business/inventory, with six query, three function and three procedure challenges in total across both datasets. Exact challenge topics and distribution between datasets remain to be authored. Difficulty follows prerequisites; avoid promising every difficulty level. | Confirmed datasets and type allocation |
| D05 | How is learning guided? | Optional hints revealed progressively: a conceptual nudge, a relevant SQL function or technique, then a partial example. An explained solution is available separately. Standalone lessons are deferred until after MVP. Prerequisite notes and starter SQL remain challenge-authoring details. | Confirmed |
| D06 | Who uses the app, and where? | Hosted static website accessible to anyone with the URL, without accounts. Learners run a local helper connected to their own MySQL 8.4; bundled Docker MySQL is optional. Public HTTPS-to-loopback browser permissions remain to be verified. | Confirmed helper direction; public deployment open |
| D07 | What is explicitly deferred? | Accounts and learner statistics tracking are confirmed deferrals and among the first priorities after MVP. Standalone lessons are also confirmed deferred. Other proposed deferrals: third dataset/library expansion, schema-design/performance grading, connected projects, desktop installer, multiplayer, leaderboards, marketplace and AI-generated content. Hosting is required for MVP. | Partially confirmed |
| D08 | What makes the MVP successful, and who trials it? | Initial audience target remains 10 simultaneous learners; SQL now runs on individual computers. Earlier A$150/month shared-stack estimate/ceiling is historical and needs revision for static hosting and helper distribution. Proposed success: learners set up/pair the helper, complete representative challenges and restore drafts without developer intervention. Trial learners/content reviewer remain open. | Partially confirmed; estimate to revise |

The challenge-type allocation is confirmed; refine individual topics against the confirmed audience and agreed learning outcomes. Proposed: include transaction handling within procedure challenges rather than requiring a separate curriculum area at launch.

Draft curriculum: [12 MVP challenge outlines](querylab-mvp-challenges.md). Individual scenarios, routine signatures and business rules remain proposed pending review. The draft allocates six challenges to each dataset and preserves the confirmed six-query/three-function/three-procedure total.

## Curriculum implications of the confirmed audience

- Assume intermediate SQL experience; do not require introductory SELECT lessons before challenges.
- Use realistic scenarios requiring reasoning about business rules, relationships or edge cases. Challenge quality is not measured solely by query length or advanced syntax.
- Confirmed prerequisite baseline: filtering, joins, grouping/aggregation, NULL handling and subqueries. CTEs, window functions, stored routines and transaction handling are skills learners can develop rather than universal entry requirements. Challenges introducing these skills should state prerequisites and offer appropriate guidance.
- Candidate challenge themes include refund-adjusted customer spending, tied rankings, inactivity over reporting windows and validated atomic stock transfers. These are examples, not an approved content list.
- Confirmed hint progression: conceptual nudge, named function/technique, then a partial example. For example: "Have you considered DENSE_RANK() when customers can tie?" Hints are optional and requested by the learner; an explained solution is available separately. Hints should not expose hidden test data. Standalone lessons are deferred until after MVP.
- Hosted website delivery is confirmed, with access open to anyone who has the URL. The initial capacity target is 10 simultaneous learners.

## Learner behavior decisions

| ID | Decision to make | Proposed starting point | Status |
| --- | --- | --- | --- |
| D09 | What does Run do? | Execute against the learner's current disposable practice workspace and show results or errors. Changes remain until reset or session expiry. Run does not grade or record a pass. Save editor drafts independently. | Confirmed |
| D10 | What does Submit do? | Grade the submitted SQL against fresh test fixtures and show actionable feedback, leaving the practice workspace and editor draft unchanged. Durable attempt history and learner statistics are not MVP commitments. | Confirmed |
| D11 | What does reset or restart preserve? | Save editor drafts in the browser so refresh does not lose SQL. Reset restores practice objects/data while retaining the draft. Practice data may reset when the anonymous session expires; show clearly when a workspace expires or is recreated. Browser-local drafts are limited to that browser/device and may be lost if its storage is cleared. No account-based resume, durable progress history or persistence of practice database mutations is promised. Exact session lifetime remains open. | Confirmed behavior; expiry duration open |
| D12 | What counts as independent completion? | Independent-versus-assisted statistics and durable assistance history are deferred with learner statistics. MVP can provide hints, solutions and submission feedback without a progress dashboard. Define completion/assistance metrics when post-MVP tracking is designed. | Deferred |
| D13 | How does sandbox practice work? | A separate resettable workspace for each selected dataset, under the same execution limits. No automatic grading; challenge work is unaffected by sandbox mutations. | Proposed |
| D14 | What interaction baseline is required? | Desktop browser, keyboard-operable editor and controls, readable errors, wide result grids and clear running/cancelled states. Confirm minimum small-screen support. | Proposed |
| D15 | What is the MVP visual direction? | Focused Midnight Workbench: retain charcoal/mint branding with a compact challenge overview and wider editor. Full Requirements and Expected output expand on demand; Schema opens as a support panel/dock; Results expand after execution. Focus hides supporting panels. Reference: [selected revision](design/querylab-04-focused-workbench.png) and [interaction contract](docs/ui-simplification-review.md). This supersedes the persistent expanded three-pane default. | Confirmed |

## Engineering decisions to specify before implementation

**Current architecture supersession:** the earlier shared-hosting bullets below are retained as planning history. The authorized direction is now static hosting plus local execution. MySQL credentials remain local; pairing uses a local secret and short-lived bearer token. Exact origin and loopback Host checks protect the helper. Namespace-scoped cleanup preserves unrelated databases. Dataset downloads contain public practice data; helper-managed practice/grading fixtures are automatic and independent. Local grading assets are inspectable by learners, so feedback is for practice rather than protected assessment. Windows preview packaging and a guided launcher are implemented; clean-machine installation, broader platform/browser support and a revised hosting estimate remain open.

These need concrete contracts, but the user need not choose low-level mechanisms. Resolve them using the agreed product behavior and document the rationale. Earlier local-profile defaults must be adapted for hosted learners.

- **Stack and environment:** confirm the brief's proposed React/TypeScript, FastAPI and real MySQL approach; select pinned versions/configuration after compatibility checks. Docker Compose remains a candidate for development, not a confirmed production hosting architecture. Select hosting based on budget, concurrency and isolation needs; document deployment and recovery.
- **SQL submission contract:** define whole-script versus selection execution, multiple statements/result sets, complete routine definitions, DELIMITER handling and transaction/session lifetime. Explicit multi-statement transactions must have a supported execution path.
- **Execution ownership:** specify practice, grading and reset privileges; allowed SQL operations; routine security; hidden-fixture lifecycle. Proposed MVP default: one active execution/grading job per learner, enforced across tabs. Define cross-learner isolation and authorization for every workspace/job; validate the hosting isolation model before accepting learner SQL.
- **Hosted access and operations:** MVP uses anonymous practice, open to anyone with the URL, targeting 10 simultaneous learners within a provisional A$150/month hosting ceiling. Define an anonymous session/workspace identifier and enforce access boundaries server-side; no login does not mean a shared mutable database. Specify anonymous-session quotas, platform-wide execution limits, workspace expiry/cleanup, operational backups, monitoring and recovery. Define a clear busy/queue response when capacity is reached. Ten simultaneous learners is a usage target, not a promise of ten unbounded queries running at once; establish execution concurrency and resource limits through measurement. Database work must be bounded so one visitor cannot exhaust shared resources. Provider selection and production deployment remain future work; this planning decision does not initiate a purchase.
- **Limits and recovery:** select result, execution and resource bounds through the vertical slice. Cancellation must stop database work; show truncation and infrastructure failures separately from grading failures.
- **Challenge contracts:** version dataset and challenge definitions; define signatures, business rules, result ordering/types, NULL/decimal/date rules, errors, state changes and rollback expectations. Verify reference and alternative answers plus plausible wrong answers.
- **Persistence:** browser-local editor draft storage is confirmed. Key drafts by challenge/dataset version (and sandbox dataset where applicable) so switching exercises does not overwrite unrelated SQL. Define autosave/restore details and communicate anonymous workspace expiry; exact expiry duration remains open. Durable attempt history, account-based progress, statistics and cross-device resume are deferred. Keep challenge/dataset definitions versioned; design future history compatibility when tracking is introduced. Operational logs for service recovery are separate from learner-facing statistics.
- **First procedure:** the challenge outline draft proposes OS-P01 (issue a refund) alongside OS-Q01 and OS-F01 for an online-store-only vertical slice. Stock transfer remains an inventory challenge. Confirm this refinement before authoring fixtures.

## Release gates

1. Product decisions and execution contracts are sufficiently resolved to specify three initial challenges without invented behavior.
2. Adapt the original first-milestone criteria to the account-free MVP: real execution, visible/hidden grading fixtures, alternative-answer checks, routine boundary/rollback tests, reset, cancellation, protected test assets, hints and explanations remain required. Saved attempt/progress history and restart persistence from original criteria 6/9 are deferred or narrowed to the draft behavior agreed in D11. Documented development startup remains useful.
3. Every shipped challenge has validated fixtures, hints, explanations and grading checks; alternative correct solutions pass and selected plausible errors fail.
4. The hosted static site works in supported browsers; a visitor can set up/pair the helper and complete representative query, function and procedure exercises without accounts or developer intervention. Verify HTTPS-to-loopback permission denial/recovery, refresh and expiry.
5. Trial findings are reviewed and release-blocking issues resolved before expanding the library.
6. Local execution controls are validated: unrelated databases/other helper namespaces remain untouched; sessions stay isolated; cancellation, compatibility checks, limits and cleanup permit recovery. A shared public SQL service is outside this architecture.

## Decision history

- 17 October 2026: User authorized Windows helper packaging, a guided prerequisite/startup/code launcher and a website download action. Implemented a standalone preview ZIP with Docker Desktop as its prerequisite. Clean-machine installation and public HTTPS/local-network permission trials remain subsequent gates; no signed installer or new platform support is implied.

- 17 October 2026: User selected the Focused Midnight Workbench revision and authorized implementation into the site. Preserve the full challenge specifications and learning/helper functionality while reducing default text and supporting panels. Earlier persistent expanded schema/default-results layout is superseded.

- 17 October 2026: User authorized the helper approach: learner-owned SQL server, frontend connection through a local helper and downloadable dataset setup SQL. Hosted frontend and account-free learning remain. Earlier zero-installation and shared hosted SQL assumptions are superseded; hosting estimate requires revision.

Hosting estimate: [MVP hosting estimate](querylab-hosting-estimate.md). Initial planning range is A$100–130/month, subject to architecture and capacity validation. User confirmed a provisional A$150/month hosting ceiling.

- 17 October 2026: User confirmed a broad audience of intermediate SQL learners, rather than a tool tailored solely to themselves. Exclude elementary retrieval exercises from the intended challenge scope.
- 17 October 2026: User expressed interest in optional hints suggesting SQL functions. Detailed hint behavior, assistance tracking and lesson format remain undecided.
- 17 October 2026: User confirmed the intermediate prerequisite baseline: joins, grouping, subqueries and NULL handling, with basic filtering assumed. CTEs, window functions, stored routines and transactions are development areas rather than entry requirements. Specific learning outcomes and challenge allocation remain proposed.
- 17 October 2026: User confirmed online store and business/inventory as the two starting MVP datasets. Challenge count and the six-query/three-function/three-procedure allocation remain proposals.
- 17 October 2026: User confirmed hosted website delivery. This supersedes local-only delivery and deferral of public hosting in the original brief/review. Accounts, public versus invite-only launch, hosting architecture, budget and concurrency remain open. Local startup checks in the original milestone remain useful for development; hosted delivery and isolation gates are additionally required for release.
- 17 October 2026: User confirmed no accounts for MVP, prioritizing functionality and challenges. Accounts and learner statistics tracking are among the first post-MVP additions. This supersedes earlier proposals for MVP durable progress/attempt history and assistance statistics. Anonymous workspace isolation remains necessary; browser-local draft persistence and session lifetime are still open.
- 17 October 2026: User confirmed browser-saved editor drafts that survive refresh, with practice data allowed to reset when an anonymous session expires. Reset retains the editor draft. Exact session expiry duration and autosave mechanics remain engineering details to specify.
- 17 October 2026: User confirmed 12 MVP challenges across the online-store and business/inventory datasets: six query, three function and three procedure challenges. Individual topics and allocation between the datasets remain to be specified.
- 17 October 2026: User confirmed optional progressive hints (conceptual nudge, named function/technique, partial example), separately available explained solutions, and deferral of standalone lessons until after MVP.
- 17 October 2026: User confirmed Run executes against practice data with changes retained until reset/session expiry; Submit grades against fresh test data without changing the practice workspace; Reset restores practice tables, data and routines while retaining the editor draft.
- 17 October 2026: User confirmed access for anyone with the URL and an initial target of 10 simultaneous learners. User stated "No budget currently"; budget is recorded as unset pending clarification, without assuming a zero-cost requirement or authorizing spending. Hosting selection and capacity validation remain engineering work.
- 17 October 2026: User clarified that a cost estimate is wanted before setting a budget. Prepared a sourced hosting estimate; no expenditure or provider selection is approved.
- 17 October 2026: User accepted A$150/month as the provisional hosting ceiling. Validate capacity and actual total charges before selecting production hosting; revisit the ceiling if the measured execution architecture cannot fit it.
- 17 October 2026: User selected Midnight Workbench as the MVP design direction. Use concept 1 as the visual reference; the other concepts remain alternatives, not additional committed features.
