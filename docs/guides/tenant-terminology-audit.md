# Tenant 术语审计清单（组织权限 vs 承租方）

> **状态**: Active  
> **审计日期**: 2026-02-11  
> **目标**: 清理“SaaS 多租户 tenant”与“承租方 tenant”语义混淆

---

## 1. 结论摘要

- 当前仓库运行时代码未发现 `tenant_filter` / `tenant_scope` 一类的 SaaS 多租户过滤实现。
- 主要混淆来自文档历史残留（`tenant_id`、`跨租户` 等描述）。
- 业务字段 `tenant_*` 主要表示“承租方（乙方）”，应保留原语义，不应误改为权限语义。
- 第二轮已将多处人类可读文本从“租户”统一为“承租方”，字段键名 `tenant_*` 保持不变以确保兼容。

---

## 2. 语义分类基线

| 分类 | 说明 | 命名口径 |
|------|------|----------|
| 组织权限语义 | 按组织架构/权限做数据范围控制 | `organization scope` / `组织范围过滤` |
| 承租方业务语义 | 合同乙方信息（姓名、证件、电话等） | `tenant_*`（保留） |
| SaaS 多租户语义 | 平台级租户隔离（tenant_id） | 仅在明确 SaaS 语境使用 |

---

## 3. 审计结果（按路径）

| 路径 | 关键术语 | 分类 | 处理决策 |
|------|----------|------|----------|
| `docs/database-design.md` | `tenant_id`（多租户） | SaaS 遗留 | 已移除表字段描述，并补充“当前基线不含 tenant_id”说明 |
| `docs/database-design.md` | “租户信息/租户名称/租户类型” | 承租方语义命名不清 | 已统一为“承租方信息/承租方名称/承租方类型（tenant_*）” |
| `docs/requirements-specification.md` | `跨租户隔离策略` | 组织权限语义表述不准 | 已改为“跨组织数据隔离策略（非 SaaS 多租户）” |
| `docs/integrations/assets-api.md` | “租户类型” | 承租方语义命名不清 | 已改为“承租方类型（tenant_type）” |
| `docs/features/prd-asset-management.md` | “租户类型” | 承租方语义命名不清 | 已改为“承租方类型（tenant_type）” |
| `backend/src/schemas/asset.py` | 字段描述“租户名称/租户类型” | 承租方语义命名不清 | 已改为“承租方名称/承租方类型” |
| `backend/src/models/asset.py` | `tenant_type` 注释“租户类型” | 承租方语义命名不清 | 已改为“承租方类型” |
| `backend/src/services/enum_data_init.py` | 枚举名称/描述“租户类型” | 承租方语义命名不清 | 已改为“承租方类型/承租方的类型分类” |
| `frontend/src/services/dictionary/config.ts` | 字典展示名“租户类型” | 承租方语义命名不清 | 已改为“承租方类型” |
| `frontend/src/components/Forms/Asset/AssetDetailedSection.tsx` | “租户信息/租户名称/租户类型” | 承租方语义命名不清 | 已统一为“承租方”表述 |
| `frontend/src/components/Asset/AssetDetailInfo.tsx` | “租户名称” | 承租方语义命名不清 | 已改为“承租方名称” |
| `frontend/src/components/Asset/AssetSearchResult.tsx` | “租户信息/租户” | 承租方语义命名不清 | 已改为“承租方信息/承租方” |
| `frontend/src/components/Analytics/Filters/FiltersSection.tsx` | “租户类型” | 承租方语义命名不清 | 已改为“承租方类型” |
| `frontend/src/components/Forms/AssetFormHelp.tsx` | “显示租户名称” | 承租方语义命名不清 | 已改为“显示承租方名称” |
| `frontend/src/components/Asset/assetExportConfig.ts` | 导出列“租户名称” | 承租方语义命名不清 | 已改为“承租方名称” |
| `frontend/src/pages/System/PromptDashboard.tsx` | 识别建议“租户名称识别” | 承租方语义命名不清 | 已改为“承租方名称识别” |
| `frontend/src/components/Asset/AssetForm.md` | “租户名称” | 承租方语义命名不清 | 已改为“承租方名称” |
| `backend/src/services/document/extractors/base.py` | `tenant_id` | 承租方业务语义 | 保留（承租方身份证/统一社会信用代码） |
| `backend/src/services/document/ocr_extraction_service.py` | `tenant_id` | 承租方业务语义 | 保留 |
| `backend/src/services/document/contract_extractor.py` | `tenant_id` | 承租方业务语义 | 保留 |
| `backend/alembic/versions/e4c9e4968dd7_initial_schema_creation.py` | `tenant_id` | SaaS 历史遗留 | 已补充“历史快照字段，已由后续迁移删除”说明 |
| `backend/alembic/versions/20260130_drop_tenant_id_columns.py` | `tenant_id` | SaaS 历史遗留 | 已补充“运行时不依赖，仅回滚兼容”说明 |
| `backend/tests/integration/crud/test_query_builder_security.py` | `test_blocked_tenant_filter_raises_error` | 命名易误解为 SaaS 过滤 | 已改为 `test_blocked_tenant_name_field_filter_raises_error` |
| `backend/src/crud/field_whitelist.py` | 注释“PII: Tenant name” | 英文注释语义不清 | 已改为 “PII: Lessee name (contract party field)” |
| `frontend/src/components/Forms/RentContract/TenantInfoSection.tsx` | 注释 “Tenant Info Section” | 注释语义不清 | 已改为 “Lessee Info Section” |
| `backend/src/models/asset.py` | `tenant_type` | 承租方业务语义 | 保留 |
| `backend/src/models/rent_contract.py` | `tenant_name` 等 | 承租方业务语义 | 保留 |

---

## 4. 后续约束（新增变更必须遵守）

1. 数据权限相关文档/注释统一使用“组织范围过滤（organization scope）”。
2. `tenant_*` 在合同/文档抽取语境默认指承租方，不代表 SaaS tenant。
3. 若确需引入 SaaS 多租户概念，必须在描述中显式标注 “SaaS 多租户”。

---

## 5. 关联文档

- [tenant 符号白名单（运行时零歧义清单）](tenant-symbol-whitelist.md)
