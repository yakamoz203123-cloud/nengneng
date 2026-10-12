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

    def test_spoken_conversion_contract_keeps_reasoning_internal(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        style_text = (ROOT / "references" / "spoken-script-style.md").read_text(
            encoding="utf-8"
        )

        for contract in (
            "口播转换门",
            "不得向用户暴露内部推理流程",
            "不得把 Skill 的内部结构写进最终文案",
            "变量关系",
            "反事实",
        ):
            self.assertIn(contract, skill_text)
        for contract in (
            "推理到口播的转换配方",
            "理论是隐形骨架",
            "先讲场景，再讲变化",
            "不宣布写作流程",
        ):
            self.assertIn(contract, style_text)

    def test_spoken_style_contract_requires_concrete_detail_and_limits_abstraction(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        style_text = (ROOT / "references" / "spoken-script-style.md").read_text(
            encoding="utf-8"
        )

        for contract in (
            "具体动作、数量、时间或对比",
            "不要连续两个以上段落只讲概念、模型或公式",
            "公式解释后必须落回具体情境",
        ):
            self.assertIn(contract, style_text)
        self.assertIn("口播自然度约束", skill_text)

    def test_standard_script_has_a_budgeted_compression_gate(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        style_text = (ROOT / "references" / "spoken-script-style.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("长度规划与压缩门", skill_text)
        for contract in (
            "950-1050",
            "一个主模型",
            "最多一个补充模型",
            "一个关键反事实",
            "超过 1200 字不得直接交付",
            "重复的边界声明",
            "第二个同义案例",
            "重复变量清单",
            "重复结论",
            "核心因果链",
        ):
            self.assertIn(contract, style_text)

    def test_structure_pattern_routes_length_details_to_single_reference(self):
        structure_text = (ROOT / "references" / "structure-patterns.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("[spoken-script-style.md](spoken-script-style.md)", structure_text)
        self.assertNotIn("短版为 400-600", structure_text)
        self.assertNotIn("长版为 1500-2200", structure_text)

    def test_pressure_scenarios_cover_over_explanation_regression(self):
        pressure_text = (ROOT / "evals" / "pressure-scenarios.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("场景 6：解释过度", pressure_text)
        self.assertIn("800-1200", pressure_text)
        self.assertIn("反事实", pressure_text)
        self.assertIn("重复", pressure_text)

    def test_evidence_contract_requires_numeric_and_population_consistency(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        fact_text = (ROOT / "references" / "fact-checking.md").read_text(
            encoding="utf-8"
        )
        misuse_text = (ROOT / "references" / "theory-misuse.md").read_text(
            encoding="utf-8"
        )
        for contract in (
            "数字自洽检查",
            "分母",
            "总体",
            "时间窗口",
            "比例存在不等于趋势存在",
        ):
            self.assertIn(contract, skill_text)
        for contract in (
            "数字—时间窗—流量自洽",
            "趋势判断",
            "数字能否支持结论",
        ):
            self.assertIn(contract, fact_text)
        for contract in ("例子内部数值不相容", "删除理论名称"):
            self.assertIn(contract, misuse_text)

    def test_v041_contract_compresses_theory_and_states_model_assumptions(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        style_text = (ROOT / "references" / "spoken-script-style.md").read_text(
            encoding="utf-8"
        )
        fact_text = (ROOT / "references" / "fact-checking.md").read_text(
            encoding="utf-8"
        )

        for contract in (
            "最小充分理论",
            "理论名称只在改变预测时保留",
            "不要把理论比较写成讲义段落",
            "数值例子必须交代前提",
        ):
            self.assertIn(contract, skill_text)
        for contract in (
            "理论比较压缩为几句服务因果链的话",
            "每段理论解释都必须回到人物选择或具体动作",
        ):
            self.assertIn(contract, style_text)
        for contract in (
            "分母、总体和时间窗口",
            "理想化假设",
            "物理量的适用条件",
        ):
            self.assertIn(contract, fact_text)

    def test_pressure_scenarios_cover_new_evidence_failure_modes(self):
        pressure_text = (ROOT / "evals" / "pressure-scenarios.md").read_text(
            encoding="utf-8"
        )

        for scenario in (
            "场景 7：数字自洽",
            "场景 8：无来源统计",
            "场景 9：装饰性理论",
        ):
            self.assertIn(scenario, pressure_text)

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
