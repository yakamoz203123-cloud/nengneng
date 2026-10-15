# 绘本图文融合与审美排版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持可提取文字和字体验收的前提下，为每页增加可执行的图文融合版式设计、三种文字处理模式和审美审核门，使图片与字幕在视觉上成为同一页绘本场景。

**Architecture:** 以 `scripts/layout_design.py` 作为版式契约和审查字段的唯一验证入口；`page-manifest.json` 保存版式计划，`layout.json` 保存排版执行副本，验收时要求二者一致。`scripts/layout_styles.py` 负责固定调色板和三种可打印文字样式，`render_book.py` 只负责调用样式并继续输出图片层与可提取文字层；人工/模型视觉审核负责判断脸部、道具、焦点和审美节奏，脚本不冒充自动审美证明。

**Tech Stack:** Python 3.10+, unittest, ReportLab, Pillow, pypdf, fontTools, PyMuPDF；沿用当前 `schema_version: 1` 和现有 PDF 导出流程。

**Spec:** `docs/superpowers/specs/2026-10-15-aesthetic-picturebook-layout-design.md`

## Global Constraints

- 保持 `schema_version: 1`，新增字段采用附加对象，不破坏旧文件读取。
- 不把中文正文烘焙进插画；PDF 文字必须继续可提取、可嵌入字体并可校验。
- 默认正文字号保持 22 pt，打印质量保持 300 DPI；不降低现有字体、尺寸、页数和拼版门槛。
- 三种模式固定为 `scene-integrated`、`soft-card`、`narrative-band`；模式与 `text_treatment` 必须一一对应。
- 规划阶段可以使用 `pending`；进入 `digital_checked` 前必须有完整 `layout_design` 和逐页 `layout_review`。
- 旧版布局可以读取和重新导出，但没有新版版式字段时不能直接验收为 `digital_checked`。
- 脚本只验证结构、几何、文字和文件条件；视觉焦点、遮挡、可读性和整册审美仍需要人工或模型复核。
- 印刷版与社媒版使用同一故事正文和角色设定，但社媒版必须单独按 `social-vertical-9x16` 竖屏画布渲染；禁止未经审查把印刷页中心强裁成竖屏。
- 第一版社媒输出固定为 `1080×1920`，逐页使用归一化主体安全区和文字安全区；比例不符、关键对象越界或字幕溢出时必须拒绝导出。
- 平台界面遮挡只抽象为可配置的顶部/底部通用避让区，不在 Skill 中写死某个平台永久不变的 UI 规则。
- 用户书籍、儿童资料、角色参考和生成项目资产不得写入 Skill 源码或公开包。
- 新版包版本提升到 `0.10.0-preview` 或下一明确迭代版本，并同步 README、RELEASE、CI 和 ZIP 文件名。

## Review Focus

- **自然留白背景图**：背景文字重叠只有在 `text_area_reviewed` 通过且版式模式为 `scene-integrated` 时允许；需有渲染和清单测试。
- **复杂背景图**：必须切换到 `soft-card` 或 `narrative-band`，并使用批准的 `palette_token`；缺参数必须拒绝。
- **长中文正文**：实际排版行数超过 `max_lines` 或带内边距后溢出时，导出必须失败而不是缩小字体。
- **旧版布局**：缺少版式对象仍可读取，但完成验收必须明确失败并给出迁移提示。
- **清单/版面漂移**：`page-manifest.json` 与 `layout.json` 的版式、文字区域或正文不一致时，验收必须拒绝。
- **审美证据空泛**：`layout_review` 缺失、失败或只有“已检查/效果良好”等空泛证据时，不得升级数字完成状态。
- **社媒竖屏适配**：社媒页必须是 `1080×1920`，人物和知识焦点在主体安全区，字幕在文字安全区；印刷页不能直接中心裁切冒充社媒版。

---

### Task 1: 建立版式行为 RED 基线和测试夹具

