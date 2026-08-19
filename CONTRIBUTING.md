# 贡献指南

欢迎提交问题、渠道适配器、规则修复和可访问性改进。

1. 从主分支创建短生命周期分支。
2. 保持改动聚焦，不提交真实简历、数据库、Cookie、Token 或账号信息。
3. 新渠道按 `docs/CHANNEL_ADAPTERS.md` 注册；普通发现/清单渠道不要在编排器增加 ID 特判，只有真正不同的多阶段写协议才单独设计执行器。
4. 新硬规则补充 `tests/test_matching.py`，新渠道至少补充离线解析或注册测试。
5. 提交前运行：

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src tests
```

真实招聘站点会变化。问题或 PR 中请写明验证日期、页面/API 证据和失败边界，不要只写“能访问”。
