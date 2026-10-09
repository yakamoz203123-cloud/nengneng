import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_skill import (  # noqa: E402
    CORE_HEADINGS,
    SELECTION_HEADINGS,
    parse_frontmatter,
    validate_skill_root,
)


class StaticValidationTests(unittest.TestCase):
    def test_current_skill_has_valid_frontmatter_and_references(self):
        errors = validate_skill_root(ROOT)

        self.assertEqual(errors, [])

    def test_skill_routes_all_numbered_theory_cards(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for index in range(1, 15):
            self.assertIn(f"references/theory-{index:02d}-", text)

    def test_skill_contract_names_selection_integration_and_lengths(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        required_contracts = (
            "主模型",
            "补充模型",
            "淘汰理由",
            "库外知识",
            "连接变量",
            "条件性预测",
            "400-600",
            "800-1200",
            "1500-2200",
        )

        for contract in required_contracts:
            self.assertIn(contract, text)

    def test_parse_frontmatter_reads_flat_name_and_description(self):
        text = "---\nname: example-skill\ndescription: Use when testing.\n---\n"

        self.assertEqual(
            parse_frontmatter(text),
            {"name": "example-skill", "description": "Use when testing."},
        )

    def test_invalid_name_and_missing_description_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "---\nname: Invalid Skill!\ndescription:\n---\n",
                encoding="utf-8",
            )

            errors = validate_skill_root(root)

        self.assertTrue(any("SKILL.md: invalid name" in error for error in errors))
        self.assertTrue(any("SKILL.md: missing description" in error for error in errors))

    def test_broken_links_and_missing_theory_headings_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            references = root / "references"
            references.mkdir()
            (root / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Use when testing.\n---\n"
                "[missing](references/nope.md)\n",
                encoding="utf-8",
            )
            (references / "theory-01-example.md").write_text(
                "# Example\n\n## 一句话定义\n",
                encoding="utf-8",
            )

            errors = validate_skill_root(root)

        self.assertTrue(any("broken link" in error for error in errors))
        self.assertTrue(any("missing theory heading" in error for error in errors))

    def test_invalid_evaluation_json_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            evaluations = root / "evals"
            evaluations.mkdir()
            (evaluations / "evals.json").write_text("{broken", encoding="utf-8")

            errors = validate_skill_root(root)

        self.assertTrue(any("evals/evals.json" in error for error in errors))

    def test_unfinished_scaffold_marker_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Use when testing.\n---\n\nTODO\n",
                encoding="utf-8",
            )

            errors = validate_skill_root(root)

        self.assertTrue(any("unfinished scaffold marker" in error for error in errors))

    def test_core_headings_remain_the_validator_contract(self):
        self.assertIn("可靠来源", CORE_HEADINGS)
        self.assertIn("事实与证据边界", CORE_HEADINGS)
        self.assertIn("连接变量", SELECTION_HEADINGS)


if __name__ == "__main__":
    unittest.main()
