# REQ-PRJ-002：项目详情按有效 project_assets 关系汇总资产

**状态**: ✅ 已完成  
**需求编号**: REQ-PRJ-002  
**里程碑**: M1（目标窗口 2026-03-04 ~ 2026-03-31）  
**作者**: GitHub Copilot  
**日期**: 2026-03-05  
**完成时间**: 2026-03-05

---

## 1. 问题诊断

### 当前实现的缺陷

前端 `ProjectDetailPage` 调用：
```typescript
assetService.getAssets({ project_id: id, page: 1, page_size: 100 })
```

但 `Asset` 表**不存在 `project_id` 列**。实际走的是 `project_name` 遗留字段模糊匹配（`Asset.project_name LIKE %...%`），属于无意义的兼容路径，结果不准确。

### REQ-PRJ-002 要求

> 默认统计范围为 `project_assets` 当前有效关系（`valid_to IS NULL`，`assets.data_status = '正常'`）。

---

## 2. 现有可复用基础

| 组件 | 位置 | 说明 |
|------|------|------|
| `project_asset_crud.get_project_assets()` | `backend/src/crud/project_asset.py` | 支持 `active_only=True`，过滤 `valid_to IS NULL` |
| `asset_crud.get_multi_by_ids_async()` | `backend/src/crud/asset.py:709` | 批量按 ID 拉取 Asset，支持 `include_deleted=False` |
| `AssetListItemResponse` | `backend/src/schemas/asset.py:506` | 轻量资产列表 schema，适合嵌套返回 |
| `ProjectService._resolve_party_filter()` | `backend/src/services/project/service.py` | 已有权限过滤逻辑，复用 |

---

## 3. 改动文件清单（6 个）

### 3.1 后端（4 个文件）

#### `backend/src/schemas/project.py`
新增两个 schema：

```python
class ProjectAssetSummary(BaseModel):
    """项目有效资产面积汇总。"""
    total_assets: int
    total_rentable_area: float
    total_rented_area: float
    occupancy_rate: float  # 百分制 0-100，保留 2 位小数

class ProjectActiveAssetsResponse(BaseModel):
    """项目有效关联资产列表响应。"""
    items: list[AssetListItemResponse]
    total: int
    summary: ProjectAssetSummary
```

#### `backend/src/services/project/service.py`
新增方法 `get_project_active_assets`：

```python
async def get_project_active_assets(
    self,
    db: AsyncSession,
    *,
    project_id: str,
    current_user_id: str | None = None,
) -> tuple[list[Asset], ProjectAssetSummary]:
    """
    获取项目当前有效关联资产列表及面积汇总。

    流程：
    1. 权限过滤（_resolve_party_filter）
    2. 校验项目存在（get_project_by_id）
    3. project_asset_crud.get_project_assets(active_only=True) 得到有效绑定
    4. asset_ids = list({pa.asset_id for pa in project_assets})  # 去重，防多条绑定
    5. asset_crud.get_multi_by_ids_async(asset_ids, include_deleted=False) 批量拉取
    6. assets = [a for a in assets if a.data_status == DataStatusValues.ASSET_NORMAL]  # 精确过滤，只保留 data_status='正常'
    7. 计算 summary（见下方 None 安全聚合方式）
    """
```

**关键约束**：
- `summary` 计算逻辑在 service 层完成，路由层不做业务计算（REQ-XCUT-002）
- 步骤 5 的 `include_deleted=False` 过滤语义为 `data_status != '已删除'`，**不等同于** `data_status = '正常'`（`data_status = '异常'` 等中间状态仍会通过）。因此步骤 6 的显式过滤是必须的，二者不可替代。
- `occupancy_rate = total_rented_area / total_rentable_area * 100`，当 `total_rentable_area == 0` 时返回 `0.0`，不触发除零异常
- `rentable_area` / `rented_area` 均为 `Decimal | None`，汇总时使用 `(a.rentable_area or Decimal(0))`，不能用裸 `sum()`

#### `backend/src/api/v1/assets/project.py`
新增端点（挂在现有 router 上）：

```
GET /projects/{project_id}/assets
response_model=APIResponse[ProjectActiveAssetsResponse]
summary="获取项目有效关联资产"
```

鉴权配置（与同文件 `GET /{project_id}` 完全一致，不得省略）：
```python
_authz_ctx: AuthzContext = Depends(
    require_authz(
        action="read",
        resource_type="project",
        resource_id="{project_id}",
        deny_as_not_found=True,
    )
)
```

端点只做：调用 `project_service.get_project_active_assets()`，将 Asset 列表转为 `AssetListItemResponse`，组装 `ProjectActiveAssetsResponse`，再用 `ResponseHandler.success()` 包装返回。

