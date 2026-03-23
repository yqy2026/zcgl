# 资产表字段补全方案（M1 收尾）

**状态**: ✅ 已完成（2026-03-05）  
**创建日期**: 2026-03-04  
**关联需求**: REQ-AST-001（字段收口）、REQ-AST-003（审核字段前置）  
**里程碑**: M1（截止 2026-03-31）

---

## 1. 问题描述

`requirements-specification.md` 第 15 节（2026-02-28 访谈冻结）补充了资产字段规格，但 `src/models/asset.py` 尚未同步：

| 规格要求 | 当前模型状态 |
|---------|-------------|
| `asset_code`（全局唯一编码） | **缺失** |
| `asset_name`（资产名称） | 以 `property_name` 替代，**命名不符规格** |
| `asset_form` / `spatial_level` / `business_usage` | **全部缺失** |
| `province_code` / `city_code` / `district_code` / `address_detail` | **全部缺失** |
| `address` 改为系统拼接只读展示字段 | 当前是可写 `String(500)` |
| `review_status` / `review_by` / `reviewed_at` / `review_reason` | **全部缺失** |

---

## 2. 方案说明

### 2.1 字段变更策略（破坏性，不兼容保留）

项目处于 0→1 阶段，直接变更，不做兼容层：

- **`property_name` → `asset_name`**：直接改列名，不保留旧列。
- **`address`**：变为应用层拼接只读字段（不存入 DB 独立列，由 `province_code/city_code/district_code/address_detail` 拼接后在 Schema 中作 `@computed_field` 或 API 响应层派生）。  
  > 重新评估：`address` 仍保留 DB 列，但值由写入时在 Service 层自动拼接，不对外开放直写。
- **新增枚举类**：`AssetForm` / `SpatialLevel` / `BusinessUsage`（在 `src/enums/` 或 model 内定义）。

### 2.2 涉及层次

```
models/asset.py          ← 字段变更 + 新枚举
schemas/asset.py         ← 对应字段 + 地址拆分校验（address_detail trim 5-200）
crud/asset.py            ← write 路径同步 address 拼接
services/asset/asset_service.py ← 写入时 address 自动拼接
alembic/versions/        ← 新建迁移文件
```

### 2.3 不在本方案范围内

- `asset_code` 编码生成规则（依赖 Party/ownership，另立方案）：本轮先加列允许 null，后续由编码生成服务填充。
- REQ-AST-003 完整审核流转（state machine）：本轮只加字段，不实现状态流转逻辑。

---

## 3. 具体变更清单

### 3.1 新增字段（`assets` 表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `asset_code` | `VARCHAR(50)` | UNIQUE, nullable（暂时） | 待编码生成服务补全 |
| `asset_name` | `VARCHAR(200)` | NOT NULL | 原 `property_name` 改名 |
| `asset_form` | `VARCHAR(20)` | NOT NULL（迁移后补默认值） | 枚举：`land/building/structure/parking/warehouse/other` |
| `spatial_level` | `VARCHAR(20)` | NOT NULL（迁移后补默认值） | 枚举：`plot/campus/building/floor/room/shop` |
| `business_usage` | `VARCHAR(20)` | NOT NULL（迁移后补默认值） | 枚举：`commercial/office/warehouse/industrial/mixed/other` |
| `province_code` | `VARCHAR(20)` | NOT NULL | 行政区省级代码 |
| `city_code` | `VARCHAR(20)` | NOT NULL | 行政区市级代码 |
| `district_code` | `VARCHAR(20)` | NOT NULL | 行政区区县代码 |
| `address_detail` | `VARCHAR(200)` | NOT NULL | trim 后长度 5-200 |
| `review_status` | `VARCHAR(20)` | NOT NULL, DEFAULT `draft` | 草稿/待审/已审/反审核 |
| `review_by` | `VARCHAR(100)` | nullable | 审核人 |
| `reviewed_at` | `TIMESTAMP` | nullable | 审核时间 |
| `review_reason` | `TEXT` | nullable | 审核原因 |

### 3.2 改名字段

| 旧名 | 新名 | 处理方式 |
|------|------|---------|
| `property_name` | `asset_name` | Alembic `op.alter_column` 改名 |

### 3.3 address 字段处理

`address` 列**保留**，但：
- Schema 层不接受客户端直接传入 `address`
- Service 层在写入前根据 `province_code/city_code/district_code/address_detail` 拼接赋值
- API 响应中 `address` 作为只读展示字段输出

---

## 4. 迁移策略

单次迁移文件：`20260304_asset_field_enrichment_m1.py`

执行顺序：
1. `ALTER TABLE assets RENAME COLUMN property_name TO asset_name`
2. `ADD COLUMN` 新增各字段（暂时 nullable）
3. `UPDATE assets SET asset_form='other', spatial_level='building', business_usage='commercial', province_code='', city_code='', district_code='', address_detail=address WHERE ...`（存量数据填充占位值，避免 NOT NULL 报错）
4. `ALTER COLUMN` 设置 NOT NULL 约束（address_detail 除外，需人工补全后再收紧）

---

## 5. 校验规则（Schema 层）

- `address_detail`：`validator` 做 `strip()`，长度 `5 ≤ len ≤ 200`，失败返回 422
- `asset_form` / `spatial_level` / `business_usage`：枚举成员校验
- `address` 字段在 CreateSchema 中标记 `exclude=True`，不接受写入

---

## 6. 测试用例建议

| 场景 | 期望 |
|------|------|
| `address_detail` 为空字符串 | 422 |
| `address_detail` trim 后 < 5 字符 | 422 |
| `address_detail` trim 后 > 200 字符 | 422 |
| 写入合法资产，`address` 字段自动拼接 | 响应 `address` = 拼接值 |
| `asset_form` 传非法枚举值 | 422 |
| `property_name` 旧字段名被拒绝 | 422 或 KeyError |

---

## 7. 完结条件

- [ ] `make migrate` 执行成功，无报错
- [ ] 存量测试数据迁移通过
- [ ] `make test-backend`（unit）通过
- [ ] `docs/features/requirements-appendix-fields.md` 中 Asset 部分状态同步
- [ ] 本文档移入 `docs/archive/backend-plans/`，`requirements-specification.md` REQ-AST-001 代码证据更新
