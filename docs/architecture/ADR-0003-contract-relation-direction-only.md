# ADR-0003: 合同上下游退化为方向标记，删除逐对配对与覆盖风险

**状态**: 🟡 已决策，待实施（2026-06-10）
**决策日期**: 2026-06-10
**实施日期**: 待定
**相关需求**: REQ-RNT-004（移除）、REQ-RNT-001 / REQ-RNT-006（口径调整）

---

## 背景

合同上下游关系原本由两套东西共同表达：

1. **`Contract.group_relation_type`**（上游/下游/委托/直租）——每份合同自带的方向标记。
2. **`ContractRelation`**（domain-model §4.11）——`parent_contract_id ↔ child_contract_id` 的**逐对配对表**，记录"哪份下游具体对应哪份上游"。

围绕配对，又派生出 REQ-RNT-004「主合同覆盖风险提示」：终端合同若在资产范围/期间上没被同组主合同盖全，生成 `missing_primary_contract` / `coverage_conflict` 风险。

代码审查发现：

- 收入/成本（`analytics_service.py:371-453`）和服务费台账（`service_fee_ledger_service.py`）**全靠 `group_relation_type` 计算，完全不碰 `ContractRelation` 配对**。
- 配对的唯一消费者是投影显示的 `upstream/downstream_contract_ids` 列表（`contract_group_service.py:872`）和覆盖风险——而这个列表可直接按 `group_relation_type` 派生。
- 配对唯一不可替代的能力是"逐对精确匹配"，只服务于逐租约毛利/分润和逐对覆盖。
- 残留 `ContractRelationType.RENEWAL`（续签关系）与 PRD「MVP 不提供续签」直接冲突。

业务判断（yellowUp）：**上下游只是为了方便管理和计算收入/成本，不要做这么多限制。覆盖不覆盖不重要。**

## 决策

1. **删除主合同覆盖风险**（REQ-RNT-004）：终端合同是否被主合同盖全，不计算、不提示、不阻断。`ProjectRisk.risk_type` 移除 `missing_primary_contract` 和 `coverage_conflict`。
2. **删除 `ContractRelation` 逐对配对表**：上下游只由每份合同的 `group_relation_type` 表达方向。
3. **投影派生改口径**：`primary_contract_ids` / `terminal_contract_ids` 按组内 `group_relation_type` 派生（上游/委托 → primary，下游/直租 → terminal），不再逐条配对。
4. **删除 `ContractRelationType.RENEWAL`**：随配对表一并移除，对齐"MVP 不提供续签"。
5. **盈亏沿归属链汇总，不靠配对**：上游成本与下游收益的关联不是合同对合同，而是因为共享同一批资产/项目。沿 合同 → 资产 → 项目 归属链汇总——上游/委托台账落成本，下游/直租台账落收益，在共享资产/项目处相减即盈亏。
6. **"当前成本/当前收益"只放项目级（及合同关系级），不放资产级**：资产级会被迫分摊多资产合同的合同级金额，违反 domain-model §6「不按资产分摊」。资产详情只列关联合同清单及各自金额，不拆分。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 保留覆盖风险 + 配对表 | 唯一能力（逐对匹配）服务的需求（覆盖、逐租约毛利）MVP 不做；补录时手填配对是纯增摩擦 |
| 保留配对表作惰性显示关联 | 当前几乎无消费者，仍要承担录入与维护负担，收益≈0 |
| 保留并升级为分润一等公民 | 与"上下游不重要、不做逐租约毛利"的业务判断冲突；`revenue_share_rule` 本就标注"MVP 只结构化留存" |

## 关键冻结决策

1. **收入/成本/服务费口径不变**：全部基于 `group_relation_type`，本次删除不影响任何统计口径。
2. **上下游不再有"配对"概念**：MVP 不存在"哪份下游对哪份上游"。
3. **逐租约毛利/分润归 vNext**：若将来需要，重建配对表。

## 影响

待实施的工程项：

- **PRD**：删 REQ-RNT-004；REQ-RNT-001 措辞去掉覆盖相关；§6.3 上下游说明改为纯方向标记。
- **domain-model.md**：删 §4.11 `ContractRelation`；§4.5.1 `ProjectRisk.risk_type` 去掉两个覆盖风险类型；§4.4 投影 `primary/terminal_contract_ids` 改派生口径；§4.3 `risk_tags` 说明去掉"缺少有效上游/委托覆盖"。
- **后端**：删 `ContractRelation` 模型 / CRUD / schema / `ContractRelationType.RENEWAL`；投影上下游列表改按 `group_relation_type` 派生；删覆盖风险计算；清理克隆路径（`contract_group_service.py:705`）对配对的写入。
- **数据库**：删 `contract_relations` 表迁移。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`合同上下游（收入/成本标记）` 词条
- 相关簇：[ADR-0002](./ADR-0002-asset-review-no-approval-workflow.md)（同期 MVP 减法）
