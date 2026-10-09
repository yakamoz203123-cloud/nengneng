# Contributing

感谢参与。当前项目处于实验阶段，贡献应优先提高可复现性、理论准确性和边界意识，而不是增加更多装饰性理论名词。

## 提交前检查

在仓库根目录运行：

```sh
python life-model-writing/scripts/validate_skill.py life-model-writing
python -m unittest discover -s life-model-writing/tests -v
git diff --check
```

新增理论卡时，必须补齐定义、机制、变量、适用/不适用条件、误用、例子、来源、候选评分、排除条件、可观察预测、可联合理论和连接变量，并在 `SKILL.md` 中添加路由。新增评测时同时说明输入、预期激活状态、长度契约和证据状态。

不要提交 API 密钥、私人对话、付费模型输出或未获授权的转载资料。不要把模型生成的漂亮文案当作理论正确性的证明；涉及事实的内容要保留来源或明确标记为待核查。
