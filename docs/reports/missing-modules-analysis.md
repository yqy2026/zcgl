# 土地物业资产管理系统 - 缺失功能分析报告

## 分析概述

本报告基于对项目的前端（42页面、159组件）、后端（33个API文件、约200个端点）和业务逻辑的全面分析，识别出系统缺失的功能模块。

---

## ⚠️ 重要发现（需求调研更新）

### 核心业务模型架构问题

通过与用户的深入访谈，发现了一个**重大架构问题**，这是原报告未能识别的：

#### 问题现状

**现有系统设计**：
- 支持两方关系：权属方 ↔ 终端租户
- RentContract 模型只有 `ownership_id` 和 `tenant_name` 字段

**实际业务需求**：
- 需要支持三方关系：权属方 ↔ 资产运营方 ↔ 终端租户
- 运营方是系统的主要使用者
- 需要支持两种合作模式：

**1. 承租方式**
```
权属方 ←─[承租合同]── 运营方 ←─[租赁合同]── 终端租户
         ↑                        ↑
      收租金                   付租金
```
- 运营方从权属方承租，再转租给终端租户
- 运营方利润 = 租金差价
- 终端租户付租金给运营方

**2. 委托运营方式**
```
权属方 ←─[委托运营协议]─ 运营方
  │                              │
  └─────[租赁合同]──── 终端租户   (运营方不签合同)
       ↑
   直收租金
```
- 运营方提供管理服务
- 权属方直接与终端租户签租赁合同
- 终端租户付租金给权属方
- 运营方利润 = 服务费（按租金百分比）

#### 影响范围

这个问题影响以下模块：
- **合同管理**：需要区分上游合同/下游合同，记录合同类型
- **租金台账**：需要记录收款方（权属方 or 运营方）
- **统计分析**：需要分别统计运营方自营收入和代收租金
- **权属方管理**：需要显示合作方式、关联资产、合同、收入统计

#### 优先级调整

**P0+ （最高优先级，高于所有其他功能）**
- **重构数据模型支持三方关系**
- **添加合同类型字段**（上游承租/委托运营协议 vs 下游租赁）
- **调整统计逻辑**（区分承租方式和委托运营方式的收入）

**估计工作量**：
- 数据库迁移：1-2天
- 后端重构：3-5天
- 前端调整：3-5天
- **总计：7-12天**

---

## 一、核心业务功能缺失（按模块分类，已调整优先级）

### 1.1 资产管理模块

#### 缺失功能
| 功能 | 优先级 | 描述 |
|------|--------|------|
| **资产折旧计算** | P1 | 折旧方法配置（直线法、双倍余额递减法）、折旧台账、累计折旧字段 |
| **资产处置管理** | P1 | 报废、出售、转让功能，处置审批流程，处置历史记录 |
| **资产维护管理** | P2 | 维修记录、保养计划、维修费用跟踪 |
| **资产盘点** | P2 | 盘点计划、盘点记录、盘点差异处理 |
| **资产评估** | P2 | 定期评估、价值变动记录 |

#### 关键文件
- 后端：`backend/src/api/v1/assets.py`, `backend/src/services/asset/`
- 前端：`frontend/src/pages/Assets/`, `frontend/src/components/Asset/`

---

### 1.2 合同管理模块 ⚠️ 架构问题

#### 核心问题（P0+ 最高优先级）

**数据模型不支持三方业务关系**：
- 现有：两方模型（权属方 ↔ 终端租户）
- 缺失：运营方角色和合同类型区分
- 影响：无法记录上游合同（承租合同/委托运营协议）

#### 真实需求（已验证）

**1. 合同详情页**（P0 确认需要）
- 展示合同主要信息：编号、承租方、资产、权属方、日期、状态、租金条款
- 展示合同扫描件PDF（支持多个文件，友好链接）
- 实际使用场景：快速了解合同、查看原始文档

**2. 合同编辑页**（P0 确认需要，但有限制）
- 使用场景：修正录入错误（经常发生）
- 限制条件：需要审批流程控制，不能随便修改
- 技术要求：开关式审批 + 可配置的审批流程

**3. 合同类型区分**（P0+ 新增需求）
- 上游合同类型：
  - 承租合同（权属方 → 运营方）
  - 委托运营协议（权属方 → 运营方）
- 下游合同类型：
  - 租赁合同（运营方 → 终端租户）
  - 租赁合同（权属方 → 终端租户，委托运营场景）

#### 缺失功能清单

| 功能 | 优先级 | 描述 |
|------|--------|------|
| **重构数据模型** | P0+ | 添加 contract_type、operator_id、upstream_contract_id 等字段 |
| **合同详情页** | P0 | 展示主要信息 + PDF附件，快速查看合同 |
| **合同编辑页** | P0 | 修正录入错误，需审批流程控制 |
| **合同PDF附件** | P0 | 支持多个PDF，创建时/编辑页可上传，详情页显示友好链接 |
| **审批流程引擎** | P0+ | 功能完备的流程引擎，支持自定义配置，开关式启用 |
| **合同变更管理** | P1 | 变更功能、补充协议管理、版本控制 |
| **合同续签** | P1 | 到期提醒、续签申请 |
| **合同终止** | P1 | 提前终止申请、终止结算 |

#### 关键文件
- 后端：`backend/src/models/rent_contract.py`（需重构）
- 后端：`backend/src/api/v1/rent_contract.py`（需扩展）
- 前端：`frontend/src/pages/Rental/`（需新增 ContractDetailPage, ContractEditPage）

---

### 1.3 租赁业务模块

#### 缺失功能
| 功能 | 优先级 | 描述 |
|------|--------|------|
| **租金调整** | P1 | 调整申请、审批流程、调整历史记录、自动递增设置 |
| **复式计费** | P2 | 按面积+固定费用的复合计费模式 |
| **阶段性计费** | P2 | 免租期、不同阶段不同费率 |
| **催缴管理** | P1 | 催缴计划、催缴记录、催缴模板、自动催缴提醒 |
| **退租管理** | P1 | 退租申请、退租审批、退租结算、押金退还、资产归还验收 |
| **发票管理** | P2 | 发票开具、记录、查询 |
| **收据管理** | P2 | 收据打印、作废、查询 |

#### 关键文件
- 后端：需新增 `rent_adjustment.py`, `rent_collection.py`, `rent_termination.py`
- 前端：需新增相关页面组件

---

### 1.4 权属方管理模块

#### 真实需求（已验证）

**使用频率**：
- 初始化时批量录入，后续偶尔新增
- 主要关注点：查看关联资产、合同、往来费用统计

