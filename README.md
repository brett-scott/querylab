# QueryLab

Real MySQL practice for intermediate SQL learners, using the selected [Focused Midnight Workbench design](design/querylab-04-focused-workbench.png).

All 12 MVP challenges are implemented across the online-store and inventory datasets: six queries, three functions and three procedures. Each includes executable fixtures, automatic grading, three progressive hints and an explained solution. This remains a local preview; public hosting and installation release checks are separate milestones. See the [curriculum verification](docs/curriculum-validation.md).

The preferred direction now uses a **static website + local helper + learner-owned MySQL**. Credentials stay on the learner's computer. See the [helper setup guide](docs/local-helper.md) and [helper validation](docs/helper-validation.md). The original all-in-one development mode remains available below.

## Deploy the website to GitHub Pages

The Vite build and [Pages workflow](.github/workflows/pages.yml) support a project URL such as `https://<account>.github.io/querylab/`. Enable **Settings → Pages → Source: GitHub Actions**, then run **Deploy QueryLab to GitHub Pages** on `main`. Later pushes to `main` deploy automatically. The workflow builds in helper mode, packages the Windows download, checks the actual base path in a browser and publishes only `frontend/dist/`. MySQL and the helper stay on each learner's computer.

See the [deployment and preview guide](docs/github-pages.md) for the full setup, repository eligibility, local checks and remaining public HTTPS validation. No site has been published from this workspace.

## Download the Windows helper

The local website at **http://127.0.0.1:8081** now provides **Download Windows helper**. Extract the ZIP and open **Start-QueryLab-Helper.cmd**. Copy the website address into the setup window, choose Start helper, then copy its pairing code back into the website. Docker Desktop with Linux containers is required; Git, Node, Python and a repository checkout are not required for this packaged flow.

See the [Windows setup guide](docs/windows-helper.md) and [download QA](docs/helper-download-qa.md). This is an unsigned Windows preview ZIP. A clean-computer installation trial and public HTTPS/local-network permission checks remain outstanding. A different helper already using port 8765 must be stopped before a separate downloaded installation can use it.

## Start the helper preview from source

Install Docker Desktop with Linux containers, then run:

```powershell
./scripts/start-helper.ps1 -Preview
```

Open the **website at http://127.0.0.1:8081**. Paste **http://127.0.0.1:8765** into its **Helper URL** field and enter the pairing code printed in your terminal. Opening the helper address directly shows a connection guide. This starts bundled practice MySQL. To use your own MySQL 8.4 server, follow the [existing-server instructions](docs/local-helper.md#use-an-existing-mysql-server). Dataset SQL downloads are available after pairing. The public HTTPS-to-localhost browser flow remains to be verified.

## Start the development stack

Install Docker Desktop with Linux containers enabled. No local Python or MySQL installation is needed for the container workflow.

On Windows PowerShell, from this directory:

```powershell
./scripts/setup.ps1
docker compose up --build --wait
```

Open **http://localhost:8080**. The setup script generates an ignored `.env` with a random database password and preserves an existing file. On other platforms, copy `.env.example` to `.env` and replace the placeholder password before starting Compose. Change `QUERYLAB_PORT` to use another local port.

```powershell
docker compose stop
```

Stopping containers retains database storage. Use the UI's Reset workspace action to restore practice fixtures; it retains browser-saved editor drafts. Anonymous sessions are temporary, and database mutations are not promised across backend restarts or expiry. Editor drafts are stored in the current browser and are lost if its storage is cleared.

## Learning workflow

The focused workbench starts with a short challenge overview and a wide editor. Open **Requirements** for the complete business rules and **Expected output** for the output contract. **Schema** opens the dataset explorer; **Focus** hides supporting panels. Results expand when you execute SQL and can be collapsed again. Drag the divider between the editor and results up or down to resize them; the divider also supports the arrow keys. Hints and explained solutions remain available on demand. Reset is in the labelled workspace menu. See [focused UI verification](docs/focused-ui-qa.md) for tested interactions and limitations.

The complete curriculum uses the focused workbench, including inventory routines, per-challenge drafts and dataset reset. Current verification is recorded in [curriculum validation](docs/curriculum-validation.md); the earlier [focused UI report](docs/focused-ui-qa.md) records the layout milestone. Public HTTPS-to-localhost browser permissions remain release work.

