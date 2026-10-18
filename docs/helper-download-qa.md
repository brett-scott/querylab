# Windows helper download: evidence QA

17 October 2026. **PASS for the tested local Windows download milestone.** A public-site release and clean-computer installation remain unverified.

## Requirements and scope

The user requested points 1–3 of the agreed next steps:

1. “Package the helper for download, starting with Windows.”
2. “Add a guided launcher that checks prerequisites, starts the helper and clearly displays the pairing code.”
3. “Add ‘Download helper’ to the website, with clear setup and recovery instructions.”

This review directly tests the static site on `http://127.0.0.1:8081`, separate local helper on port 8765, real MySQL, and installed Microsoft Edge through Playwright on Windows. Launcher-specific results supplied by the launcher owner and extracted-package verification supplied by the coordinating agent are recorded separately below. They are not inferred from screenshots of the website.

## Browser/API evidence

From `qa`:

```powershell
npx.cmd playwright test --config=playwright.helper.config.js
```

**Final frozen-package run: six tests passed in 23.0 seconds**, exit code 0; `qa/helper-test-results.json` records six expected, zero skipped, zero unexpected and zero flaky results. The earlier integrated run passed six tests in 23.2 seconds, followed by a passing narrow-screen-only capture rerun. The final run restores the full six-test report. The suite disables traces, videos and automatic screenshots; deliberate screenshots mask the pairing input. Pairing configuration is read privately from ignored local configuration and is never printed or attached.

| Tested behavior | Observed outcome |
| --- | --- |
| Public Windows package manifest and download | HTTP 200 JSON manifest and HTTP 200 ZIP, correct ZIP MIME type and `504b0304` signature |
| Package integrity | Browser-downloaded filename, byte count and independently computed SHA-256 match the manifest |
| Manifest contents | Required launcher, scripts, Compose file and README listed; no local environment, Git, node_modules or runtime-state paths listed |
| First visit | Download link visible without scrolling at 1600×1000 and 375×667; setup steps expanded; existing Helper URL stays prefilled |
| Launcher instructions | Extract All, exact command launcher filename, website address, Start helper, Copy pairing code, and return-to-pair steps displayed |
| Website-address copy | Clipboard copy succeeds and matches the current website origin; a simulated denied clipboard displays a selectable, read-only address fallback |
| Download failures | Simulated missing manifest and HTML returned as a ZIP both withhold the download link; Retry recovers after valid responses resume |
| Mobile disclosure and layout | Keyboard toggling works; no horizontal overflow at 375 pixels; pairing field and Check connection are reachable and visible after scrolling |
| Existing helper transport protections | Exact-origin denial, bearer authentication, wrong-code rejection, preflight behavior and absence of helper cookies still pass |
| Existing learning workflow | Real SQL returns 42; reference solution grades successfully; dataset SQL downloads; refresh, disconnect and re-pair retain drafts |
| Existing recovery | Invalid bearer reopens pairing; execution remains disabled while the new session's schema initializes; immediate Run then returns 123 |
| URL and outage errors | Remote helper URL is rejected before an outbound request; simulated unreachable localhost displays recovery messaging |

Final package observed during this run: version **0.3.0**, **43,585 bytes**, **22 files**, SHA-256 `2819b8748cdac77b8d9e36becf9d0298651e3335380c084833272bacf7a96848`. The archive is a small runtime source/launcher bundle; Docker downloads and builds the actual runtime on first launch. It is not a bundled Docker Desktop installer.

## Visual review

The following screenshots were opened and visually reviewed under `qa/screenshots/helper/`:

- `download-before-desktop.png`: previous source-folder instructions and unavailable-installer notice.
- `download-ready-desktop.png`: charcoal/mint card, prominent mint Download Windows helper action, explicit Docker prerequisite, and expanded numbered setup steps.
- `first-time-setup-mobile.png` and `download-mobile-viewport.png`: wrapped download action visible in the initial 375×667 viewport, readable vertically flowing setup, no horizontal clipping.
- `download-clipboard-fallback.png`: visible fallback message and selected website address after clipboard denial.
- `connection-mobile-form.png`: collapsed support instructions and labelled prefilled URL/password pairing form; code field deliberately masked.
- `download-unavailable.png` and `download-retry-recovered.png`: actionable retry state replaces the download action; valid package restores it.
- `paired-workbench-real-result.png` and `paired-grading-pass.png`: focused challenge/editor layout remains; real result 42 and passing grading feedback appear.
- `native-launcher.png`: actual off-screen rendered Windows Forms window, with website-address input, Start helper, Docker download link, labelled URL/code fields and initially disabled Copy pairing code. All visible labels fit this captured default-size window. This establishes native layout at the captured scale, not successful clicks or high-DPI behavior.

The setup instructions are intentionally longer than the paired workbench and require vertical scrolling. Download is visible immediately, and the disclosures can collapse. Screenshots establish appearance; the assertions above establish download, clipboard, pairing, execution and persistence behavior.

## Launcher and extracted-package evidence

The launcher owner reports **39 passing PowerShell checks**, covering origin validation, credential/namespace preservation, missing Docker, unavailable daemon, Windows-container mode, missing Compose, an occupied foreign port, failure/retry and isolated project ownership. Actual Windows Forms construction/disposal also passed with `-ValidateUI`; the coordinating agent also rendered the native window off-screen. This is not a record of clicking through a visible launcher.

The coordinating agent separately verified ZIP CRC/SHA and secret exclusion, extracted with Windows `Expand-Archive` into a directory containing spaces, constructed the extracted UI and started its headless shared launch engine against a separate real bundled MySQL instance on port 8767. Real extracted-package SQL returned 42, the reference query graded successfully, and Reset restored eight customers. Reopening preserved the pairing code, password and namespace. Those checks use the downloadable files rather than assuming a working repository proves a working archive.

The extracted-package reopen trial found one reproducible defect: setup duplicated the already trusted default website origin. Setup now inserts the origin idempotently. The corrected final package was regenerated, independently extracted and reopened; the default origin appeared exactly once, secrets remained unchanged, and real SQL, grading and reset passed again. The final six browser/API tests above ran against the corrected archive.

## Findings and remaining coverage

**No unresolved reproducible blocking defect remains in the tested scope.** The origin-duplication defect found in the separate extracted-package trial was fixed and retested. Fault injection intentionally created missing-download, denied-clipboard, unreachable-helper and invalid-token states; each recovered as asserted.

Public release readiness is **NOT DETERMINED**. Required follow-up remains:

- A clean Windows computer or VM with no existing repository/development setup, including Docker Desktop installation and first-run downloads.
- A visible launcher walkthrough, including high-DPI text/layout, actual clipboard use and Windows downloaded-file/unsigned-application prompts.
- A deployed HTTPS website contacting localhost with intended browser permission allow, deny and recovery behavior. Local HTTP cross-origin Edge tests do not establish this.
- Actual learner-owned MySQL installations and networking; this download/browser run uses the bundled database.

Retest when package, launcher or setup UI changes. Do not represent this local milestone as a signed installer, universal browser certification or completed public MVP.
