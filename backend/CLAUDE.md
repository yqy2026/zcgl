# Backend CLAUDE.md

后端开发专用指南。通用信息见根目录 `AGENTS.md`；本文件只保留后端专属、`AGENTS.md` 未覆盖的补充。

**Last Updated**: 2026-08-16

---

## 快速开始

```bash
cd backend
uv run --frozen --extra dev python run_dev.py   # 开发服务器 :8002（等价 make dev-backend）
uv run --frozen --extra dev python -m pytest    # 测试（命令/标记/规范见 docs/guides/testing-standards.md）
uv run --frozen --extra dev python -m ruff check . && uv run --frozen --extra dev python -m ruff format .   # lint + 格式化
```

> 手工执行后端工具一律 `uv run --frozen --extra dev <cmd>`（规则见 `AGENTS.md` §执行与变更边界），禁止系统 `python/pip`。

---

## 分层与新增功能

分层约束（业务逻辑必须放 `services/`、数据访问必须走 `crud/`）与新增功能流程（Schema → Model → CRUD → Service → API → `route_registry` 注册）见 `AGENTS.md` §架构原则 / §后端开发要点；完整示例与规范见 [`docs/guides/backend.md`](../../docs/guides/backend.md)。

---

## 数据加密

PII（身份证号/手机号等）由 CRUD 层 `SensitiveDataHandler`（`src/crud/asset_support.py`）做 AES-256-CBC 确定性加密，`DATA_ENCRYPTION_KEY` 缺失会降级为明文存储。密钥生成用 `make secrets`；配置、算法、密钥格式与字段覆盖现状见 [`docs/security/encryption.md`](../../docs/security/encryption.md)。

---

## 可选依赖

`src.core.import_utils.safe_import` 用于可选依赖优雅降级；关键依赖用 `critical=True`，缺失即失败而非静默回退：

```python
vision = safe_import("services.document.extraction_manager", fallback=None)
```
