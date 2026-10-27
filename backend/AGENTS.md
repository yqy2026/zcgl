# backend/AGENTS.md

后端专属补充。通用规则（红线、分层、SSOT、12-rule）见根目录 [`AGENTS.md`](../AGENTS.md)，本文件不重复。

---

## 命令

一律走 `uv run --frozen --extra dev <cmd>`，禁止系统 `python/pip`：

```bash
cd backend
uv sync --frozen --extra dev                                  # 安装依赖（make setup-backend 另含 document-processing）
uv run --frozen --extra dev python run_dev.py                 # 开发服务器 :8002（占用时用 :8003）
uv run --frozen --extra dev python -m pytest -m unit          # 单元测试（等价 make test-backend）
uv run --frozen --extra dev python -m ruff check . && uv run --frozen --extra dev python -m ruff format .
uv run --frozen --extra dev mypy src                          # 类型检查
```

- pytest 标记以 `pyproject.toml` 的 `[tool.pytest.ini_options].markers` 为准；启用了 `--strict-markers`，未注册标记直接报错。
- 默认 `--cov-fail-under=70`，只跑单个文件时加 `--no-cov` 避免误报覆盖率失败。
- 测试规范：[`docs/guides/testing-standards.md`](../docs/guides/testing-standards.md)

---

## 新增功能

分层与流程（Schema → Model → CRUD → Service → API → `route_registry` 注册）见根 `AGENTS.md`；完整示例见 [`docs/guides/backend.md`](../docs/guides/backend.md)。

---

## 数据加密

PII（身份证号/手机号等）由 CRUD 层 `SensitiveDataHandler`（`src/crud/asset_support.py`）做 AES-256-CBC 确定性加密，`DATA_ENCRYPTION_KEY` 缺失会降级为明文存储。密钥生成用 `make secrets`；配置、算法、密钥格式与字段覆盖现状见 [`docs/security/encryption.md`](../docs/security/encryption.md)。

---

## 可选依赖

`src.core.import_utils.safe_import` 用于可选依赖优雅降级；关键依赖用 `critical=True`，缺失即失败而非静默回退：

```python
vision = safe_import("services.document.extraction_manager", fallback=None)
```