- **Run** executes the highlighted SQL, or the full editor script when nothing is selected. Ctrl/?+Enter follows the same rule. Separate SELECT/WITH queries can start on new lines without semicolons; other statement types and stored routines retain their normal separators. Results and errors come from the current practice dataset; SQL changes persist for the anonymous session until reset.
- **Submit** grades the full editor script on fresh disposable fixtures, preserving the practice workspace. Highlighting SQL does not restrict Submit. Query correctness, function boundary cases and procedure state/rollback behavior are checked independently of SQL text.
- **Cancel** requests cancellation of database execution, not just the HTTP request.
- **Hints** reveal three authored levels; the explained solution is a separate explicit action.
- **Reset workspace** recreates the selected practice dataset and removes learner-created objects without replacing the editor draft.

Each Run uses one fresh database connection. Finish any explicit transaction within the same script; uncommitted changes roll back when it closes. This milestone allows data changes and stored routines, with table/view/trigger creation deferred. The refund exercise updates a maintained payment-refund summary before inserting its audit row so rollback grading checks a genuine partial-failure case.

The browser never receives database credentials. There are no accounts, learner statistics or durable attempt histories in this milestone.

## Development layout

| Path | Purpose |
| --- | --- |
| `frontend/` | React/TypeScript workbench, CodeMirror SQL editor, result grids and API integration |
| `backend/` | FastAPI, authored content, MySQL runner, fixture grading and anonymous session/job lifecycle |
| `compose.yaml` | Isolated development network, pinned MySQL engine, API and frontend reverse proxy |
| `compose.helper.yaml` | Loopback helper, optional bundled MySQL and independent static preview |
| `qa/` | Integration/browser checks and screenshot evidence |
| `docs/` | API contract, implementation plan and UI review |
| `design/` | Selected design reference and earlier concept images |

For frontend-only development after installing Node 24:

```powershell
cd frontend
npm ci
npm run dev
```

Use the full stack for execution and grading; an offline backend produces an explicit service error, not simulated SQL results. See `frontend/vite.config.ts` for the API proxy target.

## Verification

Frontend compilation:

```powershell
cd frontend
npm run build
```

Backend tests run inside the Python container. From the repository root, with the MySQL service running:

```powershell
docker compose run --rm --no-deps -e PYTHONPATH=/app -e QUERYLAB_INTEGRATION=1 -v "${PWD}/backend:/app:ro" backend python -m pytest tests -q -p no:cacheprovider
```

See [QA instructions](qa/README.md) for browser and API verification. The [implementation plan](docs/implementation-plan.md) separates completed work from the remaining release gates; a successful build alone is not public-hosting approval.

The GitHub Actions workflow includes the original backend/API checks and a separate static-frontend/helper browser job against real MySQL. Browser checks also run locally with the QA instructions. This workflow is supplied as source and has not been run on GitHub from this session.

## Hosting boundary

Compose binds the frontend to loopback and does not expose MySQL or the API directly. This is a development setup. Learner accounts are schema-scoped and executions are bounded, but shared-server MySQL execution needs an independent isolation review before public access. Ten simultaneous learners is a target to measure, not a capacity guarantee.

The helper architecture moves SQL execution costs to each learner's computer. All twelve challenges are implemented. GitHub Pages deployment preparation is in place; public HTTPS-to-loopback browser testing and local setup/recovery trials remain release work. Free static hosting is the current planning assumption for five simultaneous learners; see the [updated hosting estimate](querylab-hosting-estimate.md). Keep both local APIs private. Use one backend worker because anonymous session/job state is process-local.

The engine is pinned to MySQL 8.4.9 for reproducibility; review updates before public deployment. References: [MySQL release notes](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-9.html), [FastAPI container deployment](https://fastapi.tiangolo.com/deployment/docker/).

## Product records

- [MVP decisions](querylab-mvp-decisions.md)
- [Challenge outlines](querylab-mvp-challenges.md)
- [Hosting estimate](querylab-hosting-estimate.md)
- [Original brief](querylab-brief.md)

