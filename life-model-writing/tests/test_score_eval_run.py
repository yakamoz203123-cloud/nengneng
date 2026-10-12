import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_eval_run import create_run  # noqa: E402
from score_eval_run import (  # noqa: E402
    check_output,
    count_non_whitespace_characters,
    main,
    summarize_run,
    validate_score,
)


RUBRIC = json.loads((ROOT / "evals" / "rubric.json").read_text(encoding="utf-8"))


def _case_set(path: Path, count: int = 1) -> None:
    path.write_text(
        json.dumps(
            {
                "skill_name": "life-model-writing",
                "version": "0.1",
                "evals": [
                    {
                        "id": str(index),
                        "name": f"case-{index}",
                        "prompt": f"问题{index}",
                        "expected_output": f"输出{index}",
                        "assertions": ["有机制"],
                    }
                    for index in range(1, count + 1)
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _score(case_id: str, independent: bool = True, total: int = 30) -> dict[str, object]:
    if total == 30:
        values = [5, 5, 5, 5, 5, 5]
    elif total == 23:
        values = [4, 4, 3, 4, 4, 4]
    else:
        raise ValueError(f"unsupported test total: {total}")
    scores = {
        dimension["id"]: value
        for dimension, value in zip(RUBRIC["dimensions"], values)
    }
    return {
        "case_id": case_id,
        "evaluator": {"type": "human", "name": "reviewer", "independent": independent},
        "scores": scores,
        "critical_errors": [],
    }


class ScoreEvaluationTests(unittest.TestCase):
    def test_count_non_whitespace_characters(self):
        self.assertEqual(count_non_whitespace_characters("中 文\r\n"), 2)

    def test_validate_score_requires_all_dimensions_and_range(self):
        score = _score("1")
        normalized = validate_score(score, RUBRIC, "1")
        self.assertEqual(normalized["total"], 30)

        invalid = _score("1")
        invalid["scores"]["theory_selection"] = 6
        with self.assertRaises(ValueError):
            validate_score(invalid, RUBRIC, "1")

    def test_missing_score_and_non_independent_score_are_unverified(self):
        with tempfile.TemporaryDirectory() as temporary:
            case_path = Path(temporary) / "cases.json"
            _case_set(case_path, count=2)
            run_path = create_run(
                Path(temporary) / "skill",
                [case_path],
                "score-run",
                {"name": "manual"},
                "manual-import",
                "none",
            )
            (run_path / "outputs" / "1.md").write_text("有边界的输出", encoding="utf-8")
            (run_path / "scores" / "1.json").write_text(
                json.dumps(_score("1", independent=False), ensure_ascii=False),
                encoding="utf-8",
            )

            summary = summarize_run(run_path, ROOT / "evals" / "rubric.json")

            statuses = {
                case["case_id"]: case["score_status"] for case in summary["cases"]
            }
            self.assertEqual(statuses["1"], "unverified")
            self.assertEqual(statuses["2"], "unverified")
            self.assertEqual(summary["counts"]["unverified"], 2)

    def test_low_score_and_critical_error_fail(self):
        score = _score("1", total=23)
        result = validate_score(score, RUBRIC, "1")
        self.assertEqual(result["status"], "fail")

        score = _score("1")
        score["critical_errors"] = ["fabricated_research"]
        result = validate_score(score, RUBRIC, "1")
        self.assertEqual(result["status"], "fail")

    def test_check_output_reports_review_flags_without_scoring_quality(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output.md"
            output.write_text("所有人一定会这样。", encoding="utf-8")
            case = {"id": "1", "length_contract": None}

            result = check_output(case, output)

            self.assertEqual(result["status"], "review")
            self.assertIn("absolute-language", result["review_flags"])
            self.assertIn("boundary-language", result["review_flags"])

    def test_release_status_blocks_deterministic_failure_even_with_passing_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            case_path = Path(temporary) / "cases.json"
            case_path.write_text(
                json.dumps(
                    {
                        "skill_name": "life-model-writing",
                        "version": "0.2",
                        "evals": [
                            {
                                "id": "1",
                                "name": "standard-case",
                                "prompt": "问题",
                                "expected_output": "输出",
                                "assertions": ["有机制"],
                                "length_contract": "standard",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            run_path = create_run(
                Path(temporary) / "skill",
                [case_path],
                "release-gate-run",
                {"name": "manual"},
                "manual-import",
                "none",
            )
            (run_path / "outputs" / "1.md").write_text("短输出", encoding="utf-8")
            (run_path / "scores" / "1.json").write_text(
                json.dumps(_score("1"), ensure_ascii=False),
                encoding="utf-8",
            )

            summary = summarize_run(run_path, ROOT / "evals" / "rubric.json")

            case = summary["cases"][0]
            self.assertEqual(case["status"], "fail")
            self.assertEqual(case["score_status"], "pass")
            self.assertEqual(case["release_status"], "fail")
            self.assertEqual(summary["release_status"], "fail")

    def test_release_status_distinguishes_missing_and_failed_scores(self):
        with tempfile.TemporaryDirectory() as temporary:
            def run_case(run_id, output, score=None):
                case_path = Path(temporary) / f"{run_id}.json"
                case_path.write_text(
                    json.dumps(
                        {
                            "skill_name": "life-model-writing",
                            "version": "0.2",
                            "evals": [
                                {
                                    "id": "1",
                                    "name": run_id,
                                    "prompt": "问题",
                                    "expected_output": "输出",
                                    "assertions": ["有机制"],
                                    "length_contract": "standard",
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                run_path = create_run(
                    Path(temporary) / "skill",
                    [case_path],
                    run_id,
                    {"name": "manual"},
                    "manual-import",
                    "none",
                )
                (run_path / "outputs" / "1.md").write_text(output, encoding="utf-8")
                if score is not None:
                    (run_path / "scores" / "1.json").write_text(
                        json.dumps(score, ensure_ascii=False),
                        encoding="utf-8",
                    )
                return summarize_run(run_path, ROOT / "evals" / "rubric.json")

            valid_output = "但是" + "中" * 798
            missing_score = run_case("missing-score", valid_output)
            failed_score = run_case("failed-score", valid_output, _score("1", total=23))
            passing_score = run_case("passing-score", valid_output, _score("1"))

            self.assertEqual(missing_score["release_status"], "unverified")
            self.assertEqual(failed_score["release_status"], "fail")
            self.assertEqual(passing_score["release_status"], "pass")

    def test_cli_returns_nonzero_for_failed_release_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            case_path = Path(temporary) / "cases.json"
            case_path.write_text(
                json.dumps(
                    {
                        "skill_name": "life-model-writing",
                        "version": "0.2",
                        "evals": [
                            {
                                "id": "1",
                                "name": "cli-gate",
                                "prompt": "问题",
                                "expected_output": "输出",
                                "assertions": ["有机制"],
                                "length_contract": "standard",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            run_path = create_run(
                Path(temporary) / "skill",
                [case_path],
                "cli-gate",
                {"name": "manual"},
                "manual-import",
                "none",
            )
            (run_path / "outputs" / "1.md").write_text("短输出", encoding="utf-8")
            (run_path / "scores" / "1.json").write_text(
                json.dumps(_score("1"), ensure_ascii=False),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--run-dir",
                        str(run_path),
                        "--rubric",
                        str(ROOT / "evals" / "rubric.json"),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("release_status=fail", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
