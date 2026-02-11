# 剩余问题与待办事项清单（复核版）

**最后更新**: 2026-02-11  
**复核范围**: 后端模型 / CRUD 查询路径 / Alembic 迁移 / 工作区状态  
**当前阶段**: Phase 2（性能优化推进中）

---

## 📌 复核结论

### ✅ 已确认完成

1. **Phase 1.2 已完成**
   - Service 层直连数据库整改完成（见 `CHANGELOG.md` 历史记录）。
2. **`Asset.active_contract` 基础优化已落地**
   - 已具备关系未加载保护、实例级缓存、单次选择逻辑。
3. **`crud/asset.py` 已支持按场景控制合同投影加载**
   - 具备 `include_contract_projection` 开关，可用于规避不必要关系加载。

### ⚠️ 已确认仍存在（本清单重点）

1. **Phase 2.1 复合索引仍未在环境执行**
   - 已新增迁移脚本：`backend/alembic/versions/20260211_add_phase2_aligned_performance_indexes.py`
   - 但尚需在测试/生产环境执行 `alembic upgrade head` 并验证命中效果。

2. **旧版索引草案与现模型存在字段不一致问题**
   - 典型已修正项：
     - `notifications.user_id` → `notifications.recipient_id`
     - `tasks`（旧概念）→ `async_tasks`（现表）
     - `property_certificates.asset_id`（不存在）→ `property_cert_assets(asset_id, certificate_id)`
     - `assets.total_area`（不存在）→ `assets.actual_property_area`
   - 本复核版已全部按当前 schema 对齐。

3. **Phase 2.2 仍需“二次审计补盲”**
   - `active_contract` 的基础问题已修，但尚未完成全链路 statement-count 审计（列表/详情/导出/统计）。

4. **Phase 2.3 缓存策略未完整落地**
   - 尚未形成统一缓存预热服务与写路径失效闭环（尤其是字典/组织/权限相关场景）。

5. **工作区尚未清理**
   - 当前仓库存在大量未提交变更，建议在性能改造上线前先收敛变更边界。

---

## 🎯 Phase 2.1（已落地迁移脚本，待执行）

### 迁移文件

- `backend/alembic/versions/20260211_add_phase2_aligned_performance_indexes.py`

### 本次新增索引（对齐现模型）

#### 资产 (`assets`)

- `ix_assets_ownership_usage_active`：`(ownership_id, usage_status)` + 软删过滤
- `ix_assets_project_status`：`(project_id, data_status)`
- `ix_assets_management_nature_active`：`(management_entity, property_nature)` + 软删过滤
- `ix_assets_active_created_at`：`(created_at DESC)` + 软删过滤
- `ix_assets_area_range_active`：`(actual_property_area)` + 软删过滤 + 非空过滤

#### 租赁合同 (`rent_contracts`)

- `ix_rent_contracts_ownership_status_active`：`(ownership_id, contract_status)` + 软删过滤
- `ix_rent_contracts_status_end_date_active`：`(contract_status, end_date)` + 软删过滤
- `ix_rent_contracts_type_status_active`：`(contract_type, contract_status)` + 软删过滤
- `ix_rent_contracts_tenant_name_trgm_active`：`tenant_name` trigram + 软删过滤

#### 租金台账 (`rent_ledger`)

- `ix_rent_ledger_contract_year_month`：`(contract_id, year_month)`
- `ix_rent_ledger_payment_status_due_date`：`(payment_status, due_date)`
- `ix_rent_ledger_year_month`：`(year_month)`
- `ix_rent_ledger_ownership_payment_status`：`(ownership_id, payment_status)`
- `ix_rent_ledger_asset_year_month`：`(asset_id, year_month)`

#### 权属方 / 项目

- `ix_ownerships_active_data_status`：`ownerships(is_active, data_status)`
- `ix_ownerships_name_trgm`：`ownerships(name)` trigram
- `ix_projects_status_created_at`：`projects(project_status, created_at DESC)`
- `ix_projects_is_active_true`：`projects(is_active)`（`WHERE is_active IS TRUE`）

#### 产权证关联 / 通知 / 异步任务 / 操作日志

- `ix_property_cert_assets_asset_id_cert_id`：`property_cert_assets(asset_id, certificate_id)`
- `ix_notifications_recipient_read_created`：`notifications(recipient_id, is_read, created_at DESC)`
- `ix_notifications_type_created_at`：`notifications(type, created_at DESC)`
- `ix_async_tasks_status_created_at`：`async_tasks(status, created_at DESC)`
- `ix_async_tasks_user_status_created_at`：`async_tasks(user_id, status, created_at DESC)`
- `ix_operation_logs_user_created_at`：`operation_logs(user_id, created_at DESC)`
- `ix_operation_logs_module_created_at`：`operation_logs(module, created_at DESC)`
- `ix_operation_logs_ip_address`：`operation_logs(ip_address)`

### 执行步骤

```bash
cd backend
alembic upgrade head
```

### 执行后验证

```sql
-- 示例：检查 assets 索引
SELECT indexname
FROM pg_indexes
WHERE tablename = 'assets'
ORDER BY indexname;

-- 示例：关键查询计划验证
EXPLAIN ANALYZE
SELECT id, property_name
FROM assets
WHERE ownership_id = '...'
  AND usage_status = '...'
  AND (data_status IS NULL OR data_status != '已删除')
ORDER BY created_at DESC
LIMIT 50;
```

---

## 🧪 Phase 2.2（N+1 二次审计补盲）

### 当前状态

- ✅ 基础修复已完成（模型层缓存 + 关系加载保护 + CRUD 投影开关）
- ⏳ 尚未完成全链路查询计数审计

### 待办

1. 选定高频接口（资产列表/详情/导出/统计）做 statement-count 基线。
2. 固化“列表/详情”加载策略，避免回归到隐式懒加载。
3. 为关键路径补充查询次数回归测试（防止二次退化）。

### 验收标准

- 高频列表接口查询次数稳定在预期阈值内（无 N+1 放大）。
- 对应单测可在 CI 环境稳定复现。

---

## 🧠 Phase 2.3（缓存策略完善）

### 当前状态

- 已有统一缓存管理能力与装饰器。
- 尚缺“启动预热 + 写入失效 + 命中率指标”闭环。

### 待办

1. 增加缓存预热服务（字典/枚举/组织等低频变更数据）。
2. 在关键 CRUD 写路径落地缓存失效策略（按 namespace/pattern）。
3. 增加命中率、延迟等观测指标，形成可调优闭环。

### 验收标准

- 热点读取命中率可观测并达到目标阈值。
- 变更后缓存可及时失效，无数据陈旧问题。

---

## 🧹 工程治理与交付建议

1. **先清理工作区**
   - 在性能变更上线前，先完成大规模未提交改动的分类与收敛。
2. **分批发布**
   - 建议先发布 Phase 2.1（索引），再推进 Phase 2.2/2.3，便于定位收益与风险。
3. **保留回滚路径**
   - 本次迁移已提供完整 `downgrade`，生产执行前建议先在测试环境演练。

---

## ✅ 下一步（可立即执行）

1. 测试环境执行索引迁移并导出 `EXPLAIN ANALYZE` 对比结果。
2. 确认最慢 3 条查询的命中改进情况。
3. 输出“索引收益复盘”后，再进入 Phase 2.2 的查询计数审计。
