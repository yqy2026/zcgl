# 资产管理 API

## ✅ Status
**当前状态**: Draft (2026-02-03)

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

## 相关代码
- 资产路由: `backend/src/api/v1/assets/`
- 资产模型: `backend/src/models/asset.py`
- 资产服务: `backend/src/services/asset/`
