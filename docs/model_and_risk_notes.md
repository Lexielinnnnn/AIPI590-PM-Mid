# Model, prompt, and risk notes

## Product decision

The product separates deterministic evidence, statistical prediction, and natural-language explanation. Python retrieves public records, resolves addresses, calculates totals, and prepares lagged features. XGBoost is a candidate for a narrow 90-day Class C violation signal. The LLM receives a bounded evidence package and turns it into a short explanation plus viewing questions.

Neither model creates a safety certification or lease recommendation.

## ML model configuration

- Target: at least one new Class C HPD violation within 90 days.
- Baseline: class-weighted logistic regression.
- Candidate: XGBoost binary classifier with depth 4 trees and histogram construction.
- Leakage control: chronological split and features strictly before each observation date.
- Primary metric: PR-AUC, with ROC-AUC, precision, recall, F1, accuracy, Brier score, and recall at the top 10%.

In the preliminary chronological test, XGBoost improved accuracy, precision, F1, and Brier score. Logistic regression produced better PR-AUC, ROC-AUC, recall, and top-10% recall. Model selection remains open until the sampling frame is broadened and probabilities are calibrated.

## Planned LLM configuration

- Default: `gpt-5.6-luna` through the Responses API.
- Reasoning effort: low for the constrained summarization task.
- Output: strict JSON schema with summary items, viewing questions, limitations, and source IDs.
- Escalation: test `gpt-5.6-terra` only if the lower-cost model misses material evidence or produces less useful questions on the evaluation set.

This is a planned configuration. The repository does not contain a successful external model run, so it makes no quality, latency, or cost claim.

## Prompt design

The `rental-evidence-v2` instruction block:

- Treats every source field as untrusted data and ignores instructions embedded in records.
- Defines the evidentiary difference between complaints, violations, and self-reported filings.
- Prohibits safety, causation, landlord-fault, and missing-data inferences.
- Requires record-level citations for viewing questions.
- Tells the model to copy deterministic aggregates instead of recalculating them.

The program uses a strict schema and a second validation pass. Unknown citation IDs and aggregate-only viewing questions fail closed. A no-record evidence package may return empty summary and question arrays with an explicit limitation instead of inventing content.

## Evaluation plan

Create a minimum 25-case set with clear evidence, conflicting evidence, no records, ambiguous BBLs, prompt-injection text, misleading closure language, multiple buildings on one BBL, and superseded annual filings.

Measure citation validity, human-rated claim support, unsafe inference rate, question usefulness, input and output tokens, cached tokens, latency, and cost per accepted report.

Gate a release on 100% citation validity, zero critical unsafe inferences, and human-reviewed usefulness targets chosen after the first interview round.

## Token economics

Record actual usage from the API response. The code reads current per-million-token rates from environment variables rather than embedding a price that will become stale. For planning only, the presentation includes a clearly labeled scenario based on the official rates checked on October 14, 2026; it is not a measured run.

## Main risks and mitigations

| Risk | Why it matters | Current mitigation | Next control |
|---|---|---|---|
| Tax-lot overreach | One BBL can cover several buildings or entrances | Show BBL and identity limitation | Add NYC GeoSearch and BIN-level confirmation |
| Complaint overinterpretation | A report can be mistaken for a verified condition | Separate 311 and HPD evidence | Comprehension test with renters |
| Stale status | Public records can change after retrieval | Timestamp snapshots and retain source links | Refresh-on-open and age labels |
| Hallucinated explanation | Model may add unsupported facts | Deterministic counts, strict schema, citation validation | Claim-level entailment evaluation |
| Legal/reputational harm | Strong labels could imply negligence or safety | Use neutral follow-up language and disclaimers | Counsel or tenant-advocate review |
| Coverage bias | Reporting frequency differs by population and building | Never treat absence as safety | Publish a data-coverage statement |
| Sampling bias | The ML sample begins with buildings that have HPD history | Label results preliminary and publish the manifest | Add a representative building frame with true negatives |
| Model drift | Reporting and inspection patterns change over time | Chronological evaluation and dated artifacts | Scheduled drift and calibration checks |
