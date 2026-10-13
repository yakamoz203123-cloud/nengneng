# Changelog

## V0.6 architecture upgrade — 2026-10-13 — experimental, unreleased

- 将 14 张理论卡重新定位为高频参考，不再把它们当作理论使用边界。
- 在生产 `SKILL.md` 中加入开放式理论发现、理论有效性审查、任务级临时理论卡和无可靠理论时拒绝强行套用的规则。
- 增加 `references/open-theory-discovery.md` 与 12 题 V0.6 压力测试合同；新增理论误用诊断标签，但没有伪造模型运行结果。
- 保持临时理论不自动写入长期知识库，不新增第三方依赖，不调用付费模型。
- 本轮为实验性架构升级，尚未证明优于旧版或精简提示词，也未创建稳定版发布标签。

## v0.4.1-experimental — 2026-10-12

- 补齐公开实验版的 README、证据说明和许可证入口；现有许可证为 Apache License 2.0。
- 记录已见主题、未见主题和同提示词理论必要性评测的真实结果，并明确未通过的门槛，不把局部优势包装成普遍优越性。
- 记录 20 题试跑的长度结果和非独立评审限制，作为后续回归的起点。
- 本次发布层补齐不修改 `SKILL.md`、理论卡、评测脚本或测试逻辑。

## Unreleased — experimental

- Added a 14-card theory library with candidate-selection and cross-disciplinary bridge fields.
- Added deterministic evaluation run creation, output import, checks, and rubric summaries.
- Added ten real content cases, activation cases, and an explicitly unverified historical baseline.
- Added clean-install validation, repository documentation, and Windows/Ubuntu CI.

This project is not yet a stable release. Content-quality claims require independent scoring of fresh model outputs.

## 2026-10-09 evidence note

- Added two v0.2 forward-run baselines. Both are explicitly marked unverified: one used the current Codex context with three smoke outputs, and the automatic-discovery run could not be exercised in the available host.
- Added a blinded review-packet generator so an independent evaluator can score fresh outputs without receiving prior scores or expected activation conclusions.
- Added guarded import of independent score JSON with rubric validation and no-overwrite protection.
