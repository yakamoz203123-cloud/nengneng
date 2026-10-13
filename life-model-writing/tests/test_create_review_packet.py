import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_review_packet import create_review_packet  # noqa: E402


class ReviewPacketTests(unittest.TestCase):
    def test_packet_renames_case_ids_and_outputs_for_true_blind_review(self):
        run_dir = ROOT / "evals" / "baselines" / "v0.2-run-1"
        rubric = ROOT / "evals" / "rubric.json"

        with tempfile.TemporaryDirectory() as temporary:
            packet_dir = Path(temporary) / "packet"
            create_review_packet(
                run_dir=run_dir,
                skill_root=ROOT,
                rubric_path=rubric,
                output_dir=packet_dir,
            )

            cases = json.loads((packet_dir / "cases.json").read_text(encoding="utf-8"))
            output_names = sorted(path.name for path in (packet_dir / "outputs").glob("*.md"))

            self.assertEqual([case["id"] for case in cases], [
                "sample-001",
                "sample-002",
                "sample-003",
            ])
            self.assertEqual(
                output_names,
                ["sample-001.md", "sample-002.md", "sample-003.md"],
            )
            self.assertNotIn("activation-direct-01", (packet_dir / "cases.json").read_text(encoding="utf-8"))
            self.assertNotIn("activation-direct-01", (packet_dir / "manifest.json").read_text(encoding="utf-8"))

    def test_packet_is_blinded_and_contains_only_review_inputs(self):
        run_dir = ROOT / "evals" / "baselines" / "v0.2-run-1"
        rubric = ROOT / "evals" / "rubric.json"

        with tempfile.TemporaryDirectory() as temporary:
            packet_dir = Path(temporary) / "packet"
            manifest = create_review_packet(
                run_dir=run_dir,
                skill_root=ROOT,
                rubric_path=rubric,
                output_dir=packet_dir,
            )

            self.assertEqual(manifest["case_count"], 3)
            self.assertEqual(
                manifest["omitted_case_ids"],
                [
                    "omitted-002",
                    "omitted-004",
                    "omitted-005",
                    "omitted-006",
                    "omitted-007",
                    "omitted-009",
                    "omitted-010",
                    "omitted-011",
                    "omitted-012",
                    "omitted-013",
                    "omitted-014",
                    "omitted-015",
                ],
            )

            for relative_path in (
                "manifest.json",
                "rubric.json",
                "cases.json",
                "reviewer-instructions.md",
                "skill/SKILL.md",
                "skill/references/theory-14-diffusion-thresholds-propagation.md",
                "outputs/sample-001.md",
                "outputs/sample-002.md",
                "outputs/sample-003.md",
            ):
                self.assertTrue((packet_dir / relative_path).is_file(), relative_path)

            cases = json.loads((packet_dir / "cases.json").read_text(encoding="utf-8"))
            self.assertEqual(len(cases), 3)
            self.assertTrue(all("expected_activation" not in case for case in cases))
            self.assertFalse((packet_dir / "scores").exists())
            self.assertNotIn("unverified", (packet_dir / "reviewer-instructions.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
