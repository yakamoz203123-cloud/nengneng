import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from regression_gate import evaluate_run, validate_contract  # noqa: E402


DIMENSIONS = [
    "theory_selection",
    "causal_reasoning",
    "cross_disciplinary_integration",
    "spoken_naturalness",
    "content_completeness",
    "factual_accuracy_and_boundaries",
]


def _contract() -> dict[str, object]:
    return {
        "schema_version": "1",
        "case_ids": ["t01-x", "t01-y"],
        "pairs": [{"pair_id": "t01", "case_ids": ["t01-x", "t01-y"]}],
        "hard_checks": {
            "min_non_whitespace": 800,
            "max_non_whitespace": 1200,
            "forbidden_terms": ["内部流程"],
        },
        "regression_gates": {
            "min_skill_case_total": 27,
            "min_skill_average_total": 28.0,
            "min_skill_advantage": 2.0,
            "min_skill_wins": 1,
            "min_skill_dimension_average": 4.0,
            "max_critical_errors": 0,
        },
    }


def _score(case_id: str, value: int = 5, independent: bool = True) -> dict[str, object]:
    return {
        "case_id": case_id,
        "evaluator": {"type": "blind-test", "name": "reviewer", "independent": independent},
        "scores": {dimension: value for dimension in DIMENSIONS},
        "critical_errors": [],
    }


def _write_run(root: Path, *, ordinary_total: int = 24) -> tuple[Path, Path]:
    run_dir = root / "run"
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "scores").mkdir()
    contract_path = root / "contract.json"
    contract = _contract()
    contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    manifest = {
        "run_id": "test-run",
        "skill_name": "life-model-writing",
        "cases": [{"id": case_id} for case_id in contract["case_ids"]],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "reveal.json").write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "pair_id": "t01",
                        "skill_case_id": "t01-x",
                        "ordinary_case_id": "t01-y",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = "但是" + "中" * 798
    for case_id in contract["case_ids"]:
        (run_dir / "outputs" / f"{case_id}.md").write_text(text, encoding="utf-8")
    (run_dir / "scores" / "t01-x.json").write_text(
        json.dumps(_score("t01-x", 5), ensure_ascii=False), encoding="utf-8"
    )
    ordinary_value = 4 if ordinary_total == 24 else 5
    (run_dir / "scores" / "t01-y.json").write_text(
        json.dumps(_score("t01-y", ordinary_value), ensure_ascii=False), encoding="utf-8"
    )
    return run_dir, contract_path


class RegressionGateTests(unittest.TestCase):
    def test_checked_in_v03_baseline_passes(self):
        result = evaluate_run(
            ROOT / "evals" / "baselines" / "v0.3-run-1",
            ROOT / "evals" / "baselines" / "v0.3-run-1" / "regression-contract.json",
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["hard_checks"]["total"], 10)

    def test_validate_contract_requires_pairs_to_cover_case_ids(self):
        contract = _contract()
        validate_contract(contract)
        contract["pairs"][0]["case_ids"] = ["t01-x"]
        with self.assertRaises(ValueError):
            validate_contract(contract)

    def test_baseline_shape_passes_hard_checks_and_relative_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["hard_checks"]["failed"], 0)
            self.assertEqual(result["metrics"]["skill_wins"], 1)

    def test_short_output_fails_even_when_score_is_perfect(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            (run_dir / "outputs" / "t01-x.md").write_text("短文", encoding="utf-8")
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "fail")
            self.assertGreater(result["hard_checks"]["failed"], 0)

    def test_forbidden_internal_term_fails_hard_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            (run_dir / "outputs" / "t01-x.md").write_text(
                "内部流程" + "中" * 798, encoding="utf-8"
            )
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "fail")
            check = next(item for item in result["hard_checks"]["cases"] if item["case_id"] == "t01-x")
            self.assertIn("internal-leakage", check["reasons"])

    def test_skill_case_below_floor_fails_relative_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            score = _score("t01-x", 5)
            for dimension in DIMENSIONS[:4]:
                score["scores"][dimension] = 4
            (run_dir / "scores" / "t01-x.json").write_text(
                json.dumps(score, ensure_ascii=False), encoding="utf-8"
            )
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "fail")
            self.assertIn("gate-failed:min_skill_case_total", result["blocking_reasons"])

    def test_reveal_from_another_pair_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            reveal = json.loads((run_dir / "reveal.json").read_text(encoding="utf-8"))
            reveal["pairs"][0]["skill_case_id"] = "t02-x"
            (run_dir / "reveal.json").write_text(
                json.dumps(reveal, ensure_ascii=False), encoding="utf-8"
            )
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "fail")
            self.assertTrue(any(reason.startswith("invalid-reveal:") for reason in result["blocking_reasons"]))

    def test_missing_independent_score_is_unverified_not_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            (run_dir / "scores" / "t01-x.json").unlink()
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "unverified")
            self.assertIn("missing-score:t01-x", result["unverified_reasons"])

    def test_non_independent_score_is_unverified_not_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            score = _score("t01-x", independent=False)
            (run_dir / "scores" / "t01-x.json").write_text(
                json.dumps(score, ensure_ascii=False), encoding="utf-8"
            )
            result = evaluate_run(run_dir, contract_path)
            self.assertEqual(result["status"], "unverified")
            self.assertIn("unverified-score:t01-x", result["unverified_reasons"])

    def test_skill_only_critical_error_scope_does_not_block_control_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["critical_error_scope"] = "skill_cases_only"
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False), encoding="utf-8"
            )
            ordinary_score = _score("t01-y", 4)
            ordinary_score["critical_errors"] = ["unsupported_causality"]
            (run_dir / "scores" / "t01-y.json").write_text(
                json.dumps(ordinary_score, ensure_ascii=False), encoding="utf-8"
            )

            result = evaluate_run(run_dir, contract_path)

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["metrics"]["skill_critical_error_count"], 0)
            self.assertEqual(result["metrics"]["ordinary_critical_error_count"], 1)

    def test_skill_only_critical_error_scope_still_blocks_skill_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, contract_path = _write_run(Path(temporary))
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["critical_error_scope"] = "skill_cases_only"
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False), encoding="utf-8"
            )
            skill_score = _score("t01-x", 5)
            skill_score["critical_errors"] = ["unsupported_causality"]
            (run_dir / "scores" / "t01-x.json").write_text(
                json.dumps(skill_score, ensure_ascii=False), encoding="utf-8"
            )

            result = evaluate_run(run_dir, contract_path)

            self.assertEqual(result["status"], "fail")
            self.assertIn("critical-error:t01-x", result["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()