**1. 权属方详情页**（P0 确认需要）
- 展示权属方基本信息
- 展示关联资产统计
- 展示所有合同列表
- 展示收入统计（区分承租/委托运营方式）：
  - 承租方式：租金收入（从运营方收取）
  - 委托运营方式：服务费支出（付给运营方）

**2. 权属方编辑页**（P0 确认需要）
- 需要独立的编辑页面
- 使用频率：偶尔修改

**3. 合作方式字段**（P0+ 新增需求）
- 需要在权属方或合同中记录合作方式（承租/委托运营）
- 影响统计和收入计算

#### 缺失功能清单

| 功能 | 优先级 | 描述 |
|------|--------|------|
| **权属方详情页** | P0 | 展示基本信息 + 关联资产 + 合同列表 + 收入统计 |
| **权属方编辑页** | P0 | 独立的编辑页面 |
| **权属方创建页** | P1 | 初始化时使用，可优先考虑批量导入 |
| **收入统计分析** | P1 | 区分承租方式收入和委托运营方式支出 |

#### 关键文件
- 后端：`backend/src/api/v1/ownership.py`（API已完整，需补充收入统计接口）
- 前端：`frontend/src/pages/Ownership/`（需创建详情页、编辑页）

---

### 1.5 项目管理模块 ⚠️ 伪需求发现

#### 真实需求（已验证）

**使用频率**：经常使用，日常都要使用
**定位**：主要日常运营管理入口，资产按项目归集呈现

**核心需求**：
1. **区分"管理"和"查看"，操作类和呈现类，面对不同角色**
2. **资产项目运营管理功能**（不是44字段的表单）

#### 角色分类

| 角色 | 需求类型 | 主要功能 |
|------|---------|---------|
| **运营人员** | 操作类 | 录入项目、管理资产、处理合同 |
| **财务人员** | 查看类 | 查看收入统计、收缴情况 |
| **管理层** | 查看类 | 查看整体报表、决策分析 |

#### 项目管理功能（操作类）

面向运营人员：
- 录入/编辑项目基本信息（名称、编码等）
- 向项目中添加/移除资产
- 查看项目内资产的租赁状态
- 对项目内资产进行批量操作

#### 项目查看功能（呈现类）

面向财务/管理人员：
- 项目概览卡片（资产数量、出租率、收入）
- 资产列表（可点击查看详情）
- 租赁统计图表（出租率趋势、收入趋势）

#### 伪需求识别

❌ **报告中提到的"44字段表单"是伪需求**
- 报告认为需要：投资信息、时间计划、合作单位等大量字段
- 实际需要：资产项目运营管理功能
- 结论：不是简单的CRUD表单，而是项目管理界面

#### 真实缺失功能

| 功能 | 优先级 | 描述 |
|------|--------|------|
| **项目管理页面** | P0 | 操作类：录入项目、管理资产、批量操作 |
| **项目查看页面** | P0 | 呈现类：概览卡片、资产列表、统计图表 |
| **项目详情页** | P1 | 深入查看单个项目的详细信息 |
| **角色权限控制** | P1 | 不同角色看到不同功能 |

#### 关键文件
- 后端：`backend/src/api/v1/project.py`（API已完整）
- 前端：`frontend/src/pages/Project/`（需重新设计，不是简单的CRUD页面）

---

## 二、系统级功能缺失

### 2.1 审批流程引擎 ❌ 完全缺失

| 功能 | 优先级 | 描述 |
|------|--------|------|
| **审批流程配置** | P0 | 可视化流程设计器、流程模板管理 |
| **审批实例管理** | P0 | 审批实例创建、执行、撤回 |
| **待办事项** | P0 | 待办列表、已办列表、抄送列表 |
| **审批记录** | P0 | 审批历史、审批意见、审批统计 |

#### 建议实现方案
- 后端新增：`backend/src/services/workflow/`, `backend/src/api/v1/workflow.py`
- 前端新增：`frontend/src/pages/Workflow/`, `frontend/src/components/Workflow/`

---

### 2.2 消息通知系统 ❌ 完全缺失

| 功能 | 优先级 | 描述 |
|------|--------|------|
| **通知中心** | P0 | 站内消息中心、消息分类、已读未读 |
| **邮件通知** | P1 | SMTP配置、邮件模板、邮件发送 |
| **短信通知** | P2 | 短信网关集成、短信模板 |
| **消息推送** | P2 | WebSocket实时推送 |
| **提醒配置** | P1 | 提醒规则配置（合同到期、租金催缴等） |

#### 建议实现方案
- 后端新增：`backend/src/services/notification/`, `backend/src/api/v1/notifications.py`
- 前端新增：消息中心组件、通知组件

---

### 2.3 报表管理增强

| 功能 | 优先级 | 描述 |
|------|--------|------|
| **自定义报表** | P2 | 报表设计器、自定义报表模板 |
| **报表订阅** | P2 | 定时发送报表到邮箱 |
| **数据钻取** | P2 | 从汇总数据钻取到明细数据 |
| **图表配置** | P2 | 用户自定义图表配置 |

---

## 三、辅助功能缺失

### 3.1 财务管理
- 财务报表生成（月报、季报、年报）
- 欠款管理（逾期提醒、催收流程）
- 财务凭证管理

### 3.2 客户/承租方管理
- 承租方档案管理
- 承租方信用评级
- 承租方黑名单
- 承租方投诉管理

### 3.3 移动端适配
- 响应式移动端页面
- 移动端专用功能（扫码、拍照）
- 离线数据同步

### 3.4 数据集成
- 与财务系统集成
- 与OA系统集成
- API接口文档页面
- Webhook配置管理

---

## 四、实现优先级总结

### P0 - 急需补充（核心业务阻塞）
1. **合同详情页和编辑页** - 合同管理核心功能缺失
2. **权属方CRUD完整功能** - 权属管理只有列表页
3. **项目CRUD完整功能** - 项目管理只有列表页
4. **审批流程引擎** - 规范化管理基础
5. **消息通知中心** - 配合提醒和审批的必需功能

### P1 - 重要功能（业务完整性）
1. **合同到期提醒** - 业务关键功能
2. **资产折旧计算** - 财务核算需要
3. **资产处置管理** - 完整资产生命周期
4. **租金调整功能** - 业务灵活性
5. **合同变更/续签/终止** - 合同管理完整性
6. **催缴管理** - 收租效率提升
7. **退租管理** - 租赁业务闭环
8. **邮件通知** - 配合提醒功能

### P2 - 增强功能（用户体验）
1. **资产维护管理** - 资产保值增值
2. **资产盘点** - 资产安全
3. **自定义报表** - 数据分析灵活性
4. **高级可视化** - 用户体验提升
5. **文件管理增强** - 文档安全性
6. **移动端适配** - 移动办公支持
7. **承租方管理** - 客户关系管理

