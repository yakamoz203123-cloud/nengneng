# Changelog

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
