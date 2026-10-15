# Rental Radar

Rental Radar is an evidence-first NYC rental research prototype. A renter enters an address; the program retrieves public records, resolves a tax-lot identifier when the evidence supports one, computes all counts in Python, and produces a source-linked report. A separate ML pipeline predicts a narrow follow-up outcome, while an optional LLM turns bounded evidence into a cited explanation.

The product supports due diligence and better viewing questions. It does not issue a safety score, certify current conditions, or recommend whether to sign a lease.

## Midterm status

Completed and verified:

- Live 311 retrieval with pagination and before/after count checks.
- BBL inference when all returned 311 records agree on one tax lot.
- BBL joins to HPD Housing Maintenance Code violations and HPD bedbug filings.
- Deterministic counts, status breakdowns, a transparent follow-up label, and source links.
- A responsive HTML evidence report for a short demo.
- Offline snapshots for repeatable grading and development.
- A Responses API connector with a strict JSON schema and citation-ID validation.
- A reproducible data-preparation and XGBoost training pipeline with a chronological test split.
- A committed XGBoost model, feature schema, metrics, predictions, and model card.
- Fifteen unit tests plus exact-hash offline replay validation.

Still unverified or incomplete:

- The external LLM connector has not been run with project credentials, so model quality, latency, token usage, and actual cost remain unmeasured.
- The preliminary ML sample begins with buildings that have HPD history; its metrics do not represent every NYC rental building.
- A BBL can contain multiple addresses or buildings. The current join is a tax-lot join, not a confirmed building or entrance match.
- No customer interviews are documented yet. The interview guide and evidence log are in `docs/customer_discovery.md`; do not claim interview findings until signed notes are added.
- Multi-address comparison, authentication, deployment, accessibility testing, and mobile usability testing remain future work.

## Run the verified sample

Python 3.10+ is required. The core pipeline uses only the standard library.

```bash
python rental_radar.py \
  --address '3325 Neptune Avenue' \
  --borough BROOKLYN \
  --start 2026-01-01 \
  --end 2026-10-14 \
  --offline sample/raw_records.json \
  --out replay
```

Open `replay/report.html` in a browser for the demo view. The end date is exclusive.

Run a live retrieval:

```bash
python rental_radar.py \
  --address '3325 Neptune Avenue' \
  --borough BROOKLYN \
  --start 2026-01-01 \
  --end 2026-10-14 \
  --out output
```

An optional `SOCRATA_APP_TOKEN` can reduce public API throttling. Never commit credentials.

## Verified sample results

The October 14, 2026 snapshot for the exact address query contains:

- 23 exact-address 311 requests; 15 pass the starter rental-related category filter and 3 are recorded open.
- 56 HPD violations in the 2026 date window; 47 are recorded open and 12 of those are Class C.
- 34 building-period bedbug filings retained after applying the superseding-filing rule; the latest reporting period totals 541 dwelling units and 135 reported infested units across the joined BBL.

The BBL appears to cover a property complex, so the HPD and bedbug totals cannot be attributed to one entrance or apartment. That is a core identity-resolution risk, not a detail to hide.

## Data flow

1. Query NYC 311 by exact normalized street address, borough, and date window.
2. Infer a BBL only when every returned 311 record with a BBL agrees. A user may provide an independently verified 10-digit BBL instead.
3. Query HPD violations within the date window and all available annual bedbug filings for that BBL.
4. Save the raw source records and retrieval provenance before interpretation.
5. Compute counts and a rules-based follow-up label outside the LLM.
6. Build Markdown, HTML, and a bounded evidence package with record-level source IDs.
7. Optionally ask an LLM to summarize the package. Reject output with missing or unknown citation IDs.

## Machine learning pipeline

The ML target is whether a selected BBL receives a new Class C HPD violation within the next 90 days. Features include lagged 311 volume, recent HPD violations by class, severe-violation recency, the latest available bedbug rate, missingness, month, and borough.

Install and run:

```bash
python -m pip install -r requirements-ml.txt

python ml_pipeline.py all \
  --data-dir data/ml \
  --prepared data/prepared/model_dataset.csv \
  --artifacts model_artifacts \
  --start 2023-01-01 \
  --end 2026-01-01 \
  --per-borough 25 \
  --candidate-pool 1000
```

