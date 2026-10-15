# Validation

Validated on October 14, 2026.

- Live retrieval returned 23 exact-address 311 requests, 56 HPD violations in the date window, and 35 raw bedbug filing rows for the resolved BBL.
- Before/after source counts matched for all three APIs.
- The bedbug preparation step retained 34 active building-period filings after applying the dataset's superseding-filing rule.
- Fifteen focused unit tests passed.
- Offline replay produced byte-identical `evidence.json`, `data_report.md`, and `report.html` files.
- Aggregate reconciliation checks passed: 15 eligible 311 records = 12 closed + 3 open; 56 HPD violations = 9 closed + 47 open; HPD classes = 34 B + 15 C + 7 A.
- Source links are retained in the bounded evidence package.
- The ML pipeline completed on 125 BBLs and 2,750 monthly observations using a chronological split. Full preliminary metrics and limitations are saved in `model_artifacts/metrics.json` and `model_artifacts/MODEL_CARD.md`.

Not validated:

- No external LLM request was made, so model quality, latency, usage, and cost remain unmeasured.
- No customer interviews or usability sessions are documented.
- BBL-to-building identity was not independently confirmed; the sample BBL covers multiple records and likely multiple buildings or entrances.
