# LLM API design

## Choice and role

Rental Radar uses `gpt-5.6-luna` through the Responses API as the starting explanation model. It is used only after deterministic retrieval, aggregation, and optional ML prediction. The task is narrow: turn a bounded evidence package into a short, cited summary and viewing questions.

This is controlled grounded generation rather than vector-database RAG. Python retrieves records directly from the three NYC Open Data APIs and passes selected records plus deterministic aggregates to the model. The model has no web-search tool and does not autonomously call city APIs. This keeps provenance, counts, and query behavior outside the model.

`gpt-5.6-terra` remains a fallback only if the lower-cost model fails the quality evaluation.

## Prompt engineering

The prompt is versioned as `rental-evidence-v2` in source control. It:

- assigns the model the narrow role of explaining evidence to a prospective renter;
- marks all record fields as untrusted data and tells the model to ignore embedded instructions;
- defines the difference between complaints, violations, and owner-reported filings;
- prohibits safety, causation, landlord-fault, and missing-data inferences;
- tells the model to copy deterministic aggregates rather than recalculate them;
- requires record-level source IDs for every viewing question;
- uses a strict JSON schema for summaries, questions, and limitations.

The application caps the evidence details at 40 records each for 311 and HPD and 10 bedbug filings. It sets low reasoning effort, a 1,400-token output cap, and `store: false`.

## Guardrails

Before the call, Python controls the address query, source filters, BBL resolution, arithmetic, and evidence size. After the call, the application rejects missing sections, empty text, unknown source IDs, and questions supported only by aggregate IDs. When the source package contains no record-level evidence, empty summary and question arrays are accepted with an explicit limitation instead of forcing the model to invent content.

Schema and citation validation do not prove that a sentence follows from its cited record. The release evaluation therefore includes human claim-support review, prompt-injection cases, ambiguous BBLs, misleading closure language, no-record cases, and annual-filing supersession.

## Evaluation

The planned minimum set contains 25 representative and adversarial cases. Release gates include 100% citation-ID validity, zero critical unsafe inferences, human-rated claim support, viewing-question usefulness, latency, token use, and cost per accepted report.

## Token economics

At the official standard rates checked October 14, 2026, GPT-5.6 Luna costs $0.20 per million input tokens, $0.02 per million cached input tokens, and $1.20 per million output tokens. A planning example with 3,000 uncached input tokens and 500 output tokens costs approximately $0.0012 per report.

The code never silently hard-codes pricing. It reads the current rates from environment variables and records actual input, cached-input, and output token usage from the API response in `llm_usage.json`. The file also records the prompt version and request settings.

Official references:

- https://developers.openai.com/api/docs/models/gpt-5.6-luna
- https://developers.openai.com/api/reference/responses/overview
- https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
- https://developers.openai.com/api/docs/guides/prompting
- https://developers.openai.com/api/docs/guides/safety-best-practices
- https://developers.openai.com/api/docs/pricing
