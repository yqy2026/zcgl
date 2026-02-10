# 全局命名规范标准

> **最后更新**: 2026-01-23
> **适用范围**: 前端、后端、数据库、API

---

## 1. 总体原则

| 层级 | 命名风格 | 示例 |
|------|---------|------|
| **Python 后端** | `snake_case` | `page_size`, `created_at`, `user_id` |
| **TypeScript 前端 (API 相关)** | `snake_case` | `page_size`, `is_active`, `created_at` |
| **TypeScript 前端 (纯 UI 逻辑)** | `camelCase` | `isLoading`, `handleSubmit` |
| **数据库字段** | `snake_case` | `page_size`, `created_at` |
| **API 请求/响应字段** | `snake_case` | 前后端统一，零转换 |

### 设计理念

**全栈统一 `snake_case`** - API 相关的类型、参数、响应字段全部使用 `snake_case`，消除前后端命名转换的心智负担。

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
# limit: int       # 错误 - 应使用 page_size
# size: int        # 错误 - 应使用 page_size
# pageSize: int    # 错误 - 应使用 page_size
```

---

## 3. 前端 TypeScript 命名规范

### 3.1 组件
```typescript
// ✅ 正确 - PascalCase
const AssetForm: React.FC = () => {};
// 文件名: AssetForm.tsx
```

### 3.2 接口与类型（API 相关）
```typescript
// ✅ 正确 - 字段使用 snake_case（与后端一致）
interface AssetQueryParams {
  page: number;
  page_size: number;  // 统一标准
  is_active?: boolean;
}

interface AssetListResponse {
  items: Asset[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ❌ 禁止使用
// pageSize: number;  // 错误 - 应使用 page_size
// limit: number;     // 错误 - 应使用 page_size
// size: number;      // 错误 - 应使用 page_size
```

### 3.3 函数与变量
```typescript
// ✅ 纯 UI 逻辑使用 camelCase
const isLoading = true;
const handleSubmit = () => {};

// ✅ API 交互时的命名转换见「第 4 节 分页字段统一标准」
```

### 3.4 ESLint 配置
```javascript
// .eslintrc.js - 允许 snake_case
rules: {
  '@typescript-eslint/naming-convention': [
    'error',
    {
      selector: 'variable',
      format: ['camelCase', 'snake_case', 'UPPER_CASE'],
    },
  ],
}
```

---

## 4. 分页字段统一标准 ⚠️

### 后端标准
```python
page: int = Query(1, ge=1, description="页码")
page_size: int = Query(20, ge=1, le=100, description="每页大小")
```

### 前端标准
```typescript
interface PaginationParams {
  page: number;
  page_size: number;  // 与后端完全一致
}
```

### 响应格式
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

### 前端使用
```typescript
// ✅ 正确 - React state 使用 camelCase，API 交互使用 snake_case
const [pageSize, setPageSize] = useState(20);
const params = { page, page_size: pageSize };  // 发送时映射

// 读取响应 - 保持 snake_case 或按需转换
const { items, total, page_size } = response;
const displayPageSize = page_size;  // 可赋值给 camelCase 变量用于 UI
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
GET  /api/v1/rental-contracts/contracts
GET  /api/v1/assets/{id}/attachments
POST /api/v1/user-permissions

# ❌ 错误
/api/v1/rentContracts      # camelCase
/api/v1/rent_contracts     # snake_case
/api/v1/RentContracts      # PascalCase
```

---

## 7. 布尔值命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `is_` | 状态判断 | `is_active`, `is_deleted` |
| `has_` | 拥有判断 | `has_permission`, `has_children` |
| `can_` | 能力判断 | `can_edit`, `can_delete` |
| `should_` | 建议判断 | `should_notify` |

```python
# ✅ 正确
is_active: bool = True
has_attachments: bool = False
can_approve: bool = check_permission(user)

# ❌ 错误
active = True         # 缺少前缀，语义不明确
enabled = False       # 建议用 is_enabled
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

// ✅ 也可以 - Enum 成员使用 PascalCase（TypeScript 惯例）
enum AssetType {
  Land = 'land',
  Building = 'building',
  Equipment = 'equipment',
}
// 注意：TypeScript 使用 PascalCase，Python 使用 UPPER_SNAKE_CASE
```

---

## 9. 文件命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| **Python 模块** | `snake_case.py` | `rent_contract.py`, `asset_service.py` |
| **React 组件** | `PascalCase.tsx` | `AssetForm.tsx`, `ContractList.tsx` |
| **TypeScript 工具** | `camelCase.ts` | `apiClient.ts`, `formatDate.ts` |
| **类型定义** | `camelCase.ts` | `assetType.ts`, `contractDetail.ts`, `rentContract.ts` |
| **常量文件** | `camelCase.ts` | `constants.ts`, `config.ts` |
| **样式文件** | `PascalCase.module.css` | `AssetForm.module.css` |

---

## 10. 检查清单

- ✓ 后端 Python 代码使用 `snake_case`
- ✓ 前端 API 相关字段使用 `snake_case`（与后端统一）
- ✓ 分页字段: 全栈统一 `page_size`
- ✓ 类名使用 `PascalCase`
- ✓ 常量使用 `UPPER_SNAKE_CASE`
- ✓ API 路径使用 `kebab-case`
- ✓ 布尔值使用语义前缀 (`is_`, `has_`, `can_`)
- ✓ 枚举成员: Python 使用 `UPPER_SNAKE_CASE`，TypeScript 使用 `PascalCase`
- ✓ React state setter 使用 `camelCase` (如 `setPageSize`)
