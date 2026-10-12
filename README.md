# life-model-writing

`life-model-writing` 是一个面向 Codex 的实验性 Skill：把日常生活中的社会现象、行为选择、人际关系和商业问题，转化为有理论依据、可复核机制和自然口播表达的中文文案。

当前版本重点支持经济学、博弈论、概率/数学建模、反馈与网络、存量—流量和扩散阈值等解释框架。它先重构问题，再比较候选理论，建立变量和因果链，检查反例与边界，最后输出一版中文长口播。它只负责生产文案，不负责生成视频。

当前发布标识：`v0.4.1-experimental`。`v0.4.2` 是后续评测批次名称，不代表本仓库已经发布了同名产品版本。

## 状态

这是公开实验版本，不是稳定的自动化内容生产服务。仓库中的结构校验和评测运行器可复现；高质量文案仍需要模型运行和独立人工/模型复核。历史基线中的内容评分尚未完成独立评分，因此不能把工程测试通过等同于内容质量通过。

## 当前证据（截至 2026-10-12）

- 已见主题的正式门槛评测通过：Skill 平均分 29.7，较对照高 5.1 分，10 个案例中 9 个胜出。详见 [`v0.4.1-run-2-report.md`](life-model-writing/evals/v0.4.1-run-2-report.md)。
- 未见主题的泛化评测得到 Skill 29.5、对照 27.6，优势为 1.9 分，但未达到预设的最小优势门槛。详见 [`v0.4.1-generalization-run-1-report.md`](life-model-writing/evals/v0.4.1-generalization-run-1-report.md)。
- 同提示词的理论必要性评测中，Skill 29.25、对照 29.0，优势仅 0.25 分；没有关键错误，但未通过优势和胜场门槛。详见 [`v0.4.2-theory-necessity-run-1-report.md`](life-model-writing/evals/v0.4.2-theory-necessity-run-1-report.md)。
- 20 题试跑中有 19/20 篇通过长度契约，1 篇为 793 字；该轮定性检查不是独立盲评，不能作为质量证明。详见 [`PILOT-REPORT.md`](life-model-writing/evals/runs/v0.4.1-pilot-run-1/PILOT-REPORT.md)。

这些证据支持“结构化流程在部分主题上有帮助”，不支持“Skill 对所有主题稳定优于普通大模型”的结论。

## 不适用范围

Skill 不替代医疗、法律、投资或心理诊断意见，也不应把模型推论写成这些领域的确定性结论。它不负责视频、配音、剪辑、发布或外部付费模型调用。

## 安装到个人 Codex Skills

### PowerShell

在仓库根目录执行：

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$destination = Join-Path $codexHome "skills\life-model-writing"
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Copy-Item -Recurse -Force .\life-model-writing\* $destination
```

### POSIX shell

```sh
codex_home="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$codex_home/skills/life-model-writing"
cp -R life-model-writing/. "$codex_home/skills/life-model-writing/"
```

安装后的标准位置是 `${CODEX_HOME}/skills/life-model-writing`；未设置 `CODEX_HOME` 时是 `~/.codex/skills/life-model-writing`。仓库内运行校验时直接使用 `life-model-writing/`，不需要复制第二份源码。

首次使用建议显式调用：

```text
$life-model-writing
微信群人越多，为什么越没人说话？请先完成问题建模和理论竞争，再给我一版标准长度中文口播。
```

本地安装不等于当前宿主一定支持自动发现。若自动发现没有触发，继续使用显式 `$life-model-writing`；不要把“文件已复制”当成运行验证。

需要更强理论参与时，可以在调用中加入：

```text
$life-model-writing
请从数学或理论模型角度解释这个现象。至少比较两个候选理论；至少明确一个变量关系、公式或可计算的条件预测；说明模型假设、反事实变化和不适用边界；最后转成自然中文口播。不要只罗列术语，也不要把模型推论写成无条件的社会事实。
```

## 示例问题

- 直接机制问题：`微信群人越多，为什么越没人说话？`
- 间接生活问题：`为什么免费活动报名很多，到场率却可能不高？`
- 边界压力问题：`请把一个团队效率低的问题写成口播，但不要为了显得专业堆砌理论。`

## 验证与评测

当前检查不需要第三方 Python 依赖：

```sh
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
```

评测运行器位于 `life-model-writing/scripts/`，案例、评分规则、历史基线位于 `life-model-writing/evals/`。运行产物默认写入被 Git 忽略的 `life-model-writing/evals/runs/`；不可变的发布证据应复制到 `evals/baselines/` 并保留 manifest、原始输出、检查结果和评分。

需要独立评审时，先生成一个不带既有分数和预期激活结论的盲评包：

```sh
python life-model-writing/scripts/create_review_packet.py --run-dir life-model-writing/evals/runs/<run-id> --skill-root life-model-writing --rubric life-model-writing/evals/rubric.json --output-dir life-model-writing-review
```

评审员把 score JSON 写入盲评包的 `scores/` 后，用导入器安全导回原始运行：

```sh
python life-model-writing/scripts/import_review_scores.py --run-dir life-model-writing/evals/runs/<run-id> --packet-dir life-model-writing-review --rubric life-model-writing/evals/rubric.json
python life-model-writing/scripts/score_eval_run.py --run-dir life-model-writing/evals/runs/<run-id> --rubric life-model-writing/evals/rubric.json
```

评审员必须把 `evaluator.independent` 设为 `true`；没有这个字段的结果只能保持未验证，已有评分也不会被覆盖。

## Skill 与基础模型各自贡献什么

Skill 提供入口边界、理论卡片、候选理论竞争、变量和机制链模板、反例/事实状态检查、口播长度契约以及可复现评测约束。基础模型仍负责自然语言理解、理论选择的实际判断、推理执行和最终措辞；外部检索或人工审阅若未实际发生，不能假定已经发生。

## 已知限制

- 当前评测器能验证结构、长度、事实/边界提示和评分汇总格式，不能仅靠静态检查证明一篇文案的理论正确性。
- 自动发现路径依赖 Codex 宿主环境，仓库本身不能在所有宿主中证明自动加载成功。
- 理论卡片提供候选框架，不是穷尽的学术数据库；关键事实和研究结论仍需单独核查。
- `evals/baselines/audit-2026-10-09/` 保留的是历史未独立评分基线，不能作为已通过的质量证明。
- 已见主题的优势不能直接外推到未见主题；当前泛化和同提示词评测都没有通过预设的优势门槛。
- 20 题试跑包含一篇长度不合格输出，且没有完成独立盲评；它是发现问题的试验，不是发布质量认证。

## 许可证

本项目使用 [Apache License 2.0](LICENSE)。发布或再分发时请保留许可证和版权声明。
