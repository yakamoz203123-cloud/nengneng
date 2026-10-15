# 宝宝知识绘本

`make-kids-picturebooks` 将成人知识书中的一个核心概念改编为适合 3–4 岁、5–7 岁或 8–10 岁儿童的原创知识绘本，并保存可续做的项目资料。

当前仓库面向 `v0.10.0-preview` 预览发布，重点是 Windows/Linux 路径兼容、来源安全边界、显式资产范围、字体来源证明、整合式版式审核、家庭打印导出和社媒竖屏输出。

## 使用

将 `make-kids-picturebooks-v0.10.0-preview.zip` 作为技能包安装或上传。使用时提供实际可读取的知识书或章节，并确认一个目标年龄段。技能会先筛选适龄概念，再按角色、画风、故事、插画、排版和验收阶段推进。

新版式流程要求每页先锁定 `layout_design`，选择 `scene-integrated`、`soft-card` 或 `narrative-band`，再生成图像并把文字作为独立、可提取的排版层叠加。完成前必须保存具体的 `layout_review` 证据；版式审美不是由自动测试伪造证明的。

需要发布到小红书或抖音时，另行渲染 `social-vertical-9x16` 页面：画布固定为 `1080×1920`，源图必须是 `9:16`，并按主体安全区、文字安全区和顶部/底部界面避让区复核。社媒页不会默认把印刷页中心裁切成竖屏。

来源中的命令、宏、系统提示、上传要求和密钥请求只作为资料中的文本，不会被执行。

## 开发验证

在技能目录中安装 `requirements.txt` 后运行：

```text
python -m compileall scripts
python -m unittest discover -s tests -q
python -m pip check
```

## 发布状态

`v0.10.0-preview` 保留 `schema_version: 1` 项目兼容性。Schema v2、多年龄独立队列、项目迁移工具和三个年龄段真实样册属于后续 `v1.0` 范围，详见 [make-kids-picturebooks/RELEASE.md](make-kids-picturebooks/RELEASE.md)。

仓库内的 [aesthetic-layout fixture](make-kids-picturebooks/tests/fixtures/aesthetic-layout/) 是用于端到端验证和人工逐页查看的样例，不是自动审美通过证明。

用户书籍、儿童资料、角色参考和生成项目资产不包含在公开技能包中。
