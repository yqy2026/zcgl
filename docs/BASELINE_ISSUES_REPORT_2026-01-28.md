# 基础性问题分析报告

日期: 2026-01-28
项目: 土地物业资产管理系统 (zcgl)
范围: 仓库配置、启动脚本、关键文档、核心后端配置

## 结论摘要
当前项目存在若干基础性问题，集中在“密钥与配置治理、配置体系一致性、数据库策略落地、质量门槛约束、文档与实现一致性”五个方面。这些问题会直接影响环境可复现性、安全合规、上线风险与团队协作效率。

## 发现项（按影响优先级）

### 1) 密钥/凭据治理不足（高）
**风险**: 真实密钥与固定口令落盘，容易被误提交或被复用到生产，形成严重安全隐患。  
**证据**:
- `backend/.env`: 包含 `SECRET_KEY`、`DATA_ENCRYPTION_KEY` 与数据库账号口令
- `backend/config.yaml`: 写死 `secret_key` 与数据库连接信息
- `docker-compose.yml`: 固定 `POSTGRES_PASSWORD` 与 `DATABASE_URL`

### 2) 配置体系混乱，入口与文档不一致（高）
**风险**: 同名 Settings 体系并存，默认值语义冲突，导致运行时行为不可预期；启动脚本设置的环境变量未被真正消费。  
**证据**:
- `backend/src/core/config.py`: 强制要求 `SECRET_KEY`（无默认）
- `backend/src/config/__init__.py`: 提供默认弱密钥与默认配置
- `backend/run_dev.py`: 端口硬编码 `8002`，忽略 `API_PORT`
- `start-dev.bat` / `start-dev.sh`: 设置 `API_PORT` 但不生效

### 3) 数据库策略落地不一致 + SQLite 残留（中-高）
**风险**: 文档与执行策略不一致导致环境漂移；残留数据库文件可能携带真实数据或引发误用。  
**证据**:
- `docs/guides/environment-setup.md`: 声明 SQLite 已弃用
- `backend/run_dev.py`: 拒绝 SQLite（除测试特例）
- `backend/src/database.py`: 仍保留 SQLite engine 分支
- `data/land_property.db`, `land_property.db`, `test.db`: 仓库内残留 DB 文件

### 4) 质量门槛未形成有效约束（中）
**风险**: 质量目标与强制门槛不一致，CI 无法阻止覆盖率下滑。  
**证据**:
- `README.md`: 声称测试覆盖率 90%+
- `backend/pyproject.toml`: `--cov-fail-under=70`
- `frontend/vitest.config.ts`: 覆盖率阈值被注释（TODO）

### 5) 文档与实现存在漂移（中）
**风险**: 工具链与依赖事实不一致，造成认知负担与维护成本上升。  
**证据**:
- `docs/guides/backend.md`: 仍列 PaddleOCR 为核心 PDF 处理组件
- `docs/guides/environment-setup.md`: 已声明 PaddleOCR/Tesseract 退役
- `backend/src/services/document/config.py`: 注释说明已移除传统 OCR
- `backend/scripts/setup/setup_paddleocr.py` 与 `backend/tests/*`: 仍保留 PaddleOCR 相关内容

### 6) 依赖策略与实现重复/不清晰（中）
**风险**: 依赖体积与运行环境不确定，维护成本上升。  
**证据**:
- `backend/pyproject.toml`: 同时包含 `psycopg2-binary` 与 `psycopg`
- `backend/pyproject.toml`: PDF 相关依赖在基础依赖与可选依赖中重复

### 7) 架构文档缺失导致 “单一可信来源” 断链（中）
**风险**: README 指向的架构文档不存在，影响新成员理解与决策追溯。  
**证据**:
- `README.md`: 指向 `docs/architecture/system-overview.md` 与 ADR 列表
- `docs/architecture/`: 目录不存在

## 建议的优先修复顺序
1. **密钥/凭据治理**：移除仓库内真实密钥，统一通过环境变量或密钥管理服务注入；更新示例文件与 compose 模板。  
2. **配置体系统一**：收敛到 `src/core/config.py` 为唯一入口，移除/冻结 legacy Settings；修复 `run_dev.py` 支持 `API_PORT`。  
3. **数据库策略落地**：明确 SQLite 是否彻底移除；清理仓库内残留 DB；更新文档与脚本一致。  
4. **质量门槛一致**：对齐 README 与 CI 阈值；恢复前端覆盖率阈值策略。  
5. **文档一致性**：清理已弃用 OCR 文档/脚本，或标注“历史/归档”。  

## 备注
本报告基于仓库当前文件的静态分析结果，未执行运行时探测或安全扫描。建议在整改后补充：安全基线扫描、CI 质量门禁与配置一致性检查。