---

## 五、关键文件清单

### 需要新增的后端文件
```
backend/src/api/v1/
├── workflow.py          # 审批流程API
├── notifications.py     # 通知系统API
├── rent_adjustment.py   # 租金调整API
├── rent_collection.py   # 催缴管理API
├── rent_termination.py  # 退租管理API
├── asset_depreciation.py # 资产折旧API
├── asset_disposal.py    # 资产处置API
└── asset_maintenance.py # 资产维护API

backend/src/services/
├── workflow/            # 工作流服务
│   ├── engine.py       # 流程引擎
│   ├── instance.py     # 实例管理
│   └── task.py         # 任务管理
├── notification/        # 通知服务
│   ├── service.py      # 通知服务
│   ├── templates.py    # 消息模板
│   └── email.py        # 邮件通知
└── finance/            # 财务服务
    ├── depreciation.py # 折旧计算
    └── billing.py      # 计费服务
```

### 需要新增的前端页面
```
frontend/src/pages/
├── Contract/
│   ├── ContractDetailPage.tsx    # 合同详情页（缺失）
│   └── ContractEditPage.tsx      # 合同编辑页（缺失）
├── Ownership/
│   ├── OwnershipCreatePage.tsx   # 权属方创建页（缺失）
│   ├── OwnershipEditPage.tsx     # 权属方编辑页（缺失）
│   └── OwnershipDetailPage.tsx   # 权属方详情页（缺失）
├── Project/
│   ├── ProjectCreatePage.tsx     # 项目创建页（缺失）
│   ├── ProjectEditPage.tsx       # 项目编辑页（缺失）
│   └── ProjectDetailPage.tsx     # 项目详情页（缺失）
├── Workflow/
│   ├── WorkflowDesignPage.tsx    # 流程设计页（新增）
│   ├── TodoListPage.tsx          # 待办列表页（新增）
│   └── DoneListPage.tsx          # 已办列表页（新增）
└── Notification/
    └── NotificationCenterPage.tsx # 消息中心页（新增）
```

---

## 六、实施建议

### 阶段1：基础功能补全（2-3周）
1. 补全合同详情页和编辑页
2. 补全权属方CRUD完整功能
3. 补全项目CRUD完整功能

### 阶段2：核心业务流程（3-4周）
1. 实现审批流程引擎
2. 实现消息通知系统
3. 实现合同到期提醒
4. 实现租金调整和催缴管理

### 阶段3：资产生命周期（2-3周）
1. 实现资产折旧计算
2. 实现资产处置管理
3. 实现资产维护管理

### 阶段4：增强功能（按需）
1. 自定义报表
2. 移动端适配
3. 承租方管理
4. 数据集成

---

## 七、P0模块详细技术实现方案

### 7.1 合同管理模块

#### 后端API现状评估 ✅

**已有端点（完整）**:
```python
GET    /api/v1/rental-contracts/contracts/{contract_id}     # 获取合同详情
PUT    /api/v1/rental-contracts/contracts/{contract_id}     # 更新合同
GET    /api/v1/rental-contracts/contracts/{id}/terms        # 获取租金条款
GET    /api/v1/rental-contracts/contracts/{id}/ledger       # 获取台账记录
DELETE /api/v1/rental-contracts/contracts/{contract_id}     # 删除合同
```

**数据模型** (`backend/src/models/rent_contract.py`):
- RentContract: 20个字段（基础信息+关联）
- RentTerm: 9个字段（租金条款）
- RentLedger: 15个字段（台账记录）
- RentContractHistory: 历史变更记录

**级联删除规则**:
- 删除合同 → 自动删除租金条款（RentTerm）
- 删除合同 → 自动删除台账记录（RentLedger）
- 删除合同 → 保留历史记录（RentContractHistory）

#### 前端页面实现方案

**需新增的页面**:

1. **ContractDetailPage.tsx** - 合同详情页
```typescript
// 路由: /rental/contracts/:id
// 功能:
// - 展示完整合同信息（分区展示）
// - 展示租金条款列表（表格）
// - 展示关联台账记录
// - 展示历史变更记录
// - 操作按钮：编辑、删除、生成台账、导出PDF

// 关键API调用
const { data: contract } = useQuery({
  queryKey: ['contract', id],
  queryFn: () => rentContractService.getContract(id),
});

const { data: terms } = useQuery({
  queryKey: ['contract-terms', id],
  queryFn: () => rentContractService.getContractTerms(id),
});

const { data: ledger } = useQuery({
  queryKey: ['contract-ledger', id],
  queryFn: () => rentContractService.getContractLedger(id),
});
```

**页面布局**:
```
┌─────────────────────────────────────────┐
│  返回按钮  合同详情  编辑  删除 导出    │
├─────────────────────────────────────────┤
│  [基本信息卡片]                          │
│  - 合同编号、承租方、资产、权属方         │
│  - 签订日期、租期、状态                   │
├─────────────────────────────────────────┤
│  [租金条款表格]                          │
│  - 开始日期 | 结束日期 | 月租金 | 管理费  │
│  - 总金额 | 描述                          │
├─────────────────────────────────────────┤
│  [租金台账记录]                          │
│  - 年月 | 应收金额 | 实收金额 | 支付状态  │
├─────────────────────────────────────────┤
│  [历史变更记录]                          │
│  - 操作时间 | 操作类型 | 操作人 | 变更内容 │
└─────────────────────────────────────────┘
```

2. **ContractEditPage.tsx** - 合同编辑页
```typescript
// 路由: /rental/contracts/:id/edit
// 功能:
// - 复用 RentContractForm 组件（mode="edit"）
// - 预加载现有合同数据
// - 表单提交调用 updateContract API
// - 保存后跳转到详情页

// 实现要点
const ContractEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: contract, isLoading } = useQuery({
    queryKey: ['contract', id],
    queryFn: () => rentContractService.getContract(id),
    enabled: !!id,
  });

  const mutation = useMutation({
    mutationFn: (data: RentContractUpdate) =>
      rentContractService.updateContract(id, data),
    onSuccess: () => {
      message.success('合同更新成功');
      navigate(`/rental/contracts/${id}`);
    },
  });

  if (isLoading) return <Spin />;
  return (
    <RentContractForm
      initialValues={contract}
      mode="edit"
      onSubmit={mutation.mutate}
      onCancel={() => navigate(`/rental/contracts/${id}`)}
    />
  );
};
```

**复用现有组件**:
- ✅ `RentContractForm` - 表单组件（已支持编辑模式）
- ✅ `RentContract/BasicInfoSection` - 基本信息区
- ✅ `RentContract/TenantInfoSection` - 承租方信息区
- ✅ `RentContract/ContractPeriodSection` - 合同期信息区
- ✅ `RentContract/RentTermsSection` - 租金条款区
- ✅ `RentContract/OtherInfoSection` - 其他信息区

