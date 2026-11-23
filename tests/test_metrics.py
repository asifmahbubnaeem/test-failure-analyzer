import unittest

from evals import metrics


class MetricsTests(unittest.TestCase):
    pairs = [("product_bug", "product_bug"), ("product_bug", "test_bug"), ("flaky", "flaky"), ("environment", "(no answer)")]

    def test_accuracy_and_per_category(self):
        self.assertEqual(metrics.accuracy(self.pairs), 0.5)
        pc = metrics.per_category(self.pairs)
        self.assertEqual((pc["product_bug"]["recall"], pc["test_bug"]["precision"]), (0.5, 0.0))

    def test_scenario_weighting_counts_each_scenario_once(self):
        rows = [{"scenario": "a", "expected": "x", "predicted": "x"}] * 3 + [{"scenario": "b", "expected": "y", "predicted": "z"}]
        self.assertEqual(metrics.accuracy([(r["expected"], r["predicted"]) for r in rows]), 0.75)
        self.assertEqual(metrics.scenario_weighted_accuracy(rows), 0.5)

    def test_confusion_table_lists_no_answer_column(self):
        table = metrics.confusion_table(self.pairs)
        self.assertIn("(no answer)", table.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
