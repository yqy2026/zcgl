# 数据模型字段对比分析

## 前端Asset接口字段分析

基于前端 `types/asset.ts` 的字段定义：

### 基本信息
- id: string
- ownership_entity: string
- ownership_category?: string
- project_name?: string
- property_name: string
- address: string
- ownership_status: OwnershipStatus
- property_nature: PropertyNature
- usage_status: UsageStatus
- business_category?: string
- is_litigated?: boolean
- notes?: string

### 面积相关字段
- land_area?: number
- actual_property_area?: number
- rentable_area?: number
- rented_area?: number
- unrented_area?: number (自动计算)
- non_commercial_area?: number
- occupancy_rate?: number (自动计算)
- include_in_occupancy_rate?: boolean

### 用途相关字段
- certificated_usage?: string
- actual_usage?: string

### 租户相关字段
- tenant_name?: string
- tenant_contact?: string
- tenant_type?: TenantType

### 合同相关字段
- lease_contract_number?: string
- contract_start_date?: string
- contract_end_date?: string
- contract_status?: ContractStatus
- monthly_rent?: number
- deposit?: number
- is_sublease?: boolean
- sublease_notes?: string

### 管理相关字段
- manager_name?: string
- business_model?: BusinessModel
- operation_status?: OperationStatus

### 财务相关字段
- annual_income?: number
- annual_expense?: number
- net_income?: number (自动计算)

### 接收相关字段
- operation_agreement_start_date?: string
- operation_agreement_end_date?: string
- operation_agreement_attachments?: string

### 终端合同相关字段
- terminal_contract_files?: string

### 项目相关字段
- project_id?: string
- ownership_id?: string

### 系统字段
- data_status?: DataStatus
- created_by?: string
- updated_by?: string
- version?: number
- tags?: string

### 审核相关字段
- last_audit_date?: string
- audit_status?: AuditStatus
- auditor?: string
- audit_notes?: string

### 时间戳
- created_at?: string
- updated_at?: string

### 多租户支持
- tenant_id?: string

## 后端Asset模型字段分析

基于后端 `models/asset.py` 的字段定义：

### 基本信息
- id: String (UUID)
- ownership_entity: String(200) - 权属方
- ownership_category: String(100) - 权属类别
- project_name: String(200) - 项目名称
- property_name: String(200) - 物业名称
- address: String(500) - 物业地址
- ownership_status: String(50) - 确权状态
- property_nature: String(50) - 物业性质
- usage_status: String(50) - 使用状态
- business_category: String(100) - 业态类别
- is_litigated: Boolean - 是否涉诉
- notes: Text - 备注

### 面积相关字段
- land_area: DECIMAL(12, 2) - 土地面积
- actual_property_area: DECIMAL(12, 2) - 实际房产面积
- rentable_area: DECIMAL(12, 2) - 可出租面积
- rented_area: DECIMAL(12, 2) - 已出租面积
- unrented_area: DECIMAL(12, 2) - 未出租面积
- non_commercial_area: DECIMAL(12, 2) - 非经营物业面积
- occupancy_rate: DECIMAL(5, 2) - 出租率
- include_in_occupancy_rate: Boolean - 是否计入出租率统计

### 用途相关字段
- certificated_usage: String(100) - 证载用途
- actual_usage: String(100) - 实际用途

### 租户相关字段
- tenant_name: String(200) - 租户名称
- tenant_type: String(20) - 租户类型
- tenant_contact: String(200) - 租户联系方式

### 合同相关字段
- lease_contract_number: String(100) - 租赁合同编号
- contract_start_date: Date - 合同开始日期
- contract_end_date: Date - 合同结束日期
- monthly_rent: DECIMAL(15, 2) - 月租金
- deposit: DECIMAL(15, 2) - 押金
- is_sublease: Boolean - 是否分租/转租
- sublease_notes: Text - 分租/转租备注

### 管理相关字段
- business_model: String(50) - 接收模式
- operation_status: String(20) - 经营状态
- manager_name: String(100) - 管理责任人（网格员）

### 财务相关字段
- annual_income: DECIMAL(15, 2) - 年收益
- annual_expense: DECIMAL(15, 2) - 年支出
- net_income: DECIMAL(15, 2) - 净收益

### 接收相关字段
- operation_agreement_start_date: Date - 接收协议开始日期
- operation_agreement_end_date: Date - 接收协议结束日期
- operation_agreement_attachments: Text - 接收协议文件

### 终端合同相关字段
- terminal_contract_files: Text - 终端合同文件

### 项目相关字段
- project_id: String (Foreign Key to projects.id)
- ownership_id: String (Foreign Key to ownerships.id)

### 系统字段
- data_status: String(20) - 数据状态
- version: Integer - 版本号
- tags: Text - 标签
- created_by: String(100) - 创建人
- updated_by: String(100) - 更新人

### 审核相关字段
- last_audit_date: Date - 最后审核时间
- audit_status: String(20) - 审核状态
- audit_notes: Text - 审核备注
- auditor: String(100) - 审核人

### 时间戳
- created_at: DateTime - 创建时间
- updated_at: DateTime - 更新时间

### 多租户支持
- tenant_id: String(50) - 租户ID

## 字段对比结果

### ✅ 完全匹配的字段
绝大部分字段在前后端之间都有对应，包括：
- 所有基本信息字段
- 所有面积相关字段
- 所有用途相关字段
- 所有租户相关字段
- 所有合同相关字段
- 所有管理相关字段
- 所有财务相关字段
- 所有接收相关字段
- 终端合同字段
- 项目关联字段
- 系统字段
- 审核字段
- 时间戳
- 多租户字段

### ❌ 前端有但后端没有的字段
- `contract_status: ContractStatus` - 前端定义的合同状态枚举，后端模型中不存在此字段

### ❌ 后端有但前端没有的字段
经过对比，所有后端字段在前端都有对应定义

### ⚠️ 类型差异
- 日期字段：前端使用 `string`，后端使用 `Date` 和 `DateTime`
- 数值字段：前端使用 `number`，后端使用 `DECIMAL` (通过API序列化为字符串)
- 文本字段：前端使用 `string`，后端有 `String` 和 `Text` 之分

## 总结

前后端数据模型一致性**非常好**，只有极少数差异：

1. **主要问题**：前端多了一个 `contract_status` 字段，后端模型中不存在
2. **次要问题**：数据类型在序列化层面的正常差异（Date vs string，Decimal vs number）

这表明项目的前后端数据模型设计相当规范和一致。