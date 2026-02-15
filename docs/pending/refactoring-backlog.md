# 待处理重构任务清单

**创建日期**: 2026-02-13
**最后校准**: 2026-02-15
**来源**: 项目基础性问题完整修复清单（部分中高风险任务）

---

## 概述

本文档记录需要独立迭代的重构任务。2026-02-14 已根据当前代码基线完成一次校准，重点修正了已过期描述并重排执行顺序，降低重复施工风险。

### 本次校准结论（摘要）

- `OrganizationPage` 已使用 React Query，不再归类为“纯反模式页面”
- `backend/src/services/document/pdf_to_images.py` 已实现，PDF 任务从“实现模块”调整为“测试与注释校准”
- `Decimal/Number` 转换从“低优先级”提升为“中优先级”，先做链路统一入口

---

## 1. 前端数据获取模式统一（React Query / Mutation）

**优先级**: 高
**风险**: 中
**预估工作量**: 4-6 天

### 问题描述

以下页面仍存在 `useState + useEffect + 手动 loading` 的数据流模式，维护成本高，且缓存与失效策略不统一：

| 文件 | 路径 | 当前问题 |
|------|------|----------|
| DictionaryPage.tsx | `frontend/src/pages/System/DictionaryPage.tsx` | 多处手动 `fetch*` 与 `setLoading` |
| EnumFieldPage.tsx | `frontend/src/pages/System/EnumFieldPage.tsx` | 列表/统计/值管理并行请求均手动管理 |
| AssetImport.tsx | `frontend/src/components/Asset/AssetImport.tsx` | 命令式导入流程未统一到 mutation 模式 |

说明：`OrganizationPage.tsx` 已在当前基线中使用 React Query，不再列入本任务范围。

### 重构策略

1. **读操作统一为 `useQuery`**：字典类型、字典值、统计等查询使用稳定 `queryKey`
2. **写操作统一为 `useMutation`**：增删改与导入操作统一 mutation 生命周期
3. **失效策略显式化**：mutation 成功后仅失效受影响 key，避免全页手动重刷
4. **错误处理统一化**：将重复 toast/try-catch 模式收敛到 hook 层

### 分批计划

- 批次 A（2 天）：`DictionaryPage`（已完成，2026-02-14）
- 批次 B（2 天）：`EnumFieldPage`（已完成，2026-02-14）
- 批次 C（1-2 天）：`AssetImport` 改造为 `useMutation` 驱动的导入流程（已完成，2026-02-14）

### 验收标准

- [x] `DictionaryPage` 与 `EnumFieldPage` 不再通过 `useEffect` 直接调用 `dictionaryService`
- [x] `AssetImport` 主导入动作使用 `useMutation`
- [x] 查询 key 命名统一且可追踪（页面内不再散落手动刷新链）
- [x] 受影响页面无功能回归（创建、编辑、删除、刷新、导入）

---

## 2. 超大组件拆分

**优先级**: 中
**风险**: 中
**预估工作量**: 6-8 天

### 问题描述

以下页面体量过大（当前基线统计），单文件承载过多状态、渲染与事件逻辑：

| 文件 | 行数（当前） | 建议拆分方向 |
|------|-------------|-------------|
| UserManagementPage.tsx | 959 | 列表 + 表单 + 权限分配 |
| EnumFieldPage.tsx | 927 | 类型列表 + 值列表 + 编辑弹窗 |
| RoleManagementPage.tsx | 921 | 角色列表 + 权限矩阵 + 角色表单 |
| OperationLogPage.tsx | 919 | 列表 + 筛选器 + 详情抽屉 |
| OrganizationPage.tsx | 823 | 列表 + 组织树 + 历史记录 |
| PromptDashboard.tsx | 819 | 统计卡 + 图表 + 任务面板 |

### 拆分模式

以 `UserManagementPage` 为模板：

```
frontend/src/pages/System/UserManagement/
├── index.tsx                # 容器层（路由入口）
├── UserList.tsx             # 列表展示
├── UserForm.tsx             # 新增/编辑表单
├── PermissionAssign.tsx     # 权限分配
├── hooks/
│   ├── useUsers.ts          # 查询
│   └── useUserMutations.ts  # 写操作
├── types.ts
└── UserManagement.module.css
```

### 当前进展（2026-02-14）

