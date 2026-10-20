# QueryLab MVP hosting estimate

## Current static-hosting plan — 18 October 2026

**Accounts iteration:** the user waived the pilot and selected Google sign-in. The implemented account design adds Supabase authentication and a metadata-only PostgreSQL progress store while retaining Pages and learner-local SQL. Supabase Free currently includes social OAuth, 50,000 monthly active users and a 500 MB database. A$0/month remains a reasonable initial service-cost planning assumption for five simultaneous learners within the free allowances; this is not an uptime or usage guarantee. Low-activity free projects may pause after a week. No paid service has been activated. [Current Supabase pricing](https://supabase.com/pricing), [pausing](https://supabase.com/docs/guides/platform/free-project-pausing), [activation guide](docs/accounts-and-statistics.md).

The MVP now targets **five simultaneous learners**, each running their own helper and MySQL. The public host serves the static Vite website and Windows helper download; it does not execute SQL, grade submissions or store learner accounts. The account-enabled compiled website plus helper ZIP total about 1 MB; account/progress data is stored separately in Supabase.

**Planning estimate: A$0/month for GitHub Pages hosting**, provided the repository/account is eligible. GitHub Free supports Pages from public repositories; private repositories require an eligible paid plan. No custom domain is required when using the included `github.io` URL. A paid GitHub plan, custom domain, development/maintenance work and learner-local Docker resources are excluded from this figure.

GitHub lists a 1 GB published-site limit and soft 100 GB/month bandwidth limit. Five concurrent visitors alone does not determine monthly transfer, but QueryLab's small static build and local SQL execution make free hosting a reasonable starting assumption. Commercial SaaS use is restricted. Sources checked 18 October 2026: [Pages limits and eligibility](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [HTTPS support](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).

The [Pages deployment workflow and guide](docs/github-pages.md) are prepared. The user reports successful deployment, hosted query/function/procedure runs and submissions, refresh/draft recovery, disconnect/re-pair and a fresh helper installation trial. The pilot has been waived; the next iteration is Google accounts/statistics using the free-plan estimate above. Explicit expiry and broader browser-permission recovery remain open. The agent has not independently inspected the deployment or its billing. No paid plan change or domain purchase was performed by the agent.

## Historical shared-server estimate — superseded

The estimates and recommendation below assume hosted SQL execution and are retained as history. They are **not the budget recommendation for the current helper-based MVP**.

**Architecture update, 17 October 2026:** the user has now authorized a static hosted website connected to a learner-local helper/MySQL. The shared-server estimates below are historical and do not represent current expected costs or an approved purchase. Re-estimate static hosting and helper distribution after selecting the deployment approach; SQL execution resources are supplied by learners. See [local helper](docs/local-helper.md).

Prepared 17 October 2026. Planning estimate, not a quote, capacity certification or authorization to purchase.

## Assumptions

- Public, account-free website; two compact synthetic datasets and 12 challenges.
- Initial target of 10 simultaneous learners, with bounded/queued SQL execution rather than 10 unbounded jobs.
- Always-on self-managed Linux hosting, real MySQL practice environments, reproducible fixtures and anonymous workspace cleanup.
- No AI API charges, managed database, high availability or paid monitoring assumed.
- Isolation architecture is still to be validated. A shared host does not mean shared learner credentials or mutable workspaces.

## Published price anchors

[DigitalOcean Basic Droplet pricing](https://www.digitalocean.com/pricing/droplets) lists 2 vCPU/4 GiB at US$24/month, 4 vCPU/8 GiB at US$48/month, and 8 vCPU/16 GiB at US$96/month. Disk and a transfer allowance are included in those plans.

[DigitalOcean backup pricing](https://docs.digitalocean.com/products/backups/details/pricing/) lists weekly backups at an additional 20% of the server price and daily backups at 30% under percentage-based plans.

These are reference prices, not a provider selection. Check regional availability and checkout pricing before purchase.

## Scenarios

| Scenario | Example monthly compute + weekly backup cost | Indicative monthly AUD allowance |
| --- | --- | --- |
| Small technical trial | 4 GiB server: US$24 + US$4.80 = US$28.80 | A$50–65 |
| Candidate MVP starting point | 8 GiB server: US$48 + US$9.60 = US$57.60 | A$100–130 |
| Separate app and SQL execution hosts | 4 GiB app + 8 GiB runner: US$72 + US$14.40 = US$86.40 | A$155–195 |
| More execution headroom | 4 GiB app + 16 GiB runner: US$120 + US$24 = US$144 | A$255–300 |

AUD allowances use an illustrative conversion of US$1 = A$1.60, not a verified current exchange rate. They include room for 10% GST if applicable and minor extras; actual conversion, tax and payment fees vary. A custom domain is additional annual expenditure: reserve approximately A$20–40/year as an unquoted allowance, with the actual extension/renewal price to be checked. A provider URL avoids that initial purchase if suitable.

The 4 GiB trial is for feasibility, not a promised 10-learner deployment. The 8 GiB option is a candidate to benchmark, not demonstrated capacity. Multiple disposable MySQL instances and grading fixtures can increase memory needs substantially. The separate-host scenarios provide architectural flexibility but do not themselves prove isolation or performance.

## Recommendation

Use A$100–130/month as the initial planning range. The user confirmed a provisional A$150/month hosting ceiling on 17 October 2026. If the execution design requires a separate host or more memory, revisit the ceiling before deployment. Provider selection and deployment remain future work; no purchase has been initiated.

Validate actual memory use, query/grading concurrency, cancellation and reset performance with 10 simulated active learners before choosing production capacity. Define a queue/busy response and resource quotas. Keep fixed instance sizes initially to make costs predictable; review transfer, storage and backup overages separately.

This estimate excludes development effort, server maintenance labor, additional staging environments, high availability and substantial traffic/abuse overages. Anonymous practice data is disposable; backups protect deployment recovery rather than promise restoration of expired learner sessions.
