# 资产管理 API

## Status

**当前状态**: Supplemental (2026-04-28)

本页只补充资产 API 的使用边界，不作为权威契约。权威入口如下：

- 产品需求：[`docs/prd.md`](../prd.md)
- API 契约：[`docs/specs/api-contract.md`](../specs/api-contract.md)
- 字段契约：[`docs/specs/domain-model.md`](../specs/domain-model.md)
- 实现追踪：[`docs/traceability/requirements-trace.md`](../traceability/requirements-trace.md)

## 当前资产端点

| 能力 | 方法与路径 | 说明 |
|---|---|---|
| 列表 | `GET /api/v1/assets` | 分页、筛选、排序、搜索，按主体绑定自动过滤 |
| 详情 | `GET /api/v1/assets/{asset_id}` | 返回资产主数据和必要投影 |
| 创建 | `POST /api/v1/assets` | 创建草稿资产，需满足权限和主体范围约束 |
| 更新 | `PATCH /api/v1/assets/{asset_id}` | 审核态关键字段受控，版本冲突返回 409 |
| 删除 | `DELETE /api/v1/assets/{asset_id}` | 逻辑删除，存在关联约束时拒绝 |
| 恢复 | `POST /api/v1/assets/{asset_id}/restore` | 恢复逻辑删除资产 |
| 导出列表 | `GET /api/v1/assets/all` | 导出场景使用的不分页读取，受 `max_export` 限制 |
| 按 ID 批量读取 | `POST /api/v1/assets/by-ids` | 根据资产 ID 列表批量返回资产 |
| 附件 | `/api/v1/assets/{asset_id}/attachments/*` | 管理资产附件 |
| 审核动作 | `/api/v1/assets/{asset_id}/submit-review|approve-review|reject-review|reverse-review|resubmit-review|withdraw-review` | 资产审核状态流转 |
| 审核日志 | `GET /api/v1/assets/{asset_id}/review-logs` | 返回资产审核日志 |
| 租赁摘要 | `GET /api/v1/assets/{asset_id}/lease-summary` | 按上游、下游、委托、直租展示租赁情况 |

## 字段与业务规则

- 写入主线使用 `asset_name`、`owner_party_id`、`manager_party_id`、`project_id` 等当前字段。
- `address` 是系统拼接的只读展示字段，外部写入应提交行政区字段和 `address_detail`。
- `rented_area` 不得大于 `rentable_area`。
- `unrented_area`、`occupancy_rate_total` 等统计展示值属于派生口径，字段定义见领域模型契约。
- 资产删除为逻辑删除；若存在有效合同组、合同、台账或其他业务约束，删除应被拒绝。
- 资产进入合同签订等关键流转前必须满足审核状态约束。

## 数据范围

- 常规资产查询不使用 `view_mode`，系统按用户主体绑定自动收口。
- 产权方绑定用户只看绑定产权方范围内资产。
- 运营方绑定用户只看绑定运营方范围内资产。
- 多绑定用户返回各绑定范围并集，并按资产主键去重。
- `X-Perspective` 已废弃，不作为当前请求契约。

## Out of Scope

以下历史入口或代码骨架不纳入当前 MVP 验收，不应作为新开发依赖：

- 产权证管理 API
- 权属方管理 API
- 资产自定义字段配置 API
