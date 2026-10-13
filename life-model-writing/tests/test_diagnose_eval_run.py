import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from diagnose_eval_run import diagnose_run, main  # noqa: E402


TAXONOMY = {
    "version": "1.0",
    "blocking_tags": ["unsupported_causality"],
    "tags": [
        {"id": "unsupported_causality", "label": "未经支持的因果"},
        {"id": "missing_counterfactual", "label": "缺少反事实"},
    ],
}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _run_root(root: Path) -> tuple[Path, Path]:
    run_dir = root / "run"
    (run_dir / "diagnostics").mkdir(parents=True)
    _write_json(
        run_dir / "manifest.json",
        {"run_id": "diagnostic-run", "cases": [{"id": "pair-x"}, {"id": "pair-y"}]},
    )
    _write_json(
        run_dir / "reveal.json",
        {
            "pairs": [
                {
                    "pair_id": "pair",
                    "skill_case_id": "pair-x",
                    "ordinary_case_id": "pair-y",
                }
            ]
        },
    )
    taxonomy_path = root / "taxonomy.json"
    _write_json(taxonomy_path, TAXONOMY)
    return run_dir, taxonomy_path


def _diagnostic(case_id: str, tags: list[str], independent: bool = True) -> dict[str, object]:
    return {
        "case_id": case_id,
        "evaluator": {"type": "human", "name": "reviewer", "independent": independent},
        "error_tags": tags,
    }


class DiagnoseEvaluationRunTests(unittest.TestCase):
    def test_valid_pair_aggregates_skill_and_ordinary_tags(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, taxonomy_path = _run_root(Path(temporary))
            _write_json(
                run_dir / "diagnostics" / "pair-x.json",
                _diagnostic("pair-x", ["missing_counterfactual"]),
            )
            _write_json(
                run_dir / "diagnostics" / "pair-y.json",
                _diagnostic("pair-y", ["unsupported_causality"]),
            )

            result = diagnose_run(run_dir, taxonomy_path)

            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["verified_case_count"], 2)
            self.assertEqual(result["conditions"]["skill"]["error_case_count"], 1)
            self.assertEqual(result["conditions"]["ordinary"]["error_case_count"], 1)
            self.assertEqual(
                result["conditions"]["ordinary"]["tag_counts"]["unsupported_causality"],
                1,
            )

    def test_unknown_tag_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, taxonomy_path = _run_root(Path(temporary))
            _write_json(
                run_dir / "diagnostics" / "pair-x.json",
                _diagnostic("pair-x", ["not-a-real-tag"]),
            )

            result = diagnose_run(run_dir, taxonomy_path)

            self.assertEqual(result["status"], "fail")
            self.assertIn("unknown-tag:pair-x:not-a-real-tag", result["blocking_reasons"])

    def test_missing_or_non_independent_diagnostics_are_unverified(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, taxonomy_path = _run_root(Path(temporary))
            _write_json(
                run_dir / "diagnostics" / "pair-x.json",
                _diagnostic("pair-x", [], independent=False),
            )

            result = diagnose_run(run_dir, taxonomy_path)

            self.assertEqual(result["status"], "unverified")
            self.assertIn("unverified-diagnostic:pair-x", result["unverified_reasons"])
            self.assertIn("missing-diagnostic:pair-y", result["unverified_reasons"])

    def test_invalid_reveal_mapping_cannot_cross_assign_conditions(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, taxonomy_path = _run_root(Path(temporary))
            reveal = json.loads((run_dir / "reveal.json").read_text(encoding="utf-8"))
            reveal["pairs"][0]["skill_case_id"] = "not-in-manifest"
            _write_json(run_dir / "reveal.json", reveal)

            result = diagnose_run(run_dir, taxonomy_path)

            self.assertEqual(result["status"], "fail")
            self.assertTrue(
                any(reason.startswith("invalid-reveal:") for reason in result["blocking_reasons"])
            )

    def test_cli_returns_nonzero_for_unverified_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir, taxonomy_path = _run_root(Path(temporary))
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--run-dir", str(run_dir), "--taxonomy", str(taxonomy_path)])

            self.assertEqual(exit_code, 2)
            self.assertIn("status=unverified", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
