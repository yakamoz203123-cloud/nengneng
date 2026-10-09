import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_review_packet import create_review_packet  # noqa: E402


class ReviewPacketTests(unittest.TestCase):
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
                    "activation-direct-02",
                    "activation-indirect-02",
                    "activation-incomplete-01",
                    "activation-incomplete-02",
                    "activation-incomplete-03",
                    "activation-negative-02",
                    "activation-negative-03",
                    "activation-negative-04",
                    "activation-negative-05",
                    "activation-edge-01",
                    "activation-edge-02",
                    "activation-edge-03",
                ],
            )

            for relative_path in (
                "manifest.json",
                "rubric.json",
                "cases.json",
                "reviewer-instructions.md",
                "skill/SKILL.md",
                "skill/references/theory-14-diffusion-thresholds-propagation.md",
                "outputs/activation-direct-01.md",
                "outputs/activation-indirect-01.md",
                "outputs/activation-negative-01.md",
            ):
                self.assertTrue((packet_dir / relative_path).is_file(), relative_path)

            cases = json.loads((packet_dir / "cases.json").read_text(encoding="utf-8"))
            self.assertEqual(len(cases), 3)
            self.assertTrue(all("expected_activation" not in case for case in cases))
            self.assertFalse((packet_dir / "scores").exists())
            self.assertNotIn("unverified", (packet_dir / "reviewer-instructions.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