> 说明：同文件中列表端点统一用 `APIResponse[PaginatedData[...]]` 包装，单对象端点（`GET /{project_id}`、`PUT`、`POST`）返回裸 schema。本端点是"项目下资产列表"，属列表语义，使用 `APIResponse[ProjectActiveAssetsResponse]` 包装（不使用 `PaginatedData`，因为当前 M1 返回全量有效资产，无需分页）。

#### `backend/src/schemas/project.py` imports
需要引入 `AssetListItemResponse`：
```python
from ..schemas.asset import AssetListItemResponse
```

> ⚠️ **循环导入风险**：`asset.py` 依赖 `project.py` 的名称不存在，`project.py` 引用 `AssetListItemResponse` 是单向依赖，安全。

---

### 3.2 前端（2 个文件）

#### `frontend/src/services/projectService.ts`
新增方法：
```typescript
async getProjectAssets(projectId: string): Promise<ProjectActiveAssetsResponse>
```
调用 `GET /api/v1/projects/{projectId}/assets`，后端返回 `APIResponse<ProjectActiveAssetsResponse>`，前端用现有统一拦截器解包后取 `data` 字段。

类型定义新增到 **`frontend/src/types/project.ts`**（与项目现有类型组织一致，不新建文件）：
```typescript
export interface ProjectAssetSummary {
  total_assets: number;
  total_rentable_area: number;
  total_rented_area: number;
  occupancy_rate: number;
}

export interface ProjectActiveAssetsResponse {
  items: Asset[];
  total: number;
  summary: ProjectAssetSummary;
}
```

#### `frontend/src/pages/Project/ProjectDetailPage.tsx`
将：
```typescript
queryFn: () => assetService.getAssets({ project_id: id, page: 1, page_size: 100 })
```
替换为：
```typescript
queryFn: () => projectService.getProjectAssets(id as string)
```

统计数据读取从 `response.summary` 取值（不再前端全量计算），`useMemo` 块简化为：
```typescript
const summary = assetsData?.summary ?? { total_rentable_area: 0, total_rented_area: 0, occupancy_rate: 0 };
```

---

## 4. 测试用例

### 4.1 单元测试（新增）

**`backend/tests/unit/services/project/test_project_service.py`**

| 用例名 | 验证点 |
|--------|--------|
| `test_get_project_active_assets_filters_inactive` | `valid_to` 有值的绑定不出现在结果中 |
| `test_get_project_active_assets_excludes_deleted_assets` | `data_status='已删除'` 的资产不返回 |
| `test_get_project_active_assets_summary_zero_rentable_area` | `total_rentable_area=0` 时 `occupancy_rate=0.0`，不触发 ZeroDivisionError |
| `test_get_project_active_assets_empty_project` | 无有效绑定时返回空列表 + summary 全零 |

**`backend/tests/unit/api/v1/test_project.py`**

| 用例名 | 验证点 |
|--------|--------|
| `test_get_project_assets_endpoint_returns_200` | 正常调用返回 200 + `items/total/summary` 结构 |
| `test_get_project_assets_endpoint_not_found` | 项目不存在返回 404 |

---

## 5. 关于"双入口进入合同组"的说明

REQ-PRJ-002 验收条件第二项：
> 资产、项目双入口可进入同一合同组详情。

ContractGroup 实体尚未建立（REQ-RNT-001 📋，M2 范围），无法实现导航入口。  
**本次不实现此条**，在 `requirements-specification.md` REQ-PRJ-002 验收条件旁添加注备：`（合同组双入口，M2 实现，依赖 REQ-RNT-001）`。

---

## 6. SSOT 联动动作

实施完成后必须执行：

| 动作 | 文件 |
|------|------|
| REQ-PRJ-002 状态改为 ✅ | `docs/requirements-specification.md` |
| 追踪矩阵第 11 节补入代码证据 | `docs/requirements-specification.md` |
| 本方案移入 archive/ | `docs/archive/backend-plans/` |
| `plans/README.md` 更新 | 从活跃方案移除本行 |
| `CHANGELOG.md` 更新 | 记录本次变更 |

---

## 7. 边界情况

1. **同一资产多次绑定同一项目**（多条 `valid_to IS NULL` 记录）：service 层用 set comprehension `list({pa.asset_id for pa in project_assets})` 显式去重后再调用 `get_multi_by_ids_async`，资产只出现一次，不重复计算面积。
2. **项目无 `manager_party_id`**（数据迁移遗留场景）：权限过滤不依赖 `manager_party_id` 直接 fail-close，正常降级返回结果。
3. **大量资产**（> 1000 条）：`get_multi_by_ids_async` 用 `IN` 查询，PostgreSQL 支持；M1 数据量上限 5000 资产，无需分页，但端点预留 `page/page_size` 参数供后续扩展（当前不实现分页逻辑，直接返回全量有效资产）。
4. **并发 unbind + 请求**：`valid_to IS NULL` 过滤在数据库层执行，天然一致，无需额外锁。
