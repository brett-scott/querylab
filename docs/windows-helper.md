# Windows helper download and launcher

The current download is version **0.4.1** and includes all twelve MVP challenges. Existing downloaded runtimes need the updated bundle to receive the expanded curriculum. See [curriculum validation](curriculum-validation.md).

The website now serves a standalone Windows preview ZIP. Learners need Docker Desktop with Linux containers; Git, Node, Python and the QueryLab repository are not required on their computer. The archive includes the local runtime source, launcher and configuration templates; first startup downloads Docker images and builds the helper locally. Docker Desktop itself is not bundled or installed automatically.

## Learner journey

1. Open QueryLab and choose **Download Windows helper**. The site checks that the current package and its manifest exist before enabling the download.
2. In File Explorer choose **Extract All**, then open the extracted `QueryLab-Helper` folder. Keep this folder for subsequent launches and upgrades.
3. Double-click **Start-QueryLab-Helper.cmd**. It opens the guided Windows setup window.
4. On the website choose **Copy website address**, then paste that address into the launcher. This explicitly trusts that website to connect to the local helper after pairing.
5. Choose **Start helper**. The launcher checks Docker, its daemon, Linux-container mode and Compose. It starts the private database/helper in the background, then checks MySQL readiness.
6. Choose **Copy pairing code**, return to the website, paste it into Pairing code and choose **Pair helper**. The default Helper URL remains prefilled; use the launcher's URL if using a custom port. Allow browser local-network access if asked.

Windows is the first packaged platform. This is an unsigned ZIP/script preview rather than a signed MSI or executable installer. Windows downloaded-file prompts, high-DPI behavior, first-run Docker installation and the full journey on a clean Windows computer still require validation. HTTPS-to-localhost browser permission testing also remains a separate release gate.

## Restart, recovery and privacy

Closing the window keeps Docker containers running. Reopen the same launcher and choose Start helper to retrieve the code again. To stop the services, stop this installation's `querylab-installed-...` project in Docker Desktop. Startup failure preserves configuration so the learner can correct the problem and retry.

The generated `.env.helper` contains the local pairing code, namespace and database credentials. Keep it private and retain it with its database volume. The website download never includes a configured environment file. The launcher checks ownership of an occupied port and refuses to overwrite another installation. A development helper already running on port 8765 must be stopped before a separate downloaded installation uses that port.

Each installation's Docker project is derived from its persistent namespace. This preserves data isolation between extracted installations. The launcher adds the selected exact website origin without resetting credentials or the namespace. Passwords remain local; no HTTP credential configuration or code-disclosure endpoint is added. Local grading assets are inspectable by the computer's owner and support practice rather than exam integrity.

Advanced users may configure an existing compatible MySQL instance in the local `.env.helper`; its settings are preserved and bundled MySQL is omitted. The default first-launch flow uses the bundled practice instance. See [local helper](local-helper.md) for database requirements and execution boundaries.

## Building the download

From the repository root:

```powershell
node scripts/package-helper.mjs
```

This produces generated, ignored files in `frontend/public/downloads/`:

- `querylab-helper-windows.zip`
- `querylab-helper-windows.json` with version, bytes, SHA-256, platform, requirements and file inventory.

Packaging uses an explicit source allowlist. It excludes local `.env` files, repository metadata, runtime state, caches and development dependencies. PowerShell files are packaged as UTF-8 with BOM for Windows PowerShell 5.1. ZIP entries have deterministic ordering/timestamps. The manifest checksum verifies archive integrity; it is not a code-signing certificate.

Both frontend build variants and the dev server generate the download automatically. Docker frontend builds now use repository-root context with a strict `.dockerignore`, because the package needs backend/launcher sources as well as frontend files. Only built static files are copied to the final Nginx image. Upload all of `frontend/dist/`, including `downloads/`, when hosting the static website.

## Verification

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/test-helper-launcher.ps1
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File distribution/windows/launch-helper.ps1 -ValidateUI
```

The native window can be rendered offscreen without displaying code using `-ValidateUI -PreviewPath <png-path>`. This is layout evidence, not an interactive desktop walkthrough.

`scripts/verify-helper-package.py` independently checks the archive using Python's standard ZIP implementation, validates CRC/SHA and confirms credential exclusion. It is a developer check, not a learner prerequisite. CI source includes the package check and Windows launcher checks; local evidence is recorded in [download QA](helper-download-qa.md) and [helper validation](helper-validation.md).