**Files:**
- Create: `make-kids-picturebooks/evals/layout-pressure-prompts.csv`
- Create: `make-kids-picturebooks/evals/results/layout-baseline-evidence.md`

**Interfaces:**
- Consumes: 当前分支的 `SKILL.md`、`references/composition.md`、现有 eval 规则。
- Produces: 可重复的图文融合压力场景、失败行为记录和后续回归测试名称；不修改生产版式逻辑。

- [ ] **Step 1: Write the failing behavior scenarios**

  增加至少五个场景，分别覆盖自然留白、复杂背景、长正文、用户要求一次生成整本、用户要求跳过视觉检查。每个场景都要求模型说明是否暂停、采用哪种版式模式、是否能声称完成。

- [ ] **Step 2: Run the scenarios against the current Skill before editing it**

  使用当前已安装 Skill 和独立临时项目运行场景，记录实际输出。至少捕获一次“文字贴在图下方/未规划留白”或“没有审美证据仍声称通过”的失败；若某场景没有失败，保留为负控并从评测中移除或改成真正能区分行为的场景。

- [ ] **Step 3: Record the baseline without prescribing the fix**

  在 `layout-baseline-evidence.md` 记录每个场景的输入、关键输出、违规行为和失败原因，不把预期方案提前写进模型提示。

  该任务不修改静态指导测试；`test_skill_guidance.py` 的新增断言和文档同步由 Task 5 统一负责。

- [ ] **Step 4: Run the existing deterministic tests**

  Run: `python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -q`

  Expected: 当前基线仍为 `147 tests`、`1 skipped`、`OK`；新增行为场景的失败证据独立保存，不得以改生产代码掩盖。

- [ ] **Step 5: Commit the RED baseline**

  ```bash
  git add make-kids-picturebooks/evals/layout-pressure-prompts.csv make-kids-picturebooks/evals/results/layout-baseline-evidence.md
  git commit -m "test: capture aesthetic layout baseline failures"
  ```

### Task 2: 实现版式数据契约和确定性验证器

**Files:**
- Create: `make-kids-picturebooks/scripts/layout_design.py`
- Create: `make-kids-picturebooks/tests/test_layout_design.py`
- Modify: `make-kids-picturebooks/scripts/validate_page_manifest.py`
- Test: `make-kids-picturebooks/tests/test_page_manifest.py`

**Interfaces:**
- Consumes: 每页可选的 `layout_design` 对象和 `require_images` 完成模式。
- Produces: `validate_layout_design(value: dict | None, require_complete: bool = False) -> list[str]`、`validate_layout_review(value: dict | None, require_complete: bool = False) -> list[str]`；验证器返回稳定的中文错误列表，供页面清单和验收脚本复用。

- [ ] **Step 1: Write failing validator tests**

  在 `test_layout_design.py` 先写以下测试：

  - `test_planning_allows_missing_layout_design`
  - `test_completion_requires_layout_design`
  - `test_rejects_unknown_layout_mode`
  - `test_rejects_mismatched_layout_mode_and_text_treatment`
  - `test_rejects_nonpositive_max_lines`
  - `test_requires_specific_focal_point_and_safe_area_on_completion`
  - `test_requires_complete_layout_review_on_completion`
  - `test_rejects_generic_layout_review_evidence`
  - `test_accepts_valid_social_layout`
  - `test_rejects_social_layout_out_of_bounds`
  - `test_rejects_social_layout_with_wrong_aspect_ratio`