**表单验证规则**:
```typescript
// 日期范围验证
validator: (_, value) => {
  if (value.end_date <= value.start_date) {
    return Promise.reject('结束日期必须大于开始日期');
  }
  return Promise.resolve();
}

// 租金条款连续性验证
validateRentTerms: (terms: RentTerm[]) => {
  // 1. 首尾条款匹配
  if (terms[0].start_date !== contract.start_date) {
    throw Error('第一条条款开始日期必须等于合同开始日期');
  }
  if (terms[terms.length - 1].end_date !== contract.end_date) {
    throw Error('最后一条条款结束日期必须等于合同结束日期');
  }

  // 2. 连续性检查
  for (let i = 0; i < terms.length - 1; i++) {
    if (terms[i].end_date !== terms[i + 1].start_date) {
      throw Error('租金条款时间范围必须连续');
    }
  }
}
```

**需新增的组件**:
```typescript
// frontend/src/components/Rental/ContractDetailInfo.tsx
export interface ContractDetailInfoProps {
  contract: RentContract;
  onEdit: () => void;
  onDelete: () => void;
}

// 功能分区展示
- BasicInfoCard: 基本信息
- RentTermsTable: 租金条款表格
- RelatedLedgerTable: 关联台账
- HistoryTimeline: 历史记录时间线
```

**关键文件路径**:
```
后端:
✅ backend/src/api/v1/rent_contract.py (已有，无需修改)
✅ backend/src/services/rent_contract/service.py (已有，无需修改)
✅ backend/src/schemas/rent_contract.py (已有，无需修改)

前端需新增:
🆕 frontend/src/pages/Rental/ContractDetailPage.tsx
🆕 frontend/src/pages/Rental/ContractEditPage.tsx
🆕 frontend/src/components/Rental/ContractDetailInfo.tsx

前端可复用:
✅ frontend/src/components/Forms/RentContract/ (整个目录)
✅ frontend/src/services/rentContractService.ts
✅ frontend/src/types/rentContract.ts
```

---

### 7.2 权属方管理模块

#### 后端API现状评估 ✅

**已有端点（100%完整）**:
```python
POST   /api/v1/ownerships/                              # 创建权属方
GET    /api/v1/ownerships/{id}                          # 获取详情
PUT    /api/v1/ownerships/{id}                          # 更新权属方
DELETE /api/v1/ownerships/{id}                          # 删除权属方
GET    /api/v1/ownerships/                              # 列表查询
POST   /api/v1/ownerships/search                        # 搜索
GET    /api/v1/ownerships/dropdown-options              # 下拉选项
PUT    /api/v1/ownerships/{id}/projects                 # 更新关联项目
POST   /api/v1/ownerships/{id}/toggle-status            # 切换状态
GET    /api/v1/ownerships/statistics/summary            # 统计信息
```

**数据模型** (`backend/src/models/asset.py` - Ownership类):
```python
# 12个核心字段
- id: str (UUID)
- name: str (200字符)          # 权属方全称
- code: str (100字符)          # 权属编码 (自动生成: OWYYMMXXX)
- short_name: str              # 简称
- address: str                 # 地址
- management_entity: str       # 管理单位
- notes: Text                  # 备注
- is_active: bool              # 状态
- data_status: str             # 数据状态
- created_at/updated_at        # 时间戳
- created_by/updated_by        # 操作人

# 关联关系
- assets → Asset[] (一对多)
- owned_rent_contracts → RentContract[] (一对多)
- ownership_relations → ProjectOwnershipRelation[] (多对多)
```

**级联删除规则**:
- 删除权属方 → 检查关联资产数量，有资产则禁止删除
- 删除权属方 → 级联删除租赁合同
- 删除权属方 → 级联删除项目关联关系

#### 前端页面实现方案

**需新增的页面**:

1. **OwnershipCreatePage.tsx** - 权属方创建页
```typescript
// 路由: /ownership/new
// 功能:
// - 使用 OwnershipForm 组件（mode="create"）
// - 表单字段：名称、简称、地址、管理单位、备注、关联项目
// - 编码自动生成
// - 名称唯一性验证

const OwnershipCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: (data: OwnershipCreate) =>
      ownershipService.createOwnership(data),
    onSuccess: () => {
      message.success('权属方创建成功');
      navigate('/ownership');
    },
  });

  return (
    <PageContainer title="新建权属方">
      <OwnershipForm
        mode="create"
        onSubmit={mutation.mutate}
        onCancel={() => navigate('/ownership')}
      />
    </PageContainer>
  );
};
```

2. **OwnershipEditPage.tsx** - 权属方编辑页
```typescript
// 路由: /ownership/:id/edit
// 功能: 类似创建页，但预加载数据

const OwnershipEditPage: React.FC = () => {
  const { id } = useParams();
  const { data: ownership } = useQuery({
    queryKey: ['ownership', id],
    queryFn: () => ownershipService.getOwnership(id),
  });

  return (
    <OwnershipForm
      initialValues={ownership}
      mode="edit"
      onSubmit={handleUpdate}
    />
  );
};
```

3. **OwnershipDetailPage.tsx** - 权属方详情页
```typescript
// 路由: /ownership/:id
// 功能:
// - 展示完整权属方信息
// - 展示关联资产列表（分页）
// - 展示关联项目列表
// - 展示关联合同列表
// - 统计数据卡片

const OwnershipDetailPage: React.FC = () => {
  const { id } = useParams();
  const { data: ownership } = useQuery({
    queryKey: ['ownership', id],
    queryFn: () => ownershipService.getOwnership(id),
  });

  const { data: assets } = useQuery({
    queryKey: ['ownership-assets', id],
    queryFn: () => ownershipService.getOwnershipAssets(id),
  });

  return (
    <PageContainer
      title="权属方详情"
      extra={
        <Space>
          <Button onClick={() => navigate(`/ownership/${id}/edit`)}>编辑</Button>
          <Button danger onClick={handleDelete}>删除</Button>
        </Space>
      }
    >
      <Row gutter={16}>
        {/* 左侧：详情卡片 */}
        <Col span={18}>
          <Card title="基本信息">
            <Descriptions column={2}>
              <Descriptions.Item label="权属方全称">
                {ownership?.name}
              </Descriptions.Item>
              <Descriptions.Item label="权属方编码">
                <Tag color="blue">{ownership?.code}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="简称">
                {ownership?.short_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge
                  status={ownership?.is_active ? 'success' : 'default'}
                  text={ownership?.is_active ? '启用' : '禁用'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="地址" span={2}>
                {ownership?.address || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="管理单位">
                {ownership?.management_entity || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>
                {ownership?.notes || '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="关联资产" style={{ marginTop: 16 }}>
            <Table
              columns={assetColumns}
              dataSource={assets}
              pagination={{ pageSize: 5 }}
              rowKey="id"
            />
          </Card>
        </Col>

        {/* 右侧：统计卡片 */}
        <Col span={6}>
          <Card>
            <Statistic
              title="关联资产"
              value={ownership?.asset_count}
              prefix={<HomeOutlined />}
              suffix="个"
            />
          </Card>
          <Card style={{ marginTop: 16 }}>
            <Statistic
              title="关联项目"
              value={ownership?.project_count}
              prefix={<ProjectOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
};
```

