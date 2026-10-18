# QueryLab bounded local capacity smoke

Observed at 2026-10-17T06:11:15.443Z against http://127.0.0.1:8080. Result: **PASS**.

This is one burst of ten short jobs on synthetic teaching fixtures: seven exploratory join/aggregate queries and the three available reference submissions. Reference solutions are deliberately fetched from the explicit explained-solution endpoint. There are ten independent opaque cookie contexts, one job per visitor. No cookies, SQL scripts or result rows are recorded here.

## Results

- Fresh sessions: 10; eleventh-session response: 429 (capacity_reached).
- Session creation p50 / p95: 14.7 / 16 ms.
- Successful jobs: 10/10; errors: 0.
- Job wall-clock p50 / p95: 1315.6 / 3028 ms.
- Burst wall-clock duration: 3028.6 ms.
- Idle session expiry returned by API: 3600 seconds.

| Visitor | Challenge | Operation | Wall time including queue + polling (ms) | Server execution time (ms) | Grade passed |
| --- | --- | --- | ---: | ---: | --- |
| 1 | OS-Q01 | submit | 1315.4 | 1278 | true |
| 2 | OS-F01 | submit | 2657.3 | 2530 | true |
| 3 | OS-P01 | submit | 3028 | 2840 | true |
| 4 | OS-Q01 | run | 449.2 | 326 | N/A |
| 5 | OS-Q01 | run | 698.1 | 289 | N/A |
| 6 | OS-Q01 | run | 943.4 | 240 | N/A |
| 7 | OS-Q01 | run | 1315.6 | 362 | N/A |
| 8 | OS-Q01 | run | 1686.9 | 289 | N/A |
| 9 | OS-Q01 | run | 1686.3 | 272 | N/A |
| 10 | OS-Q01 | run | 1920.8 | 278 | N/A |


## Interpretation and limits

The local implementation defaults to ten sessions, four execution workers and an eight-second SQL deadline. The smoke records observed completion and admission behaviour; it does not measure sustained throughput, resource headroom, destructive/adversarial workloads, network latency, browser rendering or production costs. The p95 is the nearest-rank estimate from only ten heterogeneous job samples, with 100 ms polling resolution. It has no statistical confidence claim and is not a public-hosting SLA or proof that the A$150/month budget is sufficient. Server execution times include engine workspace/grader work but are distinct from client-visible queue and polling time.

Run after a clean API restart with no competing tests:

    node qa/capacity-smoke.mjs

The script does not restart services or delete workspaces. The operator must clear its ten sessions afterward before opening the preview to learners. A second run without cleanup is expected to fail on occupied capacity. The local-host check prevents inadvertently using this script against a public deployment.
