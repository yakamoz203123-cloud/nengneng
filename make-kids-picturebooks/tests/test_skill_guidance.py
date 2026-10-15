from pathlib import Path
import json
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
        for term in ("可嵌入的TrueType", "可提取文字", "最低打印字号"):
            with self.subTest(term=term):
                self.assertIn(term, printing)
        for term in ("font-license.txt", "font-provenance.json"):
            with self.subTest(term=term):
                self.assertIn(term, acceptance)
        self.assertIn("validate_exports.py", acceptance)
        self.assertIn("export_book.py", acceptance)
        self.assertIn("acceptance", acceptance)


    def test_private_real_child_character_guidance_is_explicit(self) -> None:
        skill = read("SKILL.md")
        characters = read("references/characters.md")

        for term in ("真实儿童", "私有项目", "privacy_scope", "public_release"):
            with self.subTest(term=term):
                self.assertIn(term, skill + characters)
        self.assertIn("不进入 Skill 仓库或 GitHub", skill + characters)
        for term in ("pending", "不等于", "approved"):
            self.assertIn(term, skill + characters)


    def test_fast_image_generation_protocol_is_explicit(self) -> None:
        combined = "\n".join(
            read(path)
            for path in (
                "SKILL.md",
                "references/characters.md",
                "references/social-output.md",
            )
        )

        for term in (
            "快速出图协议",
            "production_reference_path",
            "先完成 `layout_design` 再调用图像生成器",
            "每页一次生成",
            "两页一批",
            "不要重复提交",
            "先检查已有结果",
            "稳定基础提示词",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)

    def test_production_queue_and_performance_protocol_are_explicit(self) -> None:
        combined = "\n".join(
            read(path)
            for path in (
                "SKILL.md",
                "references/production-workflow.md",
                "references/characters.md",
                "references/acceptance.md",
                "RELEASE.md",
            )
        )
        for term in (
            "generation_queue.py",
            "一次规划",
            "分阶段",
            "story.md",
            "storyboard.json",
            "max_in_flight",
            "默认 2",
            "2—3",
            "断点续跑",
            "缓存",
            "reset-page",
            "只重新生成该页",
            "一版完整成品",
            "不自动生成多套备选",
            "不接入新的付费图像接口",
            "总耗时",
            "失败率",
            "输出质量",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)


    def test_page_manifest_template_exposes_private_production_reference_slot(self) -> None:
        template = json.loads(read("assets/page-manifest-template.json"))
        page = template["pages"][0]

        self.assertEqual(
            page["production_reference_path"],
            "characters/v1/production-reference.png",
        )


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

    def test_layout_and_social_guidance_contract_is_explicit(self) -> None:
        skill = read("SKILL.md")
        composition = read("references/composition.md")
        art_direction = read("references/art-direction.md")
        printing = read("references/printing.md")
        acceptance = read("references/acceptance.md")
        social = read("references/social-output.md")
        combined = "\n".join(
            (skill, composition, art_direction, printing, acceptance, social)
        )

        for term in (
            "layout_design",
            "scene-integrated",
            "soft-card",
            "narrative-band",
            "图像不得生成文字",
            "生成前锁定文字安全区",
            "layout_review",
            "social-vertical-9x16",
            "1080×1920",
            "技术分层",
            "视觉融合",
            "不能声称自动审美通过",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)

        self.assertIn("layout_design", skill)
        self.assertIn("layout_review", acceptance)
        self.assertIn("social-vertical-9x16", social)

    def test_social_guidance_requires_portrait_full_bleed_and_in_scene_text(self) -> None:
        combined = "\n".join(
            read(path)
            for path in (
                "SKILL.md",
                "references/composition.md",
                "references/social-output.md",
            )
        )

        for term in (
            "portrait-full-bleed",
            "text_placement",
            "in-scene",
            "禁止横向条幅",
            "禁止底部通栏",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)

    def test_social_profiles_define_xiaohongshu_default_and_douyin_opt_in(self) -> None:
        skill = read("SKILL.md")
        readme = read("../README.md")
        rubric = read("evals/rubric.md")
        composition = read("references/composition.md")
        art_direction = read("references/art-direction.md")
        printing = read("references/printing.md")
        acceptance = read("references/acceptance.md")
        social = read("references/social-output.md")
        combined = "\n".join(
            (skill, readme, rubric, composition, art_direction, printing, acceptance, social)
        )

        for term in (
            "xiaohongshu-feed-3x4",
            "1080×1440",
            "小红书静态图文",
            "默认3:4",
            "social-vertical-9x16",
            "抖音/长屏",
            "不能把横向图塞入竖屏",
            "补大块空白",
            "两个 profile",
            "一次导出只绑定一个 profile",
            "分别建立 profile-specific 输出版本",
            "不直接缩放",
            "中心裁切",
            "`social_pages` 每条记录必须包含独立的 `layout_review`",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)

        for template_path in (
            "assets/page-manifest-template.json",
            "assets/book-template.json",
        ):
            template = json.loads(read(template_path))
            social_layout = template["pages"][0]["layout_design"]["social_layout"]
            self.assertEqual(social_layout["profile"], "xiaohongshu-feed-3x4")
            self.assertEqual(
                social_layout["canvas"], {"width_px": 1080, "height_px": 1440}
            )
            self.assertEqual(social_layout["source_aspect_ratio"], "3:4")
            self.assertEqual(
                social_layout["subject_safe_area"], [0.50, 0.20, 0.42, 0.54]
            )
            self.assertEqual(
                social_layout["text_safe_area"], [0.08, 0.12, 0.38, 0.24]
            )
            self.assertEqual(
                social_layout["composition_mode"], "portrait-full-bleed"
            )
            self.assertEqual(social_layout["text_placement"], "in-scene")

    def test_social_image_generation_requires_native_ratio_preflight(self) -> None:
        combined = "\n".join(
            read(path)
            for path in (
                "SKILL.md",
                "references/social-output.md",
                "references/acceptance.md",
            )
        )

        for term in (
            "preflight_image_generation.py",
            "image_generation_blocked",
            "实际尺寸",
            "不能缩放、中心裁切或补白",
            "先生成一张探针图",
        ):
            with self.subTest(term=term):
                self.assertIn(term, combined)

    def test_formal_evals_include_verified_layout_pressure_cases(self) -> None:
        prompts = read("evals/prompts.csv")
        rubric = read("evals/rubric.md")

        for case_id in (
            "layout_natural_whitespace",
            "layout_complex_background",
            "layout_long_copy",
            "layout_whole_book_one_shot",
            "layout_skip_visual_review",
        ):
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, prompts)

        self.assertIn("baseline", rubric)
        self.assertIn("不能把 baseline 结果", rubric)
