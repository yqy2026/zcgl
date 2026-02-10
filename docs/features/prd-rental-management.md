# 租赁管理 PRD

> ⚠️ **状态变更（2026-02-09）**  
> 本文档已降级为历史草稿，不再作为需求权威来源。  
> 当前权威规格请使用：`docs/requirements-specification.md`  
> 模块证据附录请使用：`docs/features/requirements-appendix-modules.md`

## ✅ Status
**当前状态**: Historical Draft (2026-02-09)

## 背景与目标
覆盖租赁合同的全流程管理，提升合同录入、变更与统计效率。

## 目标范围
- 合同信息维护与归档
- 租金台账与收款记录
- 合同到期提醒与状态管理

## 非目标
- 财务核算系统
- 复杂的税务或发票系统

## 关键需求
- 合同字段完整与校验
- 变更历史可追溯
- 与资产/权属方关联

## 验收标准
- 合同 CRUD 可用
- 合同状态流转符合预期
- 统计指标可用

## 参考
- `backend/src/api/v1/rent_contracts/`
- [数据库设计](../database-design.md)
