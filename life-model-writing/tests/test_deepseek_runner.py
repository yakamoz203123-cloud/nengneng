import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from eval_common import load_case_sets  # noqa: E402
from reference_router import load_routes  # noqa: E402
from run_deepseek_eval import (  # noqa: E402
    MAX_LENGTH_REPAIR_PASSES,
    ORDINARY_SYSTEM,
    SKILL_SYSTEM_PREFIX,
    build_length_repair_messages,
    _set_manifest_case_source,
    build_messages,
    build_output_check,
    normalize_case_records,
    standard_length_violation,
)


class DeepSeekRunnerTests(unittest.TestCase):
    def test_length_repair_has_a_hard_maximum(self):
        self.assertEqual(MAX_LENGTH_REPAIR_PASSES, 2)

    def test_standard_length_violation_covers_both_bounds_only(self):
        case = {"length_contract": "standard"}

        self.assertIsNone(standard_length_violation(case, "字" * 800))
        self.assertEqual(standard_length_violation(case, "字" * 799), "underlength")
        self.assertEqual(standard_length_violation(case, "字" * 1201), "overlength")
        self.assertIsNone(standard_length_violation({"length_contract": "short"}, "字" * 1201))

    def test_length_repair_messages_keep_draft_and_match_violation(self):
        original = build_messages("ordinary", "原始题目", "")
        repaired = build_length_repair_messages(original, "这是超长草稿", "overlength")

        self.assertEqual(repaired[:2], original)
        self.assertEqual(repaired[2]["role"], "assistant")
        self.assertEqual(repaired[2]["content"], "这是超长草稿")
        self.assertEqual(repaired[3]["role"], "user")
        self.assertIn("只输出压缩后的完整口播文案", repaired[3]["content"])
        self.assertIn("不要截断", repaired[3]["content"])

        underlength = build_length_repair_messages(original, "这是过短草稿", "underlength")
        self.assertIn("补充缺失的机制桥梁、关键变量关系", underlength[3]["content"])

    def test_both_conditions_have_an_explicit_safe_compression_target(self):
        for system_prompt in (ORDINARY_SYSTEM, SKILL_SYSTEM_PREFIX):
            self.assertIn("950—1100", system_prompt)
            self.assertIn("超过 1100", system_prompt)
            self.assertIn("非空白字符", system_prompt)

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

    def test_output_check_records_standard_length_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "case.md"
            output.write_text("字" * 1201, encoding="utf-8")

            result = build_output_check(
                {"id": "case", "length_contract": "standard"}, output
            )

            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["checks"][2]["name"], "length-contract")


if __name__ == "__main__":
    unittest.main()
