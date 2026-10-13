import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_eval_run import create_run  # noqa: E402
from eval_common import EvaluationDataError  # noqa: E402


FIXTURE = Path(__file__).parent / "fixtures" / "valid-content-cases.json"
INVALID_FIXTURE = Path(__file__).parent / "fixtures" / "invalid-content-cases.json"


class CreateEvaluationRunTests(unittest.TestCase):
    def test_create_run_writes_manifest_and_artifact_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            skill_root = Path(temporary) / "skill"
            run_path = create_run(
                skill_root=skill_root,
                case_paths=[FIXTURE],
                run_id="run-001",
                model={"name": "manual", "backend_version": "unknown", "parameters": {}},
                invocation_mode="manual-import",
                human_intervention="none",
                now=datetime(2026, 10, 9, 1, 2, 3, tzinfo=timezone.utc),
            )

            self.assertEqual(run_path, skill_root / "evals" / "runs" / "run-001")
            self.assertTrue((run_path / "manifest.json").is_file())
            self.assertTrue((run_path / "outputs").is_dir())
            self.assertTrue((run_path / "checks").is_dir())
            self.assertTrue((run_path / "scores").is_dir())

            manifest = json.loads((run_path / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["created_at"], "2026-10-09T01:02:03+00:00")
            self.assertEqual(manifest["git_commit"], "unknown")
            self.assertEqual(manifest["cases"][0]["id"], "1")
            self.assertEqual(manifest["cases"][0]["kind"], "content")
            self.assertEqual(len(manifest["cases"][0]["prompt_sha256"]), 64)

    def test_invalid_cases_create_no_run_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            skill_root = Path(temporary) / "skill"

            with self.assertRaises(EvaluationDataError):
                create_run(
                    skill_root=skill_root,
                    case_paths=[INVALID_FIXTURE],
                    run_id="invalid-run",
                    model={"name": "manual"},
                    invocation_mode="manual-import",
                    human_intervention="none",
                )

            self.assertFalse((skill_root / "evals" / "runs" / "invalid-run").exists())

    def test_duplicate_run_id_preserves_original_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            skill_root = Path(temporary) / "skill"
            run_path = create_run(
                skill_root,
                [FIXTURE],
                "same-run",
                {"name": "first"},
                "manual-import",
                "none",
            )
            original = (run_path / "manifest.json").read_bytes()

            with self.assertRaises(FileExistsError):
                create_run(
                    skill_root,
                    [FIXTURE],
                    "same-run",
                    {"name": "second"},
                    "manual-import",
                    "none",
                )

            self.assertEqual((run_path / "manifest.json").read_bytes(), original)

    def test_create_run_preserves_optional_experiment_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            skill_root = Path(temporary) / "skill"
            experiment = {
                "engine": "codex",
                "condition": "skill",
                "repeat_index": 1,
                "sampling": {"temperature": 0.2, "seed": 41},
            }
            run_path = create_run(
                skill_root=skill_root,
                case_paths=[FIXTURE],
                run_id="metadata-run",
                model={"name": "manual"},
                invocation_mode="manual-import",
                human_intervention="none",
                experiment=experiment,
            )

            manifest = json.loads((run_path / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["experiment"], experiment)


if __name__ == "__main__":
    unittest.main()
