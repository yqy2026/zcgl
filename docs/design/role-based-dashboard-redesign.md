# 角色化工作台设计方案

## 1. 问题背景

通过深度访谈确认，当前工作台（`frontend/src/pages/Dashboard/DashboardPage.tsx`）存在以下问题：

- **工作台面向所有人，又不像为任何人设计**。当前展示"资产管理看板"，内容偏资产统计，无法满足领导、资产管理、招商、物业运维四类岗位的日常工作需求。
- **导航按后端模块划分**（项目/资产/合同/主体/财务/分析），但运营方在工作中并不以模块视角操作，而是以任务、待办和风险处置视角推进工作。

## 2. 角色定义

运营方内部 4 种岗位，各自的工作台聚焦不同信息与操作：

### 2.1 领导/管理层

| 维度 | 说明 |
|------|------|
| 核心关注 | 经营大盘、收入/收缴率、高风险事项、决策依据 |
| 信息密度 | 低（只看关键指标和异常） |
| 典型操作 | 查看 → 下钻 → 问原因 → 决策 |
| 核心指标 | 总收入（自营+代理）、收缴率、出租率、高风险项目数 |

### 2.2 资产管理

| 维度 | 说明 |
|------|------|
| 核心关注 | 资产台账、出租率、合同到期、审核待办、资产状态 |
| 信息密度 | 中（需要明细列表和逐项操作入口） |
| 典型操作 | 审核合同 → 查看到期 → 补充资产信息 → 导出明细 |
| 核心指标 | 在管资产数、已租/空置面积、到期合同数、待审核数 |

### 2.3 招商

| 维度 | 说明 |
|------|------|
| 核心关注 | 空置资源、意向客户、招商进度、推盘 |
| 信息密度 | 中（需要推荐列表和跟进记录） |
| 典型操作 | 查看空置资产 → 录入意向 → 报价 → 签约 |
| 核心指标 | 空置面积、待租资产数、意向客户数、本月签约数 |

### 2.4 物业运维

| 维度 | 说明 |
|------|------|
| 核心关注 | 工单处理、巡检计划、入驻/退租交接、设备异常 |
| 信息密度 | 高（需要今日工单列表和状态追踪） |
| 典型操作 | 处理工单 → 确认巡检 → 退租验收 → 派单维修 |
| 核心指标 | 今日工单数、待维修数、巡检完成率、入驻/退租数 |

## 3. 设计方案

### 3.1 整体结构

保持现有主导航不动，工作台首页根据**当前登录用户的角色**渲染不同的工作台布局。

```
主导航（不变）
工作台 / 项目运营 / 资产资源 / 合同中心 / 财务台账 / 主体中心 / 经营分析 / 系统管理
  ↑
用户打开系统默认进入「工作台」
工作台根据角色展示：
  - 领导 → 经营大盘 + 高风险 + 收入趋势 + 项目总览
  - 资产 → 资产统计 + 待办 + 出租率分布 + 在租明细
  - 招商 → 空置资源 + 意向客户 + 招商漏斗 + 快捷操作
  - 物业 → 工单列表 + 入驻退租 + 设备异常 + 巡检计划
```

### 3.2 角色判定方式

方式一（推荐）：根据用户绑定的角色（`roles[]`）自动匹配工作台。一个用户可能有多个角色，优先级：

```
用户 roles → 含 "admin" 或 "system_admin" → 领导工作台
           → 含 "executive" → 领导工作台
           → 含 "reviewer" → 资产管理（待审核是其核心工作）
           → 含 "ops_admin" → 资产管理
           → 默认 → 资产管理（最通用的工作台）
```

方式二：工作台顶部保留「角色视角」切换器，用户可手动切换查看其他角色视角。

### 3.3 布局规范

每个工作台统一采用以下页面骨架：

