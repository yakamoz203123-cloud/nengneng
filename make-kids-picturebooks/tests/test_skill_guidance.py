from pathlib import Path
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (SKILL_DIR / relative_path).read_text(encoding="utf-8")


class SkillGuidanceTests(unittest.TestCase):
    def test_workflow_routes_to_continuity_and_final_gates(self) -> None:
        skill = read("SKILL.md")

        for link in (
            "references/characters.md",
            "references/composition.md",
            "references/page-records.md",
            "references/review.md",
            "references/printing.md",
            "references/acceptance.md",
        ):
            self.assertIn(link, skill)

        for term in (
            "manifest continuity fields",
            "state_id",
            "summary",
            "character_reference_path",
            "character bible",
            "adjacent-page pair",
            "text-image state matching",
            "validate_exports.py",
            "export_book.py",
            "acceptance",
        ):
            self.assertIn(term, skill)


    def test_reference_guidance_defines_structured_continuity_and_review(self) -> None:
        characters = read("references/characters.md")
        composition = read("references/composition.md")
        records = read("references/page-records.md")
        review = read("references/review.md")
        printing = read("references/printing.md")
        acceptance = read("references/acceptance.md")

        self.assertIn("character bible", characters)
        self.assertIn("character_reference_path", characters)
        self.assertIn("text-image state matching", composition)
        for term in ("state_id", "summary", '"status"', '"evidence"'):
            self.assertIn(term, records)
        self.assertIn("adjacent-page pair", review)
        self.assertIn("human/model visual review", review)
        self.assertIn("font", printing)
        self.assertIn("validate_exports.py", acceptance)
        self.assertIn("export_book.py", acceptance)
        self.assertIn("acceptance", acceptance)


    def test_docs_limit_deterministic_checks_to_record_and_file_validation(self) -> None:
        combined = "\n".join(
            read(path)
            for path in (
                "SKILL.md",
                "references/review.md",
                "references/acceptance.md",
            )
        )

        self.assertIn("deterministic gates", combined)
        self.assertIn("never automatic proof", combined)
        self.assertIn("science/story consistency", combined)
