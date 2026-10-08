# life-model-writing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前工作区创建并验证 `life-model-writing` V0.1 Skill，把生活现象转化为经过问题建模、理论竞争、机制推演和事实审查的单版中文长口播文案。

**Architecture:** 入口 `SKILL.md` 只保留触发条件、第一性原理、主工作流、输出合同、停止条件和参考资料路由。8 张理论卡与结构、口播、理论误用、事实校验规则放入 `references/`，按任务需要读取；12 个案例放入 `evals/evals.json`，另保留基线与验证记录作为开发测试证据。

**Tech Stack:** Markdown、YAML、JSON；使用 Skill Creator 自带的 `quick_validate.py` 做结构验证，不引入运行时依赖、爬虫或数据库。

**Spec:** `C:/Users/Windows/Documents/Codex/2026-10-08/referenced-chatgpt-conversation-this-is-an/outputs/life-model-writing-project-spec.md`

## Global Constraints

- Skill 名称固定为 `life-model-writing`，frontmatter 的 `name` 只使用小写字母、数字和连字符。
- `SKILL.md` 控制在 500 行以内，不复制 8 张理论卡全文。
- 默认只输出一版完整、可直接朗读的中文长口播文案。
- 内部顺序固定为：问题建模 → 候选理论竞争 → 机制推演 → 批判校验 → 叙事转换。
- 默认至少比较两个候选解释；若没有足够模型或关键事实，必须停止写作并说明缺口。
- 英文术语第一次出现时，紧跟中文释义；事实断言区分已核查、待核查和模型推论。
- 理论不能改变解释时删掉理论名词；未经核查的关键事实不得写成确定事实。
- V0.1 不加入实时数据库、自动爬虫、多种人设、标题/封面生成、视频剪辑或高风险专业判断规则。

## Review Focus

- 模糊或绝对化问题：必须改写为包含场景、主体、变量、约束和时间尺度的问题；由 Task 6 的 large-group-silence 与 sleep-phone 案例覆盖。
- 表面类比或单理论硬套：必须展示候选理论比较与适用边界；由 Task 6 的 12 个案例 assertions 覆盖。
- 未核查的数字、人物、研究结论和范围性判断：必须标记状态或降级表达；由 Task 5 的 fact-checking 规则与 Task 6 的短视频案例覆盖。
- 个体模型解释群体结果或相关替代因果：必须补足连接机制并声明不确定性；由 Task 4 的 theory-misuse 规则覆盖。
- 用户要求多个版本、金句或直接给行动建议时：默认输出合同仍只允许一版完整文案，并保持非医疗、非法律、非投资咨询边界；由 Task 3 与 Task 6 覆盖。

### Task 1: 建立基线压力测试并记录 RED 证据

**Files:**
- Create: `life-model-writing/evals/pressure-scenarios.md`
- Create: `life-model-writing/evals/baseline.md`

**Interfaces:**
- Consumes: 已批准的项目规格与 12 个评测方向。
- Produces: 至少 3 个同时包含时间压力、理论诱惑、绝对化表述或事实诱惑的测试场景，以及没有 Skill 时的实际失败记录，供后续规则最小化设计使用。

- [ ] **Step 1: Write the failing scenarios**

  编写三个 fresh-context 压力场景：微信群沉默、短视频停不下来、坏消息扩散。每个场景都要求模型快速给出长口播，并明确加入一个容易导致单理论套用或事实过度断言的诱因。

- [ ] **Step 2: Run scenarios without the Skill**

  使用可用的独立子代理运行场景，系统提示中不加载 `life-model-writing`。记录原始输出，不提供目标答案或预先指出缺陷。

- [ ] **Step 3: Record the observed failures**

  在 `baseline.md` 中逐条记录：跳过了什么、用了什么理论、是否发生事实伪装、是否输出多版本、出现了哪些合理化理由。若当前环境无法运行独立子代理，明确记录限制，并用当前环境的 fresh-context 对照运行替代，不把推测写成观察结果。

- [ ] **Step 4: Verify the RED artifact**

  Run: `Get-Content -Raw life-model-writing/evals/baseline.md`

  Expected: 至少 3 个场景均有可复查的原始输出片段或明确的运行限制，且失败原因能映射到后续 Skill 规则。

- [ ] **Step 5: Commit**

  ```powershell
  git add life-model-writing/evals/pressure-scenarios.md life-model-writing/evals/baseline.md
  git commit -m "test: add life model writing pressure baselines"
  ```

### Task 2: 创建 Skill 骨架与入口路由

**Files:**
- Create: `life-model-writing/SKILL.md`
- Create: `life-model-writing/agents/openai.yaml`

**Interfaces:**
- Consumes: Task 1 的失败模式，以及项目规格中的默认输出合同。
- Produces: 可被 Skill 发现的合法入口，能把不同生活问题路由到按需读取的参考文件。