- [x] `UserManagementPage` 已完成目录化拆分（`index.tsx` + `components/` + `hooks/` + `types.ts`）
- [x] `RoleManagementPage` 已完成目录化拆分（`index.tsx` + `components/` + `hooks/` + `types.ts`）
- [x] `OperationLogPage` 已完成目录化拆分（`index.tsx` + `components/` + `hooks/` + `types.ts/constants.tsx/utils.ts`）
- [x] `OrganizationPage` 已完成目录化拆分（`index.tsx` + `components/` + `hooks/` + `types.ts/constants.tsx/utils.tsx`）
- [x] `PromptDashboard` 已完成目录化拆分（`index.tsx` + `components/` + `hooks/` + `types.ts/constants.tsx/utils.ts`）
- [x] 结构验证完成：`madge` 扫描 5 个拆分目录共 99 文件，结果无循环依赖
- [x] 关键交互回归完成：`OrganizationPage`/`RoleManagementPage`/`UserManagementPage`/`OperationLogPage`/`PromptDashboard` 定向测试共 39 项通过（含筛选、编辑、提交、刷新、详情查看与错误分支）

### 验收标准

- [x] 容器组件建议控制在 `<= 350` 行，展示子组件建议 `<= 300` 行
- [x] 展示组件不直接包含服务层调用
- [x] 拆分后无循环依赖与跨层导入漂移
- [x] 关键交互回归通过（筛选、分页、编辑、提交、刷新）

---

## 3. Decimal/Number 转换链路统一

**优先级**: 中
**风险**: 中
**预估工作量**: 2-4 天（首批）+ 渐进推广

### 问题描述

后端金额/面积大量使用 `Decimal`，前端业务类型以 `number` 为主。虽然 `convertBackendToFrontend` 与 `DecimalUtils` 已存在，但尚未成为服务层统一返回入口，导致不同页面存在重复的手动转换与潜在精度/类型不一致。

### 首批改造范围

- 优先覆盖高频字段：`land_area`、`actual_property_area`、`rentable_area`、`monthly_rent`、`deposit/total_deposit`
- 在服务层建立统一转换出口（优先“服务方法返回前转换”，暂不做全局拦截器）
- 清理页面层分散的 `parseFloat`/类型兜底逻辑

### 渐进式方案

1. **入口统一**：在核心服务返回数据前调用 `convertBackendToFrontend`
2. **类型收敛**：前端类型定义与真实返回结构对齐，减少“string | number”扩散
3. **测试补齐**：为至少 1-2 个关键服务补充转换链路测试
4. **文档固化**：在 `frontend/CLAUDE.md` 增加“何时转换、在哪里转换”规范

### 验收标准

- [x] 首批高频字段在服务层统一转换，不依赖页面层临时 parse
- [x] 新增/改造服务包含对应单测或契约测试
- [x] 前端类型定义与转换策略一致
- [x] 开发指南明确“默认在服务层完成 Decimal->number”

---

## 4. PDF 文档处理测试与注释校准

**优先级**: 低
**风险**: 低
**预估工作量**: 0.5-1 天

### 问题描述

当前 PDF 转图能力已存在于 `backend/src/services/document/pdf_to_images.py`，但部分测试/注释仍保留“模块未实现”历史描述，容易误导后续开发与排障。

### 调整方向

1. 清理测试文件中的过期注释（如“not yet implemented”）
2. 核查 `pdf_to_images` 相关测试语义与当前实现是否一致
3. 明确依赖策略（PyMuPDF 优先，`pdf2image` 作为 fallback）并补充到文档

### 验收标准

- [x] 不再存在“模块未实现”这类与现状冲突的描述
- [x] PDF 相关单测描述与当前实现一致
- [x] 文档中明确 PDF 渲染后端依赖与回退策略

### 验证记录（2026-02-15）

- [x] 使用项目虚拟环境执行：`backend/.venv/bin/pytest -o addopts='' tests/unit/services/document/test_pdf_edge_cases.py tests/unit/services/document/extractors/test_base.py -q`，结果 `86 passed`
- [x] 补齐 `pytest-cov` 后按常规无覆盖率回归命令执行：`backend/.venv/bin/pytest tests/unit/services/document/test_pdf_edge_cases.py tests/unit/services/document/extractors/test_base.py -q --no-cov`，结果 `86 passed`

---

## 执行顺序建议（重排）

```
已完成: Backlog 校准（2026-02-14）

第 1 周: 问题 1（DictionaryPage + EnumFieldPage）
第 2 周: 问题 3（Decimal/Number 首批链路统一，已完成）
第 3-4 周: 问题 2（User/Role/Operation 拆分，已完成）
第 5 周: 问题 2（Organization + PromptDashboard，已完成）+ 问题 4（PDF 注释校准，已完成）
持续进行: 问题 3（新增功能按统一入口接入）
```

---

## 相关文档

- [前端开发指南](../guides/frontend.md)
- [测试标准](../guides/testing-standards.md)
- [CLAUDE.md](../../CLAUDE.md)
