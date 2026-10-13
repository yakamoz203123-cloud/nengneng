import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_review_packet import create_review_packet  # noqa: E402
from import_review_scores import import_review_scores  # noqa: E402


class ReviewScoreImportTests(unittest.TestCase):
    def test_import_remaps_blind_sample_id_to_original_case_id(self):
        source_run = ROOT / "evals" / "baselines" / "v0.2-run-1"
        rubric_path = ROOT / "evals" / "rubric.json"

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            run_dir = temporary_root / "run"
            packet_dir = temporary_root / "packet"
            shutil.copytree(source_run, run_dir)
            create_review_packet(
                run_dir=run_dir,
                skill_root=ROOT,
                rubric_path=rubric_path,
                output_dir=packet_dir,
            )

            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
            dimension_ids = [dimension["id"] for dimension in rubric["dimensions"]]
            score = {
                "case_id": "sample-001",
                "evaluator": {"type": "independent-test", "independent": True},
                "scores": {dimension_id: 4 for dimension_id in dimension_ids},
                "critical_errors": [],
                "total": 24,
            }
            score_dir = packet_dir / "scores"
            score_dir.mkdir()
            (score_dir / "sample-001.json").write_text(
                json.dumps(score, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            imported = import_review_scores(
                run_dir=run_dir,
                packet_dir=packet_dir,
                rubric_path=rubric_path,
            )

            self.assertEqual([item["case_id"] for item in imported], ["activation-direct-01"])
            self.assertTrue((run_dir / "scores" / "activation-direct-01.json").is_file())

    def test_import_requires_independent_scores_and_refuses_overwrite(self):
        source_run = ROOT / "evals" / "baselines" / "v0.2-run-1"
        rubric_path = ROOT / "evals" / "rubric.json"

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            run_dir = temporary_root / "run"
            packet_dir = temporary_root / "packet"
            shutil.copytree(source_run, run_dir)
            create_review_packet(
                run_dir=run_dir,
                skill_root=ROOT,
                rubric_path=rubric_path,
                output_dir=packet_dir,
            )

            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
            dimension_ids = [dimension["id"] for dimension in rubric["dimensions"]]
            score = {
                "case_id": "sample-001",
                "evaluator": {"type": "independent-test", "independent": True},
                "scores": {dimension_id: 4 for dimension_id in dimension_ids},
                "critical_errors": [],
                "total": 24,
            }
            score_dir = packet_dir / "scores"
            score_dir.mkdir()
            (score_dir / "sample-001.json").write_text(
                json.dumps(score, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            imported = import_review_scores(
                run_dir=run_dir,
                packet_dir=packet_dir,
                rubric_path=rubric_path,
            )

            self.assertEqual([item["case_id"] for item in imported], ["activation-direct-01"])
            self.assertEqual(
                json.loads(
                    (run_dir / "scores" / "activation-direct-01.json").read_text(
                        encoding="utf-8"
                    )
                ),
                score,
            )
            with self.assertRaises(FileExistsError):
                import_review_scores(
                    run_dir=run_dir,
                    packet_dir=packet_dir,
                    rubric_path=rubric_path,
                )


if __name__ == "__main__":
    unittest.main()
