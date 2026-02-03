# 组件导航

## 🎯 Purpose
提供前端组件的快速定位与统一入口，降低“目录太散/不好找”的认知负担。

## ✅ Status
**当前状态**: Active (2026-02-03 更新)

---

## 🚪 推荐入口

### 统一入口（命名空间导出）
```ts
import { Asset, Analytics, Common, Forms } from '@/components';

const { AssetList } = Asset;
const { AnalyticsDashboard } = Analytics;
const { TableWithPagination } = Common;
const { AssetForm } = Forms;
```

### 模块入口（目录内 index.ts）
```ts
import { AssetList, AssetSearch } from '@/components/Asset';
import { AnalyticsDashboard, AnalyticsFilters } from '@/components/Analytics';
import { TableWithPagination } from '@/components/Common';
import { AssetForm } from '@/components/Forms';
```

> 未提供 `index.ts` 的目录，继续按具体文件路径导入即可。

---

## 🧭 组件目录导航表

| 模块 | 目录 | 入口文件 | 说明 |
| --- | --- | --- | --- |
| 资产管理 | `frontend/src/components/Asset` | `index.ts` | 资产列表、搜索、导入导出 |
| 分析看板 | `frontend/src/components/Analytics` | `index.ts` | 分析面板、统计卡片、图表 |
| 分析筛选 | `frontend/src/components/Analytics/Filters` | `index.ts` | 筛选条件与预设 |
| 图表库 | `frontend/src/components/Charts` | `index.ts` | 通用业务图表 |
| 通用组件 | `frontend/src/components/Common` | `index.ts` | 表格、工具栏、错误展示 |
| 认证组件 | `frontend/src/components/Auth` | `index.ts` | 登录守卫与鉴权 |
| 表单组件 | `frontend/src/components/Forms` | `index.ts` | 资产/租赁/项目表单入口 |
| 资产表单 | `frontend/src/components/Forms/Asset` | `index.ts` | 资产表单分段 |
| 租赁表单 | `frontend/src/components/Forms/RentContract` | `index.ts` | 合同表单分段 |
| 仪表盘 | `frontend/src/components/Dashboard` | `index.ts` | 趋势卡片与洞察 |
| 布局组件 | `frontend/src/components/Layout` | `index.ts` | 页面布局与导航 |
| 加载组件 | `frontend/src/components/Loading` | `index.ts` | Loading/Skeleton |
| 路由组件 | `frontend/src/components/Router` | `index.ts` | 路由装配与动态路由 |
| 反馈组件 | `frontend/src/components/Feedback` | `index.ts` | 提示、对话框、进度 |
| 错误处理 | `frontend/src/components/ErrorHandling` | `index.ts` | ErrorBoundary/UX |
| 通知中心 | `frontend/src/components/Notification` | `index.ts` | 站内通知 |
| 系统管理 | `frontend/src/components/System` | `index.ts` | 权限守卫、面包屑、提示编辑 |
| 系统监控 | `frontend/src/components/Monitoring` | `index.ts` | 监控看板与健康状态 |
| 权属方 | `frontend/src/components/Ownership` | `index.ts` | 权属方列表与详情 |
| 项目管理 | `frontend/src/components/Project` | `index.ts` | 项目列表与选择 |
| 租赁管理 | `frontend/src/components/Rental` | `index.ts` | 合同、台账与导入 |
| 数据字典 | `frontend/src/components/Dictionary` | `index.ts` | 字典选择与预览 |
| 产权证 | `frontend/src/components/PropertyCertificate` | `index.ts` | 上传/审核组件 |
| PDF 导入 | `frontend/src/components/Contract/PDFImport` | `index.ts` | 合同 PDF 导入流程 |

---

## 🧩 目录补充说明

- `Contract/` 目录暂未提供统一导出（仅 `PDFImport` 有入口），可继续按文件路径引用。
- 若某目录新增组件较多，建议补齐 `index.ts` 并在本表中登记入口。
