# Compatibility Scoring Methodology

Overall score =

0.15 * domain
+ 0.25 * variable
+ 0.20 * availability
+ 0.15 * joint availability
+ 0.10 * temporal
+ 0.10 * geographic
+ 0.05 * source quality

Variable status scores:

- EXACT_AVAILABLE: 1.00
- DERIVABLE: 0.85
- PARTIALLY_AVAILABLE: 0.65
- PROXY_AVAILABLE: 0.45
- AGGREGATE_ONLY: 0.30
- MISSING: 0.00

Critical-variable gate: a missing or aggregate-only critical eligibility variable makes the policy NOT_READY. Proxy-backed critical variables can be READY_WITH_WARNINGS only if the proxy is explicitly approved and joint availability is adequate.

Temporal scores use configurable sensitivity classes. These are project assumptions, not universal scientific constants.
