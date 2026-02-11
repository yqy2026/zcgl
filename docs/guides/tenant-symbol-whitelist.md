# tenant 符号白名单（运行时零歧义清单）

> **状态**: Active  
> **生成日期**: 2026-02-11  
> **用途**: 明确哪些 `tenant*` 符号可保留（承租方语义），哪些仅限历史迁移，哪些不得新增。

---

## 1. 结论（可直接用于评审）

- 当前运行时代码未发现 SaaS 多租户上下文符号（如 `tenant_scope`、`tenant_filter`、`current_tenant`）。
- `tenant_*` 在当前系统中主要代表**承租方（合同乙方）业务字段**，属于保留白名单。
- `tenant_id` 在运行时仅用于**合同抽取中的证件号/统一社会信用代码语义**，不表示 SaaS tenant。
- SaaS 多租户遗留仅存在于 Alembic 历史迁移链，且已在后续迁移中删除。

---

## 2. 允许保留（Runtime WhiteList）

### 2.1 核心模型/Schema（承租方业务字段）

| 类别 | 关键文件 | 保留符号 |
|------|----------|----------|
| ORM 模型 | `backend/src/models/rent_contract.py` | `tenant_name`, `tenant_contact`, `tenant_phone`, `tenant_address`, `tenant_usage` |
| ORM 模型 | `backend/src/models/asset.py` | `tenant_type`, 计算属性 `tenant_name` |
| Pydantic Schema | `backend/src/schemas/rent_contract.py` | `tenant_*`（合同输入/输出） |
| Pydantic Schema | `backend/src/schemas/asset.py` | `tenant_name`, `tenant_type` |

### 2.2 API/Service（承租方筛选与处理）

| 类别 | 关键文件 | 保留符号 |
|------|----------|----------|
| API 参数 | `backend/src/api/v1/rent_contracts/contracts.py` | `tenant_name` 筛选参数 |
| 服务层 | `backend/src/services/rent_contract/service.py` | `tenant_name` 过滤参数 |
| 文档抽取 | `backend/src/services/document/contract_extractor.py` | `tenant_name`, `tenant_phone`, `tenant_address`, `tenant_id`（证件号语义） |
| OCR 提示 | `backend/src/services/document/ocr_extraction_service.py` | `tenant_id`（证件号语义） |
| Vision 提示 | `backend/src/services/document/extractors/base.py` | `tenant_id`（证件号语义） |

### 2.3 前端类型与表单（承租方展示/录入）

| 类别 | 关键文件 | 保留符号 |
|------|----------|----------|
| 类型定义 | `frontend/src/types/pdfImport.ts` | `tenant_name`, `tenant_contact`, `tenant_phone`, `tenant_address` |
| 合同表单 | `frontend/src/components/Forms/RentContract/TenantInfoSection.tsx` | `tenant_*` 表单字段 |
| 合同上下文 | `frontend/src/components/Forms/RentContract/RentContractFormContext.tsx` | `tenant_*` 状态字段 |
| 资产表单 | `frontend/src/components/Forms/Asset/AssetDetailedSection.tsx` | `tenant_name`, `tenant_type`（只读展示） |

---

## 3. 历史迁移白名单（非运行时语义）

> 以下仅用于迁移历史回放/回滚兼容，**不构成运行时多租户能力**。

| 文件 | 符号 | 状态 |
|------|------|------|
| `backend/alembic/versions/e4c9e4968dd7_initial_schema_creation.py` | `tenant_id` 列 | 历史快照，后续已删除 |
| `backend/alembic/versions/20260130_drop_tenant_id_columns.py` | 删除/回滚 `tenant_id` | 仅迁移兼容 |
| `backend/alembic/versions/345d5f07ee41_merge_heads_before_ocr_cleanup.py` | `20260130_drop_tenant_id_columns` 引用 | 迁移分支合并元数据 |

---

## 4. 禁止新增（Guardrail）

以下符号在当前架构中应视为**禁止新增**（除非明确引入 SaaS 多租户并完成架构评审）：

- `tenant_scope`
- `tenant_filter`
- `current_tenant`
- `TenantContext`
- `X-Tenant` / `x-tenant` 请求头语义
- 任何用于权限隔离的 `tenant_id` 运行时字段

---

## 5. 待确认的文本项（不影响运行时）

以下是“文案层可能仍会让人联想到租户隔离”的点，建议产品/研发共同确认是否继续改为“承租方”：

| 文件 | 当前文本 | 建议 |
|------|----------|------|
| `frontend/src/pages/Project/ProjectDetailPage.tsx` | 列标题“租户” | 评估改为“承租方” |
| `frontend/src/components/Forms/RentContractForm.tsx` | 注释“租户合同创建/编辑表单组件” | 建议改为“承租方合同创建/编辑表单组件” |
| `backend/src/schemas/contact.py` | `entity_type` 描述含 `tenant` | 若语义指承租方，建议补注释说明 |

---

## 6. 复核命令（建议纳入巡检）

```bash
rg -n "tenant_filter|tenant_scope|current_tenant|TenantContext|X-Tenant|x-tenant|MULTI_TENANT|tenantId\\b" backend/src frontend/src
rg -n "tenant_id" backend/src backend/alembic
```

预期结果：
- 第一条命令在运行时目录应无命中。
- 第二条命令仅命中文档抽取语义与 Alembic 历史迁移。

