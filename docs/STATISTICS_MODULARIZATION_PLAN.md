# Statistics.py 模块化设计方案

**日期**: 2026-01-17
**目标文件**: `backend/src/api/v1/statistics.py` (1,259 lines)
**目标**: 拆分为 5 个功能模块，主文件减少到 ~50 行

---

## 端点分组分析

### 当前端点（17个）

| 端点 | 行数估算 | 功能域 | 目标模块 |
|------|---------|--------|----------|
| `/` (get_basic_statistics) | ~160 | 基础统计 | basic_stats.py |
| `/summary` | ~80 | 基础统计 | basic_stats.py |
| `/occupancy-rate/overall` | ~40 | 占用率 | occupancy_stats.py |
| `/occupancy-rate/by-category` | ~70 | 占用率 | occupancy_stats.py |
| `/occupancy-rate` | ~60 | 占用率 | occupancy_stats.py |
| `/area-summary` | ~40 | 面积统计 | area_stats.py |
| `/area-statistics` | ~50 | 面积统计 | area_stats.py |
| `/financial-summary` | ~100 | 财务统计 | financial_stats.py |
| `/ownership-distribution` | ~60 | 分布统计 | distribution.py |
| `/property-nature-distribution` | ~50 | 分布统计 | distribution.py |
| `/usage-status-distribution` | ~60 | 分布统计 | distribution.py |
| `/asset-distribution` | ~60 | 分布统计 | distribution.py |
| `/trend/{metric}` | ~70 | 趋势分析 | trend_stats.py |
| `/dashboard-data` | ~140 | 综合仪表盘 | basic_stats.py |
| `/comprehensive` | ~140 | 综合统计 | basic_stats.py |
| `/cache/clear` | ~20 | 缓存管理 | basic_stats.py |
| `/cache/info` | ~20 | 缓存管理 | basic_stats.py |

**总计**: ~1,220 行代码 + ~40 行导入和定义

---

## 模块设计

```
statistics.py (主文件) - 50 行
├── 导入所有子模块路由
├── 聚合路由
└── 注册到应用

statistics_modules/
├── __init__.py - 导出所有路由
├── basic_stats.py - 基础统计和仪表盘 (~350 lines)
│   ├── GET / - 基础统计
│   ├── GET /summary - 统计摘要
│   ├── GET /dashboard-data - 仪表盘数据
│   ├── GET /comprehensive - 综合统计
│   ├── POST /cache/clear - 清除缓存
│   └── GET /cache/info - 缓存信息
│
├── occupancy_stats.py - 占用率统计 (~170 lines)
│   ├── GET /occupancy-rate/overall - 总体占用率
│   ├── GET /occupancy-rate/by-category - 分类占用率
│   └── GET /occupancy-rate - 占用率统计
│
├── area_stats.py - 面积统计 (~90 lines)
│   ├── GET /area-summary - 面积摘要
│   └── GET /area-statistics - 面积统计
│
├── financial_stats.py - 财务统计 (~100 lines)
│   └── GET /financial-summary - 财务摘要
│
├── distribution.py - 分布统计 (~230 lines)
│   ├── GET /ownership-distribution - 产权分布
│   ├── GET /property-nature-distribution - 物业性质分布
│   ├── GET /usage-status-distribution - 使用状态分布
│   └── GET /asset-distribution - 资产分布（已应用字段验证）
│
└── trend_stats.py - 趋势分析 (~70 lines)
    └── GET /trend/{metric} - 趋势数据
```

---

## 共享代码

### 共享模型（保留在主文件）

```python
# Pydantic models shared across modules
- BasicStatisticsResponse
- OccupancyRateStatsResponse
- AreaSummaryResponse
- FinancialSummaryResponse
- TrendDataResponse
```

### 共享依赖

```python
# Common imports for all modules
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...crud.asset import asset as asset_crud
```

---

## 迁移策略

### 阶段 1: 创建模块结构
1. 创建 `statistics_modules/` 目录
2. 创建 6 个模块文件
3. 设置 `__init__.py` 导出

### 阶段 2: 迁移端点
1. **basic_stats.py** - 迁移基础统计端点（6个）
2. **occupancy_stats.py** - 迁移占用率端点（3个）
3. **area_stats.py** - 迁移面积统计端点（2个）
4. **financial_stats.py** - 迁移财务统计端点（1个）
5. **distribution.py** - 迁移分布统计端点（4个）
6. **trend_stats.py** - 迁移趋势分析端点（1个）

