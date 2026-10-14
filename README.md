# Rental Radar

Rental Radar is an evidence-first NYC rental research prototype. A renter enters an address; the program retrieves public records, resolves a tax-lot identifier when the evidence supports one, computes all counts in Python, and produces a source-linked report plus a constrained input package for an optional LLM explanation.

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
- Nine unit tests plus exact-hash offline replay validation.

Still unverified or incomplete:

- The external LLM connector has not been run with project credentials, so model quality, latency, token usage, and actual cost remain unmeasured.
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

Guardrails include untrusted-data instructions, deterministic counts, strict structured output, record-level source IDs, rejection of invented citations, bounded evidence, and explicit interpretation limits. Citation existence is not factual entailment; a human must still compare generated claims with the source record.

## Evaluation

```bash
python -m unittest -v
```

The current tests cover category scope, open-status handling, duplicate IDs, HPD class aggregation, bedbug filing supersession, BBL ambiguity, query escaping, and LLM citation rejection. `sample/validation.md` records the live and replay checks.

## Source datasets

- NYC 311 Service Requests from 2020 to Present: https://data.cityofnewyork.us/d/erm2-nwe9
- HPD Housing Maintenance Code Violations: https://data.cityofnewyork.us/d/wvxf-dwi5
- HPD Bedbug Reporting: https://data.cityofnewyork.us/d/wz6d-d3jb
- Socrata paging guidance: https://dev.socrata.com/docs/paging.html
- OpenAI Responses API: https://developers.openai.com/api/reference/responses/overview
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs

## Interpretation limits

311 complaints are reports, not verified conditions. HPD violations have a stronger evidentiary basis, but status can change and some closure pathways rely on owner certification. Bedbug filings are annual and owner reported. Multiple records can describe one issue, and missing records do not establish safety. The product should support investigation, not replace an inspection, legal advice, or a renter's judgment.
