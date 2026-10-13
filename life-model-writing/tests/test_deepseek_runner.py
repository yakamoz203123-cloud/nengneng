import sys
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from eval_common import load_case_sets  # noqa: E402
from reference_router import load_routes  # noqa: E402
from run_deepseek_eval import (  # noqa: E402
    _set_manifest_case_source,
    build_messages,
    normalize_case_records,
)


class DeepSeekRunnerTests(unittest.TestCase):
    def test_normalize_case_records_requires_paired_ordinary_and_skill_cases(self):
        records = normalize_case_records(
            {
                "evals": [
                    {
                        "id": "pair-01-x",
                        "pair_id": "pair-01",
                        "condition": "ordinary",
                        "prompt": "同一个题目",
                    },
                    {
                        "id": "pair-01-y",
                        "pair_id": "pair-01",
                        "condition": "skill",
                        "prompt": "同一个题目",
                    },
                ]
            }
        )

        self.assertEqual(records["pair-01-x"]["condition"], "ordinary")
        self.assertEqual(records["pair-01-y"]["condition"], "skill")

    def test_skill_message_contains_routed_context_but_ordinary_does_not(self):
        ordinary = build_messages(
            "ordinary", "题目", "SKILL AND THEORY CONTEXT"
        )
        skill = build_messages("skill", "题目", "SKILL AND THEORY CONTEXT")

        self.assertNotIn("SKILL AND THEORY CONTEXT", ordinary[0]["content"])
        self.assertIn("SKILL AND THEORY CONTEXT", skill[0]["content"])
        self.assertEqual(ordinary[1]["content"], "题目")
        self.assertEqual(skill[1]["content"], "题目")

    def test_checked_in_v05_pack_has_ten_cases_and_five_complete_routes(self):
        cases_path = ROOT / "evals" / "v0.5-test-cases.json"
        routes_path = ROOT / "evals" / "v0.5-reference-routes.json"
        data = json.loads(cases_path.read_text(encoding="utf-8"))

        records = normalize_case_records(data)
        self.assertEqual(len(records), 10)
        self.assertEqual(len(load_case_sets([cases_path])), 10)
        routes = load_routes(routes_path, ROOT)
        self.assertEqual(set(routes["cases"]), {f"v05-fresh-0{index}" for index in range(1, 6)})

    def test_subset_manifest_points_back_to_the_declared_cases_file(self):
        manifest = {"cases": [{"id": "x", "source": "temporary.json"}]}

        _set_manifest_case_source(manifest, Path("evals/v0.5-test-cases.json"))

        self.assertEqual(
            manifest["cases"][0]["source"], str(Path("evals/v0.5-test-cases.json"))
        )


if __name__ == "__main__":
    unittest.main()
