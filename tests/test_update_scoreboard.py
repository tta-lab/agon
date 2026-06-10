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


class ManualNoteStatusTest(unittest.TestCase):
    def test_benchmark_leakage_is_not_effective_pass(self):
        entry = {
            "classification": "pass",
            "display_status": "benchmark_leakage",
        }

        self.assertFalse(update_scoreboard.is_effective_pass(entry))

    def test_benchmark_leakage_makes_task_status_failed(self):
        entries = [
            {
                "classification": "pass",
                "display_status": "benchmark_leakage",
            }
        ]

        self.assertEqual(update_scoreboard.task_status(entries), "failed")

    def test_load_notes_indexes_task_notes_by_normalized_task_key(self):
        notes = {
            "entries": [],
            "tasks": [
                {
                    "task": "terminal-bench/mteb-leaderboard",
                    "status": "benchmark_leakage",
                    "note": "exclude task",
                }
            ],
        }

        index = update_scoreboard.index_notes(notes)

        self.assertEqual(
            index[("task", "mteb-leaderboard")]["status"], "benchmark_leakage"
        )


if __name__ == "__main__":
    unittest.main()
