import unittest

from rental_radar import (
    estimate_llm_cost,
    infer_bbl,
    literal,
    summarize,
    summarize_bedbugs,
    summarize_hpd,
    validate_llm,
)


def evidence_stub():
    return {
        "aggregate_source_ids": ["aggregate:311", "aggregate:hpd", "aggregate:bedbug"],
        "records": {
            "311": [{"source_id": "311:1"}],
            "hpd_violations": [{"source_id": "hpd:2"}],
            "bedbug_filings": [{"source_id": "bedbug:3:2025-10-31"}],
        },
    }


class Checks(unittest.TestCase):
    def test_scope_and_status(self):
        rows = [
            {"unique_key": "1", "agency": "HPD", "complaint_type": "HEAT/HOT WATER", "status": "Closed", "created_date": "2026-01-01"},
            {"unique_key": "2", "agency": "NYPD", "complaint_type": "Noise - Residential", "status": "Open"},
            {"unique_key": "3", "agency": "DOT", "complaint_type": "Street Condition"},
        ]
        selected, counts = summarize(rows)
        self.assertEqual(len(selected), 2)
        self.assertEqual(counts["eligible_requests"], 2)
        self.assertEqual(counts["excluded_requests"], 1)
        self.assertEqual(counts["open_requests"], 1)

    def test_empty(self):
        self.assertIsNone(summarize([])[1]["latest_created"])

    def test_duplicate_311_fails(self):
        with self.assertRaises(ValueError):
            summarize([{"unique_key": "1"}, {"unique_key": "1"}])

    def test_hpd_open_class_c(self):
        counts = summarize_hpd([
            {"violationid": "10", "class": "C", "violationstatus": "Open", "inspectiondate": "2026-03-01"},
            {"violationid": "11", "class": "B", "violationstatus": "Close", "inspectiondate": "2026-02-01"},
        ])
        self.assertEqual(counts["violations"], 2)
        self.assertEqual(counts["open_violations"], 1)
        self.assertEqual(counts["open_class_c"], 1)

    def test_latest_bedbug_filing_wins_per_building_and_period(self):
        rows = [
            {"building_id": "A", "filling_period_end_date": "2024-10-31", "filing_date": "2025-01-01", "of_dwelling_units": "10", "infested_dwelling_unit_count": "8"},
            {"building_id": "A", "filling_period_end_date": "2024-10-31", "filing_date": "2025-02-01", "of_dwelling_units": "10", "infested_dwelling_unit_count": "2"},
            {"building_id": "B", "filling_period_end_date": "2024-10-31", "filing_date": "2025-01-15", "of_dwelling_units": "5", "infested_dwelling_unit_count": "1"},
        ]
        counts = summarize_bedbugs(rows)
        self.assertEqual(counts["active_filings"], 2)
        self.assertEqual(counts["latest_dwelling_units"], 15)
        self.assertEqual(counts["latest_infested_units"], 3)

    def test_bbl_requires_single_candidate(self):
        bbl, resolution = infer_bbl([{"bbl": "1000000001"}, {"bbl": "1000000001"}])
        self.assertEqual(bbl, "1000000001")
        self.assertEqual(resolution["status"], "resolved")
        self.assertIsNone(infer_bbl([{"bbl": "1"}, {"bbl": "2"}])[0])

    def test_unknown_citation_fails(self):
        data = {
            "summary": [{"text": "Claim", "source_ids": ["invented"]}],
            "viewing_questions": [{"text": "Question?", "source_ids": ["311:1"]}],
            "limitations": ["Limit"],
        }
        with self.assertRaises(ValueError):
            validate_llm(data, evidence_stub())

    def test_aggregate_only_question_fails(self):
        data = {
            "summary": [{"text": "Claim", "source_ids": ["aggregate:311"]}],
            "viewing_questions": [{"text": "Question?", "source_ids": ["aggregate:311"]}],
            "limitations": ["Limit"],
        }
        with self.assertRaises(ValueError):
            validate_llm(data, evidence_stub())

    def test_query_literal(self):
        self.assertEqual(literal("O'BRIEN"), "'O''BRIEN'")

    def test_llm_cost_uses_cached_rate(self):
        usage = {"input_tokens": 3000, "output_tokens": 500, "input_tokens_details": {"cached_tokens": 1000}}
        cost = estimate_llm_cost(usage, "0.20", "0.02", "1.20")
        self.assertAlmostEqual(cost, 0.00102)

    def test_empty_llm_sections_allowed_when_no_records_exist(self):
        evidence = {"aggregate_source_ids": ["aggregate:311"], "records": {"311": [], "hpd_violations": [], "bedbug_filings": []}}
        validate_llm({"summary": [], "viewing_questions": [], "limitations": ["No records in the supplied window."]}, evidence)


if __name__ == "__main__":
    unittest.main()
