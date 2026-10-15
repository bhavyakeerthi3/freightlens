# Verification report - FreightLens 1.1

Story: an analyst opens a dashboard, compares weekly route rates, filters findings, and inspects exact source evidence; a question is parsed by route and period against the same stored analysis.

| Boundary | Status | Evidence |
| --- | --- | --- |
| Shipment input to analysis | Passed | 2,940 supplied shipments; 728 route-weeks; exact sample comparison percentages checked by automated tests. |
| Analysis to output | Passed | 11 unexplained alerts, 2 evidence-supported candidates, 715 normal rows. Original contractual CSV SHA-256 unchanged. |
| API to browser | Passed | Browser rendered all summary values, 104 weeks for Mumbai-Pune, and 13 candidate findings. Server logs show HTTP 200 for assets and all data endpoints. |
| Month question to evidence | Passed | Chennai-Bangalore March 2025 returns the Mar 10 rise as unsupported; the expired N001 flood note is not used. |
| Finding to source | Passed | Feb 24 Chennai-Bangalore dialog shows rate 3.5828, history 2.7253, peers 2.5837, source N001 and Feb 24-Mar 8 window. |
| Filtering and pagination | Passed | Evidence-supported filter gives 2 rows; Delhi-Chennai plus that verdict gives a clear empty result; second candidate page shows findings 9-13 of 13. |
| Navigation | Passed | Evidence library renders all ten supplied notes; Method & quality shows formulas, limitations and reproducibility commands. |
| CSV download and invalid URLs | Passed | HTTP tests verify the attachment header, exact eight-column contract, 728 rows, unknown-path 404, and oversized-query 400. |
| Browser diagnostics | Passed | No browser error/warning console entries during the walkthrough. |
| Phone layout | Passed | Tested at 390 x 844; a visually-hidden table heading caused document overflow and was fixed. After reload: root and body widths 375px within the 390px viewport; the data table scrolls inside its own container. Temporary viewport override reset. |
| Reproducibility | Passed | Three fresh CLI processes; identical CSV, audit and cost-log bytes. Hashes saved in reproducibility.json. |

21 automated tests pass, with 14 evidence-retrieval subcases. These validate implementation and supplied-note grounding, not externally measured business precision/recall. The local HTTP integration tests use an isolated ephemeral port and shut down their own server.

Preview: `dashboard-preview.jpg`. To rerun: `python verify.py`; to inspect interactively: `python demo.py`.