### 阶段 3: 更新主文件
1. 删除已迁移的端点代码
2. 导入所有子路由
3. 使用 `router.include_router()` 聚合

### 阶段 4: 测试
1. 验证所有端点 URL 保持不变
2. 运行集成测试
3. 手动测试关键端点

---

## 代码示例

### 新的 statistics.py (主文件)

```python
"""
统计分析API - 主路由聚合器

本文件已重构为模块化架构：
- 业务逻辑分散到 statistics_modules/ 子模块
- 保持所有原有 URL 路径和响应格式
- 完全向后兼容

模块结构:
- basic_stats.py - 基础统计和仪表盘
- occupancy_stats.py - 占用率统计
- area_stats.py - 面积统计
- financial_stats.py - 财务统计
- distribution.py - 分布统计
- trend_stats.py - 趋势分析
"""

from fastapi import APIRouter
from .statistics_modules import (
    basic_stats_router,
    occupancy_stats_router,
    area_stats_router,
    financial_stats_router,
    distribution_router,
    trend_stats_router,
)

# 主路由器
router = APIRouter()

# 聚合所有子模块路由
router.include_router(basic_stats_router)
router.include_router(occupancy_stats_router)
router.include_router(area_stats_router)
router.include_router(financial_stats_router)
router.include_router(distribution_router)
router.include_router(trend_stats_router)
```

### statistics_modules/__init__.py

```python
"""
统计模块导出

导出所有子模块的路由器
"""

from .basic_stats import router as basic_stats_router
from .occupancy_stats import router as occupancy_stats_router
from .area_stats import router as area_stats_router
from .financial_stats import router as financial_stats_router
from .distribution import router as distribution_router
from .trend_stats import router as trend_stats_router

__all__ = [
    "basic_stats_router",
    "occupancy_stats_router",
    "area_stats_router",
    "financial_stats_router",
    "distribution_router",
    "trend_stats_router",
]
```

### statistics_modules/distribution.py (示例)

```python
"""
分布统计模块

提供资产分布统计端点:
- 产权分布
- 物业性质分布
- 使用状态分布
- 自定义字段分布（带字段验证）
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...crud.asset import asset as asset_crud
from ...security.field_validator import FieldValidator

router = APIRouter()

@router.get("/asset-distribution", summary="获取资产分布统计")
async def get_asset_distribution(
    group_by: str = Query("ownership_status", description="分组字段"),
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """获取资产分布统计数据（带字段验证）"""
    # 字段验证（Phase 1 安全改进）
    FieldValidator.validate_group_by_field("Asset", group_by, raise_on_invalid=True)

    # 业务逻辑...
    ...

# ... 其他分布统计端点
```

---

## 向后兼容性保证

✅ **URL 路径不变**
- 所有端点路径保持完全相同
- 例如: `/api/v1/statistics/asset-distribution` 仍然有效

✅ **响应格式不变**
- 所有响应模型保持原样
- 客户端无需任何修改

✅ **依赖注入不变**
- 权限检查、数据库会话等保持一致

---

## 预期收益

### 代码质量
- ✅ 每个文件 < 400 行（符合 Google Python Style Guide）
- ✅ 职责单一（符合 SOLID 原则）
- ✅ 更易于理解和维护

### 开发体验
- ✅ 更快的 IDE 加载速度
- ✅ 更好的代码导航
- ✅ 减少合并冲突

### 测试
- ✅ 可以独立测试每个模块
- ✅ 更清晰的测试结构
- ✅ 更好的测试覆盖率

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| URL 路由冲突 | 中 | 保持所有路由路径不变 |
| 导入循环依赖 | 低 | 共享代码放在主文件或 utils |
| 测试中断 | 中 | 迁移后立即运行测试 |
| 遗漏端点 | 低 | 使用清单逐一迁移 |

---

## 实施时间估算

- **模块创建**: 30 分钟
- **端点迁移**: 2-3 小时（每个模块 30-40 分钟）
- **测试验证**: 1 小时
- **总计**: ~4 小时

---

**下一步**: 创建模块结构并开始迁移