The committed preliminary run contains 125 BBLs and 2,750 monthly observations. On the chronological test period, XGBoost reached 0.8971 PR-AUC, 0.8695 F1, and 0.1456 Brier score. The logistic baseline reached a higher 0.9163 PR-AUC and 0.9640 recall, so model selection remains open. See `docs/model_development_and_evaluation.md` and `model_artifacts/MODEL_CARD.md` for the full comparison and limitations.

Score a precomputed feature object with the saved native XGBoost model:

```bash
python ml_pipeline.py predict \
  --features model_artifacts/example_features.json \
  --artifacts model_artifacts
```

The prediction command validates the exact feature schema and returns the probability, the validation-selected threshold, and the product boundary. It does not convert the probability into a safety claim.

## Output files

- `raw_records.json`: retrieved source rows plus query URLs and count checks.
- `evidence.json`: deterministic aggregates and bounded record details.
- `data_report.md`: factual, deterministic report.
- `report.html`: responsive demo interface.
- `llm_input.json`: versioned instructions, strict schema, and evidence payload.
- `llm_report.json`: optional structured model response.
- `llm_usage.json`: optional actual token usage and a cost estimate when current rates are supplied.

## Optional LLM explanation

The connector uses the Responses API and defaults to `gpt-5.6-luna`, a cost-sensitive model suitable for a constrained structured-output task. Override it with `OPENAI_MODEL` after comparing quality on the project evaluation set.

```bash
export OPENAI_API_KEY='set-this-locally'
export OPENAI_MODEL='gpt-5.6-luna'
export INPUT_USD_PER_MILLION='use-current-official-rate'
export CACHED_INPUT_USD_PER_MILLION='use-current-official-rate'
export OUTPUT_USD_PER_MILLION='use-current-official-rate'

python rental_radar.py \
  --address '3325 Neptune Avenue' \
  --borough BROOKLYN \
  --start 2026-01-01 \
  --end 2026-10-14 \
  --offline sample/raw_records.json \
  --out llm-demo \
  --llm
```

Guardrails include untrusted-data instructions, deterministic counts, strict structured output, record-level source IDs, rejection of invented citations, bounded evidence, and explicit interpretation limits. The model does not use web search or autonomously call city APIs. Citation existence is not factual entailment; a human must still compare generated claims with the source record. See `docs/llm_api_plan.md` for the prompting, evaluation, and token-economics plan.

## Evaluation

```bash
python -m unittest -v
```

The current tests cover category scope, open-status handling, duplicate IDs, HPD class aggregation, bedbug filing supersession, BBL ambiguity, query escaping, LLM citations and cost arithmetic, BBL validation, sampling, model threshold selection, and review-capacity recall. `sample/validation.md` records the live and replay checks.

## Project documentation

- `docs/data_collection_and_preparation.md`: collection, cleaning, missing data, bias, and leakage controls.
- `docs/model_development_and_evaluation.md`: algorithms, split design, metrics, and preliminary results.
- `docs/llm_api_plan.md`: API architecture, prompts, guardrails, evaluation, and token economics.
- `model_artifacts/MODEL_CARD.md`: intended use, results, feature importance, and limitations.

## Source datasets

- NYC 311 Service Requests from 2020 to Present: https://data.cityofnewyork.us/d/erm2-nwe9
- HPD Housing Maintenance Code Violations: https://data.cityofnewyork.us/d/wvxf-dwi5
- HPD Bedbug Reporting: https://data.cityofnewyork.us/d/wz6d-d3jb
- Socrata paging guidance: https://dev.socrata.com/docs/paging.html
- OpenAI Responses API: https://developers.openai.com/api/reference/responses/overview
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs

## Interpretation limits

311 complaints are reports, not verified conditions. HPD violations have a stronger evidentiary basis, but status can change and some closure pathways rely on owner certification. Bedbug filings are annual and owner reported. Multiple records can describe one issue, and missing records do not establish safety. The product should support investigation, not replace an inspection, legal advice, or a renter's judgment.
