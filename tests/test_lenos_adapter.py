import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from agon_bench.adapters.lenos import LenosAgent


ROOT = Path(__file__).resolve().parents[1]


class LenosAdapterTest(unittest.TestCase):
    def test_minimal_lenos_config_does_not_install_post_step_hook(self):
        config = json.loads((ROOT / "agon_bench/lenos/config.json").read_text())

        self.assertNotIn("hooks", config)

    def test_adapter_uses_run_usage_json_instead_of_post_step_aggregation(self):
        source = (ROOT / "agon_bench/adapters/lenos.py").read_text()

        self.assertIn("--usage-json", source)
        self.assertIn('USAGE_SUMMARY_PATH = "/logs/agent/usage-summary.json"', source)
        self.assertNotIn("agon-lenos-post-step", source)
        self.assertNotIn("USAGE_HOOK_SCRIPT", source)
        self.assertNotIn("USAGE_SUMMARY_CMD", source)

    def test_apply_usage_summary_preserves_lenos_cost(self):
        context = SimpleNamespace(
            n_input_tokens=None,
            n_cache_tokens=None,
            n_output_tokens=None,
            cost_usd=None,
            metadata={"existing": "value"},
        )
        summary = {
            "input_tokens": 30,
            "input_cache_hit_tokens": 20,
            "output_tokens": 5,
            "cost_usd": 0.00123,
        }

        LenosAgent._apply_usage_summary(LenosAgent, context, summary)

        self.assertEqual(context.n_input_tokens, 30)
        self.assertEqual(context.n_cache_tokens, 20)
        self.assertEqual(context.n_output_tokens, 5)
        self.assertEqual(context.cost_usd, 0.00123)
        self.assertEqual(
            context.metadata,
            {
                "existing": "value",
                "lenos_usage": summary,
                "lenos_cost_usd": 0.00123,
            },
        )


if __name__ == "__main__":
    unittest.main()