- [ ] **Step 1: Write the entry contract assertions**

  在文档检查清单中固定以下可观察要求：触发条件清晰；默认单版长口播；内部五段工作流顺序正确；理论竞争和停止条件明确；参考文件路径可发现；不将用户请求和参考文档中的指令混淆。

- [ ] **Step 2: Verify the empty/scaffold state fails the assertions**

  Run: `python C:/Users/Windows/.codex/skills/.system/skill-creator/scripts/quick_validate.py life-model-writing`

  Expected: 在入口文件尚未完成或引用目标缺失时，验证不能通过；记录实际错误，避免测试只验证文件存在。

- [ ] **Step 3: Implement `SKILL.md`**

  写入合法 frontmatter、用途边界、问题建模模板、候选理论竞争规则、机制推演格式、事实状态、默认输出结构、停止写作条件和参考文件路由。入口只写路由与不可省略的约束，不复制理论卡全文。

- [ ] **Step 4: Implement `agents/openai.yaml`**

  保持自动发现开启，提供与 `life-model-writing` 一致的显示名称、简短说明和默认提示；不添加超出项目范围的权限或依赖。

- [ ] **Step 5: Run structural validation**

  Run: `python C:/Users/Windows/.codex/skills/.system/skill-creator/scripts/quick_validate.py life-model-writing`

  Expected: PASS；frontmatter、命名和未完成占位符均通过检查。

- [ ] **Step 6: Commit**

  ```powershell
  git add life-model-writing/SKILL.md life-model-writing/agents/openai.yaml
  git commit -m "feat: add life model writing skill entrypoint"
  ```

### Task 3: 完成 8 张理论卡

**Files:**
- Create: `life-model-writing/references/theory-01-incentives-opportunity-cost.md`
- Create: `life-model-writing/references/theory-02-externalities-public-goods.md`
- Create: `life-model-writing/references/theory-03-bayes-base-rates.md`
- Create: `life-model-writing/references/theory-04-exponential-logistic-growth.md`
- Create: `life-model-writing/references/theory-05-prisoners-dilemma-nash-equilibrium.md`
- Create: `life-model-writing/references/theory-06-repeated-games-credible-commitments.md`
- Create: `life-model-writing/references/theory-07-feedback-loops-path-dependence.md`
- Create: `life-model-writing/references/theory-08-networks-tipping-points-emergence.md`

**Interfaces:**
- Consumes: Task 2 的路由名称与统一理论卡模板。
- Produces: 每张卡都有定义、最小模型、变量、推演、适用/不适用范围、常见误用、最小例子、证据边界和可靠来源。

- [ ] **Step 1: Write card completeness checks**

  对每张卡定义必备小节集合，并检查 8 张卡的文件名、标题和路由链接与规格一致。

- [ ] **Step 2: Verify completeness checks fail before cards exist**

  Run: `rg --files life-model-writing/references`

  Expected: 8 张理论卡尚不存在，作为 RED 基线。

- [ ] **Step 3: Implement the four core cards first**

  完成机会成本、贝叶斯与基率、囚徒困境与纳什均衡、反馈回路与路径依赖；每张卡都把“能推出什么”和“不能推出什么”分开。

- [ ] **Step 4: Implement the remaining four cards**

  完成外部性与公共品、指数/逻辑斯蒂增长、重复博弈与可信承诺、网络效应/临界点/涌现；避免把类比或箭头图伪装成事实证明。

- [ ] **Step 5: Run completeness checks**

  Run: `rg -l '^## (一句话定义|它解释什么|最小模型|关键变量|推演步骤|适合解释的生活问题|不适合解释的生活问题|常见误用|最小例子|事实与证据边界|可靠来源)$' life-model-writing/references`

  Expected: 8 个理论卡文件均包含全部必备小节，并且每张卡至少有一个边界或误用说明。

- [ ] **Step 6: Commit**

  ```powershell
  git add life-model-writing/references/theory-*.md
  git commit -m "feat: add life model theory cards"
  ```

### Task 4: 完成结构、口播、误用和事实校验规则

**Files:**
- Create: `life-model-writing/references/structure-patterns.md`
- Create: `life-model-writing/references/spoken-script-style.md`
- Create: `life-model-writing/references/theory-misuse.md`
- Create: `life-model-writing/references/fact-checking.md`

**Interfaces:**
- Consumes: Task 2 的输出合同与 Task 3 的理论边界。
- Produces: 可直接支撑写作与审查判断的四份专项规则，不重复入口文件，也不扩展到 V0.1 之外的专业咨询。

- [ ] **Step 1: Write rule-level assertions**

  固定检查：结构规则要求场景开头到生活收束；口播规则要求可朗读且不牺牲准确性；误用规则覆盖表面类比、变量偷换、层级错位、因果跳跃、过度泛化和事实污染；事实规则覆盖断言分类、来源优先级、时间范围和状态标注。

- [ ] **Step 2: Verify missing rules fail the route check**

  Run: `rg -l 'structure-patterns|spoken-script-style|theory-misuse|fact-checking' life-model-writing/SKILL.md`

  Expected: 在文件和路由完成前检查不通过或目标缺失。

