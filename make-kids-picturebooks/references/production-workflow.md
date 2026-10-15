# 单 Skill 的分阶段生产流程

本流程仍由 `make-kids-picturebooks` 一个 Skill 执行，不拆成搜索、绘图或发布等独立 Skill。它把一次绘本制作拆成有明确输入输出的阶段，但保留同一册的年龄、知识、角色、画风、版式和验收上下文。

## 0. 先记录基线

对已有的 8—12 页绘本，在改流程前先记录一份性能基线：

- 总墙钟：从完整计划开始到最终验收记录的时间；
- 绘图产物跨度：第一页源图写入到最后一页源图写入的时间；如果宿主能提供，另记真实模型等待时间；
- 图像生成调用次数、失败尝试、重试次数和逐页返工次数；
- 最终输出质量：页面尺寸、DPI、字体嵌入、可提取文字、逐页 `layout_review`、连续性和 `acceptance` 结果。

旧项目没有任务级日志时，失败率、真实模型耗时或返工次数必须写成“不可测”，不能用 `acceptance.errors: []` 推断为零。优化后用同一本故事、同一质量档位和同一验收门禁复测，并在报告中区分：可观测墙钟、图像产物跨度、真实模型耗时、缓存命中耗时。

## 1. 一次规划，先完成全书

正式出图前必须完成并审核：

1. `concept.md` 或概念卡、完整 `story.md`；
2. 覆盖全书的 `storyboard.json`；
3. 覆盖相同页数的 `page-manifest.json` 和 `layout.json`；
4. 已批准且带版本号的 character Bible、`production_reference_path`、风格卡和目标社媒 profile；
5. 每页正文、安全区、动作、道具、知识证据、前页状态和后页钩子。

没有完整故事、分镜、角色版本、画风版本或版式设计时，`generation_queue.py init` 必须拒绝创建任务；不能边写故事边正式出图。探针比例预检仍是正式社媒出图的前置门禁。

## 2. 建立并执行生产队列

使用标准库脚本建立一页一个任务的队列。默认只允许 2 个任务同时处于 `running`，工具明确支持且小规模测试通过时才可调整到 3（先从 2—3 个任务开始测试）；不得把队列并发当成图像工具本身支持并发的证明。

```bash
python3 "$SKILL_DIR/scripts/generation_queue.py" init \
  /absolute/project/books/b01/v1 \
  /absolute/project/books/b01/v1/review/production-queue.json \
  --max-in-flight 2 --max-attempts 2
python3 "$SKILL_DIR/scripts/generation_queue.py" status /absolute/project/books/b01/v1/review/production-queue.json
python3 "$SKILL_DIR/scripts/generation_queue.py" claim-batch /absolute/project/books/b01/v1/review/production-queue.json --pages 1 2
```

执行时按以下阶段推进：

- `init`：校验整册计划，创建或复用一页一个任务；同一请求指纹和仍存在的输出自动命中缓存；
- `claim-batch --pages 1 2`：原子领取一组页面；默认最多领取 2 页，只有工具支持并测试通过时才把队列上限调整为 3；
- `claim --page N`：领取某页。宿主用现有图像工具提交该页，使用同一份干净生产参考图；一次只提交一个正式结果，不生成多套备选；
- `complete --page N --output PATH --elapsed-ms MS`：检查文件存在、路径在私有项目内并记录 SHA-256、耗时和输出；
- `fail --page N --error "..."`：记录失败原因，未耗尽预算的任务进入 `retryable`；只有明确失败且没有输出时才重试；
- `resume`：中断后把未完成的 `running` 任务恢复为可重试状态，已完成页不动；
- `reset-page --page N --reason "..."`：只使指定页失效，保留旧验收图并生成新的版本化输出路径，其他页保持缓存或已验收状态；用户修改某一页时只重新生成该页。

图像工具没有真实批处理或并发能力时，队列仍可用于限流、缓存和断点续跑，但不得声称已经并行绘图。不得未经授权接入新的付费图像接口，也不能用降低正式分辨率、横图补白或牺牲打印质量换速度。

## 3. 绘图与成页排版分离

图像阶段只生成无文字的正式插画，且按已锁定的 `layout_design` 为文字保留画内自然留白或悬浮卡。排版阶段再把正文作为可编辑、可提取的文字层放进正式绘本画面内部；禁止默认底部通栏字幕，也不接受独立矩形图片加页面底部正文块冒充图文融合。每批完成后先做像素、角色、相邻页、知识证据和 `layout_review`，通过后再进入下一批。

所有页面完成后，使用现有 `export_book.py` 自动生成页码、阅读版 PDF、家庭打印拼版 PDF、逐页预览和导出报告，再运行 `validate_exports.py` 与 `accept_book.py`。最终只输出一版完整成品；阅读版、打印版和内部审核图是同一成品的不同技术输出，不是多套备选方案。

## 4. 性能与质量报告

报告至少比较优化前后：总耗时、总墙钟、绘图产物跨度或真实绘图耗时、生成调用数、返工次数、失败率、缓存命中数、断点恢复情况和输出质量。失败率分母必须明确（例如“失败任务数 ÷ 任务总数”或“失败尝试数 ÷ 总尝试数”）；不可观测的旧指标写 `unknown`。质量以同一套验收脚本和人工／模型视觉审核结果为准，不用速度指标替代角色一致性、故事完整性、知识准确性、图文融合、打印分辨率或字体可提取性。
