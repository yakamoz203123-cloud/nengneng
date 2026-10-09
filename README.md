# life-model-writing

`life-model-writing` 是一个面向 Codex 的实验性 Skill：把日常生活中的社会现象、行为选择、人际关系和商业问题，转化为有理论依据、可复核机制和自然口播表达的中文文案。

当前版本重点支持经济学、博弈论、概率/数学建模、反馈与网络、存量—流量和扩散阈值等解释框架。它先重构问题，再比较候选理论，建立变量和因果链，检查反例与边界，最后输出一版中文长口播。它只负责生产文案，不负责生成视频。

## 状态

这是公开实验版本，不是稳定的自动化内容生产服务。仓库中的结构校验和评测运行器可复现；高质量文案仍需要模型运行和独立人工/模型复核。历史基线中的内容评分尚未完成独立评分，因此不能把工程测试通过等同于内容质量通过。

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

## Skill 与基础模型各自贡献什么

Skill 提供入口边界、理论卡片、候选理论竞争、变量和机制链模板、反例/事实状态检查、口播长度契约以及可复现评测约束。基础模型仍负责自然语言理解、理论选择的实际判断、推理执行和最终措辞；外部检索或人工审阅若未实际发生，不能假定已经发生。

## 已知限制

- 当前评测器能验证结构、长度、事实/边界提示和评分汇总格式，不能仅靠静态检查证明一篇文案的理论正确性。
- 自动发现路径依赖 Codex 宿主环境，仓库本身不能在所有宿主中证明自动加载成功。
- 理论卡片提供候选框架，不是穷尽的学术数据库；关键事实和研究结论仍需单独核查。
- `evals/baselines/audit-2026-10-09/` 保留的是历史未独立评分基线，不能作为已通过的质量证明。
