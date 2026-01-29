# 基础性问题整改计划

日期: 2026-01-28
项目: 土地物业资产管理系统 (zcgl)
目标: 针对基础性问题给出可执行的整改任务清单、优先级与验收标准

## 总体原则
- 先安全后一致性，再质量门槛与文档清理
- 所有变更必须可回滚，并配套文档与示例配置
- 关键改动应在 CI 中设置强制门槛

## Phase 0 — 安全与密钥治理（P0）
**目的**: 阻断敏感信息落盘与硬编码进入版本库。

**任务清单**
1. 移除仓库内真实密钥与固定口令（替换为占位符）
   - 目标文件: `backend/.env`, `backend/config.yaml`, `docker-compose.yml`
2. 统一使用 `.env.example` / `.env.template` 提供示例
3. 在启动脚本/校验脚本中增加“弱密钥拒绝启动”的提示（开发环境允许提示但不阻断）
4. 更新文档说明“生产环境必须由外部注入密钥”

**验收标准**
- 仓库中不再包含真实密钥或固定密码
- 开发环境可正常启动，生产环境强制校验通过

## Phase 1 — 配置入口收敛（P0）
**目的**: 保证配置加载路径唯一、语义一致。

**任务清单**
1. 明确 `src/core/config.py` 为唯一配置入口
2. 冻结或移除 `src/config/__init__.py` 中的 legacy Settings，避免默认弱密钥
3. 修复 `run_dev.py` 读取 `API_PORT`（与启动脚本一致）
4. 文档中统一描述配置加载流程与优先级

**验收标准**
- 应用启动只依赖 `src/core/config.py`
- `API_PORT`、`ENVIRONMENT` 等变量在实际运行中生效

## Phase 2 — 数据库策略落地（P1）
**目的**: SQLite 去留决策一致，并清理残留数据库文件。

**任务清单**
1. 明确 SQLite 是否彻底移除（或仅测试环境可用）
2. 与 `environment-setup.md`、`run_dev.py`、`database.py` 对齐策略
3. 清理仓库内 `.db` 文件（或移动至 `backups/` 且加入忽略）

**验收标准**
- 文档与代码一致
- 仓库无不必要的数据库文件

## Phase 3 — 质量门槛对齐（P1）
**目的**: 用 CI 门禁保证质量目标不回退。

**任务清单**
1. 对齐 README 与后端覆盖率阈值
2. 恢复前端覆盖率阈值或在 CI 中加增量门槛
3. 输出统一的质量基线说明文档（如 `docs/TESTING_STANDARDS.md` 更新）

**验收标准**
- CI 失败能够阻止覆盖率回退
- 文档指标与实际门槛一致

## Phase 4 — 文档与实现一致性（P2）
**目的**: 清理已弃用的 OCR 内容与断链文档。

**任务清单**
1. 更新 `docs/guides/backend.md` 的技术栈说明
2. 标注或归档 PaddleOCR 脚本/测试（如 `archive/`）
3. 补齐架构文档目录或移除 README 断链指引

**验收标准**
- 文档不再引用已弃用组件
- README 链接无断链

## Phase 5 — 依赖策略与实现对齐（P2）
**目的**: 明确依赖选型，消除重复与不确定性。

**任务清单**
1. 明确 PostgreSQL 驱动策略（`psycopg` 与 `psycopg2-binary` 二选一）
2. 清理重复的 PDF 依赖（基础依赖与可选依赖保持一致边界）
3. 更新依赖说明文档（如 `docs/guides/backend.md` 或 `README.md`）

**验收标准**
- `pyproject.toml` 中不再存在重复或冲突依赖
- 文档描述与实际依赖一致

## Phase 6 — 架构文档补齐（P2）
**目的**: 恢复“单一可信来源”的架构文档入口。

**任务清单**
1. 创建 `docs/architecture/` 目录
2. 补充 `docs/architecture/system-overview.md`（最小可用）
3. 如暂不建立 ADR 列表，在 README 中移除/替换相关指引

**验收标准**
- README 指向的架构文档路径存在且可读
- 新成员可按文档快速理解系统结构

## 依赖与决策点
- SQLite 仅测试/CI 场景允许（`ENVIRONMENT=testing` + `ALLOW_SQLITE_FOR_TESTS=true`）
- legacy `src/config` 保留为兼容 shim（禁止新增依赖）
- PostgreSQL 驱动统一为 `psycopg`（psycopg3）
- PDF 处理依赖统一归入 `pdf-basic` 可选 extra
- 已创建 ADR 目录（后续补齐条目）

## 推荐执行顺序
P0 -> P0 -> P1 -> P1 -> P2 -> P2 -> P2

## 可执行下一步
- 立即执行 Phase 0 + Phase 1（配置与密钥治理）
- 完成后进入数据库策略、质量门槛与文档一致性整改
- 依赖策略与架构文档可与 P2 阶段并行推进
