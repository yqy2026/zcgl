# ADR-0012: 合同关系锁单项目——代理合同跨项目靠共享盖章扫描件，不靠跨项目合同关系

**状态**: ✅ 已实施（2026-06-19 已落 C5/C6；2026-06-20 已落 C7/I9 合同号复合唯一与共享扫描件）
**决策日期**: 2026-06-16（2026-06-18 修订）
**相关需求**: REQ-RNT-001（合同关系作为用户可见业务对象）、REQ-RNT-002（承租/代理并行）、PRD §6.2 经营模式、§6.3 合同关系分类、ADR-0011（台账固化归属）

---

## 背景

`ContractGroup.project_id`（domain-model §4.3）条件必填、「一条合同关系必须归属一个项目」（REQ-RNT-001）；`Contract.contract_group_id`（§4.7）单个必填、「合同通过所属 `ContractGroup.project_id` 归属项目」。即模型的硬基数是：**一份合同 → 一个合同关系 → 一个项目**。

但现实里（2026-06-16 决策访谈）：**代理模式的委托协议可覆盖多个项目**（产权方↔运营方；承租模式没有、承租合同关系天然项目内，且**直租/上游/下游也恒单项目**——2026-06-19 grill 把原「一份代理合同」泛指收窄为委托协议，避免实施时把直租也做成跨项目；客户双指标只数直租/下游 lessee 合同、二者恒单项目，故「按合同 ID 去重」不会把跨项目兄弟记录算重）。这与单项目基数冲突，必须落地一种表达方式。同时 ADR-0011 已确立台账固化归属、§6.3 盈亏沿「合同→资产→项目」归属链汇总——这两条都要求每条台账能钉到**唯一**项目，不能让合同关系跨项目把固化项目变歧义。

## 决策

**跨项目的是「那张盖章合同」，不是「合同关系」，更不是「台账条目」：**

1. **合同关系（`ContractGroup`）恒锁单项目**：承租、代理一律一个合同关系只属一个项目，其覆盖资产同属该项目；service 层校验，违规拒绝。`ContractGroup` / `Contract` 的单项目基数不破。
2. **委托协议跨多项目 = 物理盖章扫描件层共享**（跨项目的只是委托协议，直租/上游/下游恒单项目）：同一份委托协议盖章扫描件**只上传一次**，在它覆盖的每个项目下各建一条合同关系/合同记录，**共享引用同一份扫描件**，不创建一个跨项目的合同关系，也不把一条 `Contract` 挂到多个合同组。
3. **钱不跨项目**：每条直租租金/服务费台账落唯一项目（按条目自身资产/直租解析，见 ADR-0011），服务费计入该项目应收（domain-model §4.5 `service_fee_receivable`）。
4. **补录低摩擦由「扫描件共享」兜，建模摩擦正当**：合同关系是建模动作、不要求零摩擦（CONTEXT「合同关系（建模对象）」）；一份代理合同在 N 个项目各建一条关系是如实表达「这份合同在 N 个项目分别承载 N 笔经营关系」，扫描件不重传。
5. **资产-关系-项目一致性硬校验**（两条不变量，service 层）：
   - **`Contract.asset_ids ⊆ ContractGroup.asset_ids`**：一份合同覆盖资产不得超出其所属合同关系范围；留空表示「覆盖本关系全部资产（整租）」，是低摩擦默认（台账固化时回退到组 `asset_ids`，见 ADR-0011）。
   - **合同组覆盖资产同属该组项目**：`ContractGroup.asset_ids` 每个资产的当前项目（active `project_assets.valid_to IS NULL` 绑定）必须等于 `ContractGroup.project_id`。2026-06-19 已在 service 层补齐：创建/编辑合同关系先校验资产当前项目，再校验既有组间冲突；否则资产可绑到与自身当前项目不符的合同组，台账固化项目（ADR-0011）与 §6.3 归属链失真。
