# 土地物业资产管理系统 - 数据库设计文档

> **版本**: v2.0
> **更新日期**: 2026-01-23
> **数据库**: PostgreSQL
> **ORM**: SQLAlchemy 2.0

---

## 目录

1. [概述](#1-概述)
2. [核心业务模块](#2-核心业务模块)
3. [用户与权限模块](#3-用户与权限模块)
4. [合同与财务模块](#4-合同与财务模块)
5. [组织架构模块](#5-组织架构模块)
6. [系统支撑模块](#6-系统支撑模块)
7. [关联表](#7-关联表)
8. [ER图](#8-er图)

---

## 1. 概述

本系统包含 **45+ 个数据表**，分为以下主要模块：

| 模块 | 表数量 | 核心功能 |
|------|--------|----------|
| 核心业务 | 9 | 资产、项目、权属方、产权证管理 |
| 用户权限 | 14 | 用户认证、RBAC、动态权限 |
| 合同财务 | 8 | 租赁合同、租金台账、押金、催缴 |
| 组织架构 | 4 | 组织、职位、员工 |
| 系统支撑 | 10+ | 通知、日志、任务、枚举、PDF导入 |

---

## 2. 核心业务模块

### 2.1 资产表 (assets)

> 核心资产信息表，存储物业资产的完整信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 资产ID (UUID) |
| **基本信息** ||||
| `ownership_category` | String(100) | | 权属类别 |
| `project_name` | String(200) | | 项目名称 |
| `property_name` | String(200) | NOT NULL | 物业名称 |
| `address` | String(500) | NOT NULL | 物业地址 |
| `ownership_status` | String(50) | NOT NULL | 确权状态 |
| `property_nature` | String(50) | NOT NULL | 物业性质 |
| `usage_status` | String(50) | NOT NULL | 使用状态 |
| `business_category` | String(100) | | 业态类别 |
| `is_litigated` | Boolean | NOT NULL, DEFAULT FALSE | 是否涉诉 |
| `notes` | Text | | 备注 |
| **面积信息** ||||
| `land_area` | DECIMAL(12,2) | | 土地面积（平方米）|
| `actual_property_area` | DECIMAL(12,2) | | 实际房产面积（平方米）|
| `rentable_area` | DECIMAL(12,2) | | 可出租面积（平方米）|
| `rented_area` | DECIMAL(12,2) | | 已出租面积（平方米）|
| `non_commercial_area` | DECIMAL(12,2) | | 非经营物业面积（平方米）|
| `include_in_occupancy_rate` | Boolean | NOT NULL, DEFAULT TRUE | 是否计入出租率统计 |
| **用途信息** ||||
| `certificated_usage` | String(100) | | 证载用途 |
| `actual_usage` | String(100) | | 实际用途 |
| **租户信息** ||||
| `tenant_name` | String(200) | | 租户名称 |
| `tenant_type` | String(20) | | 租户类型 |
| **合同信息** ||||
| `lease_contract_number` | String(100) | | 租赁合同编号 |
| `contract_start_date` | Date | | 合同开始日期 |
| `contract_end_date` | Date | | 合同结束日期 |
| `monthly_rent` | DECIMAL(15,2) | | 月租金（元）|
| `deposit` | DECIMAL(15,2) | | 押金（元）|
| `is_sublease` | Boolean | NOT NULL, DEFAULT FALSE | 是否分租/转租 |
| `sublease_notes` | Text | | 分租/转租备注 |
| **管理信息** ||||
| `business_model` | String(50) | | 接收模式 |
| `operation_status` | String(20) | | 经营状态 |
| `manager_name` | String(100) | | 管理责任人（网格员）|
| **接收协议** ||||
| `operation_agreement_start_date` | Date | | 接收协议开始日期 |
| `operation_agreement_end_date` | Date | | 接收协议结束日期 |
| `operation_agreement_attachments` | Text | | 接收协议文件 |
| `terminal_contract_files` | Text | | 终端合同文件 |
| **关联字段** ||||
| `project_id` | String | FK → projects.id | 项目ID |
| `ownership_id` | String | FK → ownerships.id | 权属方ID |
| **系统字段** ||||
| `data_status` | String(20) | NOT NULL, DEFAULT '正常' | 数据状态 |
| `version` | Integer | NOT NULL, DEFAULT 1 | 版本号 |
| `tags` | Text | | 标签 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |
| `audit_notes` | Text | | 审核备注 |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |
| `tenant_id` | String(50) | | 租户ID（多租户）|

**计算属性**:
- `unrented_area`: 未出租面积 = 可出租面积 - 已出租面积
- `occupancy_rate`: 出租率(%) = 已出租面积 / 可出租面积 × 100

**说明**:
- `ownership_entity` 不再作为存储字段；权属方名称从 `ownership_id` 关联的 `ownerships.name` 动态获取。

---

### 2.2 资产变更历史表 (asset_history)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 历史记录ID |
| `asset_id` | String | FK → assets.id, NOT NULL | 资产ID |
| `operation_type` | String(50) | NOT NULL | 操作类型 |
| `field_name` | String(100) | | 字段名称 |
| `old_value` | Text | | 原值 |
| `new_value` | Text | | 新值 |
| `operator` | String(100) | | 操作人 |
| `operation_time` | DateTime | | 操作时间 |
| `description` | Text | | 操作描述 |
| `change_reason` | String(200) | | 变更原因 |
| `ip_address` | String(45) | | IP地址 |
| `user_agent` | Text | | 用户代理 |
| `session_id` | String(100) | | 会话ID |

---

### 2.3 资产文档表 (asset_documents)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 文档ID |
| `asset_id` | String | FK → assets.id, NOT NULL | 资产ID |
| `document_name` | String(200) | NOT NULL | 文档名称 |
| `document_type` | String(50) | NOT NULL | 文档类型 |
| `file_path` | String(500) | | 文件路径 |
| `file_size` | Integer | | 文件大小(字节) |
| `mime_type` | String(100) | | 文件MIME类型 |
| `upload_time` | DateTime | | 上传时间 |
| `uploader` | String(100) | | 上传人 |
| `description` | Text | | 文档描述 |

---

### 2.4 项目表 (projects)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String(36) | PK | 项目ID |
| **基本信息** ||||
| `name` | String(200) | NOT NULL | 项目名称 |
| `short_name` | String(100) | | 项目简称 |
| `code` | String(100) | UNIQUE, NOT NULL | 项目编码 |
| `project_type` | String(50) | | 项目类型 |
| `project_scale` | String(50) | | 项目规模 |
| `project_status` | String(50) | NOT NULL, DEFAULT '规划中' | 项目状态 |
| `start_date` | Date | | 开始日期 |
| `end_date` | Date | | 结束日期 |
| `expected_completion_date` | Date | | 预计完成日期 |
| `actual_completion_date` | Date | | 实际完成日期 |
| **地址信息** ||||
| `address` | String(500) | | 项目地址 |
| `city` | String(100) | | 城市 |
| `district` | String(100) | | 区域 |
| `province` | String(100) | | 省份 |
| **联系信息** ||||
| `project_manager` | String(100) | | 项目经理 |
| `project_phone` | String(50) | | 项目电话 |
| `project_email` | String(100) | | 项目邮箱 |
| **投资信息** ||||
| `total_investment` | DECIMAL(15,2) | | 总投资 |
| `planned_investment` | DECIMAL(15,2) | | 计划投资 |
| `actual_investment` | DECIMAL(15,2) | | 实际投资 |
| `project_budget` | DECIMAL(15,2) | | 项目预算 |
| **项目描述** ||||
| `project_description` | Text | | 项目描述 |
| `project_objectives` | Text | | 项目目标 |
| `project_scope` | Text | | 项目范围 |
| **相关单位** ||||
| `management_entity` | String(200) | | 管理单位 |
| `ownership_entity` | String(200) | | 权属单位 |
| `construction_company` | String(200) | | 施工单位 |
| `design_company` | String(200) | | 设计单位 |
| `supervision_company` | String(200) | | 监理单位 |
| **系统字段** ||||
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否启用 |
| `data_status` | String(20) | NOT NULL, DEFAULT '正常' | 数据状态 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 2.5 权属方表 (ownerships)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 权属方ID |
| `name` | String(200) | NOT NULL | 权属方全称 |
| `code` | String(100) | NOT NULL | 权属方编码 |
| `short_name` | String(100) | | 权属方简称 |
| `address` | String(500) | | 地址 |
| `management_entity` | String(200) | | 管理单位 |
| `notes` | Text | | 备注 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 状态 |
| `data_status` | String(20) | NOT NULL, DEFAULT '正常' | 数据状态 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 2.6 项目-权属方关系表 (project_ownership_relations)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 关系ID |
| `project_id` | String | FK → projects.id, NOT NULL | 项目ID |
| `ownership_id` | String | FK → ownerships.id, NOT NULL | 权属方ID |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否有效 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 2.7 产权证表 (property_certificates)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 产权证ID |
| `certificate_number` | String(100) | UNIQUE, NOT NULL, INDEX | 证书编号 |
| `certificate_type` | Enum | NOT NULL, INDEX | 证书类型 |
| **提取元数据** ||||
| `extraction_confidence` | Float | | LLM提取置信度 (0-1) |
| `extraction_source` | String(20) | DEFAULT 'manual' | 数据来源：llm/manual |
| `verified` | Boolean | DEFAULT FALSE | 是否人工审核 |
| **基本信息** ||||
| `registration_date` | Date | | 登记日期 |
| `property_address` | String(500) | | 坐落地址 |
| `property_type` | String(50) | | 用途 |
| **房屋信息** ||||
| `building_area` | String(50) | | 建筑面积（平方米）|
| `floor_info` | String(100) | | 楼层信息 |
| **土地信息** ||||
| `land_area` | String(50) | | 土地使用面积（平方米）|
| `land_use_type` | String(50) | | 土地使用权类型 |
| `land_use_term_start` | Date | | 土地使用期限起 |
| `land_use_term_end` | Date | | 土地使用期限止 |
| **其他信息** ||||
| `co_ownership` | String(200) | | 共有情况 |
| `restrictions` | Text | | 权利限制情况 |
| `remarks` | Text | | 备注 |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |
| `created_by` | String(100) | | 创建人ID |

**证书类型枚举 (CertificateType)**:
- `real_estate`: 不动产权证（新版）
- `house_ownership`: 房屋所有权证（旧版）
- `land_use`: 土地使用证
- `other`: 其他权属证明

---

### 2.8 权利人表 (property_owners)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 权利人ID |
| `owner_type` | Enum | NOT NULL, INDEX | 权利人类型 |
| `name` | String(200) | NOT NULL, INDEX | 权利人姓名/单位名称 |
| `id_type` | String(50) | | 证件类型 |
| `id_number` | String(100) | | 证件号码（加密存储）|
| `phone` | String(20) | | 联系电话（加密存储）|
| `address` | String(500) | | 地址 |
| `organization_id` | String | FK → organizations.id | 关联组织ID |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |

**权利人类型枚举 (OwnerType)**:
- `individual`: 个人
- `organization`: 组织/企业
- `joint`: 共有

---

### 2.9 系统数据字典表 (system_dictionaries)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String(50) | PK | 字典ID |
| `dict_type` | String(50) | NOT NULL | 字典类型 |
| `dict_code` | String(50) | NOT NULL | 字典编码 |
| `dict_label` | String(100) | NOT NULL | 字典标签 |
| `dict_value` | String(100) | NOT NULL | 字典值 |
| `sort_order` | Integer | NOT NULL, DEFAULT 0 | 排序 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否启用 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |

---

### 2.10 资产自定义字段表 (asset_custom_fields)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String(50) | PK | 字段ID |
| `field_name` | String(100) | NOT NULL | 字段名称 |
| `display_name` | String(100) | NOT NULL | 显示名称 |
| `field_type` | String(20) | NOT NULL | 字段类型 |
| `is_required` | Boolean | NOT NULL, DEFAULT FALSE | 是否必填 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否启用 |
| `sort_order` | Integer | NOT NULL, DEFAULT 0 | 排序 |
| `default_value` | Text | | 默认值 |
| `field_options` | Text | | 字段选项(JSON) |
| `validation_rules` | Text | | 验证规则(JSON) |
| `help_text` | Text | | 帮助文本 |
| `description` | Text | | 描述 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |

---

## 3. 用户与权限模块

### 3.1 用户表 (users)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 用户ID |
| **基本信息** ||||
| `username` | String(50) | UNIQUE, NOT NULL, INDEX | 用户名 |
| `email` | String(100) | UNIQUE, NOT NULL, INDEX | 邮箱 |
| `full_name` | String(100) | NOT NULL | 全名 |
| **认证信息** ||||
| `password_hash` | String(255) | NOT NULL | 密码哈希 |
| `password_history` | JSON | | 密码历史记录 |
| **角色与状态** ||||
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否激活 |
| `is_locked` | Boolean | NOT NULL, DEFAULT FALSE | 是否锁定 |
| **登录信息** ||||
| `last_login_at` | DateTime | | 最后登录时间 |
| `failed_login_attempts` | Integer | NOT NULL, DEFAULT 0 | 失败登录次数 |
| `locked_until` | DateTime | | 锁定到期时间 |
| `password_last_changed` | DateTime | | 密码最后修改时间 |
| **组织关联** ||||
| `employee_id` | String | FK → employees.id | 关联员工ID |
| `default_organization_id` | String | FK → organizations.id | 默认组织ID |
| **审计信息** ||||
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

**说明**:
- 用户角色由 RBAC 表 `roles` 与 `user_role_assignments` 维护，`users` 表不再存储角色字段。

---

### 3.2 用户会话表 (user_sessions)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 会话ID |
| `user_id` | String | FK → users.id, NOT NULL | 用户ID |
| `session_id` | String(100) | UNIQUE | 会话标识 |
| `refresh_token` | String(255) | UNIQUE, NOT NULL | 刷新令牌 |
| `device_info` | Text | | 设备信息 |
| `device_id` | String(100) | | 设备ID |
| `platform` | String(50) | | 平台 |
| `ip_address` | String(45) | | IP地址 |
| `user_agent` | Text | | 用户代理 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否活跃 |
| `expires_at` | DateTime | NOT NULL | 过期时间 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `last_accessed_at` | DateTime | NOT NULL | 最后访问时间 |

---

### 3.3 审计日志表 (audit_logs)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 日志ID |
| **用户信息** ||||
| `user_id` | String | FK → users.id, NOT NULL | 用户ID |
| `username` | String(50) | NOT NULL | 用户名 |
| `user_role` | String(20) | | 用户角色 |
| `user_organization` | String(200) | | 用户所属组织 |
| **操作信息** ||||
| `action` | String(100) | NOT NULL | 操作动作 |
| `resource_type` | String(50) | | 资源类型 |
| `resource_id` | String | | 资源ID |
| `resource_name` | String(200) | | 资源名称 |
| **请求信息** ||||
| `api_endpoint` | String(200) | | API端点 |
| `http_method` | String(10) | | HTTP方法 |
| `request_params` | Text | | 请求参数 |
| `request_body` | Text | | 请求体 |
| **响应信息** ||||
| `response_status` | Integer | | 响应状态码 |
| `response_message` | String(500) | | 响应消息 |
| **环境信息** ||||
| `ip_address` | String(45) | | IP地址 |
| `user_agent` | Text | | 用户代理 |
| `session_id` | String(100) | | 会话ID |
| `created_at` | DateTime | NOT NULL | 创建时间 |

---

### 3.4 角色表 (roles)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 角色ID |
| `name` | String(100) | UNIQUE, NOT NULL | 角色名称 |
| `display_name` | String(200) | NOT NULL | 显示名称 |
| `description` | Text | | 角色描述 |
| `level` | Integer | NOT NULL, DEFAULT 1 | 角色级别 |
| `category` | String(50) | | 角色类别 |
| `is_system_role` | Boolean | NOT NULL, DEFAULT FALSE | 是否系统角色 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否激活 |
| `organization_id` | String | FK → organizations.id | 所属组织ID |
| `scope` | String(50) | DEFAULT 'global' | 权限范围 |
| `scope_id` | String | | 范围ID |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 3.5 权限表 (permissions)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 权限ID |
| `name` | String(100) | UNIQUE, NOT NULL | 权限名称 |
| `display_name` | String(200) | NOT NULL | 显示名称 |
| `description` | Text | | 权限描述 |
| `resource` | String(50) | NOT NULL | 资源类型 |
| `action` | String(50) | NOT NULL | 操作类型 |
| `is_system_permission` | Boolean | NOT NULL, DEFAULT FALSE | 是否系统权限 |
| `requires_approval` | Boolean | DEFAULT FALSE | 是否需要审批 |
| `max_level` | Integer | | 最大级别 |
| `conditions` | JSON | | 权限条件(JSON) |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 3.6 用户角色分配表 (user_role_assignments)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 分配ID |
| `user_id` | String | FK → users.id, NOT NULL | 用户ID |
| `role_id` | String | FK → roles.id, NOT NULL | 角色ID |
| `assigned_by` | String(100) | | 分配人 |
| `assigned_at` | DateTime | NOT NULL | 分配时间 |
| `expires_at` | DateTime | | 过期时间 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否激活 |
| `reason` | Text | | 分配原因 |
| `notes` | Text | | 备注 |
| `context` | JSON | | 上下文信息(JSON) |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |

---

### 3.7 资源权限表 (resource_permissions)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 资源权限ID |
| `resource_type` | String(50) | NOT NULL | 资源类型 |
| `resource_id` | String | NOT NULL | 资源ID |
| `user_id` | String | FK → users.id | 用户ID |
| `role_id` | String | FK → roles.id | 角色ID |
| `permission_id` | String | FK → permissions.id | 权限ID |
| `permission_level` | String(20) | DEFAULT 'read' | 权限级别 |
| `granted_at` | DateTime | NOT NULL | 授权时间 |
| `expires_at` | DateTime | | 过期时间 |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否激活 |
| `granted_by` | String(100) | | 授权人 |
| `reason` | Text | | 授权原因 |
| `conditions` | JSON | | 权限条件(JSON) |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |

**权限级别**: `read` / `write` / `delete` / `admin`

---

### 3.8 统一授权表 (permission_grants)

> 说明：项目已统一为 `permission_grants` 单表授权模型；`dynamic_permissions`、`temporary_permissions`、`conditional_permissions`、`permission_requests`、`permission_delegations` 等旧表已移除。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK, INDEX | 授权记录ID |
| `user_id` | String | FK → users.id, NOT NULL, INDEX | 用户ID |
| `permission_id` | String | FK → permissions.id, NOT NULL, INDEX | 权限ID |
| `grant_type` | String(50) | NOT NULL, DEFAULT 'direct', INDEX | 授权类型 |
| `effect` | String(10) | NOT NULL, DEFAULT 'allow', INDEX | 授权效果 |
| `scope` | String(50) | NOT NULL, DEFAULT 'global', INDEX | 作用域 |
| `scope_id` | String | INDEX | 作用域ID |
| `conditions` | JSON | | 条件表达式 |
| `starts_at` | DateTime | INDEX | 生效时间 |
| `expires_at` | DateTime | INDEX | 过期时间 |
| `priority` | Integer | NOT NULL, DEFAULT 100 | 优先级（越大越高） |
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE, INDEX | 是否激活 |
| `source_type` | String(50) | INDEX | 来源类型 |
| `source_id` | String | INDEX | 来源记录ID |
| `granted_by` | String(100) | | 授权人 |
| `reason` | Text | | 授权原因 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `revoked_at` | DateTime | | 撤销时间 |
| `revoked_by` | String(100) | | 撤销人 |

**授权类型**: `direct` / `dynamic` / `temporary` / `conditional` / `resource` / `delegation` / `request_approved` / `template_based`

**授权效果**: `allow` / `deny`

**作用域**: `global` / `organization` / `project` / `asset` / `custom`

---

### 3.9 权限审计日志表 (permission_audit_logs)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 日志ID |
| `action` | String(50) | NOT NULL | 操作类型 |
| `resource_type` | String(50) | | 资源类型 |
| `resource_id` | String | | 资源ID |
| `user_id` | String | FK → users.id | 用户ID |
| `operator_id` | String | FK → users.id | 操作人ID |
| `old_permissions` | JSON | | 原权限(JSON) |
| `new_permissions` | JSON | | 新权限(JSON) |
| `reason` | Text | | 变更原因 |
| `ip_address` | String(45) | | IP地址 |
| `user_agent` | Text | | 用户代理 |
| `created_at` | DateTime | NOT NULL | 创建时间 |

---

## 4. 合同与财务模块

### 4.1 租金合同表 (rent_contracts)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 合同ID |
| **基本信息** ||||
| `contract_number` | String(100) | UNIQUE, NOT NULL | 合同编号 |
| `ownership_id` | String | FK → ownerships.id, NOT NULL | 权属方ID |
| `contract_type` | Enum | NOT NULL, DEFAULT 'lease_downstream' | 合同类型 |
| `upstream_contract_id` | String | FK → rent_contracts.id | 上游合同ID |
| **甲方/权属方信息** ||||
| `owner_name` | String(200) | | 甲方/权属方名称 |
| `owner_contact` | String(100) | | 甲方联系人 |
| `owner_phone` | String(20) | | 甲方联系电话 |
| **服务费率** ||||
| `service_fee_rate` | DECIMAL(5,4) | | 服务费率（仅委托运营）|
| **承租方信息** ||||
| `tenant_name` | String(200) | NOT NULL | 承租方名称 |
| `tenant_contact` | String(100) | | 承租方联系人 |
| `tenant_phone` | String(20) | | 承租方联系电话 |
| `tenant_address` | String(500) | | 承租方地址 |
| `tenant_usage` | String(500) | | 用途说明 |
| **合同日期** ||||
| `sign_date` | Date | NOT NULL | 签订日期 |
| `start_date` | Date | NOT NULL | 租期开始日期 |
| `end_date` | Date | NOT NULL | 租期结束日期 |
| **金额信息** ||||
| `total_deposit` | DECIMAL(15,2) | DEFAULT 0 | 总押金金额 |
| `monthly_rent_base` | DECIMAL(15,2) | | 基础月租金 |
| `payment_cycle` | Enum | DEFAULT 'monthly' | 付款周期 |
| **状态信息** ||||
| `contract_status` | String(20) | DEFAULT '有效' | 合同状态 |
| `payment_terms` | Text | | 支付条款 |
| `contract_notes` | Text | | 合同备注 |
| **系统字段** ||||
| `data_status` | String(20) | DEFAULT '正常' | 数据状态 |
| `version` | Integer | DEFAULT 1 | 版本号 |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |
| `tenant_id` | String(50) | | 租户ID（多租户）|
| `source_session_id` | String(100) | | PDF导入会话ID |

**合同类型枚举 (ContractType)**:
- `lease_upstream`: 上游租赁合同（运营方承租）
- `lease_downstream`: 下游租赁合同（转租给终端租户）
- `entrusted`: 委托运营合同

**付款周期枚举 (PaymentCycle)**:
- `monthly`: 月付
- `quarterly`: 季付
- `semi_annual`: 半年付
- `annual`: 年付

---

### 4.2 租金条款表 (rent_terms)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 条款ID |
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联合同ID |
| `start_date` | Date | NOT NULL | 条款开始日期 |
| `end_date` | Date | NOT NULL | 条款结束日期 |
| `monthly_rent` | DECIMAL(15,2) | NOT NULL | 月租金金额 |
| `rent_description` | String(500) | | 租金描述 |
| `management_fee` | DECIMAL(15,2) | DEFAULT 0 | 管理费 |
| `other_fees` | DECIMAL(15,2) | DEFAULT 0 | 其他费用 |
| `total_monthly_amount` | DECIMAL(15,2) | | 月总金额 |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |

---

### 4.3 租金台账表 (rent_ledger)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 台账ID |
| **关联信息** ||||
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联合同ID |
| `asset_id` | String | FK → assets.id | 关联资产ID |
| `ownership_id` | String | FK → ownerships.id, NOT NULL | 权属方ID |
| **时间信息** ||||
| `year_month` | String(7) | NOT NULL | 年月 (YYYY-MM) |
| `due_date` | Date | NOT NULL | 应缴日期 |
| **金额信息** ||||
| `due_amount` | DECIMAL(15,2) | NOT NULL | 应收金额 |
| `paid_amount` | DECIMAL(15,2) | DEFAULT 0 | 实收金额 |
| `overdue_amount` | DECIMAL(15,2) | DEFAULT 0 | 逾期金额 |
| **支付状态** ||||
| `payment_status` | String(20) | DEFAULT '未支付' | 支付状态 |
| `payment_date` | Date | | 支付日期 |
| `payment_method` | String(50) | | 支付方式 |
| `payment_reference` | String(100) | | 支付参考号 |
| **滞纳金** ||||
| `late_fee` | DECIMAL(15,2) | DEFAULT 0 | 滞纳金 |
| `late_fee_days` | Integer | DEFAULT 0 | 滞纳天数 |
| **其他** ||||
| `notes` | Text | | 备注 |
| `data_status` | String(20) | DEFAULT '正常' | 数据状态 |
| `version` | Integer | DEFAULT 1 | 版本号 |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |

**支付状态**: `未支付` / `部分支付` / `已支付` / `逾期`

---

### 4.4 押金台账表 (rent_deposit_ledger)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 押金记录ID |
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联合同ID |
| `transaction_type` | Enum | NOT NULL | 交易类型 |
| `amount` | DECIMAL(15,2) | NOT NULL | 金额 |
| `transaction_date` | Date | NOT NULL | 交易日期 |
| `related_contract_id` | String | FK → rent_contracts.id | 关联合同ID（续签转移）|
| `notes` | Text | | 备注 |
| `operator` | String(100) | | 操作人 |
| `operator_id` | String(50) | | 操作人ID |
| `created_at` | DateTime | | 创建时间 |

**押金交易类型枚举 (DepositTransactionType)**:
- `receipt`: 收取押金
- `refund`: 退还押金
- `deduction`: 抵扣（如欠租抵扣）
- `transfer_out`: 转出（续签时转到新合同）
- `transfer_in`: 转入（从旧合同续签转入）

---

### 4.5 服务费台账表 (service_fee_ledger)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 服务费ID |
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联委托运营合同ID |
| `source_ledger_id` | String | FK → rent_ledger.id | 关联的租金台账ID |
| `year_month` | String(7) | NOT NULL | 年月 (YYYY-MM) |
| `paid_rent_amount` | DECIMAL(15,2) | NOT NULL | 实收租金（计算基数）|
| `fee_rate` | DECIMAL(5,4) | NOT NULL | 服务费率 |
| `fee_amount` | DECIMAL(15,2) | NOT NULL | 服务费金额 |
| `settlement_status` | String(20) | DEFAULT '待结算' | 结算状态 |
| `settlement_date` | Date | | 结算日期 |
| `notes` | Text | | 备注 |
| `operator` | String(100) | | 操作人 |
| `operator_id` | String(50) | | 操作人ID |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |

---

### 4.6 合同历史记录表 (rent_contract_history)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 历史记录ID |
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联合同ID |
| `change_type` | String(50) | NOT NULL | 变更类型 |
| `change_description` | Text | | 变更描述 |
| `old_data` | JSON | | 变更前数据 |
| `new_data` | JSON | | 变更后数据 |
| `operator` | String(100) | | 操作人 |
| `operator_id` | String(50) | | 操作人ID |
| `created_at` | DateTime | | 创建时间 |

---

### 4.7 合同附件表 (rent_contract_attachments)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 附件ID |
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联合同ID |
| `file_name` | String(255) | NOT NULL | 文件名 |
| `file_path` | String(500) | NOT NULL | 文件存储路径 |
| `file_size` | Integer | | 文件大小(字节) |
| `mime_type` | String(100) | | 文件MIME类型 |
| `file_type` | String(50) | DEFAULT 'other' | 文件类型 |
| `description` | Text | | 附件描述 |
| `uploader` | String(100) | | 上传人 |
| `uploader_id` | String(50) | | 上传人ID |
| `created_at` | DateTime | | 上传时间 |

**文件类型**: `contract_scan` / `id_card` / `other`

---

### 4.8 催缴记录表 (collection_records)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 催缴记录ID |
| `ledger_id` | String | FK → rent_ledger.id, NOT NULL | 关联的租金台账ID |
| `contract_id` | String | FK → rent_contracts.id, NOT NULL | 关联合同ID |
| `collection_method` | Enum | NOT NULL | 催缴方式 |
| `collection_date` | Date | NOT NULL | 催缴日期 |
| `collection_status` | Enum | DEFAULT 'pending' | 催缴状态 |
| `contacted_person` | String(100) | | 被联系人 |
| `contact_phone` | String(20) | | 联系电话 |
| `promised_amount` | DECIMAL(15,2) | | 承诺付款金额 |
| `promised_date` | Date | | 承诺付款日期 |
| `actual_payment_amount` | DECIMAL(15,2) | | 实际付款金额 |
| `collection_notes` | Text | | 催缴备注 |
| `next_follow_up_date` | Date | | 下次跟进日期 |
| `operator` | String(100) | | 操作人 |
| `operator_id` | String(50) | | 操作人ID |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |

**催缴方式枚举 (CollectionMethod)**:
- `phone`: 电话催缴
- `sms`: 短信催缴
- `email`: 邮件催缴
- `wecom`: 企业微信催缴
- `visit`: 上门催缴
- `letter`: 催缴函
- `other`: 其他

**催缴状态枚举 (CollectionStatus)**:
- `pending`: 待催缴
- `in_progress`: 催缴中
- `success`: 催缴成功
- `failed`: 催缴失败
- `partial`: 部分成功

---

## 5. 组织架构模块

### 5.1 组织表 (organizations)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 组织ID |
| **基本信息** ||||
| `name` | String(200) | NOT NULL | 组织名称 |
| `code` | String(50) | NOT NULL | 组织编码 |
| `level` | Integer | NOT NULL, DEFAULT 1 | 组织层级 |
| `sort_order` | Integer | DEFAULT 0 | 排序 |
| `type` | String(20) | NOT NULL | 组织类型 |
| `status` | String(20) | NOT NULL, DEFAULT 'active' | 状态 |
| **联系信息** ||||
| `phone` | String(20) | | 联系电话 |
| `email` | String(100) | | 邮箱 |
| `address` | String(200) | | 地址 |
| **负责人信息** ||||
| `leader_name` | String(50) | | 负责人姓名 |
| `leader_phone` | String(20) | | 负责人电话 |
| `leader_email` | String(100) | | 负责人邮箱 |
| **层级关系** ||||
| `parent_id` | String | FK → organizations.id | 上级组织ID |
| `path` | String(1000) | | 组织路径（/分隔）|
| **描述信息** ||||
| `description` | Text | | 组织描述 |
| `functions` | Text | | 主要职能 |
| **系统信息** ||||
| `is_deleted` | Boolean | NOT NULL, DEFAULT FALSE | 是否删除 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 5.2 职位表 (positions)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 职位ID |
| `name` | String(100) | NOT NULL | 职位名称 |
| `level` | Integer | NOT NULL, DEFAULT 1 | 职位级别 |
| `category` | String(50) | | 职位类别 |
| `organization_id` | String | FK → organizations.id, NOT NULL | 所属组织ID |
| `description` | Text | | 职位描述 |
| `responsibilities` | Text | | 岗位职责 |
| `requirements` | Text | | 任职要求 |
| `salary_min` | Integer | | 最低薪资 |
| `salary_max` | Integer | | 最高薪资 |
| `is_deleted` | Boolean | NOT NULL, DEFAULT FALSE | 是否删除 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 5.3 员工表 (employees)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 员工ID |
| **基本信息** ||||
| `employee_no` | String(50) | UNIQUE, NOT NULL | 员工编号 |
| `name` | String(100) | NOT NULL | 姓名 |
| `gender` | String(10) | | 性别 |
| `birth_date` | DateTime | | 出生日期 |
| `id_card` | String(20) | | 身份证号 |
| **联系信息** ||||
| `emergency_contact` | String(100) | | 紧急联系人 |
| `emergency_phone` | String(20) | | 紧急联系电话 |
| **组织关系** ||||
| `organization_id` | String | FK → organizations.id, NOT NULL | 所属组织ID |
| `position_id` | String | FK → positions.id | 职位ID |
| `direct_supervisor_id` | String | FK → employees.id | 直接上级ID |
| **工作信息** ||||
| `hire_date` | DateTime | | 入职日期 |
| `probation_end_date` | DateTime | | 试用期结束日期 |
| `employment_type` | String(20) | | 用工类型 |
| `work_location` | String(200) | | 工作地点 |
| **薪资信息** ||||
| `base_salary` | Integer | | 基本工资 |
| `performance_salary` | Integer | | 绩效工资 |
| `total_salary` | Integer | | 总薪资 |
| **状态信息** ||||
| `resignation_date` | DateTime | | 离职日期 |
| `resignation_reason` | Text | | 离职原因 |
| **其他信息** ||||
| `education` | String(50) | | 学历 |
| `major` | String(100) | | 专业 |
| `skills` | Text | | 技能 |
| `notes` | Text | | 备注 |
| **系统信息** ||||
| `is_deleted` | Boolean | NOT NULL, DEFAULT FALSE | 是否删除 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

**用工类型**: `full_time` / `part_time` / `contract` / `intern`

---

### 5.4 组织变更历史表 (organization_history)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 历史记录ID |
| `organization_id` | String | FK → organizations.id, NOT NULL | 组织ID |
| `action` | String(20) | NOT NULL | 操作类型 |
| `field_name` | String(100) | | 变更字段 |
| `old_value` | Text | | 原值 |
| `new_value` | Text | | 新值 |
| `change_reason` | String(500) | | 变更原因 |
| `created_at` | DateTime | NOT NULL | 操作时间 |
| `created_by` | String(100) | | 操作人 |

---

## 6. 系统支撑模块

### 6.1 联系人表 (contacts)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 联系人ID |
| **关联实体** ||||
| `entity_type` | String(50) | NOT NULL, INDEX | 关联实体类型 |
| `entity_id` | String | NOT NULL, INDEX | 关联实体ID |
| **基本信息** ||||
| `name` | String(100) | NOT NULL | 联系人姓名 |
| `title` | String(100) | | 职位/头衔 |
| `department` | String(100) | | 部门 |
| **联系方式** ||||
| `phone` | String(20) | | 手机号码 |
| `office_phone` | String(20) | | 办公电话 |
| `email` | String(200) | | 电子邮箱 |
| `wechat` | String(100) | | 微信号 |
| `address` | String(500) | | 地址 |
| **分类信息** ||||
| `contact_type` | Enum | NOT NULL, DEFAULT 'general' | 联系人类型 |
| `is_primary` | Boolean | NOT NULL, DEFAULT FALSE | 是否主要联系人 |
| **备注信息** ||||
| `notes` | Text | | 备注 |
| `preferred_contact_time` | String(100) | | 偏好联系时间 |
| `preferred_contact_method` | String(50) | | 偏好联系方式 |
| **系统字段** ||||
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否启用 |
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

**实体类型**: `ownership` / `project` / `tenant`

**联系人类型枚举 (ContactType)**:
- `primary`: 主要联系人
- `finance`: 财务联系人
- `operations`: 运营联系人
- `legal`: 法务联系人
- `general`: 一般联系人

---

### 6.2 通知表 (notifications)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String(36) | PK | 通知ID |
| `recipient_id` | String(36) | FK → users.id, NOT NULL | 接收用户ID |
| `type` | String(50) | NOT NULL, INDEX | 通知类型 |
| `priority` | String(20) | DEFAULT 'normal' | 通知优先级 |
| `title` | String(200) | NOT NULL | 通知标题 |
| `content` | Text | NOT NULL | 通知内容 |
| `related_entity_type` | String(50) | | 关联实体类型 |
| `related_entity_id` | String(36) | | 关联实体ID |
| `is_read` | Boolean | DEFAULT FALSE, INDEX | 是否已读 |
| `read_at` | DateTime | | 已读时间 |
| `is_sent_wecom` | Boolean | DEFAULT FALSE | 是否已发送企业微信 |
| `wecom_sent_at` | DateTime | | 企业微信发送时间 |
| `wecom_send_error` | Text | | 企业微信发送错误信息 |
| `extra_data` | Text | | 额外数据（JSON）|

**通知类型常量**:
- `contract_expiring`: 合同即将到期
- `contract_expired`: 合同已到期
- `payment_overdue`: 付款逾期
- `payment_due`: 付款到期提醒
- `approval_pending`: 审批待办
- `system_notice`: 系统通知

**通知优先级**: `low` / `normal` / `high` / `urgent`

---

### 6.3 操作日志表 (operation_logs)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 日志ID |
| **用户信息** ||||
| `user_id` | String | NOT NULL | 操作用户ID |
| `username` | String(100) | | 操作用户名 |
| **操作信息** ||||
| `action` | String(50) | NOT NULL | 操作类型 |
| `action_name` | String(200) | | 操作名称 |
| `module` | String(50) | NOT NULL | 操作模块 |
| `module_name` | String(200) | | 模块名称 |
| **资源信息** ||||
| `resource_type` | String(50) | | 资源类型 |
| `resource_id` | String(100) | | 资源ID |
| `resource_name` | String(200) | | 资源名称 |
| **请求信息** ||||
| `request_method` | String(10) | | HTTP方法 |
| `request_url` | Text | | 请求URL |
| `request_params` | Text | | 请求参数(JSON) |
| `request_body` | Text | | 请求体(JSON) |
| **响应信息** ||||
| `response_status` | Integer | | 响应状态码 |
| `response_time` | Integer | | 响应时间(毫秒) |
| `error_message` | Text | | 错误消息 |
| **环境信息** ||||
| `ip_address` | String(45) | | 客户端IP |
| `user_agent` | Text | | 用户代理 |
| `details` | Text | | 详细信息(JSON) |
| `created_at` | DateTime | NOT NULL | 创建时间 |

---

### 6.4 安全事件表 (security_events)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 事件ID |
| `event_type` | String(50) | NOT NULL, INDEX | 事件类型 |
| `severity` | String(20) | NOT NULL | 严重级别 |
| `user_id` | String | INDEX | 用户ID |
| `ip_address` | String(45) | INDEX | IP地址 |
| `metadata` | JSON | | 事件元数据 |
| `created_at` | DateTime | NOT NULL, INDEX | 事件时间戳 |

**复合索引**:
- `ix_security_events_event_type_created_at`
- `ix_security_events_user_id_created_at`
- `ix_security_events_ip_created_at`
- `ix_security_events_severity_created_at`

**安全事件类型枚举 (SecurityEventType)**:
- `auth_failure`: 认证失败
- `auth_success`: 认证成功
- `permission_denied`: 权限拒绝
- `rate_limit_exceeded`: 超出速率限制
- `suspicious_activity`: 可疑活动
- `account_locked`: 账户锁定

**安全严重级别枚举 (SecuritySeverity)**:
- `low`: 低
- `medium`: 中
- `high`: 高
- `critical`: 严重

---

### 6.5 异步任务表 (async_tasks)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 任务ID |
| **基本信息** ||||
| `task_type` | String(50) | NOT NULL | 任务类型 |
| `status` | String(20) | NOT NULL, DEFAULT 'pending' | 任务状态 |
| `title` | String(200) | NOT NULL | 任务标题 |
| `description` | Text | | 任务描述 |
| **时间信息** ||||
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `started_at` | DateTime | | 开始时间 |
| `completed_at` | DateTime | | 完成时间 |
| **进度信息** ||||
| `progress` | Integer | DEFAULT 0 | 进度百分比 (0-100) |
| `total_items` | Integer | | 总项目数 |
| `processed_items` | Integer | DEFAULT 0 | 已处理项目数 |
| `failed_items` | Integer | DEFAULT 0 | 失败项目数 |
| **结果信息** ||||
| `result_data` | JSON | | 结果数据 |
| `error_message` | Text | | 错误信息 |
| **用户和会话** ||||
| `user_id` | String(100) | | 创建用户ID |
| `session_id` | String(100) | | 会话ID |
| **配置和参数** ||||
| `parameters` | JSON | | 任务参数 |
| `config` | JSON | | 任务配置 |
| **系统字段** ||||
| `is_active` | Boolean | DEFAULT TRUE | 是否活跃 |
| `retry_count` | Integer | DEFAULT 0 | 重试次数 |
| `max_retries` | Integer | DEFAULT 3 | 最大重试次数 |

**任务状态 (TaskStatus)**:
- `pending`: 待处理
- `running`: 运行中
- `completed`: 已完成
- `failed`: 失败
- `cancelled`: 已取消

---

### 6.6 枚举字段类型表 (enum_field_types)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 枚举类型ID |
| `name` | String(100) | NOT NULL | 枚举类型名称 |
| `code` | String(50) | UNIQUE, NOT NULL | 枚举类型编码 |
| `category` | String(50) | | 枚举类别 |
| `description` | Text | | 枚举类型描述 |
| `is_system` | Boolean | NOT NULL, DEFAULT FALSE | 是否系统内置 |
| `is_multiple` | Boolean | NOT NULL, DEFAULT FALSE | 是否支持多选 |
| `is_hierarchical` | Boolean | NOT NULL, DEFAULT FALSE | 是否层级结构 |
| `default_value` | String(100) | | 默认值 |
| `validation_rules` | JSON | | 验证规则(JSON) |
| `display_config` | JSON | | 显示配置(JSON) |
| `status` | String(20) | NOT NULL, DEFAULT 'active' | 状态 |
| `is_deleted` | Boolean | NOT NULL, DEFAULT FALSE | 是否删除 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 6.7 枚举字段值表 (enum_field_values)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 枚举值ID |
| `enum_type_id` | String | FK → enum_field_types.id, NOT NULL | 枚举类型ID |
| `label` | String(100) | NOT NULL | 显示标签 |
| `value` | String(100) | NOT NULL | 枚举值 |
| `code` | String(50) | | 枚举编码 |
| `description` | Text | | 描述 |
| **层级信息** ||||
| `parent_id` | String | FK → enum_field_values.id | 父级枚举值ID |
| `level` | Integer | DEFAULT 1 | 层级级别 |
| `path` | String(1000) | | 层级路径 |
| **显示配置** ||||
| `sort_order` | Integer | DEFAULT 0 | 排序 |
| `color` | String(20) | | 颜色标识 |
| `icon` | String(50) | | 图标 |
| `extra_properties` | JSON | | 扩展属性(JSON) |
| **状态信息** ||||
| `is_active` | Boolean | NOT NULL, DEFAULT TRUE | 是否启用 |
| `is_default` | Boolean | NOT NULL, DEFAULT FALSE | 是否默认值 |
| `is_deleted` | Boolean | NOT NULL, DEFAULT FALSE | 是否删除 |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |
| `created_by` | String(100) | | 创建人 |
| `updated_by` | String(100) | | 更新人 |

---

### 6.8 PDF导入会话表 (pdf_import_sessions)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | Integer | PK | 会话自增ID |
| `session_id` | String(100) | UNIQUE, NOT NULL, INDEX | 会话标识 |
| **文件信息** ||||
| `original_filename` | String(500) | NOT NULL | 原始文件名 |
| `file_size` | Integer | NOT NULL | 文件大小 |
| `file_path` | String(1000) | | 文件存储路径 |
| `content_type` | String(100) | DEFAULT 'application/pdf' | 文件类型 |
| **状态信息** ||||
| `status` | Enum | NOT NULL, DEFAULT 'uploading' | 会话状态 |
| `current_step` | Enum | | 当前处理步骤 |
| `progress_percentage` | Float | DEFAULT 0.0 | 进度百分比 |
| `error_message` | Text | | 错误信息 |
| **处理结果** ||||
| `extracted_text` | Text | | 原始提取的文本 |
| `extracted_data` | JSON | | 提取的结构化数据 |
| `processing_result` | JSON | | 完整处理结果 |
| `validation_results` | JSON | | 验证结果 |
| `matching_results` | JSON | | 匹配结果 |
| `confidence_score` | Float | DEFAULT 0.0 | 整体置信度 |
| **处理配置** ||||
| `processing_method` | String(50) | | 处理方法 |
| `ocr_used` | Boolean | DEFAULT FALSE | OCR使用（已弃用）|
| `processing_options` | JSON | | 用户选择的处理选项 |
| **时间戳** ||||
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |
| `completed_at` | DateTime | | 完成时间 |
| **用户信息** ||||
| `user_id` | Integer | | 处理用户ID |
| `organization_id` | Integer | | 组织ID |

**会话状态枚举 (SessionStatus)**:
- `uploading`: 文件上传中
- `uploaded`: 文件上传完成
- `processing`: PDF处理中
- `text_extracted`: 文本提取完成
- `info_extracted`: 信息提取完成
- `validating`: 数据验证中
- `matching`: 数据匹配中
- `ready_for_review`: 待用户确认
- `completed`: 处理完成
- `failed`: 处理失败
- `cancelled`: 用户取消
- `confirmed`: 用户确认导入

---

### 6.9 Prompt模板表 (prompt_templates)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | String | PK | 模板ID |
| `name` | String(100) | UNIQUE, NOT NULL | Prompt名称 |
| `doc_type` | String(50) | NOT NULL, INDEX | 文档类型 |
| `provider` | String(50) | NOT NULL, INDEX | LLM提供商 |
| `description` | String(500) | | Prompt描述 |
| **Prompt内容** ||||
| `system_prompt` | Text | NOT NULL | 系统提示词 |
| `user_prompt_template` | Text | NOT NULL | 用户提示词模板 |
| `few_shot_examples` | JSON | | Few-shot示例 |
| **元数据** ||||
| `version` | String(20) | NOT NULL | 版本号 |
| `status` | String(20) | DEFAULT 'draft' | 状态 |
| `tags` | JSON | | 标签列表 |
| **性能指标** ||||
| `avg_accuracy` | Float | DEFAULT 0.0 | 平均准确率 |
| `avg_confidence` | Float | DEFAULT 0.0 | 平均置信度 |
| `total_usage` | Integer | DEFAULT 0 | 总使用次数 |
| **关系** ||||
| `current_version_id` | String | FK → prompt_versions.id | 当前版本ID |
| `parent_id` | String | FK → prompt_templates.id | 父模板ID |
| **审计字段** ||||
| `created_at` | DateTime | | 创建时间 |
| `updated_at` | DateTime | | 更新时间 |
| `created_by` | String(100) | | 创建人ID |

---

## 7. 关联表

### 7.1 角色权限关联表 (role_permissions)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `role_id` | String | PK, FK → roles.id | 角色ID |
| `permission_id` | String | PK, FK → permissions.id | 权限ID |
| `created_at` | DateTime | | 创建时间 |
| `created_by` | String(100) | | 创建人 |

---

### 7.2 合同-资产关联表 (rent_contract_assets)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `contract_id` | String | PK, FK → rent_contracts.id | 合同ID |
| `asset_id` | String | PK, FK → assets.id | 资产ID |
| `created_at` | DateTime | | 关联创建时间 |

---

### 7.3 产权证-权利人关联表 (property_certificate_owners)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `certificate_id` | String | PK, FK → property_certificates.id | 产权证ID |
| `owner_id` | String | PK, FK → property_owners.id | 权利人ID |
| `ownership_share` | Numeric(5,2) | | 拥有权比例（百分比）|
| `owner_category` | String(50) | | 权利人类别 |

---

### 7.4 产权证-资产关联表 (property_cert_assets)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `certificate_id` | String | PK, FK → property_certificates.id | 产权证ID |
| `asset_id` | String | PK, FK → assets.id | 资产ID |
| `link_type` | String(50) | | 关联类型 |
| `notes` | String(500) | | 关联备注 |

---

## 8. ER图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              核心业务关系                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌──────────────┐    N:N    ┌─────────────────────┐    N:N    ┌─────────────────┐  │
│   │   Projects   │◄─────────►│ProjectOwnershipRel  │◄─────────►│   Ownerships    │  │
│   └──────┬───────┘           └─────────────────────┘           └────────┬────────┘  │
│          │1:N                                                           │1:N        │
│          ▼                                                              ▼           │
│   ┌──────────────┐    N:N    ┌─────────────────────┐           ┌─────────────────┐  │
│   │    Assets    │◄─────────►│ rent_contract_assets│◄─────────►│  RentContracts  │  │
│   └──────┬───────┘           └─────────────────────┘           └────────┬────────┘  │
│          │1:N                                                           │1:N        │
│          ├─────────────────┐                                   ┌────────┼───────────┤
│          ▼                 ▼                                   ▼        ▼           │
│   ┌──────────────┐  ┌──────────────┐                   ┌────────────┐ ┌───────────┐ │
│   │ AssetHistory │  │AssetDocuments│                   │ RentTerms  │ │RentLedger │ │
│   └──────────────┘  └──────────────┘                   └────────────┘ └───────────┘ │
│                                                                                     │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                         产权证关系                                            │  │
│   │  ┌──────────────┐  N:N  ┌──────────────────────┐  N:N  ┌─────────────────┐   │  │
│   │  │PropertyCerts │◄─────►│property_cert_owners  │◄─────►│ PropertyOwners  │   │  │
│   │  └──────┬───────┘       └──────────────────────┘       └─────────────────┘   │  │
│   │         │N:N                                                                  │  │
│   │         └─────────►property_cert_assets◄───────────────Assets                │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              用户权限关系                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌──────────────┐    N:N    ┌─────────────────────┐    N:N    ┌─────────────────┐  │
│   │    Users     │◄─────────►│ UserRoleAssignments │◄─────────►│     Roles       │  │
│   └──────┬───────┘           └─────────────────────┘           └────────┬────────┘  │
│          │1:N                                                           │N:N        │
│          ├─────────────────┬─────────────────┐                         ▼           │
│          ▼                 ▼                 ▼               ┌─────────────────┐   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │  Permissions    │   │
│   │ UserSessions │  │  AuditLogs   │  │Notifications │       └─────────────────┘   │
│   └──────────────┘  └──────────────┘  └──────────────┘                              │
│                                                                                     │
│   ┌──────────────────────────────────────────────────────────────────────────────┐  │
│   │                      动态权限扩展                                             │  │
│   │  DynamicPermissions ◄───► TemporaryPermissions ◄───► ConditionalPermissions  │  │
│   │  PermissionTemplates ◄───► PermissionRequests ◄───► PermissionDelegations    │  │
│   └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              组织架构关系                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌──────────────┐                                                                  │
│   │ Organizations│◄─────────(self-reference: parent_id)                            │
│   └──────┬───────┘                                                                  │
│          │1:N                                                                       │
│          ├─────────────────┐                                                        │
│          ▼                 ▼                                                        │
│   ┌──────────────┐  ┌──────────────┐                                                │
│   │  Positions   │  │  Employees   │◄─────────(self-reference: direct_supervisor)  │
│   └──────┬───────┘  └──────────────┘                                                │
│          │1:N              ▲                                                        │
│          └─────────────────┘                                                        │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 附录：表统计

| 模块 | 表名 | 中文名称 |
|------|------|----------|
| **核心业务** | assets | 资产表 |
| | asset_history | 资产变更历史表 |
| | asset_documents | 资产文档表 |
| | projects | 项目表 |
| | ownerships | 权属方表 |
| | project_ownership_relations | 项目-权属方关系表 |
| | property_certificates | 产权证表 |
| | property_owners | 权利人表 |
| | system_dictionaries | 系统数据字典表 |
| | asset_custom_fields | 资产自定义字段表 |
| **用户权限** | users | 用户表 |
| | user_sessions | 用户会话表 |
| | audit_logs | 审计日志表 |
| | roles | 角色表 |
| | permissions | 权限表 |
| | role_permissions | 角色权限关联表 |
| | user_role_assignments | 用户角色分配表 |
| | resource_permissions | 资源权限表 |
| | permission_grants | 统一授权表 |
| | permission_audit_logs | 权限审计日志表 |
| **合同财务** | rent_contracts | 租金合同表 |
| | rent_terms | 租金条款表 |
| | rent_ledger | 租金台账表 |
| | rent_deposit_ledger | 押金台账表 |
| | service_fee_ledger | 服务费台账表 |
| | rent_contract_history | 合同历史记录表 |
| | rent_contract_attachments | 合同附件表 |
| | rent_contract_assets | 合同-资产关联表 |
| | collection_records | 催缴记录表 |
| **组织架构** | organizations | 组织表 |
| | positions | 职位表 |
| | employees | 员工表 |
| | organization_history | 组织变更历史表 |
| **系统支撑** | contacts | 联系人表 |
| | notifications | 通知表 |
| | operation_logs | 操作日志表 |
| | security_events | 安全事件表 |
| | async_tasks | 异步任务表 |
| | task_history | 任务历史表 |
| | excel_task_configs | Excel任务配置表 |
| | enum_field_types | 枚举字段类型表 |
| | enum_field_values | 枚举字段值表 |
| | enum_field_usage | 枚举字段使用表 |
| | enum_field_history | 枚举字段历史表 |
| | pdf_import_sessions | PDF导入会话表 |
| | pdf_import_session_logs | 会话操作日志表 |
| | pdf_import_configurations | 处理配置表 |
| | prompt_templates | Prompt模板表 |
| | prompt_versions | Prompt版本表 |
| | extraction_feedback | 提取反馈表 |
| | prompt_metrics | Prompt性能指标表 |

---

**文档结束**
