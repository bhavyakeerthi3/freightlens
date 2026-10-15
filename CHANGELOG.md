# Changes in 1.1

## Public deployment

- Production demo at https://freightlens-two.vercel.app in the `bk` Vercel team.
- Static CDN assets plus a read-only Python 3.12 function for results, notes and grounded questions; no persistent server or runtime filesystem writes.
- Hosted labels identify the public synthetic-data demo. Original CSV bytes are preserved for download.
- Eight unauthenticated HTTP checks validate public access, all data endpoints, questions, assets and the downloadable CSV. Deployment metadata and test evidence are under `results/`.

## Project presentation

- New FreightLens dashboard with responsive sidebar navigation, summary cards, a native SVG route chart, accessible chart markers, source-evidence dialogs and paginated findings.
- Route/verdict/date filters, meaningful empty states, CSV download, Evidence library and Method & quality views.
- Offline assets, loading/error handling, Windows launcher and project metadata.

## Functional fixes

- Questions now honor route, month/year and ISO dates rather than returning the entire route history. Ambiguous multi-route or multi-period questions receive guidance. Missing year scope is explicit.
- Configurable-threshold explanations now describe the threshold actually used.
- Required fields, duplicate note IDs and nonfinite tonne-km exposures are validated.
- Unknown HTTP paths correctly return 404 rather than silently serving the homepage. Oversized questions return 400, static files are allowlisted, JSON disallows NaN, and server errors get a readable client message.
- Numeric audit records now carry exact source evidence, validity dates, explanations and shipment counts, so the interface can explain a verdict without reconstructing it.

## Verification

- 21 automated tests plus 14 evidence subcases; three fresh-process reproducibility comparisons.
- Browser walkthrough of route analysis, month question, evidence modal and navigation; additional results in `results/verification.md`.
- The default output CSV and its original SHA-256 remain unchanged. UI improvements do not alter the contractual output columns or default alert results.
