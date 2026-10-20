# Google accounts and learning statistics

## Current scope

The user chose to skip the learner pilot because no testers are available and authorized work towards accounts/statistics. Google sign-in is confirmed. The engineering defaults below keep the current GitHub Pages website and local SQL helper intact.

- Guest practice remains available. Signing in adds a private progress record.
- Supabase provides Google authentication, the progress API and PostgreSQL storage. The helper does not receive Google tokens or account credentials.
- The first dashboard shows completed challenges, graded submissions, submission pass rate, challenges passed without hints/solution recorded, progress by challenge/version and the latest 20 submissions.
- Only challenge/result/assistance metadata is synced. SQL text, result rows, fixture contents, helper pairing/bearer tokens and MySQL credentials are excluded.
- Editor drafts remain local to this browser. This release does not sync SQL drafts, import earlier guest attempts, add leaderboards, measure time spent learning or provide certificates.

Implementation is prepared locally. **Live Google sign-in requires the owner to configure Supabase and Google, then redeploy.** No Supabase project URL or publishable key has been supplied. Until both public configuration variables are set, the site retains guest-only behavior and hides the account control.

## Enable accounts on the live site

Current site: **https://brett-scott.github.io/querylab/**.

### 1. Create the account/progress backend

Create a dedicated **Free** project in [Supabase](https://supabase.com/dashboard). In its SQL editor, run the entire [progress migration](../supabase/migrations/202610180001_progress.sql) once. This creates `challenge_attempts`, its row-level security policies, an index, and a `challenge_progress` view that respects the caller's row permissions. Use a dedicated QueryLab project; this migration creates new objects rather than altering an existing application.

From the project's API settings, note:

- Project URL: `https://<project-ref>.supabase.co`
- **Publishable** key: `sb_publishable_...` (the legacy `anon` key is also supported)

The website can contain these public values because access is enforced by authentication and row-level security. **Never put a Supabase secret/service-role key or Google client secret into GitHub variables, frontend environment files or browser code.** Builds reject secret/service-role keys and incomplete configuration. See [Supabase API keys](https://supabase.com/docs/guides/api/api-keys) and [row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security).

### 2. Configure Google sign-in

Follow [Supabase's Google setup guide](https://supabase.com/docs/guides/auth/social-login/auth-google) to create a Google Cloud OAuth **Web application** client and configure its audience/branding.

| Google setting | Value |
| --- | --- |
| Authorized JavaScript origin | `https://brett-scott.github.io` |
| Authorized redirect URI | `https://<project-ref>.supabase.co/auth/v1/callback` — copy the exact callback URL from Supabase's Google provider settings |
| Scopes | Basic sign-in identity: `openid`, email and profile |

Enable **Google** in Supabase's authentication providers and enter the Google client ID and secret **there**. Google returns to Supabase first; Supabase then returns to QueryLab. The Google callback is not the GitHub Pages address.

If the Google application is in Testing mode, add the Google accounts that will sign in as test users. Configure the appropriate audience/publication state when opening access beyond those users. Do not add Gmail, Drive or other unrelated API scopes.

### 3. Configure the return address

In Supabase **Authentication → URL Configuration**:

- Site URL: `https://brett-scott.github.io/querylab/`
- Allowed redirect URL: `https://brett-scott.github.io/querylab/`

The trailing slash and `/querylab/` path matter. The frontend uses a PKCE authorization-code flow and returns to the existing index page, so Pages does not need an `/auth/callback` route. It remembers the selected challenge in this tab, restores it on return, and removes the temporary authentication parameters. See [Supabase PKCE](https://supabase.com/docs/guides/auth/sessions/pkce-flow).

For local preview only, additionally allow `http://127.0.0.1:5173/querylab/` (or `/` if building at the root). Do not change the local helper's trusted origin when the public site's hostname stays the same.

### 4. Add the public GitHub build configuration

Commit and push this iteration's source changes to `main`, including the updated Pages workflow, account components and database migration. Keep configured environment files and secrets out of the commit. A deployment before the public variables are set will remain guest-only.

In the GitHub repository, open **Settings → Secrets and variables → Actions → Variables** and add both repository variables:

```text
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

The [Pages workflow](../.github/workflows/pages.yml) passes these public values into the Vite build. Run **Deploy QueryLab to GitHub Pages** on `main` again. No secret key or additional self-hosted server is needed. The existing helper download does not need an upgrade for account support.

### 5. Verify the live account flow

Open the deployed site, choose **Sign in → Continue with Google**, and confirm you return to the same challenge. Pair the helper if necessary. Submit an incorrect answer and a correct answer, open **Progress**, and check the counts. Verify a second browser/device using the same Google account can see the saved record. Signing out should keep local SQL drafts/helper connection but hide account progress.

Test real Google authorization denial and cloud unavailability as well. The local automated OAuth tests use controlled responses and do not establish that your Google console, Supabase redirects or hosted policies were configured correctly.

## Metric definitions and recovery

| Metric | Definition |
| --- | --- |
| Graded submissions | A Submit job observed to complete with a `grading` result, saved once under a unique submission UUID |
| Completed challenges | Distinct challenge IDs with at least one saved passing submission, across saved versions |
| Submission pass rate | Passing graded submissions divided by all graded submissions; no submissions displays a dash |
| Passed without hints or solution | Distinct challenges with a passing attempt that recorded zero hints and no revealed solution |
| Challenge progress | Aggregate by challenge ID and version; later failed attempts do not erase an earlier completion |
| Recent submissions | Latest 20 saved attempts, ordered by client-observed completion time |

Run does not record an attempt. Failed grading counts towards pass rate; execution/policy/infrastructure errors and cancellation do not. Opening a solution confirmation does not count as viewing it; successfully revealing the solution does. Assistance is remembered per browser draft/challenge version across refresh and Reset, including assistance seen before login. These are personal practice statistics based on the learner-local helper and browser records, not tamper-proof assessment results.

A submission captures the account identity when Submit starts. A different account cannot receive that result if sign-in changes during grading. The same idempotency UUID is used on retry. Cloud write failures queue only metadata under the original account in local browser storage and retry on reconnect, account return or **Retry sync**. A queue is never uploaded under another account. If browser storage is unavailable, the user is told to keep the tab open for retry.

The active graded job's ID and metadata are retained in this tab's session storage, bound to the account, helper origin and challenge/version. Refresh can recover its result while that same helper session/job still exists. If the helper has restarted or its session expired, the site asks for a new submission and does not invent a saved outcome. Closing the tab removes this active-job recovery state; successfully synced attempts remain in the cloud. Guest attempts are not backfilled into an account.

Cloud history is append-only for the browser role. Each account can select/insert only its own rows; anonymous access is denied. The aggregate view uses `security_invoker`, so it cannot expose other users' totals. Managed account deletion by the project owner in Supabase Auth cascades to the saved attempts. A self-service account-deletion UI, draft sync and additional statistics can be later iterations.

## Costs and operation

For the initial five simultaneous learners, Supabase Free is a reasonable starting point: its published allowance includes 50,000 monthly active users and a 500 MB database, with social OAuth included. Free projects can pause after a week of low activity; restore a paused project in the dashboard if sign-in/progress becomes unavailable. Guest SQL practice can continue while cloud accounts are unavailable. This is a planning estimate, not a purchase or availability promise. Sources checked 18 October 2026: [pricing](https://supabase.com/pricing), [free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

GitHub Pages continues hosting static assets. Supabase stores only account/progress data; SQL execution stays local. No paid plan, Google configuration, cloud database or user account has been created by this implementation.

## Local checks

With Node 24 installed, from the repository root:

```powershell
node --experimental-strip-types --test frontend/tests/progress.test.mjs
node scripts/test-progress-database.mjs
```

The second command needs Docker and creates a disposable, unexposed PostgreSQL 17 container. It verifies ownership before removing its own test container. It checks real SQL grants/RLS, cross-account access, append-only history, duplicate retries and assistance aggregates; its `auth.uid()`/roles are a minimal Supabase authorization fixture rather than a hosted Supabase instance.

For the controlled Google/REST browser checks, install dependencies in `frontend/` and `qa/`, then build with test-only public configuration:

```powershell
cd frontend
$env:QUERYLAB_BASE_PATH = '/querylab/'
$env:VITE_SUPABASE_URL = 'https://querylab-auth.test'
$env:VITE_SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_querylab_browser_test'
npm run build:helper
cd ../qa
npx playwright test --config playwright.accounts.config.js
```

The callback test runs without a helper. To include actual SQL grading, run an isolated development helper first, set `QUERYLAB_ACCOUNTS_WITH_HELPER=1`, and use its matching ignored `.env.helper`. `QUERYLAB_HELPER_API_URL` and `QUERYLAB_ACCOUNTS_HELPER_ENV` can select a separate QA helper/configuration. Tests disable traces and automatic screenshots, clear the pairing field on failure and use fictitious account data. Never publish a build containing the test-only Supabase URL. Clear the two `VITE_SUPABASE_*` environment variables and rebuild to return to guest-only preview.

The **Verify QueryLab** workflow includes these checks with a disposable helper. Production Google OAuth and live Supabase configuration remain owner-side activation checks.

## Verification record

Local checks on 18 October 2026 used Node 24, installed Edge, a separate QA helper/MySQL on loopback port 8766, and disposable PostgreSQL 17. The user's existing helper was not restarted or reconfigured.

| Check | Result |
| --- | --- |
| Progress/configuration/recovery unit tests | 8 passed |
| Actual PostgreSQL grants, RLS, idempotency and assistance aggregates | Passed |
| Account-enabled helper-mode builds at `/querylab/` and `/` | Both passed |
| Account browser suite at `/querylab/` | 2 passed in 8.5 seconds |
| Account browser suite at `/` | 2 passed in 8.3 seconds |
| Original production-mode build | Passed |
| Guest helper-mode browser suite at `/` | 2 passed in 10.5 seconds |
| Guest helper-mode browser suite at `/querylab/` | 2 passed in 10.4 seconds |
| Windows helper ZIP integrity/allowlist/credential exclusion | Passed; v0.4.1, 28 files, 63,909 bytes |
| Workflow YAML/public-variable wiring checks | Passed; GitHub workflow execution not performed here |

The account suite covers controlled Google denial and PKCE callback responses, selected-challenge return, metadata-only writes, Run exclusion, failed/passing grade counts, persistent retry across refresh, duplicate suppression, hint/solution memory, refresh during actual grading, editor readiness after recovery, sign-out and a second account's separate record. Real MySQL performs grading; Google/Supabase REST responses are controlled fixtures. Actual database access policies are exercised separately with PostgreSQL roles and a minimal `auth.uid()` fixture. Neither is a claim of successful live Google authorization or a configured hosted Supabase project.

The desktop (1600×1000) and narrow (375×800) dashboard screenshots in `qa/screenshots/accounts/` were visually reviewed. Screenshots use fictitious identities. The latest ignored account result JSON contains the root-path run; the table records both path runs. The last build was returned to guest-only helper mode at `/querylab/` and checked to exclude test-only account configuration. Backend/helper runtime code was unchanged, so the full 218-test backend suite was not rerun for this iteration.