6. **合同号按项目复合唯一（2026-06-18 grill 补）**：现状 `contracts.contract_number` 为**全局唯一**（`contract_group.py:224-226` `unique=True`），与决策点 2「一份代理合同在 N 个项目各建一条合同记录（同号）」**直接冲突**——同号第二条起被 DB 拒绝，机制落不了地。改为 **`UNIQUE(contract_number, project_id)` 复合唯一**（经 `contract_group` 落项目），并用 `data_status <> '正常' OR project_id IS NOT NULL` 持续约束正常合同必须落项目，保住「同一份合同同一个号」语义，N 条记录靠 project 区分。配套三条：
   - **共享扫描件落一份文档行**：N 条记录引用同一份扫描件文档（文件只存一份，不复制）；扫描件是共享事实底座，**替换即对同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟记录生效**（本就是同一份委托协议），且写入前逐条校验受影响合同 `contract:update` 权限；若复用既有 `storage_key` 时发现该文档已链接到本次受影响集合外的合同，必须失败暴露，不得改写范围外合同可见的扫描件元数据；删除受「每合同 ≥1 盖章扫描件」保护。
   - **更正按记录独立**：REQ-RNT-005 更正只重算该项目台账，不联动兄弟记录（各项目是该合同的不同切片，independent 是正当建模摩擦，对齐决策点 4）。
   - **不建显式「逻辑合同」聚合**：MVP 兄弟集靠 `contract_number` 相同 + 共享扫描件引用发现即可，不新增跨项目聚合对象（减法）。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| (B) `Contract` 改多对多挂多合同组 / `ContractGroup` 代理模式跨项目 | 破单项目不变量；台账固化项目（ADR-0011）、§6.3 归属链、按项目分区统计全得重做，把刚关掉的歧义重新打开——为代理这个边角破核心不变量 |
| 承租模式也允许合同关系跨项目 | 无业务依据，承租合同关系天然在一个项目内 |
| 强行把代理合同当成一条记录、项目归属留空 | 台账无法按项目归集服务费，违反 §4.5 服务费计入项目应收、§6.3 归属链 |

## 关键冻结决策

1. **合同关系单项目是承租/代理共同的硬不变量。**
2. **代理合同跨项目只在盖章扫描件层共享，不上升到合同关系或台账。**
3. **每条台账落唯一项目**，与 ADR-0011 固化归属一致。
4. **合同号按项目复合唯一**（`UNIQUE(contract_number, project_id)`），正常合同必须有 `project_id`；N 条同号记录靠 project 区分；替换共享扫描件只联动同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟记录，更正按记录独立。

## 影响

工程项状态：

- **后端（C5/C6 已实施，2026-06-19）**：合同关系创建/编辑已校验「覆盖资产同属本关系当前项目」（按 active `project_assets` 当前绑定）；新增合同入组已校验 `Contract.asset_ids ⊆ ContractGroup.asset_ids`，编辑合同关系资产范围时也会校验不得小于已有合同显式覆盖资产，留空=整租继续跳过新增合同子集校验。证据：`backend/src/crud/contract_group.py`、`backend/src/services/contract/contract_group_service.py`、`backend/tests/unit/services/contract/test_contract_group_service.py`。
- **后端（C7/I9 已实施，2026-06-20）**：`contracts.contract_number` 去全局 `unique=True`，新增 `Contract.project_id` 并改 `UNIQUE(contract_number, project_id)`（Alembic 迁移含存量项目回填、正常合同缺项目 fail-loud、持续 check constraint 与同项目重号冲突检测）；共享扫描件文档单存、多 `Contract` 引用同一文档行，替换/删除只联动同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟记录，写入前逐条鉴权，复用既有 `storage_key` 时拒绝范围外链接，删除按「每合同 ≥1 扫描件」保护；更正流程复制来源扫描件但保持按记录独立，不联动兄弟记录台账。证据：`backend/src/models/contract_group.py`、`backend/src/crud/contract.py`、`backend/src/services/contract/contract_group_service.py`、`backend/src/api/v1/contracts/contract_groups.py`、`backend/alembic/versions/20260620_contract_number_project_scan_documents.py`。
- **domain-model**：§4.3 ContractGroup `project_id` 标注「单项目硬不变量，覆盖资产同属该项目」；§4.7 Contract 注明「盖章扫描件可被多项目下合同记录共享引用」（本次随手落）。
- **PRD**：§6.2 / §6.3 / REQ-RNT-001 明文「合同关系锁单项目；代理合同跨项目靠共享扫描件」（本次随手落）。
- **CONTEXT.md**：增「合同关系锁单项目（代理合同跨项目靠共享扫描件）」词条（本次随手落）。
- **traceability**：REQ-RNT-001 已补 C7/I9 实现证据；REQ-RNT-002 继续由单项目合同关系与经营模式拆分口径承载。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `CONTEXT.md`：`合同关系锁单项目（代理合同跨项目靠共享扫描件）`、`合同关系（建模对象）`、`合同补录` 词条
- domain-model §4.3 ContractGroup、§4.7 Contract、§4.5 ProjectAnalytics
- 相关簇：[ADR-0011](./ADR-0011-ledger-frozen-attribution.md)（台账固化归属——本 ADR 保证固化项目唯一）、[ADR-0003](./ADR-0003-contract-relation-direction-only.md)（上下游只做方向标记）
