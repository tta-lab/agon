import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import serve_scoreboard


class ComparisonSummaryTest(unittest.TestCase):
    def test_benchmark_leakage_is_excluded_from_pass_and_cost_summary(self):
        payload = {
            "entries": [
                {
                    "task_key": "leaky-task",
                    "harness": "Lenos",
                    "model": "gpt-5.5",
                    "job": "lenos-job",
                    "reward": 1.0,
                    "display_status": "benchmark_leakage",
                    "input_tokens": 100,
                    "cache_tokens": 20,
                    "cache_miss_tokens": 80,
                    "output_tokens": 10,
                },
                {
                    "task_key": "leaky-task",
                    "harness": "Codex CLI",
                    "model": "gpt-5.5",
                    "job": "codex-job",
                    "reward": 1.0,
                    "display_status": "benchmark_leakage",
                    "input_tokens": 100,
                    "cache_tokens": 20,
                    "cache_miss_tokens": 80,
                    "output_tokens": 10,
                },
            ]
        }

        summary = serve_scoreboard.comparison_summary(payload)

        self.assertEqual(summary["lenos"]["passes"], 0)
        self.assertEqual(summary["codex_cli"]["passes"], 0)
        self.assertEqual(summary["paired_success_count"], 0)
        self.assertEqual(summary["estimated_cost"]["lenos"], 0)
        self.assertEqual(summary["estimated_cost"]["codex_cli"], 0)


if __name__ == "__main__":
    unittest.main()
