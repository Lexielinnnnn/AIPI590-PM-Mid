import unittest
from unittest.mock import patch
from demo_server import report_for


class DemoChecks(unittest.TestCase):
    def request(self, **kwargs):
        return dict(address="3325 Neptune Avenue", borough="BROOKLYN", start="2026-01-01", end="2026-10-14", **kwargs)

    def test_empty_results_do_not_claim_building_identity(self):
        with patch("demo_server.rr.fetch_311", return_value=([], {"count_before": 0})), patch("demo_server.rr.fetch_hpd_violations") as hpd:
            result = report_for(self.request())
            self.assertIsNone(result["evidence"]["bbl"])
            hpd.assert_not_called()
            self.assertEqual(result["provenance"]["hpd_violations"]["status"], "skipped")

    def test_rejects_invalid_borough_before_network(self):
        request=self.request()
        request["borough"]="OTHER"
        with self.assertRaises(ValueError):
            report_for(request)

    def test_rejects_excessive_date_range(self):
        request=self.request()
        request["start"]="2000-01-01"
        with self.assertRaises(ValueError):
            report_for(request)

    def test_upstream_failure_is_not_a_zero_report(self):
        with patch("demo_server.rr.fetch_311", side_effect=RuntimeError("Unavailable")):
            with self.assertRaises(RuntimeError):
                report_for(self.request())
