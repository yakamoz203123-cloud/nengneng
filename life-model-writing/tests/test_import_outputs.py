import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_eval_run import create_run  # noqa: E402
from import_outputs import import_output, import_output_directory  # noqa: E402


FIXTURE = Path(__file__).parent / "fixtures" / "valid-content-cases.json"


class ImportOutputTests(unittest.TestCase):
    def _make_run(self, temporary: str, case_path: Path = FIXTURE) -> Path:
        return create_run(
            skill_root=Path(temporary) / "skill",
            case_paths=[case_path],
            run_id="import-run",
            model={"name": "manual"},
            invocation_mode="manual-import",
            human_intervention="none",
        )

    def test_import_preserves_bytes_and_records_sha256(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_path = self._make_run(temporary)
            source = Path(temporary) / "source.md"
            source_bytes = b"\xe4\xb8\xad\xe6\x96\x87\r\n"
            source.write_bytes(source_bytes)

            record = import_output(run_path, "1", source)

            imported = run_path / "outputs" / "1.md"
            self.assertEqual(imported.read_bytes(), source_bytes)
            self.assertEqual(record["byte_length"], len(source_bytes))
            self.assertEqual(
                record["sha256"], hashlib.sha256(source_bytes).hexdigest()
            )
            manifest = json.loads(
                (run_path / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["outputs"][0]["case_id"], "1")

    def test_unknown_case_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_path = self._make_run(temporary)
            source = Path(temporary) / "source.md"
            source.write_text("输出", encoding="utf-8")

            with self.assertRaises(ValueError):
                import_output(run_path, "unknown", source)

    def test_duplicate_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_path = self._make_run(temporary)
            first = Path(temporary) / "first.md"
            second = Path(temporary) / "second.md"
            first.write_bytes(b"first\r\n")
            second.write_bytes(b"second\r\n")
            import_output(run_path, "1", first)

            with self.assertRaises(FileExistsError):
                import_output(run_path, "1", second)

            self.assertEqual((run_path / "outputs" / "1.md").read_bytes(), b"first\r\n")

    def test_directory_import_skips_missing_expected_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            case_path = Path(temporary) / "two-cases.json"
            case_path.write_text(
                json.dumps(
                    {
                        "skill_name": "life-model-writing",
                        "version": "0.1",
                        "evals": [
                            {
                                "id": "1",
                                "name": "one",
                                "prompt": "问题一",
                                "expected_output": "输出一",
                                "assertions": ["有机制"],
                            },
                            {
                                "id": "2",
                                "name": "two",
                                "prompt": "问题二",
                                "expected_output": "输出二",
                                "assertions": ["有边界"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            run_path = self._make_run(temporary, case_path)
            source_dir = Path(temporary) / "outputs-source"
            source_dir.mkdir()
            (source_dir / "1.md").write_text("只有第一题", encoding="utf-8")

            records = import_output_directory(run_path, source_dir)

            self.assertEqual([record["case_id"] for record in records], ["1"])
            self.assertTrue((run_path / "outputs" / "1.md").is_file())
            self.assertFalse((run_path / "outputs" / "2.md").exists())


if __name__ == "__main__":
    unittest.main()