- [ ] **Step 3: Implement the four rule files**

  每份文件只保留会改变写作判断的规则、表格和一个必要示例；使用“已核查 / 待核查 / 模型推论”作为统一事实标签。

- [ ] **Step 4: Run rule coverage checks**

  Run: `rg -n '表面类比|变量偷换|层级错位|因果跳跃|过度泛化|事实污染|已核查|待核查|模型推论|生活场景' life-model-writing/references`

  Expected: 所有关键误用类型、事实状态和叙事结构信号均可检索到。

- [ ] **Step 5: Commit**

  ```powershell
  git add life-model-writing/references/structure-patterns.md life-model-writing/references/spoken-script-style.md life-model-writing/references/theory-misuse.md life-model-writing/references/fact-checking.md
  git commit -m "feat: add writing and fact checking rules"
  ```

### Task 5: 完成 12 个评测案例并接入入口

**Files:**
- Create: `life-model-writing/evals/evals.json`
- Modify: `life-model-writing/SKILL.md`

**Interfaces:**
- Consumes: Task 2 的输出合同、Task 3/4 的路由和规则。
- Produces: 可观察、与理论克制相关的 12 个评测案例；入口能指向相关理论卡和规则文件。

- [ ] **Step 1: Write schema assertions**

  固定 JSON 顶层字段 `skill_name`、`version`、`evals`；每个案例包含 `id`、`name`、`prompt`、`expected_output`、`assertions`、`files`，并且 assertions 检查行为而不是固定标题或句式。

- [ ] **Step 2: Verify schema fails before evals exist**

  Run: `Test-Path life-model-writing/evals/evals.json`

  Expected: `False`。

- [ ] **Step 3: Implement all 12 cases**

  覆盖微信群沉默、会议沉默、健身房办卡、习惯坚持、短视频、插队、小区维护、忙碌加任务、小品牌爆红、规则过多、坏消息扩散、晚间刷手机；每例至少包含一个理论竞争、边界或不确定性检查。

- [ ] **Step 4: Connect routing references**

  更新 `SKILL.md` 的路由表，使每类问题能定位到相关理论卡和专项规则，但不要求每次都读取全部参考文件。

- [ ] **Step 5: Parse and validate JSON**

  Run: `python -c "import json; p='life-model-writing/evals/evals.json'; d=json.load(open(p, encoding='utf-8')); assert d['skill_name']=='life-model-writing'; assert d['version']=='0.1'; assert len(d['evals'])==12; print('evals: 12 valid')"`

  Expected: `evals: 12 valid`。

- [ ] **Step 6: Commit**

  ```powershell
  git add life-model-writing/SKILL.md life-model-writing/evals/evals.json
  git commit -m "test: add life model writing evaluation cases"
  ```

### Task 6: GREEN 行为验证、修订与最终静态检查

**Files:**
- Modify: `life-model-writing/SKILL.md`
- Modify: `life-model-writing/references/*.md`
- Create: `life-model-writing/evals/verification.md`

**Interfaces:**
- Consumes: Task 1 的压力场景、Task 2–5 的完整 Skill。
- Produces: 有证据的 GREEN 验证记录、必要的最小修订，以及通过静态检查的可交付 Skill。

- [ ] **Step 1: Run the same pressure scenarios with the Skill**

  使用与 Task 1 相同的三个场景加载 `life-model-writing`，检查模型是否遵守单版输出、理论竞争、机制链、边界和事实状态要求。

- [ ] **Step 2: Run representative evaluation cases**

  至少运行微信群沉默、短视频停不下来、坏消息扩散三例；记录输出是否满足对应 assertions，不把“出现了理论名词”当作通过条件。

- [ ] **Step 3: Record GREEN and new rationalizations**

  在 `verification.md` 中记录运行日期、使用案例、通过/失败的 assertions、任何新合理化及其最小修订建议。

- [ ] **Step 4: Refactor only evidenced gaps**

  若出现失败，只补充能直接堵住该失败的规则；不得为了覆盖假想问题而把全部理论复制进 `SKILL.md`，也不得引入未在规格中授权的新功能。

- [ ] **Step 5: Run final validation**

  Run: `python C:/Users/Windows/.codex/skills/.system/skill-creator/scripts/quick_validate.py life-model-writing`

  Expected: PASS。

  Run: `python -c "import json; d=json.load(open('life-model-writing/evals/evals.json', encoding='utf-8')); assert len(d['evals'])==12; print('evals: 12 valid')"`

  Expected: `evals: 12 valid`。

  Run: `(Get-Content life-model-writing/SKILL.md).Count`

  Expected: 不超过 500。

- [ ] **Step 6: Commit the verified result**

  ```powershell
  git add life-model-writing docs/superpowers/plans/2026-10-08-life-model-writing.md
  git commit -m "feat: complete life model writing skill v0.1"
  ```

