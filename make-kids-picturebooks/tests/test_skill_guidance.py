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

    def test_page_manifest_contract_and_final_acceptance_order_are_structural(self) -> None:
        records = read("references/page-records.md")
        acceptance = read("references/acceptance.md")

        self.assertIn(
            "每页保存正文版本、角色版本、稳定的 `character_reference_path`",
            records,
        )
        self.assertIn(
            '`previous_page_state`、`current_page_entry` 和 `next_page_hook` 都是且仅是 '
            '`{"state_id":"稳定状态标识","summary":"可核对的本页状态说明"}`',
            records,
        )
        self.assertIn(
            "相邻页中前页 `next_page_hook.state_id` 必须等于后页 "
            "`current_page_entry.state_id`",
            records,
        )
        self.assertIn(
            '`text_image_match` 和 `continuity_review` 都是且仅是 '
            '`{"status":"pending|passed|failed","evidence":"实际观察的证据"}`',
            records,
        )
        self.assertIn("不改 schema_version", records)
        self.assertIn(
            "最终顺序是：运行 `export_book.py` 到新的版本目录，它先生成 `reading.pdf` "
            "和 `print.pdf`，再用 `validate_exports.py` 验证这两份新 PDF；完成 "
            "human/model visual review 后，运行 `accept_book.py` 检查最终素材，所有检查通过后以 "
            "`--accept` 保存新 acceptance 记录。",
            acceptance,
        )

    def test_agent_metadata_avoids_unsupported_api_product(self) -> None:
        metadata = read("agents/openai.yaml")
        self.assertNotIn("\n  - api\n", metadata)