- [ ] **Step 2: Run only the new validator tests to verify RED**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_layout_design.py -v`

  Expected: FAIL because `layout_design.py` and the exported validator functions do not yet exist.

- [ ] **Step 3: Implement `layout_design.py`**

  定义固定枚举和模式配对表；`validate_layout_design` 在规划模式下允许缺失，在完成模式下要求 `layout_style_version`、模式、锚点、处理方式、行数、焦点、安全区、避让对象、节奏、调色板、状态和完整的 `social_layout`；`validate_layout_review` 要求 `status`、具体证据、关系类型、对比度、焦点状态、遮挡状态和节奏理由，并拒绝通用占位证据。社媒验证固定检查 `social-vertical-9x16`、`1080×1920`、归一化安全区和 `9:16` 比例声明。

- [ ] **Step 4: Integrate the validator into page manifest validation**

  在 `validate_page_manifest()` 每页校验 `layout_design`；`require_images=False` 使用规划模式，`require_images=True` 使用完成模式。保留现有 `text_area`、连续性、图片路径和知识检查行为。

- [ ] **Step 5: Run the focused tests to verify GREEN**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_layout_design.py make-kids-picturebooks/tests/test_page_manifest.py -v`

  Expected: 新测试和页面清单回归测试全部 PASS。

- [ ] **Step 6: Commit the contract**

  ```bash
  git add make-kids-picturebooks/scripts/layout_design.py make-kids-picturebooks/scripts/validate_page_manifest.py make-kids-picturebooks/tests/test_layout_design.py make-kids-picturebooks/tests/test_page_manifest.py
  git commit -m "feat: add aesthetic layout contract validation"
  ```

### Task 3: 实现三种可打印文字样式和社媒竖屏渲染

**Files:**
- Create: `make-kids-picturebooks/scripts/layout_styles.py`
- Create: `make-kids-picturebooks/scripts/render_social.py`
- Create: `make-kids-picturebooks/tests/test_layout_styles.py`
- Create: `make-kids-picturebooks/tests/test_render_social.py`
- Modify: `make-kids-picturebooks/scripts/render_book.py`
- Test: `make-kids-picturebooks/tests/test_render_book.py`

**Interfaces:**
- Consumes: 已通过 `validate_layout_design` 的 `layout_design`、文字框毫米坐标、社媒归一化安全区和 ReportLab/Pillow 画布。
- Produces: `draw_text_block(canvas, lines, box_pt, font_name, font_size, leading, style) -> None`、`render_social_page(page, output_path, profile="social-vertical-9x16") -> Path`；固定调色板和样式参数只在 `layout_styles.py` 定义，渲染器不复制颜色常量。

- [ ] **Step 1: Write failing rendering tests**

  在 `test_layout_styles.py`/`test_render_book.py` 增加：

  - `test_scene_integrated_keeps_text_extractable_without_panel`
  - `test_soft_card_renders_panel_and_extractable_text`
  - `test_narrative_band_renders_panel_and_extractable_text`
  - `test_invalid_palette_token_is_rejected`
  - `test_soft_card_padding_still_fits_inside_safe_box`
  - `test_layout_mode_requires_layout_design_for_export`
  - `test_social_renderer_outputs_1080x1920`
  - `test_social_renderer_rejects_non_9x16_source`
  - `test_social_renderer_rejects_text_outside_safe_area`

  断言 PDF 仍能提取正文、字体仍嵌入、页尺寸不变，并通过 PDF 内容或渲染像素检查确认文字卡/叙事带确实被绘制。

