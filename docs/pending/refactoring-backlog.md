# 待处理重构任务清单

**创建日期**: 2026-02-13
**来源**: 项目基础性问题完整修复清单（部分中高风险任务）

---

## 概述

本文档记录了需要更多规划和时间的重构任务。这些任务在 2026-02-13 的修复批次中被识别，但由于风险较高或工作量较大，需要单独规划迭代。

---

## 1. 前端状态管理反模式重构

**优先级**: 高
**风险**: 中
**预估工作量**: 3-5 天

### 问题描述

以下页面使用 `useState + useEffect` 管理 API 数据，违反 React Query 最佳实践：

| 文件 | 路径 |
|------|------|
| DictionaryPage.tsx | `frontend/src/pages/System/DictionaryPage.tsx` |
| EnumFieldPage.tsx | `frontend/src/pages/System/EnumFieldPage.tsx` |
| OrganizationPage.tsx | `frontend/src/pages/System/OrganizationPage.tsx` |
| AssetImport.tsx | `frontend/src/components/Asset/AssetImport.tsx` |

### 重构方案

#### 示例：DictionaryPage 重构

**1. 创建自定义 Hook**

```typescript
// frontend/src/hooks/useDictionaryTypes.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dictionaryService } from '@/services';

export function useDictionaryTypes() {
  return useQuery({
    queryKey: ['dictionary-types'],
    queryFn: () => dictionaryService.getTypes(),
    staleTime: 5 * 60 * 1000, // 5 分钟
  });
}

export function useCreateDictionaryType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dictionaryService.createType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dictionary-types'] });
    },
  });
}
```

**2. 重构组件**

```typescript
// 修改前:
const [dictTypes, setDictTypes] = useState<string[]>([]);
const [loading, setLoading] = useState(false);

useEffect(() => {
  setLoading(true);
  dictionaryService.getTypes()
    .then(setDictTypes)
    .finally(() => setLoading(false));
}, []);

// 修改后:
const { data: dictTypes = [], isLoading } = useDictionaryTypes();
```

### 验收标准

- [ ] 所有目标页面使用 React Query
- [ ] 移除手动的 loading 状态管理
- [ ] 测试覆盖率保持或提升
- [ ] 无功能回归

---

## 2. 超大组件拆分

**优先级**: 中
**风险**: 中
**预估工作量**: 5-7 天

### 问题描述

以下组件超过 800 行，需要拆分为更小的子组件：

| 文件 | 行数 | 建议拆分方案 |
|------|------|-------------|
| UserManagementPage.tsx | 946 | 用户列表 + 用户表单 + 权限分配 |
| EnumFieldPage.tsx | 927 | 字段列表 + 字段编辑器 + 值管理 |
| RoleManagementPage.tsx | 921 | 角色列表 + 权限矩阵 + 角色表单 |
| OperationLogPage.tsx | 919 | 日志列表 + 详情抽屉 + 筛选器 |
| OrganizationPage.tsx | 823 | 组织树 + 成员管理 + 表单 |

### 拆分模式

以 `UserManagementPage` 为例：

```
frontend/src/pages/System/UserManagement/
├── index.tsx              # 主页面（容器）
├── UserList.tsx           # 用户列表表格
├── UserForm.tsx           # 新增/编辑表单
├── PermissionAssign.tsx   # 权限分配对话框
├── hooks/
│   ├── useUsers.ts        # 用户数据 Hook
│   └── useUserMutations.ts # 用户操作 Hook
├── types.ts               # 类型定义
└── UserManagement.module.css
```

### 主页面重构示例

```typescript
// frontend/src/pages/System/UserManagement/index.tsx
export default function UserManagementPage() {
  const { data: users, isLoading } = useUsers();
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  return (
    <PageContainer>
      <UserList
        users={users}
        loading={isLoading}
        onSelect={setSelectedUser}
      />
      <UserForm
        user={selectedUser}
        onClose={() => setSelectedUser(null)}
      />
    </PageContainer>
  );
}
```

### 验收标准

- [ ] 每个子组件不超过 300 行
- [ ] 保持功能完整性
- [ ] 提升代码可测试性
- [ ] 测试通过

---

## 3. PDF 测试跳过问题

**优先级**: 低
**风险**: 低
**预估工作量**: 1-2 天（需先确认需求）

### 问题描述

`backend/tests/unit/services/document/extractors/test_base.py` 中有 12 个测试被跳过，原因是 `pdf_to_images module not yet implemented`。

### 选项分析

| 选项 | 描述 | 工作量 |
|------|------|--------|
| A: 实现模块 | 创建 `pdf_to_images.py` 使用 PyMuPDF | 1-2 天 |
| B: 移除测试 | 如果 PDF 处理功能不再计划实现 | 0.5 天 |
| C: 保持现状 | 添加 TODO 注释，后续规划 | 0 天 |

### 如果选择选项 A

```python
# backend/src/services/document/extractors/pdf_to_images.py
"""
PDF 转图像模块
"""
from pathlib import Path
from typing import List
import fitz  # PyMuPDF


def pdf_to_images(pdf_path: Path, dpi: int = 150) -> List[bytes]:
    """将 PDF 页面转换为图像"""
    doc = fitz.open(pdf_path)
    images = []

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append(pix.tobytes("png"))

    return images
```

### 验收标准

- [ ] 确认 PDF 处理功能需求
- [ ] 根据需求选择合适的选项
- [ ] 移除或修复所有跳过的测试

---

## 4. Decimal/Number 类型转换完善

**优先级**: 低
**风险**: 低
**预估工作量**: 渐进式（新功能中应用）

### 问题描述

后端使用 `Decimal` 类型存储金额和面积，前端使用 `number`。虽然 `DecimalUtils` 工具已存在，但未在所有 API 响应处理中统一应用。

### 现有工具

```typescript
// frontend/src/utils/dataConversion.ts
export const convertBackendToFrontend = <T = unknown>(data: unknown): T => {
  // 自动转换 DECIMAL_FIELDS 中的字段
};

// frontend/src/types/asset.ts
export const DecimalUtils = {
  toNumber: (value: unknown): number => { ... },
  toString: (value: unknown): string => { ... },
};
```

### 需要检查的字段

```bash
cd frontend
grep -r "\.land_area\|\.actual_property_area\|\.rentable_area\|\.monthly_rent\|\.deposit" src/
```

### 渐进式改进方案

1. **新功能**: 在新 API 调用中使用 `convertBackendToFrontend`
2. **类型定义**: 确保 `AssetResponse` 类型已声明为 `number`（已转换）
3. **文档**: 在 `frontend/CLAUDE.md` 中记录最佳实践

### 验收标准

- [ ] 新功能使用 DecimalUtils
- [ ] 更新前端类型定义
- [ ] 添加开发指南文档

---

## 执行顺序建议

```
第 1 周: 问题 1 (状态管理) - DictionaryPage, EnumFieldPage
第 2 周: 问题 1 (状态管理) - OrganizationPage, AssetImport
第 3 周: 问题 2 (组件拆分) - UserManagementPage
第 4 周: 问题 2 (组件拆分) - RoleManagementPage
第 5 周: 问题 2 (组件拆分) - OperationLogPage, OrganizationPage
持续进行: 问题 4 (Decimal 转换)
待定: 问题 3 (PDF 测试) - 需先确认需求
```

---

## 相关文档

- [前端开发指南](../guides/frontend.md)
- [测试标准](../guides/testing-standards.md)
- [CLAUDE.md](../../CLAUDE.md)