**需扩展的组件**:
```typescript
// frontend/src/components/Forms/OwnershipForm.tsx
// 需要添加的字段:
<Card title="扩展信息" size="small">
  <Form.Item label="地址" name="address">
    <Input.TextArea rows={2} placeholder="请输入地址" />
  </Form.Item>

  <Form.Item label="管理单位" name="management_entity">
    <Input placeholder="请输入管理单位" />
  </Form.Item>

  <Form.Item label="备注" name="notes">
    <Input.TextArea rows={3} placeholder="请输入备注信息" />
  </Form.Item>
</Card>
```

**需补充的后端API**:
```python
# backend/src/api/v1/ownership.py
@router.get("/{ownership_id}/assets", response_model=List[AssetSummary])
async def get_ownership_assets(
    *,
    db: Session = Depends(deps.get_db),
    ownership_id: str
):
    """获取权属方关联的资产列表"""
    assets = ownership_service.get_related_assets(db, ownership_id)
    return assets

@router.get("/{ownership_id}/contracts", response_model=List[RentContractSummary])
async def get_ownership_contracts(
    *,
    db: Session = Depends(deps.get_db),
    ownership_id: str
):
    """获取权属方关联合同列表"""
    contracts = ownership_service.get_related_contracts(db, ownership_id)
    return contracts
```

**关键文件路径**:
```
后端:
✅ backend/src/api/v1/ownership.py (已有，需补充2个端点)
✅ backend/src/crud/ownership.py (已有)
✅ backend/src/models/asset.py (Ownership模型，已有)

前端需新增:
🆕 frontend/src/pages/Ownership/OwnershipCreatePage.tsx
🆕 frontend/src/pages/Ownership/OwnershipEditPage.tsx
🆕 frontend/src/pages/Ownership/OwnershipDetailPage.tsx
🆕 frontend/src/components/Ownership/OwnershipAssetTable.tsx

前端需扩展:
🔧 frontend/src/components/Forms/OwnershipForm.tsx (添加3个字段)

前端可复用:
✅ frontend/src/components/Ownership/OwnershipList.tsx
✅ frontend/src/components/Ownership/OwnershipDetail.tsx (需扩展)
✅ frontend/src/services/ownershipService.ts
```

---

### 7.3 项目管理模块

#### 后端API现状评估 ✅

**已有端点（100%完整）**:
```python
POST   /api/v1/projects/                    # 创建项目
GET    /api/v1/projects/{id}                # 获取详情
PUT    /api/v1/projects/{id}                # 更新项目
DELETE /api/v1/projects/{id}                # 删除项目
GET    /api/v1/projects/                    # 列表查询
POST   /api/v1/projects/search              # 搜索
GET    /api/v1/projects/dropdown-options    # 下拉选项
POST   /api/v1/projects/{id}/toggle-status  # 切换状态
GET    /api/v1/projects/statistics/summary  # 统计信息
```

**数据模型** (`backend/src/models/asset.py` - Project类):
```python
# 44个字段，分为8个区域

# 1. 基本信息区 (7字段)
- name, short_name, code (自动生成: PJYYMMXXX)
- project_type, project_scale, project_status
- project_description

# 2. 时间日期区 (4字段)
- start_date, end_date
- expected_completion_date, actual_completion_date

# 3. 地址信息区 (4字段)
- address, city, district, province

# 4. 联系信息区 (3字段)
- project_manager, project_phone, project_email

# 5. 投资信息区 (4字段)
- total_investment, planned_investment
- actual_investment, project_budget

# 6. 目标范围区 (2字段)
- project_objectives, project_scope

# 7. 合作单位区 (5字段)
- management_entity, ownership_entity
- construction_company, design_company, supervision_company

# 8. 系统字段区 (7字段)
- is_active, data_status, created_at, updated_at
- created_by, updated_by, asset_count

# 关联关系
- assets → Asset[] (一对多，级联删除)
- ownership_relations → ProjectOwnershipRelation[] (多对多)
```

**关键特性**:
- 智能编码生成（格式：PJ2501001）
- 权属方多对多关联（通过中间表）
- 资产自动计数
- 删除前检查关联资产

#### 前端页面实现方案

**需新增的页面**:

1. **ProjectCreatePage.tsx** - 项目创建页
```typescript
// 路由: /project/new
// 功能:
// - 使用分步表单（Steps组件）
// - 44个字段分为8个步骤
// - 编码自动生成
// - 名称唯一性验证

import { Steps, Card } from 'antd';

const { Step } = Steps;

const ProjectCreatePage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    { title: '基本信息', content: <BasicInfoForm /> },
    { title: '时间规划', content: <TimePlanningForm /> },
    { title: '地理位置', content: <LocationForm /> },
    { title: '联系信息', content: <ContactForm /> },
    { title: '投资预算', content: <InvestmentForm /> },
    { title: '目标范围', content: <ObjectivesForm /> },
    { title: '合作单位', content: {partnersForm /> },
    { title: '权属方关联', content: <OwnershipRelationsForm /> },
  ];

  return (
    <PageContainer title="新建项目">
      <Card>
        <Steps current={currentStep} onChange={setCurrentStep}>
          {steps.map((step, i) => (
            <Step key={i} title={step.title} />
          ))}
        </Steps>
        <div style={{ marginTop: 24 }}>
          {steps[currentStep].content}
        </div>
      </Card>
    </PageContainer>
  );
};
```

