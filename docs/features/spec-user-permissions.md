# 用户权限规格

> ⚠️ **状态变更（2026-02-09）**  
> 本文档已降级为历史草稿，不再作为需求权威来源。  
> 当前权威规格请使用：`docs/requirements-specification.md`  
> 模块证据附录请使用：`docs/features/requirements-appendix-modules.md`

## ✅ Status
**当前状态**: Historical Draft (2026-02-09)

## 角色模型
- 基础角色: `admin`, `user`
- 角色定义: `backend/src/models/auth.py`

## RBAC
- 角色与权限绑定由 RBAC 服务维护
- 关键实现: `backend/src/services/permission/rbac_service.py`

## 权限控制点
- API 层鉴权: `backend/src/middleware/auth.py`
- 角色管理 API: `/api/v1/roles`

## 说明
具体权限清单与接口限制以代码与数据库配置为准。