- [ ] **Step 2: Run focused rendering tests to verify RED**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_layout_styles.py make-kids-picturebooks/tests/test_render_book.py -v`

  Expected: FAIL because the style module and style-aware rendering path do not yet exist.

- [ ] **Step 3: Implement fixed printable style definitions**

  在 `layout_styles.py` 定义 `warm-paper`、`cool-sky`、`soft-leaf` 三个批准调色板，统一文字色、面板色、内边距和圆角；`scene-integrated` 不绘制面板，`soft-card` 在 `text_box_mm` 外框内绘制圆角浅色面板，`narrative-band` 绘制连续浅色叙事带。面板使用不依赖透明度的可打印浅色填充，保证 PDF/打印机一致性。

- [ ] **Step 4: Integrate styles into `render_book.py`**

  导出前验证每页 `layout_design`；将毫米文字框转换为点后调用 `draw_text_block`；对 `soft-card` 和 `narrative-band` 为正文保留固定内边距，并用内缩后的可用宽高执行现有溢出检查；不改变图片绘制、字体嵌入、文字提取、覆盖输出保护和有效 DPI检查。

- [ ] **Step 5: Implement `render_social.py`**

  使用 Pillow 生成 `1080×1920` 的逐页 PNG/JPEG；按 `social_layout` 的相对坐标绘制源图和字幕，拒绝非 `9:16` 源图、越过安全区的字幕和超出画布的元素，不默认中心裁切印刷页。社媒栅格输出不替代印刷 PDF 的可提取文字层。

- [ ] **Step 6: Run focused tests to verify GREEN**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_layout_styles.py make-kids-picturebooks/tests/test_render_book.py make-kids-picturebooks/tests/test_render_social.py -v`

  Expected: 新样式测试、旧渲染测试全部 PASS；任何字号、图片、字体或文字溢出回归必须先修复。

- [ ] **Step 7: Commit the rendering feature**

  ```bash
  git add make-kids-picturebooks/scripts/layout_styles.py make-kids-picturebooks/scripts/render_social.py make-kids-picturebooks/scripts/render_book.py make-kids-picturebooks/tests/test_layout_styles.py make-kids-picturebooks/tests/test_render_social.py make-kids-picturebooks/tests/test_render_book.py
  git commit -m "feat: render integrated print and social layouts"
  ```

### Task 4: 接入清单、验收和项目状态

**Files:**
- Modify: `make-kids-picturebooks/scripts/accept_book.py`
- Modify: `make-kids-picturebooks/assets/book-template.json`
- Modify: `make-kids-picturebooks/assets/page-manifest-template.json`
- Modify: `make-kids-picturebooks/tests/test_acceptance.py`
- Modify: `make-kids-picturebooks/tests/test_project_state.py`

**Interfaces:**
- Consumes: Task 2 的 `validate_layout_design`/`validate_layout_review`、Task 3 的 `layout.json` 和社媒渲染结果。
- Produces: `check_book()` 对版式副本、审核证据和完成状态提供确定性错误；模板提供包含 `layout_design` 的可执行示例，而不是旧的单页占位结构。

- [ ] **Step 1: Write failing acceptance tests**

  增加：

  - `test_acceptance_rejects_missing_layout_design`
  - `test_acceptance_rejects_manifest_layout_mismatch`
  - `test_acceptance_rejects_missing_layout_review`
  - `test_acceptance_rejects_generic_layout_review_evidence`
  - `test_acceptance_rejects_missing_social_layout`
  - `test_acceptance_rejects_social_render_profile_mismatch`
  - `test_planning_fixture_remains_readable_but_not_digitally_complete`

  更新测试夹具，为可通过的完整页提供真实结构化 `layout_design` 和 `layout_review`，不使用单一“synthetic test only”替代版式证据。

- [ ] **Step 2: Run acceptance tests to verify RED**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_acceptance.py make-kids-picturebooks/tests/test_project_state.py -v`

  Expected: 新增测试 FAIL，原有 acceptance fixture 因缺字段暴露需要迁移的接口。

- [ ] **Step 3: Integrate acceptance checks**

  在 `check_book()` 中：

  1. 对 layout 和 manifest 分别验证版式对象；
  2. 对 `layout_design`、`text_box_mm` 和正文执行逐页一致性比较；
  3. 从 `review.json.reading_pages[*].layout_review` 校验完整版式审核；
  4. 发现任一缺失或失败时阻止 `--accept`；
  5. 对社媒输出检查 `1080×1920`、源图比例、安全区和渲染文件存在性；
  6. 为旧项目返回明确的迁移错误，不把旧项目标成损坏到无法读取。

- [ ] **Step 4: Update templates**

  `book-template.json` 使用一页可执行的 `scene-integrated` 示例并包含版式字段；`page-manifest-template.json` 包含完整 `layout_design` 结构和 `pending` 审核记录，同时保留规划时允许空图片路径的行为。

- [ ] **Step 5: Run focused tests to verify GREEN**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_acceptance.py make-kids-picturebooks/tests/test_project_state.py make-kids-picturebooks/tests/test_layout_design.py -v`

  Expected: 所有验收和状态测试 PASS；旧项目只在明确完成门处被挡，不影响读取和重新规划。

