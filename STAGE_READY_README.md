# Rental Radar: presentation and usable local pilot

Based on upstream commit a3214c1, with local implementation and evaluation updates on October 15, 2026. No GitHub push is implied by this package.

## Present with no installation

Open `presentation.html` in Chrome or Edge. It contains all nine slides, the offline report, source-linked viewing checklist, and trained XGBoost trees. All presentation assets and 625 historical model cases are embedded. Source links require internet access; the demo and model inference do not.

Use arrow keys / space to navigate, F for fullscreen, O for the overview, N for notes, and D for the demo. Speaker notes appear on the same screen: hide them when projecting. Use the 8-minute timer for rehearsal and leave two minutes for questions. Recommended live talk: slide 4 offline example, topic filter, one evidence record, checklist, return. Save the model lab and live lookup for Q&A.

## Query an arbitrary NYC address

Requirements: Python 3.10+ and an internet connection. No third-party Python packages or API key are required for public-record queries.

```sh
python demo_server.py
```

Open http://127.0.0.1:8766, enter the pilot demo, and choose “Look up another NYC address”. Enter a street number and street name, borough and date range. The server queries NYC Open Data; it does not pretend that saved data are live. The end date is exclusive and the maximum query window is 731 days. Exact-address matching can miss alternate spellings. Unresolved BBLs explicitly skip HPD and bedbug queries. Upstream failures produce an error, not reassuring zeroes.

The server binds only to loopback and serves the presentation plus its own query endpoint. It is a local course prototype, not a publicly hardened production service. Close the terminal or press Ctrl+C to stop it. If port 8766 is busy, stop the previously launched copy first.

## Models and what changed

- Original upstream artifacts are preserved in `model_artifacts/`.
- New artifacts are in `model_artifacts_validated/`.
- Earlier splits exclude observations whose full 90-day target window crosses the next split boundary.
- Train: Jan–Nov 2024, 1,375 rows. Validation: Feb–Mar 2025, 250 rows. Test: Jun–Oct 2025, 625 rows.
- Current held-out average precision: XGBoost 0.8988, logistic regression 0.9175. XGBoost precision 0.8322, recall 0.8801 and Brier 0.1485. Logistic precision 0.7685, recall 0.9712 and Brier 0.1522.
- The baseline wins on ranking and recall; XGBoost wins on precision and Brier. No final model winner is declared.
- Features and target are tax-lot based. The cohort was selected using activity across the full collection window; purging target overlap does not fix this selection bias or establish citywide performance.
- Monthly rows repeat tax lots. This is a later-time test of the selected cohort, not an unseen-building test. Raw historical source files are absent from the upstream ZIP/repository; this rerun starts from its committed prepared CSV.
- Browser tree inference was checked against native XGBoost on all 625 held-out rows; maximum absolute probability difference is below 0.000001.

For training, install `requirements-ml.txt`, then run:

```sh
python -m unittest -v
python ml_pipeline.py train --data data/prepared/model_dataset.csv --artifacts model_artifacts_validated
python evaluate_guardrails.py
```

The browser model engine and reproducible HTML builder are included under `presentation_source/`. The builder references the source deck image; the delivered HTML is already self-contained.

## What remains genuinely unverified

No real customer interviews, external LLM call, or independently confirmed building identity has been supplied. The existing Responses connector is preserved, but no secret is embedded in HTML or requested in the browser. Set credentials locally only when running an explicitly selected model call. Model IDs and prices in the upstream plan must be confirmed for the team's API account. Offline contract checks only measure deterministic citation validation; they do not measure LLM claim support or prompt-injection resistance.

The team recalled one peer question, “Why only NYC?”. The presentation labels that feedback accurately and explains the pilot scope. It is not represented as a verified Plause transcript or customer interview. The original `docs/customer_discovery.md` contains the interview guide and evidence log. Fill it only with real findings.

Live reports still use transparent rules. Model-lab examples are historical held-out tax-lot observations, not predictions for a user's new address. End-to-end live feature collection, calibration, and building identity validation are required before adding ML probabilities to the renter report.
