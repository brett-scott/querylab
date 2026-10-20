# Deploy QueryLab to GitHub Pages

QueryLab's public MVP is a static Vite/React website. Each learner runs the downloaded helper and MySQL on their own computer. GitHub Pages serves the website and Windows ZIP; it does not run Python, Docker, MySQL or grading.

## First deployment

1. Commit and push the project source, including `.github/workflows/pages.yml`, to the repository's `main` branch. Keep `.env`, `.env.helper`, credentials and local editor/agent configuration out of the commit; build outputs and generated downloads are already ignored.
2. In the GitHub repository, open **Settings → Pages → Build and deployment** and set **Source** to **GitHub Actions**. The repository needs Pages access: GitHub Free supports public repositories; private repositories require an eligible paid plan. See [GitHub's publishing instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
3. Open **Actions → Deploy QueryLab to GitHub Pages → Run workflow**, select **main** and run it. Later pushes to `main` deploy automatically. If the first push ran before Pages was enabled, rerun the failed workflow after changing the setting.
4. Open the URL shown by the completed deployment. A normal project site is `https://<account>.github.io/querylab/`. Use the actual URL from GitHub, including the repository path. GitHub's `github.io` sites use HTTPS automatically; keep **Enforce HTTPS** enabled where available. See [HTTPS support](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).

No personal access token, database password or custom Actions secret is required. The workflow uses GitHub's automatic token with read access during the build and Pages/OIDC write permissions only in the deployment job. Deployments are restricted to `main`; manual runs on other branches build but do not publish. The `github-pages` environment can also be restricted to `main` in repository settings.

## What the workflow does

The build uses Node 24 and `npm ci` in `frontend/`, then runs **`npm run build:helper`**. The prebuild step generates the standalone Windows helper ZIP from allowlisted runtime files and configuration templates. Python independently checks ZIP integrity, the file list and checksum. A browser check verifies the website, ZIP download, home link and query-string refresh at the configured base path before publication.

Only **`frontend/dist/`** is uploaded as the Pages artifact. The ZIP deliberately contains the helper's runtime source and templates; configured credentials, local state and developer tooling are excluded. The development Compose stack and API are not deployed. Full backend and real-MySQL helper checks remain in the separate **Verify QueryLab** workflow; the Pages deployment does not wait for that separate workflow.

`actions/configure-pages` supplies the URL base path. Vite reads it from `QUERYLAB_BASE_PATH`, and site links use Vite's `BASE_URL`. This supports `/querylab/`, a renamed repository path, and `/` for an account site or configured custom domain. No hardcoded GitHub account name is needed. Challenge links use `?challenge=OS-F01`, so refresh does not depend on server-side SPA rewrites. See [Vite's deployment guide](https://vite.dev/guide/static-deploy#github-pages) and [GitHub's workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Learner setup on the hosted site

1. Open the hosted website and choose **Download Windows helper**.
2. Extract the ZIP and open `Start-QueryLab-Helper.cmd`. Docker Desktop must be running with Linux containers.
3. Use **Copy website address** on the website and paste that address into the launcher. This intentionally copies the **origin only**, such as `https://<account>.github.io`, without `/querylab/`; the helper validates browser origins rather than page paths.
4. Start the helper, copy its pairing code, then paste it into the website. Leave **Helper URL** at `http://127.0.0.1:8765` unless a different local port was configured. Allow local-network access if the browser asks.

When using an existing source-based installation, add the same origin without changing the installation's database credentials or namespace:

```powershell
./scripts/setup-helper.ps1 -WebsiteOrigin 'https://<account>.github.io'
./scripts/start-helper.ps1
```

Keep each learner's helper private on loopback. Publishing the website does not require exposing their helper or MySQL to the internet. A later hostname/custom-domain change requires trusting that new origin in the learner's launcher.

## Preview and check before pushing

From the repository root in PowerShell, with Node 24 installed:

```powershell
cd frontend
npm ci
$env:QUERYLAB_BASE_PATH = '/querylab/'
npm run build:helper
npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/querylab/**. Use `/` instead when testing an account site or custom domain. Stop this preview before running the automated check, which starts its own preview on port 5173:

```powershell
cd qa # from the repository root
npm ci
$env:QUERYLAB_BASE_PATH = '/querylab/'
npx playwright test --config playwright.pages.config.js --grep 'static Pages build'
```

Windows uses installed Edge. On Linux, install Chromium first with `npx playwright install --with-deps chromium`. The **Verify QueryLab** workflow checks both `/` and `/querylab/` on pushes and pull requests without requiring Pages to be enabled.

To additionally verify actual pairing, a SQL run, draft refresh and query/function/procedure grading, first start the source helper with `./scripts/start-helper.ps1` from the repository root, then run the Pages suite inside `qa/` with:

```powershell
$env:QUERYLAB_PAGES_WITH_HELPER = '1'
npx playwright test --config playwright.pages.config.js
```

The default helper template trusts the local preview origin `http://127.0.0.1:5173`; existing custom configurations may need that origin added. These tests create a private learner session and read the pairing code internally from ignored `.env.helper`. They disable traces and screenshots and clear the code field on failure. Run against a development helper, not an installation with unrelated active learners. Use `$env:QUERYLAB_BASE_PATH = '/'` for a root-path check; remove that environment variable after preview/testing to restore the normal local build default.

## Cost and release boundary

For the initial five simultaneous learners, free Pages hosting is a reasonable planning assumption when repository/account eligibility permits. The built site and helper ZIP total about 1 MB after adding the account client, well below the published 1 GB site limit. GitHub documents a soft 100 GB/month bandwidth limit and restricts commercial SaaS use. A custom domain and any paid GitHub plan are separate costs. See [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

Local root/subpath checks do not establish that a public HTTPS page can pair on every browser. Before calling the public MVP released, trial the actual deployed URL on a clean Windows machine: download/install, allow/deny/recover local-network permissions, pair, refresh, recover an expired session, and complete a query, function and procedure. The current source preparation does not itself publish a site or certify that browser journey.

## Local verification — 18 October 2026

| Check | Result |
| --- | --- |
| Original production-mode build at `/` | Passed TypeScript and Vite compilation |
| Helper-mode builds at `/querylab/` and `/` | Both passed TypeScript and Vite compilation |
| `/querylab/` browser suite, including real local MySQL | 2 passed in 11.2 seconds |
| `/` browser suite, including real local MySQL | 2 passed in 11.3 seconds |
| Independent Python ZIP verification | Passed: 28 allowlisted files, CRC/checksum, standalone Compose, credential exclusion |
| Workflow source checks | Both workflow files parsed without duplicate keys; main branch, deployment dependency/permissions and static artifact path checked |

Browser runs used installed Edge and the source helper at `127.0.0.1:8765`. At each path, the checks covered helper-mode startup without a `?helper=1` flag, ZIP signature/checksum and actual browser download, origin-only launcher address, home navigation, query-string refresh, real pairing, SQL result `42`, saved draft after refresh, and passing submissions for OS-Q01, OS-F01 and OS-P01. No JavaScript page errors or requests for an API on the static website were observed. The latest ignored `qa/pages-test-results.json` records the root-path run; the table records both completed runs.

The GitHub Actions workflows have not been executed or inspected on GitHub from this workspace. Backend code was unchanged, so the complete backend suite was not rerun for this deployment-path change.

## User-confirmed hosted acceptance checks

After deployment preparation, the user reported that the page is deployed and successfully connects to their local helper. They subsequently confirmed all four requested acceptance checks passed:

| Hosted check | Reported result |
| --- | --- |
| Run and submit a query, function and procedure challenge | Passed |
| Refresh with saved SQL draft and connection recovery | Passed |
| Disconnect and pair again | Passed |
| Another learner tries the downloaded helper from a fresh installation | Passed |

These are user-reported outcomes, separate from the agent's local automated checks. The deployment URL, browser and permission-prompt behavior were not supplied, and the live site has not been independently inspected from this workspace. Manual disconnect/re-pair does not establish recovery after an actual expired session; explicit expiry and browser permission allow/deny/recovery remain open.

The user subsequently chose to skip the pilot because no testers are available and requested accounts/statistics. Google sign-in is confirmed. See the [Google account/progress setup guide](accounts-and-statistics.md) for this next iteration; the pilot is no longer a prerequisite.
