import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agon_bench.adapters import lenos
from agon_bench.adapters.lenos import DEFAULT_LENOS_VERSION, LenosAgent


ROOT = Path(__file__).resolve().parents[1]


class LenosAdapterTest(unittest.TestCase):
    def test_default_lenos_version_uses_latest_release(self):
        self.assertEqual(DEFAULT_LENOS_VERSION, "latest")

    def test_minimal_lenos_config_does_not_install_post_step_hook(self):
        config = json.loads((ROOT / "agon_bench/lenos/config.json").read_text())

        self.assertNotIn("hooks", config)

    def test_adapter_uses_atif_trajectory_instead_of_usage_json(self):
        source = (ROOT / "agon_bench/adapters/lenos.py").read_text()

        self.assertIn("--trajectory-json", source)
        self.assertIn('TRAJECTORY_PATH = "/logs/agent/trajectory.json"', source)
        self.assertNotIn("--usage-json", source)
        self.assertNotIn(
            'USAGE_SUMMARY_PATH = "/logs/agent/usage-summary.json"', source
        )
        self.assertNotIn("agon-lenos-post-step", source)
        self.assertNotIn("USAGE_HOOK_SCRIPT", source)
        self.assertNotIn("USAGE_SUMMARY_CMD", source)

    def test_adapter_injects_task_through_context_file(self):
        source = (ROOT / "agon_bench/adapters/lenos.py").read_text()

        self.assertIn("--context-file", source)
        self.assertIn('TASK_CONTEXT_PATH = "/tmp/agon-task.md"', source)
        self.assertIn("TASK_TRIGGER", source)
        self.assertNotIn("escaped_instruction = shlex.quote(instruction)", source)

    def test_task_context_preserves_harbor_instruction_without_agon_wrapper(self):
        context = LenosAgent._task_context("Do the thing.")

        self.assertEqual(context, "Do the thing.\n")
        self.assertNotIn("Agon", context)
        self.assertNotIn("Terminal-Bench", context)

    def test_makefile_has_trajectory_validator_target(self):
        source = (ROOT / "Makefile").read_text()

        self.assertIn("validate-trajectory:", source)
        self.assertIn("TRAJECTORY", source)
        self.assertIn("harbor.utils.trajectory_validator", source)

    def test_deepseek_models_use_xhigh_reasoning(self):
        self.assertEqual(
            LenosAgent._reasoning_flag_for_model("deepseek-v4-flash"),
            " --reasoning-effort xhigh",
        )
        self.assertEqual(
            LenosAgent._reasoning_flag_for_model("deepseek/deepseek-v4-pro"),
            " --reasoning-effort xhigh",
        )

    def test_non_deepseek_models_do_not_force_reasoning(self):
        self.assertEqual(LenosAgent._reasoning_flag_for_model("gpt-5.4"), "")
        self.assertEqual(LenosAgent._reasoning_flag_for_model(None), "")

    def test_explicit_reasoning_effort_applies_to_any_model(self):
        with patch.object(lenos, "LENOS_REASONING_EFFORT", "xhigh"):
            self.assertEqual(
                LenosAgent._reasoning_flag_for_model("gpt-5.4"),
                " --reasoning-effort xhigh",
            )

    def test_populate_trajectory_context_parses_atif_final_metrics(self):
        context = SimpleNamespace(
            n_input_tokens=None,
            n_cache_tokens=None,
            n_output_tokens=None,
            cost_usd=None,
            metadata={},
        )
        stdout = json.dumps(
            {
                "schema_version": "ATIF-v1.7",
                "final_metrics": {
                    "total_prompt_tokens": 50,
                    "total_cached_tokens": 20,
                    "total_completion_tokens": 5,
                    "total_cost_usd": 0.00123,
                    "extra": {
                        "cache_miss_tokens": 30,
                        "cache_creation_tokens": 2,
                        "total_tokens": 55,
                    },
                },
            },
            indent=2,
        )

        LenosAgent(Path("/tmp"))._populate_trajectory_context(context, stdout)

        self.assertEqual(context.n_input_tokens, 50)
        self.assertEqual(context.n_cache_tokens, 20)
        self.assertEqual(context.n_output_tokens, 5)
        self.assertEqual(context.cost_usd, 0.00123)
        self.assertEqual(context.metadata["lenos_usage"]["input_cache_miss_tokens"], 30)
        self.assertEqual(context.metadata["lenos_usage"]["cache_creation_tokens"], 2)
        self.assertEqual(context.metadata["lenos_atif"]["schema_version"], "ATIF-v1.7")

    def test_populate_trajectory_context_parses_last_json_line(self):
        context = SimpleNamespace(
            n_input_tokens=None,
            n_cache_tokens=None,
            n_output_tokens=None,
            cost_usd=None,
            metadata={},
        )
        stdout = "\n".join(
            [
                "ignored log line",
                json.dumps(
                    {
                        "final_metrics": {
                            "total_prompt_tokens": 50,
                            "total_cached_tokens": 20,
                            "total_completion_tokens": 5,
                            "total_cost_usd": None,
                        },
                    }
                ),
            ]
        )

        LenosAgent(Path("/tmp"))._populate_trajectory_context(context, stdout)

        self.assertEqual(context.n_input_tokens, 50)
        self.assertEqual(context.n_cache_tokens, 20)
        self.assertEqual(context.n_output_tokens, 5)

    def test_populate_trajectory_context_ignores_missing_final_metrics(self):
        context = SimpleNamespace(
            n_input_tokens=None,
            n_cache_tokens=None,
            n_output_tokens=None,
            cost_usd=None,
            metadata={},
        )

        LenosAgent(Path("/tmp"))._populate_trajectory_context(
            context, json.dumps({"schema_version": "ATIF-v1.7"})
        )

        self.assertIsNone(context.n_input_tokens)
        self.assertIsNone(context.n_cache_tokens)
        self.assertIsNone(context.n_output_tokens)
        self.assertIsNone(context.cost_usd)
        self.assertEqual(context.metadata, {})

    def test_apply_atif_trajectory_preserves_lenos_cost(self):
        context = SimpleNamespace(
            n_input_tokens=None,
            n_cache_tokens=None,
            n_output_tokens=None,
            cost_usd=None,
            metadata={"existing": "value"},
        )
        trajectory = {
            "final_metrics": {
                "total_prompt_tokens": 50,
                "total_cached_tokens": 20,
                "total_completion_tokens": 5,
                "total_cost_usd": 0.00123,
                "extra": {"cache_miss_tokens": 30},
            }
        }

        LenosAgent._apply_atif_trajectory(LenosAgent, context, trajectory)

        self.assertEqual(context.n_input_tokens, 50)
        self.assertEqual(context.n_cache_tokens, 20)
        self.assertEqual(context.n_output_tokens, 5)
        self.assertEqual(context.cost_usd, 0.00123)
        self.assertEqual(
            context.metadata,
            {
                "existing": "value",
                "lenos_atif": trajectory,
                "lenos_usage": {
                    "input_tokens": 50,
                    "input_cache_hit_tokens": 20,
                    "input_cache_miss_tokens": 30,
                    "cache_creation_tokens": None,
                    "output_tokens": 5,
                    "total_tokens": 55,
                    "cost_usd": 0.00123,
                },
                "lenos_cost_usd": 0.00123,
            },
        )


if __name__ == "__main__":
    unittest.main()
