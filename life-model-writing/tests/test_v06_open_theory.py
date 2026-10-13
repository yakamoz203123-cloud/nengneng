import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class V06OpenTheoryContractTests(unittest.TestCase):
    def test_production_skill_allows_open_discovery_and_problem_dependent_theory_count(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for contract in (
            "开放式理论发现",
            "理论有效性",
            "临时理论卡",
            "理论数量由问题决定",
            "拒绝强行套用",
            "外部检索不可用",
            "一个理论",
            "不使用正式理论",
        ):
            self.assertIn(contract, skill_text)

        self.assertNotIn("至少提出两个候选解释", skill_text)
        self.assertIn("references/open-theory-discovery.md", skill_text)

    def test_open_theory_reference_defines_minimum_temporary_card_and_evidence_states(self):
        reference = ROOT / "references" / "open-theory-discovery.md"
        self.assertTrue(reference.is_file())
        text = reference.read_text(encoding="utf-8")

        for field in (
            "理论名称",
            "所属学科",
            "解释对象",
            "核心机制",
            "关键变量",
            "必要假设",
            "适用条件",
            "常见误用",
            "可区分的预测",
            "证据与来源状态",
            "当前验证结果",
            "本次使用理由",
        ):
            self.assertIn(field, text)

        for state in ("已核查", "模型已有知识", "待核查", "证据不足"):
            self.assertIn(state, text)

        self.assertIn("不得自动写入 references/", text)

    def test_taxonomy_has_open_discovery_failure_tags(self):
        taxonomy = json.loads(
            (ROOT / "evals" / "error-taxonomy.json").read_text(encoding="utf-8")
        )
        tags = {item["id"] for item in taxonomy["tags"]}

        self.assertIn("theory_mismatch", tags)
        self.assertIn("unsupported_theory", tags)
        self.assertIn("theory_mismatch", set(taxonomy["blocking_tags"]))

    def test_v06_pressure_pack_covers_six_required_families(self):
        cases_path = ROOT / "evals" / "v0.6-open-theory-cases.json"
        self.assertTrue(cases_path.is_file())
        data = json.loads(cases_path.read_text(encoding="utf-8"))

        self.assertEqual(data["version"], "0.6")
        self.assertEqual(len(data["evals"]), 12)
        families = {case["family"] for case in data["evals"]}
        self.assertTrue(
            {
                "in_library",
                "out_of_library",
                "theory_misuse",
                "quantitative",
                "evidence_insufficient",
                "value_judgment",
            }.issubset(families)
        )
        self.assertEqual(
            len({case["id"] for case in data["evals"]}),
            len(data["evals"]),
        )
        for case in data["evals"]:
            self.assertTrue(case["prompt"].strip())
            self.assertTrue(case["expected_risk"].strip())

    def test_precision_gate_covers_quantitative_metric_identity_and_units(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        fact_checking = (ROOT / "references" / "fact-checking.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("阻力、功率、能量和单位距离能耗", skill_text)
        self.assertIn("若题目问单位距离能耗，必须明确写出", skill_text)
        self.assertIn("若文案讨论油耗或电耗，必须同时出现单位距离", skill_text)
        self.assertIn("功率不能替代单位距离能耗", fact_checking)
        self.assertIn("单位和量纲", fact_checking)

    def test_precision_gate_blocks_public_good_and_value_judgment_shortcuts(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        misuse = (ROOT / "references" / "theory-misuse.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("仅仅多人受益不等于公共品", skill_text)
        self.assertIn("未完成这组核验前，不得把现象直接命名为公共品", skill_text)
        self.assertIn("若未核验非排他性和非竞争性，不得使用公共品", skill_text)
        self.assertIn("价值判断不能伪装成唯一最优解", skill_text)
        self.assertIn("一定、必然、所有", misuse)
        self.assertIn("条件性表达", misuse)


if __name__ == "__main__":
    unittest.main()
