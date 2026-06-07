import unittest

from scripts import update_scoreboard


class CacheMetricsTest(unittest.TestCase):
    def test_add_cache_metrics_computes_miss_and_hit_rate(self):
        entry = {
            "input_tokens": 214771,
            "cache_tokens": 173312,
        }

        update_scoreboard.add_cache_metrics(entry)

        self.assertEqual(entry["cache_miss_tokens"], 41459)
        self.assertAlmostEqual(entry["cache_hit_rate"], 0.8069618337671287)

    def test_add_cache_metrics_handles_missing_input(self):
        entry = {
            "input_tokens": None,
            "cache_tokens": 100,
        }

        update_scoreboard.add_cache_metrics(entry)

        self.assertIsNone(entry["cache_miss_tokens"])
        self.assertIsNone(entry["cache_hit_rate"])


if __name__ == "__main__":
    unittest.main()