```
┌─ 顶部：角色名 + 用户信息 + 快速刷新 ─────────────────────┐
│                                                           │
├─ 指标行：4 个核心 KPI 卡片（带趋势/对比） ────────────────┤
│                                                           │
├─ 左列（宽 2/5）    │  右列（宽 3/5）                     │
│  ┌─待办/提醒 ──┐   │  ┌─项目摘要/趋势/统计 ──────────┐  │
│  │ 条目 1      │   │  │                               │  │
│  │ 条目 2      │   │  │                               │  │
│  │ 条目 3      │   │  └───────────────────────────────┘  │
│  └─────────────┘   │                                      │
│  ┌─快捷操作 ──┐   │                                      │
│  │ 按钮组      │   │                                      │
│  └─────────────┘   │                                      │
├───────────────────────────────────────────────────────────┤
│ 底部：最近操作 / 明细列表 / 趋势图（角色决定内容）         │
└───────────────────────────────────────────────────────────┘
```

## 4. 组件规划

### 4.1 新增组件

| 组件 | 用途 | 适用角色 |
|------|------|---------|
| `RoleWorkspace` | 角色路由中枢，根据 roles 渲染对应工作台 | 全部 |
| `RoleSwitcher` | 工作台顶部的角色手动切换器（可选） | 全部 |
| `LeaderWorkspace` | 领导工作台整体布局 | 领导 |
| `AssetWorkspace` | 资产管理整体布局 | 资产 |
| `LeaseWorkspace` | 招商工作台整体布局 | 招商 |
| `PropertyWorkspace` | 物业运维整体布局 | 物业 |
| `KpiCard` | 可配置的 KPI 指标卡片（带趋势箭头、环比） | 全部 |
| `TodoItem` | 待办条目组件（带紧急级别颜色、操作链接） | 全部 |
| `ProjectSummaryCard` | 项目摘要卡片（指标网格 + 风险标签 + 进入入口） | 领导、资产 |
| `VacancyMap` | 空置资产列表组件 | 招商 |
| `ContractExpiringList` | 到期合同列表组件 | 资产 |
| `WorkOrderList` | 工单列表组件 | 物业 |
| `OccupancyChart` | 出租率分布组件（进度条或多项目对比） | 资产、领导 |
| `PipelineFunnel` | 招商漏斗组件（意向→报价→签约转化） | 招商 |
| `MoveInOutPlan` | 入驻/退租计划组件 | 物业 |

### 4.2 复用已有组件

| 已有组件 | 用途 |
|---------|------|
| `DataTrendCard` | 已有，当前用于资产指标卡，可扩展复用为通用 KPI 卡片 |
| `QuickActions` | 已有，扩展为角色可配置 |
| `QuickInsights` | 已有，可保留在领导工作台的"智能洞察"区域 |
| `ViewModeSegment` | 已有，在经营分析/报表场景保留 |

## 5. 数据依赖分析

### 5.1 已有 API（可直接消费）

| 端点 | 提供数据 | 适用于 |
|------|---------|--------|
| `GET /api/v1/analytics/comprehensive` | 综合经营数据：收入/收缴率/出租率/项目维度和模式维度拆分 | 领导、资产 |
| `GET /api/v1/projects/{id}/risks` | 项目级风险：人工标签/合同到期/欠费逾期/空置/产权证数据质量（MVP 已删覆盖类风险，见 ADR-0003） | 领导、资产 |
| `GET /api/v1/projects/{id}/ledger-summary` | 项目应收/应付/实收/实付/逾期 | 领导、资产 |
| `GET /api/v1/projects/{id}/tenants` | 项目租户/客户摘要 | 领导、资产 |
| `GET /api/v1/contract-groups` | 合同关系列表（可做待办审核的来源） | 资产 |
| `GET /api/v1/approval/pending` | 待审批列表 | 资产 |
| `GET /api/v1/assets` | 资产列表，可判断空置资产 | 招商、资产 |
| `GET /api/v1/contracts?expiring_soon=true` | 即将到期合同 | 资产、招商 |

### 5.2 需要新增的 API

