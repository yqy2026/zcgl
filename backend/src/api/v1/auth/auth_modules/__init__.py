"""
认证相关API路由 - 子模块包

认证功能已拆分到以下子模块:
- authentication.py: 认证端点（登录、登出、刷新令牌）
- users.py: 用户管理端点（CRUD、锁定、激活）
- sessions.py: 会话管理端点（查询、撤销）
- audit.py: 审计日志端点
- security.py: 安全配置端点
"""

from fastapi import APIRouter

from . import audit, authentication, security, sessions, users

# 创建主路由器
router = APIRouter()

# 包含子路由器 (每个子路由器定义自己的路径前缀)
router.include_router(authentication.router, tags=["认证管理"])
router.include_router(users.router, tags=["用户管理"])
router.include_router(sessions.router, tags=["会话管理"])
router.include_router(audit.router, tags=["审计日志"])
router.include_router(security.router, tags=["安全配置"])

__all__ = ["router"]