**表单字段分区**:
```typescript
// 1. 基本信息区 (8字段)
interface BasicInfoForm {
  name: string;                    // 项目名称 * 必填
  short_name: string;              // 项目简称
  code: string;                    // 项目编码 [自动生成]
  project_type: string;            // 项目类型 [下拉]
  project_scale: string;           // 项目规模 [下拉]
  project_status: string;          // 项目状态 [下拉]
  project_description: string;     // 项目描述
  is_active: boolean;              // 是否启用
}

// 2. 时间规划区 (4字段)
interface TimePlanningForm {
  start_date: Date;                // 开始日期
  end_date: Date;                  // 结束日期
  expected_completion_date: Date;  // 预计完成日期
  actual_completion_date: Date;    // 实际完成日期
}

// 3. 地理位置区 (4字段)
interface LocationForm {
  province: string;                // 省份 [级联选择]
  city: string;                    // 城市
  district: string;                // 区域
  address: string;                 // 项目地址
}

// 4. 联系信息区 (3字段)
interface ContactForm {
  project_manager: string;         // 项目经理
  project_phone: string;           // 项目电话 [手机验证]
  project_email: string;           // 项目邮箱 [邮箱验证]
}

// 5. 投资预算区 (4字段)
interface InvestmentForm {
  total_investment: number;        // 总投资 (万元)
  planned_investment: number;      // 计划投资
  actual_investment: number;       // 实际投资
  project_budget: number;          // 项目预算
}

// 6. 目标范围区 (2字段)
interface ObjectivesForm {
  project_objectives: string;      // 项目目标 [富文本]
  project_scope: string;           // 项目范围 [富文本]
}

// 7. 合作单位区 (5字段)
interface PartnersForm {
  management_entity: string;       // 管理单位
  ownership_entity: string;        // 权属单位
  construction_company: string;    // 施工单位
  design_company: string;          // 设计单位
  supervision_company: string;     // 监理单位
}

// 8. 权属方关联区 (动态)
interface OwnershipRelationsForm {
  ownership_relations: Array<{
    ownership_id: string;
    relation_type: string;
  }>;
}
```

2. **ProjectEditPage.tsx** - 项目编辑页
```typescript
// 路由: /project/:id/edit
// 功能: 类似创建页，但预加载数据

const ProjectEditPage: React.FC = () => {
  const { id } = useParams();
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectService.getProject(id),
  });

  if (isLoading) return <Spin />;
  return (
    <ProjectForm
      initialValues={project}
      mode="edit"
      onSubmit={handleUpdate}
    />
  );
};
```

3. **ProjectDetailPage.tsx** - 项目详情页
```typescript
// 路由: /project/:id
// 功能:
// - 展示完整项目信息
// - 展示关联资产列表（分页+统计）
// - 展示权属方关系
// - 展示项目统计数据（可视化）

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams();
  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectService.getProject(id),
  });

  const { data: assets } = useQuery({
    queryKey: ['project-assets', id],
    queryFn: () => projectService.getProjectAssets(id, { page: 1, size: 10 }),
  });

  const { data: statistics } = useQuery({
    queryKey: ['project-statistics', id],
    queryFn: () => projectService.getProjectStatistics(id),
  });

  return (
    <PageContainer
      title="项目详情"
      extra={
        <Space>
          <Button onClick={() => navigate(`/project/${id}/edit`)}>编辑</Button>
          <Button danger onClick={handleDelete}>删除</Button>
        </Space>
      }
    >
      <Row gutter={16}>
        {/* 左侧：详情内容 */}
        <Col span={18}>
          {/* 顶部概览卡片 */}
            <Col span={6}>
              <Statistic title="关联资产" value={project?.asset_count} />
            </Col>
            <Col span={6}>
              <Statistic title="总投资" value={project?.total_investment} suffix="万元" />
            </Col>
            <Col span={6}>
              <Statistic title="权属方" value={project?.ownership_count} />
            </Col>
            <Col span={6}>
              <Statistic title="总面积" value={project?.total_area} suffix="㎡" />
            </Col>
          </Row>
        </Card>

        {/* 基本信息卡片 */}
        <Card title="基本信息" style={{ marginTop: 16 }}>
          <Descriptions column={2} bordered>
            <Descriptions.Item label="项目名称">{project?.name}</Descriptions.Item>
            <Descriptions.Item label="项目编码">
              <Tag color="blue">{project?.code}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="项目类型">{project?.project_type}</Descriptions.Item>
            <Descriptions.Item label="项目规模">{project?.project_scale}</Descriptions.Item>
            <Descriptions.Item label="项目状态">
              <Badge status={project?.is_active ? 'success' : 'default'} text={project?.project_status} />
            </Descriptions.Item>
            <Descriptions.Item label="开始日期">
              {formatDate(project?.start_date)}
            </Descriptions.Item>
            {/* ... 更多字段 ... */}
          </Descriptions>
        </Card>

        {/* 关联资产表格 */}
        <Card title="关联资产" style={{ marginTop: 16 }}>
          <Table
            columns={assetColumns}
            dataSource={assets?.items}
            pagination={{
              total: assets?.total,
              pageSize: 10,
              onChange: (page) => handlePageChange(page),
            }}
            rowKey="id"
          />
        </Card>

        {/* 权属方关系 */}
        <Card title="权属方关系" style={{ marginTop: 16 }}>
          {project?.ownership_relations?.map(rel => (
            <Tag key={rel.ownership_id} color="green">
              {rel.ownership_name} ({rel.relation_type})
            </Tag>
          ))}
        </Card>
      </Col>

      {/* 右侧：统计和操作 */}
      <Col span={6}>
        {/* 统计图表 */}
        <Card title="类型分布">
          <PieChart data={statistics?.typeDistribution} />
        </Card>

        <Card title="投资统计" style={{ marginTop: 16 }}>
          <Progress
            percent={calculateProgress(statistics?.investmentStats)}
            status="active"
          />
        </Card>

        {/* 操作历史 */}
        <Card title="操作记录" style={{ marginTop: 16 }}>
          <Timeline>
            {project?.history?.map(item => (
              <Timeline.Item key={item.id}>
                {item.operation_type} - {item.operator}
                <br />
                <small>{formatDateTime(item.operation_time)}</small>
              </Timeline.Item>
            ))}
          </Timeline>
        </Card>
      </Col>
    </Row>
  </PageContainer>
  );
};
```

**需扩展的组件**:
```typescript
// frontend/src/components/Forms/ProjectForm.tsx
// 现状：仅支持2个字段（name + description）
// 需扩展：支持所有44个字段

// 方案：使用分步表单（Steps）
const ProjectForm: React.FC<ProjectFormProps> = ({ initialValues, mode, onSubmit }) => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      title: '基本信息',
      component: BasicInfoSection,
    },
    {
      title: '时间规划',
      component: TimePlanningSection,
    },
    // ... 其他6个步骤
  ];

  return (
    <Form
      form={form}
      initialValues={initialValues}
      onFinish={onSubmit}
    >
      <Steps current={currentStep}>
        {steps.map((step, i) => (
          <Step key={i} title={step.title} />
        ))}
      </Steps>

      <div style={{ marginTop: 24 }}>
        {React.createElement(steps[currentStep].component)}
      </div>

      <div style={{ marginTop: 24 }}>
        {currentStep > 0 && (
          <Button onClick={() => setCurrentStep(currentStep - 1)}>
            上一步
          </Button>
        )}
        {currentStep < steps.length - 1 ? (
          <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
            下一步
          </Button>
        ) : (
          <Button type="primary" htmlType="submit" loading={submitting}>
            提交
          </Button>
        )}
      </div>
    </Form>
  );
};
```

