# Local-helper milestone validation

## Windows download and guided launcher milestone

The website now serves a generated Windows ZIP and SHA-256 manifest. Its Download Windows helper action leads to extraction, a guided Windows Forms launcher and copyable pairing code. Docker Desktop remains required; host Git/Node/Python and the repository are unnecessary for this flow. Each installation keeps a private environment and namespace-derived Docker project; startup refuses to take over another installation's port.

Local evidence: **39 launcher behavioral checks passed**, native window construction and offscreen rendering passed, and the final ZIP passed Python ZIP/CRC/SHA/credential-exclusion verification plus Windows Expand-Archive. The extracted package ran from a folder containing spaces with its own MySQL on loopback port 8767: pairing, real SELECT 42, reference-query grading, Reset restoring eight customers, and reopening while preserving credentials/code/namespace all passed. A fresh-default trusted-origin duplication defect found during restart verification was fixed and retested; the origin now occurs exactly once. Extracting an update over the test folder preserved its private configuration. A real collision with the development helper's port 8765 was refused while both services remained healthy. The temporary package-test containers/network/volume were removed afterwards.

Both frontend build variants generate the archive automatically and passed. **57 backend helper tests passed** and **six final helper/browser/download tests passed in 23.0 seconds**. Exact final artifact details are in [download QA](helper-download-qa.md). The website now serves actual ZIP files before the helper is installed. [Setup and build instructions](windows-helper.md) describe the package and CI checks; the supplied CI changes have not been run on GitHub during this session.

This is an unsigned Windows preview ZIP, not a signed installer or a certified clean-machine release. The native form was constructed/rendered and its shared startup engine exercised; an interactive visible-window walkthrough, actual high-DPI/clipboard behavior, new-machine Docker installation and public HTTPS-to-loopback permissions remain untested.

## Previous milestone records

17 October 2026. **PASS for the tested local milestone; public MVP incomplete.** No public deployment, purchase or browser certification is represented by this record.

The subsequent [focused UI milestone](focused-ui-qa.md) implements the selected simpler workbench. Both frontend builds passed, with eight development/API/browser tests and four helper tests passing on that layout. The original backend evidence below remains unchanged; backend code was not modified for the UI revision.

**Helper URL correction:** opening the base helper address previously returned 404 despite a healthy service. It now serves a connection guide; the website field and setup instructions distinguish the website from the helper address. Verified on the running preview: helper root 200 HTML, safe status connected and website 200. All **57 helper transport/security tests passed** (including root guidance, no-secret response, legacy-mode exclusion and Origin/Host checks), and **four real-helper API/Edge browser tests passed in 8.3 seconds**. Both frontend builds passed. The helper root remains a connection guide, while the SQL editor is on the website.

**First-visitor instructions correction:** follow-up user testing found that the guide assumed an installed helper and an existing terminal code. The site now exposes expandable Windows/source-preview setup and code-retrieval instructions, inserts the actual website origin into setup, explains the printed code label and says to retain the prefilled address. The helper's own landing page provides the concrete show-code command. A fresh isolated setup-script smoke verified that the documented commands generate a private code, trust the supplied origin and print the expected label without exposing the code in test output. All **57 helper tests passed**, and **four helper API/browser tests passed in 10.7 seconds**, including keyboard disclosure, startup/retrieval command text, real pairing and mobile evidence. Both frontend builds passed. A downloadable helper is still unimplemented; these tests do not establish a self-service public install journey.

## Implemented behavior

- Static helper-mode frontend with loopback URL validation, pairing and connection/recovery UI.
- Local FastAPI helper with exact-origin CORS, loopback Host checks, rate-limited pairing and bearer-protected learning APIs. Database credentials stay in local environment configuration.
- Real MySQL execution, independent fixture grading, cancellation/reset and browser drafts using the existing three exercises.
- Persistent per-installation namespace boundaries for provisioning, orphan cleanup and deletion. Compatibility checks run before changes; global MySQL settings are not modified.
- Public SQL setup downloads for online store and inventory, independently importable in an external MySQL client.
- Windows setup/start/code-display scripts; bundled MySQL or existing-server configuration; optional standalone static preview. The original development stack remains compatible.

## Actual verification

| Check | Result |
| --- | --- |
| Full backend suite with real MySQL | **89 passed**, 14.47s; one dependency deprecation warning |
| Separate-port helper API and Edge browser suite | **4 passed**, 16.0s |
| Rebuilt original API and Edge browser regression suite | **7 passed**, 27.0s |
| Frontend helper and original-mode production builds | Passed TypeScript and Vite builds |
| Documented Windows startup command, with `-Preview -Quiet` | Passed; MySQL/helper/static site healthy |
| Separate helper configured against existing development MySQL | Passed independent pairing, real SELECT result 42, reference query grading, Reset restoring eight customers; original API remained healthy |

The separate-server smoke used a temporary helper on port 8766 connected to the pre-existing development MySQL rather than the helper's bundled server. It was stopped after verification. This establishes configurable external-server connectivity; it does not verify a MySQL installation on a learner's Windows host or all firewall/authentication configurations.

Backend coverage includes real import of both exported datasets, escaped literals and preservation of an unrelated sentinel database. Real namespace lifecycle checks preserve unrelated databases, legacy `ql_` objects and other namespaces while cleaning this installation's orphan objects. Helper unit coverage includes unavailable/incompatible MySQL startup and safe status messages. No one-hour browser wait was performed.

QA found and retested two product defects: HTTP 204 preflight incorrectly carried a JSON body, and Run could race schema provisioning immediately after re-pairing. The corrected response is empty; execution now waits for the current session/schema revision. Recovery testing deliberately holds the real schema response and checks disabled execution before releasing it. Invalid-bearer and network failures are controlled fault injection, not naturally observed outages.

Commands and screenshots: [helper QA](helper-qa.md), [original QA](../qa/README.md), [setup](local-helper.md). Independent [security review](helper-security-review.md) is bounded source review, not penetration testing. Pairing codes are masked in screenshots and tokens are excluded from helper traces. The GitHub Actions source now includes a separate helper/browser job; it has not been executed on GitHub in this session.

## Remaining work

1. Verify a deployed HTTPS static origin connecting to localhost, including browser local-network permission allow/deny/recovery. Test the intended Chrome/Edge/Firefox/Safari support matrix rather than inferring it from local Edge.
2. Trial setup with learners' actual existing MySQL installations and Docker Desktop networking. Improve distribution beyond cloning the repository; native Python instructions are supplied but untested locally.
3. Implement and validate the remaining nine challenge graders, hints and explanations. The inventory dataset export does not make its planned challenges executable.
4. Revise the earlier shared-server cost estimate for static hosting/distribution; choose hosting only after that review. Accounts and statistics remain post-MVP.

The ten-learner shared-server smoke from the initial milestone is historical evidence for that stack, not a capacity claim for every learner's local computer. Local grading is practice feedback; fixture secrecy cannot be guaranteed against the computer's owner.
