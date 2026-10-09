import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from eval_common import (  # noqa: E402
    EvaluationDataError,
    load_case_sets,
    read_json,
    validate_case_set,
)


FIXTURES = Path(__file__).parent / "fixtures"


class EvaluationSchemaTests(unittest.TestCase):
    def test_real_cases_and_activation_cases_have_versioned_coverage(self):
        product_evals = ROOT / "evals"
        real_cases = load_case_sets([product_evals / "real-cases.json"])
        activation_cases = load_case_sets([product_evals / "activation-cases.json"])

        self.assertEqual(len(real_cases), 10)
        self.assertGreaterEqual(len(activation_cases), 12)
        self.assertEqual({case["id"] for case in real_cases}, {
            f"real-{index:02d}" for index in range(1, 11)
        })
        self.assertTrue(all(case["length_contract"] == "standard" for case in real_cases))
        self.assertEqual(
            {case["expected_activation"] for case in activation_cases},
            {True, False},
        )

        categories = {case["name"].split("-")[0] for case in activation_cases}
        self.assertTrue({"direct", "indirect", "incomplete", "negative", "edge"} <= categories)

        all_ids = [
            case["id"]
            for case in load_case_sets(
                [
                    product_evals / "evals.json",
                    product_evals / "real-cases.json",
                    product_evals / "activation-cases.json",
                ]
            )
        ]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_existing_case_shape_normalizes_integer_ids(self):
        data = read_json(FIXTURES / "valid-content-cases.json")

        cases = validate_case_set(data, "valid-content-cases.json")

        self.assertEqual(cases[0]["id"], "1")
        self.assertEqual(cases[0]["kind"], "content")
        self.assertIsNone(cases[0]["length_contract"])
        self.assertIsNone(cases[0]["expected_activation"])

    def test_duplicate_ids_across_case_sets_fail(self):
        first_path = FIXTURES / "valid-content-cases.json"
        duplicate_path = FIXTURES / "valid-content-cases.json"

        with self.assertRaises(EvaluationDataError) as error:
            load_case_sets([first_path, duplicate_path])

        self.assertEqual(error.exception.field_path, "evals[0].id")

    def test_invalid_case_reports_source_and_field_path(self):
        data = read_json(FIXTURES / "invalid-content-cases.json")

        with self.assertRaises(EvaluationDataError) as error:
            validate_case_set(data, "invalid-content-cases.json")

        self.assertEqual(error.exception.source, "invalid-content-cases.json")
        self.assertEqual(error.exception.field_path, "evals[0].prompt")

    def test_invalid_kind_is_rejected(self):
        data = {
            "skill_name": "life-model-writing",
            "version": "0.1",
            "evals": [
                {
                    "id": "activation-1",
                    "name": "invalid-kind",
                    "kind": "unknown",
                    "prompt": "测试",
                    "expected_output": "输出",
                    "assertions": ["断言"],
                }
            ],
        }

        with self.assertRaises(EvaluationDataError) as error:
            validate_case_set(data, "inline.json")

        self.assertEqual(error.exception.field_path, "evals[0].kind")


if __name__ == "__main__":
    unittest.main()
