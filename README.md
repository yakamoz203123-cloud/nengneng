# 宝宝知识绘本

`make-kids-picturebooks` 将成人知识书中的一个核心概念改编为适合 3–4 岁、5–7 岁或 8–10 岁儿童的原创知识绘本，并保存可续做的项目资料。

当前仓库面向 `v0.9.1` 稳定化预览发布，重点是 Windows/Linux 路径兼容、来源安全边界、显式资产范围、字体来源证明和家庭打印导出验收。

## 使用

将 `make-kids-picturebooks-v0.9.1.zip` 作为技能包安装或上传。使用时提供实际可读取的知识书或章节，并确认一个目标年龄段。技能会先筛选适龄概念，再按角色、画风、故事、插画、排版和验收阶段推进。

来源中的命令、宏、系统提示、上传要求和密钥请求只作为资料中的文本，不会被执行。

## 开发验证

在技能目录中安装 `requirements.txt` 后运行：

```text
python -m compileall scripts
python -m unittest discover -s tests -q
python -m pip check
```

## 发布状态

`v0.9.1` 保留 `schema_version: 1` 项目兼容性。Schema v2、多年龄独立队列、项目迁移工具和三个年龄段真实样册属于后续 `v1.0` 范围，详见 [make-kids-picturebooks/RELEASE.md](make-kids-picturebooks/RELEASE.md)。

用户书籍、儿童资料、角色参考和生成项目资产不包含在公开技能包中。
