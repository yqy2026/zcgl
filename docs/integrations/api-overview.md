# API 总览

## ✅ Status
**当前状态**: Active Baseline (2026-02-09)

> 说明：本页提供 API 导航与约束摘要。  
> 需求语义与验收口径以 `docs/requirements-specification.md` 为准。

## 基础信息
- **Base URL**: `/api/v1`
- **认证方式**: Cookie 为主（登录后服务端设置 HttpOnly Cookie）
- **版本策略**: 所有 API 路径统一以 `/api/v1/*` 版本化

## 认证与安全
- 登录成功后设置 `access_token` 与 `refresh_token` Cookie
- 请求需要携带 Cookie，部分接口要求管理员权限
- 详细见：[认证 API](auth-api.md)

## 响应与错误处理
- 各模块响应结构可能不同，以具体接口与 schema 为准
- 通用错误响应使用 HTTP 状态码与 `detail` 字段

## 分页与过滤
- 列表类接口通常支持分页与查询参数
- 以具体接口定义为准（见对应路由文件）

## 相关代码
- 路由入口: `backend/src/api/v1/__init__.py`
- Schema 定义: `backend/src/schemas/`
- 响应封装: `backend/src/core/response_handler.py`
