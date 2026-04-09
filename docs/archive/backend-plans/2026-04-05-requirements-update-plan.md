# 2026-04-05 业务规格更新（资产拦截、模式解绑与实收报表）实施计划

## 状态标签
- 状态：✅ 已完成（已吸收至 2026-04-07 三维正交重构蓝图并执行完毕）
- 关联文档：`docs/requirements-specification.md`

## 1. 背景与目标
基于 2026-04-05 的规格对齐与验证：
1. **统一强化主数据审批门禁 (REQ-AST-003)**：资产入驻从发起时的软警告，变为禁止录入草稿及退回态数据的“硬阻断”。
2. **~~放宽单一模式绑定约束 (REQ-RNT-002)~~ [已撤销]**：经业务侧确认（不存在不同模式资产拼铺的极端情况），原有后端的单模式强制互斥是正确的财务防线依据，因此**取消所谓的“模式解绑与资产混编”需求**，维持强校验。
3. **补充实收与收缴率分析 (REQ-ANA-001)**：原先仅能看应收等，现在需要加看“当期实收”、“租金收缴率”来对齐实际的经营视角，同时大屏需强调模式边界（隔离查看）。

*(注：有关“无痕直纠”的方案已经按财务要求核销与重建准则被取消，不再进入本研发阶段。)*

---

## 2. User Review Required (注意事项)

> [!CAUTION]
> 根据 4 月 6 日与业务的最终确认，现实中**不存在**承租与代理资产“混合拼铺”给同一租户的跨域合并用例。
> 因此，之前有关“拆除 `_VALID_RELATION_TYPES` 静默检测防线以放开资产混录”的设计是一个**伪需求导致的致命错误**。
> 本次实施将**坚决保留核心服务层（`contract_group_service.py`）对 `revenue_mode` 和资产同源的单模式强校验**，捍卫财务和计费台账的纯洁性。

---

## 3. 实施步骤（Proposed Changes）

### P1：后端服务网强化与解绑 (Backend Core)
**目标文件**：`backend/src/services/contract/contract_group_service.py` & `backend/src/api/v1/contracts/contract_groups.py`

*   **[MODIFY] 资产审核准入硬拦截**：
    *   取消提审/建组时刻对未审核主数据注入 `X-Asset-Review-Warnings` 的妥协做法。
    *   增加校验：当任何被引用资产或主体非 `APPROVED` 态时，抛出阻断性错误（如 `BusinessRuleError`）。
*   **~~[MODIFY] 解除经营模式校验锁~~ [任务取消]**：
    *   **业务澄清完成**：不再移除 `_VALID_RELATION_TYPES`。
    *   **维持原状**：保留 `validate_revenue_mode_compatibility` 以及相关的一致性安全防线，保证合同组在财务统计上干净唯一的单模态。

### P2：后端分析引擎升级 (Analytics Data Engine)
**目标文件**：`backend/src/services/analytics/analytics_service.py` 及对应的 Schema

*   **[MODIFY] 分析数据组装查询**：
    *   修改报表分析 SQL/查询语句或组装器，使其能够在抽取 `expected_revenue` 的同时联接并汇总对应的 `actual_receipts`（当期实收额）。
    *   扩展 `AssetAnalyticsMetrics` / 对应 Schema：增加 `actual_receipts` 及基于两者计算而成的 `collection_rate` (收缴率) 字段，供前端取用。

### P3：前端大屏与防线对齐 (Frontend Dashboard)
**目标文件**：`frontend/src/pages/analytics/Dashboard.tsx` 等

*   **[MODIFY] 指标扩充展示**：
    *   调整头部横向统计卡片，增设“本期实收总计”，并在合适位置（如图表 Hover Tooltip 或主数字旁）配搭展示“收缴率”。
*   **[MODIFY] 严格分界展示**：
    *   使用 Tab/Segment 切片确保大屏只默认单示一个主模块数据（资管代理口径 / 资产自营口径），规避“全部”维度带来的财务混淆。

---

## 4. 测试与验证计划 (Verification Plan)

### 4.1 Automated Tests (单元用例调整)
1. **增加（防线补全）**：增写专门测试 —— 在组建和提交 `ContractGroup` 时夹带一个处于 `DRAFT` 或 `REJECTED` 态的 `Asset` 或 `Party`，断言是否会被系统判定为 HTTP 400 失败。
2. **测试防线验证（维持红线）**：确保 `tests/unit/services/contract/` 里对“不配对 `RevenueMode` 和 试图混编不同来源资产”依然会毫不留情地抛出 400 拦截报错。

### 4.2 Manual Verification (全景演习)
1. **强行提交违规资产**：后端本地起服后，调用创建合并组 API 并包含自捏的未通过审核记录，预期响应头被剥离，而直截了当得到体面错误：阻断操作。
2. **数据面板巡检**：进入前端面板，核对实收金额、应收金额的数字差以及收缴率的呈现形态。并确认无论当前用户拥有何等交集的跨模块系统权限，分析看版均只认当前业务模式子切片。