**表单验证规则**:
```typescript
const projectValidationRules = {
  name: [
    { required: true, message: '项目名称不能为空' },
    { max: 200, message: '项目名称最多200字符' },
    {
      validator: async (_, value) => {
        const exists = await projectService.validateProjectName(value, initialValues?.id);
        return !exists || Promise.reject('项目名称已存在');
      }
    }
  ],
  code: [
    { required: true, message: '项目编码不能为空' },
    {
      pattern: /^[A-Z]{2}\d{7,8}$/,
      message: '项目编码格式必须为: [2字母前缀][4位年月][3位序号]'
    }
  ],
  project_email: [
    { type: 'email', message: '请输入正确的邮箱格式' }
  ],
  project_phone: [
    {
      pattern: /^1[3-9]\d{9}$/,
      message: '请输入正确的手机号'
    }
  ],
  total_investment: [
    { type: 'number', min: 0, message: '投资金额不能为负数' }
  ],
};
```

**性能优化**:
```typescript
// 1. 懒加载资产列表
import { useVirtualizedList } from '@/hooks/useVirtualizedList';

const { virtualList, containerProps } = useVirtualizedList({
  dataSource: assets,
  itemHeight: 60,
  overscan: 5,
});

// 2. 防抖搜索
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';

const { searchValue, handleSearchChange } = useDebouncedSearch({
  delay: 300,
  onSearch: (value) => {
    projectService.searchProjects({ keyword: value });
  },
});

// 3. React Query缓存
const { data: project } = useQuery({
  queryKey: ['project', id],
  queryFn: () => projectService.getProject(id),
  staleTime: 5 * 60 * 1000,  // 5分钟内不重新获取
  cacheTime: 10 * 60 * 1000,  // 10分钟缓存
});
```

**关键文件路径**:
```
后端:
✅ backend/src/api/v1/project.py (已有，无需修改)
✅ backend/src/crud/project.py (已有)
✅ backend/src/models/asset.py (Project模型，已有)

前端需新增:
🆕 frontend/src/pages/Project/ProjectCreatePage.tsx
🆕 frontend/src/pages/Project/ProjectEditPage.tsx
🆕 frontend/src/pages/Project/ProjectDetailPage.tsx
🆕 frontend/src/components/Project/ProjectAssetTable.tsx
🆕 frontend/src/components/Project/ProjectStatistics.tsx

前端需扩展:
🔧 frontend/src/components/Forms/ProjectForm.tsx (从2字段扩展到44字段)
🔧 frontend/src/components/Project/ProjectDetail.tsx (添加关联资产、统计数据)

前端可复用:
✅ frontend/src/components/Project/ProjectList.tsx
✅ frontend/src/components/Project/ProjectSelect.tsx
✅ frontend/src/services/projectService.ts
```

---

## 九、最佳实践参考方案

基于开源项目调研，以下是针对核心模块的最佳实践参考方案。

### 9.1 审批流程引擎 - Flowable方案

#### 推荐方案：Flowable + REST API

**选择理由**：
- ✅ Apache 2.0 许可证，完全免费商用
- ✅ 功能完整，支持 BPMN 2.0
- ✅ 轻量级，性能优秀
- ✅ REST API 集成简单
- ✅ 社区活跃，文档完善

**技术架构**：
```yaml
架构模式:
  FastAPI Backend → REST API → Flowable Engine (Docker独立部署)
                              ↓
                        PostgreSQL/Redis

开发语言:
  - Flowable: Java
  - FastAPI集成: Python (httpx.AsyncClient)

流程定义:
  - BPMN 2.0 标准
  - 可视化设计器: Flowable Modeler

前端集成:
  - 流程图展示: React Flow / Ant Design G6
  - 审批操作界面: React + Ant Design
```

**实施步骤**（预计 8-10周）：

**阶段一：基础集成（1-2周）**
```python
# FastAPI 中调用 Flowable REST API
from httpx import AsyncClient

class WorkflowClient:
    def __init__(self):
        self.base_url = "http://flowable:8080/flowable-rest"
        self.client = AsyncClient()

    async def start_process(self, process_key: str, variables: dict):
        """启动流程实例"""
        response = await self.client.post(
            f"{self.base_url}/runtime/process-instances",
            json={
                "processDefinitionKey": process_key,
                "variables": variables
            }
        )
        return response.json()

    async def complete_task(self, task_id: str, variables: dict):
        """完成任务"""
        await self.client.post(
            f"{self.base_url}/runtime/tasks/{task_id}",
            json={"action": "complete", "variables": variables}
        )
```

**阶段二：流程定义（1-2周）**
- 设计合同审批流程（资产审批、合同审批）
- 配置审批角色和权限
- 定义流程变量和表单

**阶段三：前端集成（2-3周）**
- 实现审批操作界面
- 实时状态更新（WebSocket）
- 审批历史查看

**阶段四：高级功能（2-3周）**
- 审批超时提醒
- 并行审批支持
- 审批统计报表

**参考资源**：
- 官网：https://flowable.com/open-source/
- 文档：https://flowable.com/open-source/docs/
- Docker镜像：flowable/flowable-rest

---

### 9.2 报表和可视化 - 自研轻量级方案

#### 推荐方案：基于 ECharts + FastAPI 的自研报表

**选择理由**：
- ✅ 与现有技术栈完美融合（React + Ant Design）
- ✅ 完全可控，深度定制
- ✅ 渐进式开发，按需扩展
- ✅ 无需额外部署服务

**技术选型**：
```typescript
// 前端核心技术
{
  框架: "React 18",
  UI库: "Ant Design 5",
  图表库: "Apache ECharts 5",  // 功能最强大
  表格: "AG Grid / Ant Design Table",
  布局: "react-grid-layout",
  导出: "exceljs, jsPDF"
}

// 后端技术
{
  报表引擎: "自研 Python 服务",
  数据处理: "Pandas",
  模板引擎: "Jinja2",
  导出: "openpyxl, reportlab"
}
```