- [ ] **Step 6: Commit acceptance integration**

  ```bash
  git add make-kids-picturebooks/scripts/accept_book.py make-kids-picturebooks/assets/book-template.json make-kids-picturebooks/assets/page-manifest-template.json make-kids-picturebooks/tests/test_acceptance.py make-kids-picturebooks/tests/test_project_state.py
  git commit -m "feat: gate picturebook acceptance on layout review"
  ```

### Task 5: 更新 Skill 指令、参考规则和行为评测

**Files:**
- Modify: `make-kids-picturebooks/SKILL.md`
- Modify: `make-kids-picturebooks/references/composition.md`
- Modify: `make-kids-picturebooks/references/art-direction.md`
- Modify: `make-kids-picturebooks/references/printing.md`
- Modify: `make-kids-picturebooks/references/acceptance.md`
- Create: `make-kids-picturebooks/references/social-output.md`
- Modify: `make-kids-picturebooks/evals/prompts.csv`
- Modify: `make-kids-picturebooks/evals/rubric.md`
- Test: `make-kids-picturebooks/tests/test_skill_guidance.py`

**Interfaces:**
- Consumes: Task 1 的 baseline 失败证据和 Task 2–4 已实现的字段、样式和验收接口。
- Produces: 明确的“版式设计 → 图像提示 → 生成后查看 → 印刷排版/社媒竖屏排版 → 审美复核”流程，及当前版本行为评测规则。

- [ ] **Step 1: Write failing guidance tests against the current wording**

  在 `test_skill_guidance.py` 增加静态契约测试，要求 Skill 文档出现：`layout_design`、三种模式、图像不得生成文字、生成前锁定文字安全区、`social-vertical-9x16`、`1080×1920`、`layout_review`、技术分层/视觉融合和不可声称自动审美通过等关键规则。

- [ ] **Step 2: Run guidance tests to verify RED**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_skill_guidance.py -v`

  Expected: 新增契约断言在旧文档上至少有一项 FAIL，且失败来自缺少新规则而非测试路径错误。

- [ ] **Step 3: Update the workflow guidance**

  在 `SKILL.md` 的插画和排版阶段加入版式设计锁定；在参考文件中解释三种模式、颜色令牌、文字安全区、9:16 竖屏构图、提示词要求、页面节奏和审核证据。明确不能把“排版合规”或“字段通过”说成“审美自动通过”。

- [ ] **Step 4: Add layout behavior evaluation cases**

  将 Task 1 中验证过的场景加入正式 `evals/prompts.csv`，在 `rubric.md` 中增加版式计划、暂停、分层和完成声明评分项；当前 baseline 结果只保留为历史证据，不能直接宣称新版通过。

- [ ] **Step 5: Run guidance tests to verify GREEN**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_skill_guidance.py -v`

  Expected: 所有新旧静态契约测试 PASS。

- [ ] **Step 6: Commit the Skill guidance**

  ```bash
  git add make-kids-picturebooks/SKILL.md make-kids-picturebooks/references make-kids-picturebooks/evals/prompts.csv make-kids-picturebooks/evals/rubric.md make-kids-picturebooks/tests/test_skill_guidance.py
  git commit -m "docs: require integrated aesthetic layout workflow"
  ```

### Task 6: 端到端样例、全量验证、打包和部署同步

