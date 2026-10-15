import unittest

from ml_pipeline import choose_threshold, evenly_spaced_sample, recall_at_fraction, valid_bbl


class MLChecks(unittest.TestCase):
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
