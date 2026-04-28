# ADR-0001: Party-Role 组织架构模型

**状态**: ✅ 已实施（Phase 1–3 完成，2026-02-20）  
**决策日期**: 2026-02-16  
**实施日期**: 2026-02-16 ~ 2026-02-20  
**方案原文**: [`archive/backend-plans/2026-02-16-party-role-architecture-design.md`](../archive/backend-plans/2026-02-16-party-role-architecture-design.md)

---

## 背景

系统原始数据模型中，租客、业主、管理方等业务主体以分散字段（`tenant_name`、`owner_name`、`management_entity` 等）存储在各业务表中，导致：

- 同一主体在资产、合同、项目中以不同字段名存储，无法跨表关联
- 权限模型（RBAC）缺乏数据隔离能力，所有用户可见全量资产
- 组织层级（子公司、部门）无标准存储结构

## 决策

引入 **Party-Role 双层模型**，将"主体"与"角色关系"解耦：

### 核心表结构

| 表 | 用途 |
|----|------|
| `parties` | 统一主体注册表（企业/个人/部门） |
| `party_hierarchy` | 主体层级关系（树状结构） |
| `party_contacts` | 主体联系人 |
| `party_role_defs` | 角色类型定义（租客/业主/管理方等） |
| `party_role_bindings` | 主体在具体业务对象上的角色绑定 |
| `user_party_bindings` | 用户与主体的归属关系 |

### 权限模型

采用 **RBAC + ABAC 混合模型**：
- RBAC：管理员配置入口（角色 → 权限），禁止直接对用户/主体绑定数据策略
- ABAC：运行时数据访问决策，条件引擎使用 **JSONLogic**（`python-jsonlogic>=0.1.0`）

### 业务表改造

全域 22 张表由原散字段迁移为 `party_id` FK，包括：资产、合同、项目、产权证、台账、RBAC 角色表。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 保留原散字段 + 增加联查视图 | 无法解决数据隔离问题，技术债继续累积 |
| 分阶段兼容迁移（双写） | 系统处于 0→1 阶段，兼容代价大于收益 |
| 纯 RBAC 无 ABAC | 无法实现行级数据隔离（不同机构只能看自己的资产） |

## 关键冻结决策

1. **迁移模式**：一次切换，不做双写兼容
2. **ID 策略**：统一 `String` 类型（`Python uuid4()` 生成），不引入 `UUID` 类型迁移
3. **ABAC 策略主体**：本期删除 `abac_policy_subjects` 表，不保留
4. **管理员配置**：仅通过角色入口配置，禁止直接对用户绑定数据策略
5. **发布门禁**：数据正确性优先，迁移未通过不发布

## 结果

- Phase 1（DDL + ORM + ABAC 骨架）✅ 2026-02-18 完成
- Phase 2（业务域迁移 + 数据隔离）✅ 2026-02-19 完成  
- Phase 3（前端全量迁移 + 策略包 UI）✅ 2026-02-20 完成

## 影响

- `backend/src/models/` 新增 `party.py`、`abac.py`、`user_party_binding.py`
- 所有业务 CRUD 通过 `party_id` 关联，原 `*_name` 冗余字段下线
- 前端组织架构页面切换至 Party-Role API