| 端点 | 用途 | 优先级 |
|------|------|--------|
| `GET /api/v1/dashboard/summary` | 工作台专用聚合接口，一次请求返回当前角色的 KPI 指标、待办数、风险摘要，减少前端并发请求 | P0 |
| `GET /api/v1/dashboard/work-orders` | 物业工单列表（待处理/进行中/已完成） | P1 |
| `GET /api/v1/dashboard/move-in-out` | 入驻/退租计划列表 | P1 |
| `GET /api/v1/dashboard/lease-pipeline` | 招商漏斗：意向→报价→签约各阶段数量 | P1 |
| `GET /api/v1/dashboard/vacant-assets` | 空置资产详情（按项目分组，含面积/楼层/适合用途） | P1 |

### 5.3 现有 Dashboard Hook 改动

当前 `useDashboardData` 仅调用 `analyticsService.getComprehensiveAnalytics`，返回资产统计数据。需重构为：

```typescript
// 按角色选择数据源
const useRoleDashboard = (role: string) => {
  if (role === 'leader') return useLeaderDashboard();
  if (role === 'asset') return useAssetDashboard();
  if (role === 'lease') return useLeaseDashboard();
  if (role === 'property') return usePropertyDashboard();
};

// 各角色 hook 聚合不同的 API 请求
useLeaderDashboard → analytics/comprehensive + projects risks
useAssetDashboard → analytics/comprehensive + approval/pending + contracts expiring
useLeaseDashboard → vacant-assets + lease-pipeline
usePropertyDashboard → work-orders + move-in-out
```

## 6. 导航影响

### 6.1 无大改动

主导航保持不变，因为：
- "项目运营"、"资产资源"、"合同中心"、"财务台账"是跨角色的二级页面入口
- 角色工作台只改变首页内容，不改变导航项
- 用户可从任何工作台直接进入二级页面

### 6.2 小调整

- 工作台菜单项名称保留为"工作台"
- 右上角用户信息加"当前角色"展示
- （可选）工作台顶部加"角色快速切换"下拉

## 7. 实施顺序

### Phase 1：数据层 + 领导工作台（P0）

1. 新增 `GET /api/v1/dashboard/summary` 聚合接口
2. 替换 `useDashboardData` → `useRoleDashboard`
3. 新建 `LeaderWorkspace` 组件
4. 新建 `KpiCard`、`TodoItem` 组件
5. 修改 `DashboardPage.tsx` 为角色路由中枢
6. 补测试

产出物：领导打开系统看到经营大盘 + 高风险 + 收入趋势 + 项目总览

### Phase 2：资产管理工作台（P1）

1. 新建 `AssetWorkspace` 组件
2. 新建 `ProjectSummaryCard`、`ContractExpiringList`、`OccupancyChart` 组件
3. 连审（approval/pending）数据接入
4. 补测试

### Phase 3：招商工作台（P1）

1. 新建后端 `GET /api/v1/dashboard/vacant-assets` 和 `lease-pipeline`
2. 新建 `LeaseWorkspace` 组件
3. 新建 `VacancyMap`、`PipelineFunnel` 组件
4. 补测试

### Phase 4：物业运维工作台（P2）

1. 新建后端 `GET /api/v1/dashboard/work-orders` 和 `move-in-out`
2. 新建 `PropertyWorkspace` 组件
3. 新建 `WorkOrderList`、`MoveInOutPlan` 组件
4. 补测试

## 8. 验收标准

1. 用户登录后自动进入对应角色工作台
2. 每个工作台的 KPI 指标与对应 API 返回数据一致
3. 待办条目可点击跳转到对应处理页面
4. 项目摘要卡片点击进入项目详情页
5. 各角色切换间不丢失当前工作台浏览位置（可选）
6. 存量测试不受影响

## 9. 未解决问题 / vNext

- 用户同时有多个角色（如既是资产管理员又是招商）→ vNext 支持 Tab 式多角色并行
- 物业工单/入驻退租需要新增后端模块 → 当前先做前端骨架 + mock 数据
- 招商漏斗需要新增客户跟进流程 → 当前先做前端骨架
