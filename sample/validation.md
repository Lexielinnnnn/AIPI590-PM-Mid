# Validation

Live API returned 23 requests and passed before/after count checks. Five focused unit tests passed (scope/status handling, empty results, duplicate IDs, invalid citations, query escaping). Offline replay exactly reproduced evidence.json. Category and status totals both equal 15. Sample narrative and all question links were manually checked against the saved records. External LLM API call, model quality, token usage and cost remain untested.
