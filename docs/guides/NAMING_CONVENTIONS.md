# 全局命名规范标准

> **最后更新**: 2026-01-23
> **适用范围**: 前端、后端、数据库、API

---

## 1. 总体原则

| 层级 | 命名风格 | 示例 |
|------|---------|------|
| **Python 后端** | `snake_case` | `page_size`, `created_at`, `user_id` |
| **TypeScript 前端** | `camelCase` | `pageSize`, `createdAt`, `userId` |
| **数据库字段** | `snake_case` | `page_size`, `created_at` |
| **API 响应字段** | `snake_case` | 后端返回 `snake_case`，前端自动转换 |

---

## 2. 后端 Python 命名规范

### 2.1 类名 (Classes)
```python
# ✅ 正确 - PascalCase
class AssetService:
class RentContractCRUD:
class UserResponse:

# ❌ 错误
class asset_service:
class rentContractCrud:
```

### 2.2 函数与方法
```python
# ✅ 正确 - snake_case
def get_assets():
def calculate_occupancy_rate():
async def create_rent_contract():
```

### 2.3 变量与属性
```python
# ✅ 正确 - snake_case
property_name = "示例物业"
page_size = 20
current_user = get_current_user()
```

### 2.4 常量
```python
# ✅ 正确 - UPPER_SNAKE_CASE
SECRET_KEY = "xxx"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_PAGE_SIZE = 20
```

### 2.5 Pydantic Schema 字段
```python
# ✅ 正确 - snake_case，统一使用 page_size
class ListRequest(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)  # 统一标准

# ❌ 禁止使用
limit: int       # 错误
size: int        # 错误
pageSize: int    # 错误
```

---

## 3. 前端 TypeScript 命名规范

### 3.1 组件
```typescript
// ✅ 正确 - PascalCase
const AssetForm: React.FC = () => {};
// 文件名: AssetForm.tsx
```

### 3.2 接口与类型
```typescript
// ✅ 正确 - PascalCase
interface AssetFormProps {}
interface User {}
type PermissionScope = 'global' | 'organization';
```

### 3.3 函数与变量
```typescript
// ✅ 正确 - camelCase
const pageSize = 20;
const isLoading = true;
function handleSubmit() {}
```

### 3.4 分页类型定义
```typescript
// ✅ 正确 - camelCase
interface PaginationParams {
  page: number;
  pageSize: number;  // 统一标准
}

// ❌ 禁止使用
limit: number;    // 错误
size: number;     // 错误
```

---

## 4. 分页字段统一标准 ⚠️

### 后端标准
```python
page: int = Field(1, ge=1, description="页码")
page_size: int = Field(20, ge=1, le=100, description="每页大小")
```

### 前端标准
```typescript
interface PaginationParams {
  page: number;
  pageSize: number;
}
```

### 响应格式
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

---

## 5. 数据库命名规范

- **表名**: `snake_case` 复数 (`assets`, `rent_contracts`)
- **字段名**: `snake_case` (`property_name`, `created_at`)
- **外键**: `target_table_id` (`user_id`, `asset_id`)

---

## 6. API 路径命名规范

```
# ✅ 正确 - kebab-case
GET  /api/v1/rent-contracts
GET  /api/v1/assets/{id}/attachments
POST /api/v1/user-permissions

# ❌ 错误
/api/v1/rentContracts      # camelCase
/api/v1/rent_contracts     # snake_case
/api/v1/RentContracts      # PascalCase
```

---

## 7. 布尔值命名规范

| 前缀 | 用途 | Python 示例 | TypeScript 示例 |
|------|------|-------------|-----------------|
| `is_` / `is` | 状态判断 | `is_active`, `is_deleted` | `isActive`, `isDeleted` |
| `has_` / `has` | 拥有判断 | `has_permission`, `has_children` | `hasPermission`, `hasChildren` |
| `can_` / `can` | 能力判断 | `can_edit`, `can_delete` | `canEdit`, `canDelete` |
| `should_` / `should` | 建议判断 | `should_notify` | `shouldNotify` |

```python
# ✅ 正确
is_active: bool = True
has_attachments: bool = False
can_approve: bool = check_permission(user)

# ❌ 错误
active: bool          # 缺少前缀，语义不明确
enabled: bool         # 建议用 is_enabled
```

---

## 8. 枚举命名规范

### Python Enum
```python
# ✅ 正确 - 类名 PascalCase，成员 UPPER_SNAKE_CASE
class ContractStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"

class AssetType(str, Enum):
    LAND = "land"
    BUILDING = "building"
    EQUIPMENT = "equipment"
```

### TypeScript Enum / Union
```typescript
// ✅ 正确 - 推荐使用 Union Type
type ContractStatus = 'draft' | 'active' | 'expired' | 'terminated';

// ✅ 也可以 - Enum 成员 PascalCase
enum AssetType {
  Land = 'land',
  Building = 'building',
  Equipment = 'equipment',
}
```

---

## 9. 文件命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| **Python 模块** | `snake_case.py` | `rent_contract.py`, `asset_service.py` |
| **React 组件** | `PascalCase.tsx` | `AssetForm.tsx`, `ContractList.tsx` |
| **TypeScript 工具** | `camelCase.ts` | `apiClient.ts`, `formatDate.ts` |
| **类型定义** | `camelCase.ts` 或 `PascalCase.ts` | `asset.ts`, `Contract.ts` |
| **常量文件** | `camelCase.ts` | `constants.ts`, `config.ts` |
| **样式文件** | `PascalCase.module.css` | `AssetForm.module.css` |

---

## 10. 检查清单

- ✓ 后端 Python 代码使用 `snake_case`
- ✓ 前端 TypeScript 代码使用 `camelCase`
- ✓ 分页字段: 后端 `page_size` / 前端 `pageSize`
- ✓ 类名使用 `PascalCase`
- ✓ 常量使用 `UPPER_SNAKE_CASE`
- ✓ API 路径使用 `kebab-case`
- ✓ 布尔值使用语义前缀 (`is_`, `has_`, `can_`)
- ✓ 枚举成员使用 `UPPER_SNAKE_CASE` (Python)
