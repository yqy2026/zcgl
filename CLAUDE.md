# CLAUDE.md

本文件为 Claude Code 提供 **模型专属** 上下文补充。共享项目上下文见 `AGENTS.md`。

**Last Updated**: 2026-02-18

---

## Persona

每次回复都叫我【yellowUp】。

---

## Claude 专属规则

以下规则补充 `AGENTS.md`，仅在使用 Claude Code 时适用：

### 测试环境

- 后端测试使用项目虚拟环境，示例：
  ```bash
  cd backend && .\.venv\Scripts\pytest.exe tests/unit/... -q
  ```
- 或先激活环境再运行：
  ```bash
  cd backend && .\.venv\Scripts\activate && pytest -m unit
  ```

### 测试标记补充

除 `AGENTS.md` 中列出的标记外，还支持：`vision` / `pdf` / `rbac` / `core` / `asyncio` / `concurrency` / `load` / `stress`

### 代码质量

```bash
# Python
ruff check . && ruff format . && mypy src

# 单元测试
pytest -m unit
```

### 维护文档

每次修改后请更新 `CHANGELOG.md`。

## gstack

- **网页浏览**：统一使用 `/browse` skill（来自 gstack），永远不要使用 `mcp__claude-in-chrome__*` 工具。
- **可用 skills**：`/office-hours` `/plan-ceo-review` `/plan-eng-review` `/plan-design-review` `/design-consultation` `/design-shotgun` `/design-html` `/review` `/ship` `/land-and-deploy` `/canary` `/benchmark` `/browse` `/connect-chrome` `/qa` `/qa-only` `/design-review` `/setup-browser-cookies` `/setup-deploy` `/retro` `/investigate` `/document-release` `/codex` `/cso` `/autoplan` `/careful` `/freeze` `/guard` `/unfreeze` `/gstack-upgrade` `/learn`
