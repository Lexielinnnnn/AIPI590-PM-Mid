import unittest

from ml_pipeline import choose_threshold, evenly_spaced_sample, recall_at_fraction, valid_bbl, purged_splits


class MLChecks(unittest.TestCase):
    def test_target_windows_do_not_cross_splits(self):
        import pandas as pd
        dates = pd.date_range("2024-01-01", "2025-10-01", freq="MS")
        frame = pd.DataFrame({"observation_date": dates})
        splits = purged_splits(frame, dates[:13], dates[13:17], dates[17:])
        self.assertLessEqual(splits["train"].observation_date.max() + pd.Timedelta(days=90), splits["validation"].observation_date.min())
        self.assertLessEqual(splits["validation"].observation_date.max() + pd.Timedelta(days=90), splits["test"].observation_date.min())
        self.assertEqual(len(splits["test"]), 5)

    def test_bbl_validation(self):
        self.assertTrue(valid_bbl("3069790100"))
        self.assertFalse(valid_bbl("306979100"))
        self.assertFalse(valid_bbl(None))

    def test_activity_rank_sampling_spans_list(self):
        rows = [{"bbl": str(index), "n": str(100 - index)} for index in range(10)]
        sampled = evenly_spaced_sample(rows, 3)
        self.assertEqual([row["bbl"] for row in sampled], ["0", "4", "9"])

    def test_recall_at_fraction(self):
        recall = recall_at_fraction([1, 0, 1, 0], [0.9, 0.8, 0.7, 0.1], 0.5)
        self.assertEqual(recall, 0.5)

    def test_threshold_is_bounded(self):
        threshold = choose_threshold([0, 0, 1, 1], [0.1, 0.2, 0.7, 0.9])
        self.assertGreaterEqual(threshold, 0.05)
        self.assertLessEqual(threshold, 0.95)


if __name__ == "__main__":
    unittest.main()