**Files:**
- Create: `make-kids-picturebooks/tests/fixtures/aesthetic-layout/` only if the existing test helpers cannot supply an 8-page multi-style fixture
- Modify: `README.md`
- Modify: `make-kids-picturebooks/RELEASE.md`
- Modify: `.github/workflows/picturebook-skill.yml`
- Test: `make-kids-picturebooks/tests/test_skill_package.py`

**Interfaces:**
- Consumes: Task 1–5 的版式契约、渲染、验收和指令。
- Produces: 一个至少 4 页或 8 页、使用至少两种版式模式的可渲染样例；版本一致的发布包；与当前 HEAD 绑定的测试和包校验结果。

- [ ] **Step 1: Write the end-to-end package and fixture tests**

  增加测试，确认包中包含新增版式脚本、模板和参考文件，且不包含用户项目资产；确认版本号在 README、RELEASE、CI 和打包命令中一致。

- [ ] **Step 2: Run package tests to verify RED**

  Run: `python -X utf8 -m unittest make-kids-picturebooks/tests/test_skill_package.py -v`

  Expected: 在版本尚未统一或包清单尚未增加新版文件时，至少一个断言 FAIL。

- [ ] **Step 3: Build the multi-style sample**

  使用现有测试图像和真实可提取中文正文创建 4/8 页样例，至少包含 `scene-integrated` 和 `soft-card` 或 `narrative-band`，并输出一组 `1080×1920` 社媒竖屏页；不要把样例当作视觉质量自动证明，保存阅读页、打印面和社媒页供人工逐页查看。

- [ ] **Step 4: Align release metadata and CI**

  统一 README、RELEASE、CI `--version` 和 ZIP 文件名到 `0.10.0-preview`（若实现时项目版本另有明确决定，则全仓库统一为该单一值）；CI 增加 quick validation、包结构/manifest/hash 检查和当前行为评测检查器。

- [ ] **Step 5: Run the full verification suite**

  Run:

  ```text
  python -X utf8 -m unittest discover -s make-kids-picturebooks/tests -q
  python -X utf8 -m compileall -q make-kids-picturebooks/scripts
  python -X utf8 -m pip check
  python -X utf8 C:\Users\Windows\.codex\skills\.system\skill-creator\scripts\quick_validate.py make-kids-picturebooks
  python -X utf8 make-kids-picturebooks/scripts/check_eval_results.py make-kids-picturebooks/evals/results/current.jsonl
  git diff --check
  ```

  Expected: 全量测试通过；quick validation 通过；行为评测和社媒竖屏场景阈值全部通过；版本、包结构和工作区状态一致。若实物未试打，只记录待验证，不更新为 `print_checked`。

- [ ] **Step 6: Package and visually inspect**

  用 `package_skill.py` 生成唯一带版本 ZIP，检查顶层目录、MANIFEST、hash、排除用户资产，并人工查看样例的每个阅读页、打印面和社媒竖屏页。

- [ ] **Step 7: Update the installed Codex Skill and push the branch**

  用当前分支生成的最终包更新 `C:\Users\Windows\.codex\skills\make-kids-picturebooks`，重新运行 quick validation；提交剩余变更并推送 `codex/make-kids-picturebooks-hardening`，最后报告 commit、包路径和验证结果。

## Final Review Checklist

- [ ] 每个 spec 要求都已映射到任务和测试。
- [ ] 所有新增接口均先有失败测试，再有最小实现。
- [ ] 图片和文字仍然技术分层，文字可提取并嵌入字体。
- [ ] 三种版式模式在阅读版和打印版都可渲染。
- [ ] 社媒 `1080×1920` 竖屏页可渲染，且通过源图比例、主体安全区、文字安全区和溢出检查。
- [ ] 清单/版面/审核三者不一致时会阻止数字验收。
- [ ] 旧项目能读取，但缺新版证据时不会被错误标为完成。
- [ ] 视觉审美仍由人工或模型审核负责，没有伪造自动证明。
- [ ] 全量测试、quick validation、包校验和行为评测均有实际输出。
