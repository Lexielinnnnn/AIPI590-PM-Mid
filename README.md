# Rental Radar — single-address research prototype

This prototype retrieves real NYC 311 records, calculates counts in Python, and builds a source-linked evidence package for an LLM. Python 3.10+; no packages to install.

## Run the verified sample

```bash
python rental_radar.py --address '3325 Neptune Avenue' --borough BROOKLYN --start 2026-01-01 --end 2026-10-14 --out output
```

The end date is exclusive. Queries use exact address and borough, not fuzzy matching. Use the street spelling stored in NYC 311; abbreviated addresses may return no results. This does not resolve building identity across alternate entrances. The address was selected because a recent HPD complaint query returned it, not as a representative or worst-case building.

Replay the supplied snapshot without internet:

```bash
python rental_radar.py --address '3325 Neptune Avenue' --borough BROOKLYN --offline sample/raw_records.json --out replay
```

For another address, change `--address`, `--borough`, and the date range. Counts can change when NYC updates records. Queries page through results and check counts before/after. The API does not provide an atomic snapshot; save raw data for reproducibility. A Socrata token is optional: set SOCRATA_APP_TOKEN locally if throttled. API/network failures stop the run rather than inventing results.

## Files

- `sample/raw_records.json`: complete exact-address query snapshot and provenance.
- `sample/evidence.json`: computed statistics plus up to 40 recent eligible records.
- `sample/data_report.md`: Python-generated factual summary, not an LLM report.
- `sample/llm_input.json`: exact system instructions and evidence for an LLM.
- `sample/assistant_sample.md`: where supplied, an illustrative explanation authored in ChatGPT from the evidence; NOT a measured external API run.

## Optional LLM API call

The data API and the LLM API are different services. NYC's API supplies records; it does not generate summaries. No external LLM call has been run for the supplied example. Its connector therefore remains unverified end-to-end.

Set OPENAI_API_KEY securely in your local terminal or IDE environment, plus OPENAI_MODEL to a model you can access that supports Chat Completions and JSON-object output. Then add `--llm` to the command. This explicitly makes a potentially paid call. Never commit credentials. No specific model choice or performance claim is made here.

Alternatively, paste the system instructions and evidence from `llm_input.json` into your preferred chat model for a manual demonstration. Label that as manual, not an automated API pipeline.

The API branch saves model output and actual usage. To estimate cost, set INPUT_USD_PER_MILLION and OUTPUT_USD_PER_MILLION from current official pricing. No price is assumed. Failed citation validation rejects the generated report. Citation existence is not factual correctness: manually review every claim against its source before presenting. The model sees at most 40 recent details, with all eligible records included in aggregate counts.

## Scope and interpretation

Included: all HPD requests, plus Noise - Residential, Rodent, Indoor Air Quality, Indoor Sewage, Lead, and Asbestos. This is an explicit starter filter, not comprehensive coverage of all rental concerns. Excluded categories remain in the raw snapshot. Unique request IDs are counted once; multiple different IDs may refer to the same underlying issue. Dates/statuses are retained as recorded; a closed request does not prove a repair. Historical complaints do not establish current conditions. Missing results do not establish safety. HPD violations and bedbug filings are NOT integrated yet. BBL is retained when present, but no property-identity join is implemented.

## For the presentation

Completed: live 311 retrieval, scoped counts/statuses/dates, evidence links, reproducible snapshot, deterministic report, prepared LLM prompt.

Not completed: external LLM API validation, token/cost measurement, independent building identity verification, HPD/bedbug integration, user testing, web UI. Do not claim these are finished.

Sources:
- https://data.cityofnewyork.us/resource/erm2-nwe9.json
- https://dev.socrata.com/docs/paging.html
- https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