**架构设计**：
```
frontend/src/modules/report/
  ├── components/
  │   ├── ReportDesigner/      # 可视化报表设计器
  │   ├── ReportViewer/        # 报表查看器
  │   ├── ChartBuilder/        # 图表构建器
  │   └── ExportManager/       # 导出管理
  └── services/
      └── reportService.ts

backend/src/services/report/
  ├── report_engine.py         # 报表引擎核心
  ├── chart_builder.py         # 图表生成器
  ├── export_service.py        # 导出服务
  └── templates/               # 报表模板
```

**功能清单**：
- 报表设计器（拖拽式）
- 40+ 图表类型（基于 ECharts）
- 参数查询面板
- 定时报表生成（Celery + Redis）
- 报表导出（Excel、PDF、图片）
- 报表权限管理

**大屏可视化方案**：
```typescript
{
  布局: "CSS Grid + Flexbox",
  图表: "ECharts + Three.js",
  地图: "高德/百度地图API",
  动画: "Framer Motion",
  实时数据: "WebSocket",
  响应式: "支持 2K/4K"
}
```

**实施路线**（预计 12-16周）：

**Phase 1（1-2月）：基础报表**
- 报表设计器 MVP
- 基础图表组件库
- 报表导出（Excel）

**Phase 2（2-3月）：高级功能**
- 复杂交叉表
- 参数查询
- 定时报表
- 报表权限

**Phase 3（3-4月）：大屏可视化**
- 实时数据大屏
- 3D可视化
- 移动端适配

**参考资源**：
- ECharts：https://echarts.apache.org/
- AG Grid：https://www.ag-grid.com/
- Metabase（学习UX）：https://www.metabase.com/
- Apache Superset（大数据分析）：https://superset.apache.org/

---

### 9.3 资产管理系统 - 现有设计优势

#### 系统设计评估

根据对比行业标准（Odoo、HC物业系统等），**您的系统设计非常先进**：

| 维度 | 您的系统 | 行业标准 | 评价 |
|------|---------|---------|------|
| **三方关系模型** | ✅ 独立Ownership表 | 嵌入式 | 优秀 |
| **权限控制** | ✅ 动态权限+资源权限 | 标准RBAC | 先进 |
| **合同管理** | ✅ RentTerm+RentLedger双层 | 单层 | 灵活 |
| **审计追踪** | ✅ 完整历史记录 | 基础日志 | 完善 |
| **计算字段** | ✅ 出租率自动计算 | 存储字段 | 智能 |

**建议优化的重点**：
1. **合同状态机** - 增加状态流转控制
2. **预警系统** - 合同到期、租金逾期提醒
3. **权限模板** - 预定义角色权限组合

---

## 十、最终需求清单（已去除伪需求）

### P0+ 级别（最高优先级，架构重构）

| 模块 | 真实需求 | 参考方案 | 预计工时 |
|------|---------|---------|---------|
| **三方业务关系** | 支持权属方-运营方-终端租户，承租/委托运营 | - | 7-12天 |
| **审批流程引擎** | 功能完备，可视化配置 | Flowable + REST API | 8-10周 |
| **报表和可视化** | 自定义报表 + 大屏可视化 | ECharts + 自研 | 12-16周 |

### P0 级别（核心功能）

| 模块 | 真实需求 | 关键点 | 预计工时 |
|------|---------|--------|---------|
| **合同详情页** | 主要信息 + PDF附件 | 友好链接，支持多个PDF | 3-5天 |
| **合同编辑页** | 修正错误，需审批控制 | 审批开关 + 流程配置 | 3-5天 |
| **权属方详情页** | 基本信息 + 关联资产/合同 + 收入统计 | 区分承租/委托运营统计 | 5-7天 |
| **权属方编辑页** | 独立编辑页面 | - | 2-3天 |
| **项目管理页面** | 操作类：管理资产、批量操作 | 面向运营人员 | 5-7天 |
| **项目查看页面** | 呈现类：概览、统计图表 | 面向财务/管理 | 5-7天 |
| **站内消息中心** | 待办、通知 | - | 3-5天 |
| **提醒模块** | 独立模块，按角色权限配置 | 合同到期/租金逾期/审批待办 | 5-7天 |

### P1 级别（重要功能，后续需要）

| 模块 | 状态 | 说明 |
|------|------|------|
| **催缴管理** | ✅ 保留 | 后续需要 |
| **合同变更管理** | ✅ 保留 | 没那么急，但是需要 |
| **合同续签提醒** | ⬇️ 降级 | 到期提醒就够了 |
| **资产折旧/处置** | ⬇️ 降级到P3 | 后续可能需要 |

### 已识别的伪需求（不实现）

| 原报告认为 | 实际情况 |
|-----------|---------|
| 项目44字段表单 | 需要的是项目管理界面，不是大量字段 |
| 邮件/短信通知 | 暂不需要 |
| 租金调整功能 | 暂不需要 |
| 简单的个人提醒配置 | 需要基于角色权限的配置 |

---

## 十一、实施优先级和时间规划

### 阶段1：架构重构（2-3周）

**目标**：支持三方业务关系

**任务**：
1. 重构数据模型（添加 contract_type、operator_id 等字段）
2. 调整 RentContract API
3. 更新前端类型定义
4. 数据库迁移

### 阶段2：核心功能补全（6-8周）

**目标**：完成P0级别的前端页面

**任务**：
1. 合同详情页 + 编辑页（含PDF附件、审批控制）
2. 权属方详情页 + 编辑页（含收入统计）
3. 项目管理页面 + 项目查看页面
4. 站内消息中心
5. 提醒模块

### 阶段3：流程引擎（8-10周）

**目标**：实现功能完备的审批流程

**任务**：
1. 集成 Flowable（Docker部署）
2. 实现流程设计器
3. 实现审批操作界面
4. 实现待办事项管理
5. 实现审批历史查询

### 阶段4：报表可视化（12-16周）

**目标**：实现自定义报表和大屏可视化

**任务**：
1. 报表设计器
2. 图表组件库
3. 报表导出功能
4. 实时数据大屏
5. 移动端适配

---

## 十二、总结和建议

### 系统优势

您的系统在设计上已经非常先进：
1. **三方关系模型清晰** - Ownership/Project/Asset分离合理
2. **权限系统先进** - 动态权限+临时权限+条件权限
3. **审计追踪完善** - 历史记录+操作日志
4. **计算字段智能** - 未出租面积、出租率自动计算

### 关键建议

1. **优先处理架构问题** - 三方业务关系是基础
2. **参考最佳实践** - Flowable、ECharts等成熟方案
3. **渐进式开发** - 分阶段实施，逐步完善
4. **保持灵活性** - 预留扩展空间，避免过度设计

### 下一步行动

1. 确认优先级排序
2. 确定技术选型（Flowable、ECharts等）
3. 制定详细开发计划
4. 启动第一阶段开发

---

**文档已完成。更新时间：2025-01-03**
