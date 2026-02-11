# 资产管理 API

## ✅ Status
**当前状态**: Supplemental (2026-02-09)

> 说明：本页为资产 API 的补充说明，不作为需求权威基线。  
> 权威规格请参考：`docs/requirements-specification.md`  
> 模块证据请参考：`docs/features/requirements-appendix-modules.md`

## 核心资源
| 资源 | 路径前缀 | 说明 |
|------|----------|------|
| 资产 | `/api/v1/assets` | 资产 CRUD 与查询 |
| 项目 | `/api/v1/projects` | 项目管理 |
| 权属方 | `/api/v1/ownerships` | 权属方管理 |
| 自定义字段 | `/api/v1/asset-custom-fields` | 字段配置 |
| 产权证 | `/api/v1/property-certificates` | 产权证管理 |

## 常见操作
- 列表查询、条件筛选、分页
- 新增/更新/删除
- 批量操作（以接口实现为准）
- 导入/导出（以接口实现为准）

## 回收站与删除
- 软删除：`DELETE /api/v1/assets/{id}`（默认仅标记 data_status=已删除）
- 恢复资产：`POST /api/v1/assets/{id}/restore`（管理员）
- 彻底删除：`DELETE /api/v1/assets/{id}/hard-delete`（管理员）

## 查询参数补充
- 列表接口支持 `data_status` 筛选；传 `已删除` 可查看回收站资产

## 业务规则与校验
- **`property_name` 全局唯一**（创建/更新必须避免重名）
- 导入去重认可 `property_name + address` 逻辑
- `ownership_id` 为唯一来源；`ownership_entity` 动态读取（不落库）。导入/写入如携带 `ownership_entity` 仅用于匹配 `ownership_id`
- 面积一致性：`rented_area ≤ rentable_area`
- 计算字段 `unrented_area` / `occupancy_rate` 不落库，实时计算

## 关联与删除约束
- 资产可选关联项目/权属方
- 合同/产权证创建时必须关联资产
- 资产删除时若已关联合同或产权证，必须阻止删除

## 枚举值
- 确权状态：已确权 / 部分确权 / 未确权 / 其它
- 使用状态：出租 / 闲置 / 自用 / 公房（出租） / 公房（闲置） / 其它
- 物业性质：经营类 / 公房 / 自用 / 其它
- 承租方类型（`tenant_type`）：企业 / 个人 / 其它

## 附件与自定义字段
- 资产支持附件（PDF）上传/下载/删除（大小限制以实现为准）
- 资产支持自定义字段配置（见 `/api/v1/asset-custom-fields`）

## 权限与可见范围
- 当前按角色权限控制
- 未来将引入“角色数据范围”机制（权属方/经营方关注点不同）

## 相关代码
- 资产路由: `backend/src/api/v1/assets/`
- 资产模型: `backend/src/models/asset.py`
- 资产服务: `backend/src/services/asset/`
