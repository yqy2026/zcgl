"""
认证相关API路由 - 主路由器

认证功能已拆分到以下子模块 (auth_modules/):
- authentication.py: 认证端点（登录、登出、刷新令牌）
- users.py: 用户管理端点（CRUD、锁定、激活）
- sessions.py: 会话管理端点（查询、撤销）
- audit.py: 审计日志端点
- security.py: 安全配置端点

[REFACTORED] Original 952-line monolithic file has been split into focused modules.
Each module handles a single responsibility, following the Single Responsibility Principle.

Backward Compatibility:
- All existing API endpoints remain at the same URLs
- Sub-routers are included with appropriate prefixes
- Example: POST /api/v1/auth/login → authentication.router with prefix="/login"
"""

from fastapi import APIRouter
from .auth_modules import router as auth_modules_router

# Use the router from auth_modules which includes all sub-routers
router = auth_modules_router

__all__ = ["router"]
