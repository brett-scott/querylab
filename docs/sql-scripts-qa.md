# SQL query separators and grouping feedback

18 October 2026. QueryLab accepts separate top-level SELECT/WITH queries on new lines without semicolons. The last query also needs no trailing semicolon. Explicit semicolons still end statements: they are not removed or ignored. Other statement types and routine bodies retain normal delimiters.

The runner handles explicit statement boundaries first, then tokenizes read-query batches. It preserves nested SELECTs, CTE bodies and their main SELECT, compound SELECT operands, strings, quoted identifiers, comments and WITH ROLLUP. It does not infer boundaries in mutation/routine definitions. Multiple implicit queries still count toward the existing statement limit; query Submit still accepts only one query.

A detached GROUP BY, WHERE, ORDER BY, HAVING, LIMIT or JOIN clause now produces a direct instruction to remove the preceding semicolon and run the complete query. Validation happens before executing the script. ONLY_FULL_GROUP_BY remains enabled. The reported order/item aggregation executes successfully when its semicolon before GROUP BY is removed; genuinely missing grouping still produces MySQL's grouping error.

Verification:

- **218 backend tests passed** against real MySQL 8.4.9 in 154.57 seconds, with one existing Starlette/AnyIO deprecation warning. This includes all twelve reference graders and 30 new separator/clause tests.
- **Nine development API/browser tests passed**, including selected SQL, newline batches containing a CTE, UNION and scalar subquery, both result sets, the supplied aggregation, misplaced-semicolon feedback and strict-grouping rejection.
- The helper run passed five of six tests, including all twelve graders and Windows download integrity. Its recovery test hit the pairing rate limit; the targeted rerun passed in 4.7 seconds after the rate window reset. The production rate limit was unchanged. Test pairing inputs are cleared before failure artifacts can be collected.
- Both development and helper-mode builds passed and both local stacks were updated. The Windows download is **0.4.1**, **28 files**, **63,909 bytes**, SHA-256 `7e003896e8d432d40bdce85fee242093e46a73b8ce02b8ced4ad914fba796cca`. Both preview sites serve that same artifact; ZIP integrity, standalone Compose and credential exclusion checks passed.

Existing separately downloaded helpers need v0.4.1 for the parser change; updating only their static website cannot change their local SQL runner. The GitHub Actions workflow has not been run in this session.

MySQL's own [statement delimiter rules](https://dev.mysql.com/doc/refman/8.4/en/entering-queries.html) and [grouping rules](https://dev.mysql.com/doc/refman/8.4/en/group-by-handling.html) explain the original error. QueryLab's optional query boundaries are a client-script convenience rather than a server SQL-mode change.
