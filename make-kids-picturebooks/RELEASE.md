# make kids picturebooks 0.10.0-preview

## 发布范围

这是保留 `schema_version: 1` 兼容性的版式与社媒输出预览版本，包含以下改进：

- Windows 和 Linux 下的项目相对路径规范化；
- 来源文件和角色目录的显式资产边界；
- 字体文件、许可证和来源证明的验收要求；
- 故事页正文顺序核对，封面和封底不误判为朗读稿；
- UTF-8 测试夹具和当前 PyMuPDF 导入方式；
- 来源内容安全边界、年龄选择、角色确认和画风确认规则；
- 单顶层目录技能包与完整下载包的非覆盖式打包；
- 三种可复核的整合式文字版式：`scene-integrated`、`soft-card`、`narrative-band`；
- 版式设计契约、逐页 `layout_review` 审核记录和版式/清单/验收一致性检查；
- 小红书静态图文默认 `xiaohongshu-feed-3x4` 输出，固定为 `1080×1440`、源图3:4；抖音/长屏显式选择独立的 `social-vertical-9x16`，固定为 `1080×1920`、源图9:16。
- 小红书新页面要求 `portrait-full-bleed` 竖版满幅构图与 `in-scene` 画面内文字；模板和确定性门禁拒绝底部通栏文字区。
- 正式社媒插画前增加生成器比例预检：`preflight_image_generation.py` 读取实际探针尺寸，比例不符返回 `image_generation_blocked`，禁止横图适配后继续排版。

## 质量门迭代

本次 0.10.0-preview 质量门迭代在不改变 `schema_version: 1` 的前提下增加：

- 朗读版和印刷版 PDF 的非空、可读、页数、尺寸、可提取正文与最终字号确定性校验；印刷版默认最小字号为 18 pt，项目只能提高该阈值；
- 页间连续性记录：`previous_page_state`、`current_page_entry`、`next_page_hook`，以及有实际证据的 `text_image_match` 和 `continuity_review` 通过记录；
- 数字完成时对连续性记录、相邻页状态衔接和人工/模型视觉审核证据的强制检查；
- 稳定角色参考、文本与画面状态匹配、相邻页成对审核和最终输出检查的操作指引。
- 图像与文字分层、文字安全区锁定、版式模式一致性和社媒安全区检查。

这些检查只报告确定性缺陷；角色一致性、场景可读性和故事/科学准确性仍须由人工或模型进行视觉审核。

## 兼容性

- Python 3.10 及以上；
- 目标验证平台为 Windows 和 Linux；
- 依赖版本见 `requirements.txt`；
- 默认打印质量为 300 DPI 或更高，使用项目内附带的中文打印字体。

## 验证命令

```text
python -X utf8 -m compileall scripts
python -X utf8 -m unittest discover -s tests -q
python -X utf8 -m pip check
```

发布前还应在 Windows 和 Linux 上分别运行上述命令，并检查验收、续做、打包和重复执行不会覆盖已有输出。

## 已知范围

本版本不包含 Schema v2、多年龄独立队列、v1 到 v2 迁移工具和 3–4、5–7、8–10 岁三套真实样册。仓库中的版式样例只用于渲染回归和人工查看，不代表自动审美通过。Grok Bot 的具体 API 接入仍不包含；本版本只提供平台无关的实际输出比例预检，不会让不支持竖版的生成器获得竖版能力。行为评测更新结果也不作为本版本的完成证据；这些内容属于 v1.0 发布门槛。

公开包只包含技能源码、测试、脚本、参考资料、模板、许可证和字体来源证明，不包含任何用户书籍、儿童资料、角色参考或生成项目。
