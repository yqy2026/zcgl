# ADR-0015: 通知幂等按优先级档位——不按未读、不按天

**状态**: 🟡 已决策，待实施（2026-06-18）
**决策日期**: 2026-06-18
**相关需求**: REQ-NTF-001（通知域）、PRD §7.10；口径依赖 ADR-0007（逾期派生口径）

---

## 背景

PRD §7.10 REQ-NTF-001 原只写一条幂等规则：「同一接收人对同一对象的同类**未读**通知不重复生成（幂等）」。

代码核对（2026-06-18，`services/notification/scheduler.py`）发现实际跑了**两套互不一致、且都与 PRD 矛盾**的去重策略：

| 扫描 | 实际去重键 | 行为 |
|------|-----------|------|
| `check_contract_expiry`（合同到期） | `require_unread=True` | 有未读就不再发（符合 PRD 字面） |
| `check_payment_overdue`（付款逾期） | `created_since=today` | **按天去重**，与已读/未读无关 |
| `check_payment_due_soon`（付款到期） | `created_since=today` | 同上，按天去重 |

两套都不对：

1. **逾期日刷屏**：`created_since=today` 让同一条逾期台账对同一用户**每天扫一次重发一次**，无视已读——一条欠款 = 每天唠叨，撞 CONTEXT「消息通知（提醒非工单）」的「提醒不是工单」边界，与已删的催缴工单（ADR-0006）同病。
2. **升级档位塌缩**：`check_contract_expiry` 算了 30 天 NORMAL → 15 天 HIGH → 7 天 URGENT 的升级，但都是同一个 `CONTRACT_EXPIRING` 类型。在纯未读幂等下，只要用户晾着首条 30 天 NORMAL 不读，**最要命的 7 天 URGENT 升级永远发不出来**。
3. **PRD 字面（纯未读）本身也不够**：逾期是最需要持续提醒的一类，看一眼就再也不提，容易被遗忘。

即：现状「该停的停不下来（逾期日刷屏），该升的升不上去（到期不升级）」，两头别扭。

## 决策

**通知幂等统一为「按优先级档位」去重：**

1. **幂等键 =（接收人, 对象, 类型, 优先级档位）**。同档位不重复生成；跨档位升级各生成一次。
2. **档位由数据实时派生、不存标记位**（口径同 ADR-0007 逾期派生）：
   - 逾期：按 `days_overdue` 派生 `NORMAL → HIGH(≥7天) → URGENT(≥30天)`。
   - 合同到期 / 付款到期：按剩余天数派生 `30 → 15 → 7 天` 档位。
3. **效果**：每个对象整个生命周期最多 ~3 条递进提醒——不按天刷屏、不因首条未读而漏发后续升级。
4. 工程落点：`find_existing_notification_pairs_async` 调用改用档位键，去掉 `check_payment_overdue`/`check_payment_due_soon` 的 `created_since=today`，去掉 `check_contract_expiry` 的纯 `require_unread=True`。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 纯未读幂等（PRD 字面） | 逾期看一眼就再不提醒、易遗忘；且到期升级档位静默塌缩。若选它须连带删掉每日重发与升级档位代码（否则是死代码） |
| 按天重发（现状逾期实现） | 一条逾期天天刷屏，工单式催办，撞「提醒非工单」 |
| 固定每周一次 | 与急迫程度脱钩——快到期了还按周慢提醒，逾期早期又偏勤；档位升级更贴「越拖越急」的真实诉求 |
| 存「已提醒档位」标记位 | 重蹈 `is_verified`（ADR-0005）、手工 `overdue`（ADR-0007）覆辙；档位可由 `days_overdue`/`days_remaining` 实时派生，无须落标记位 |

## 关键冻结决策

1. **幂等按档位，不按未读、不按天**。
2. **档位实时派生，不存标记位**（与 ADR-0007 同口径）。
3. **每对象生命周期最多 ~3 条递进提醒**，跨档位升级才再发。

## 影响

待实施的工程项：

- **后端**：`scheduler.py` 三个扫描统一改档位幂等键；`find_existing_notification_pairs_async` 支持按档位过滤；补单测（同档位不重发、跨档位各发一次、逾期不日刷屏、到期升级不塌缩）。
- **PRD**：REQ-NTF-001 幂等措辞改「按优先级档位」（本次随手落）。
- **CONTEXT.md**：「消息通知（提醒非工单）」词条补档位幂等（本次随手落）。
- **traceability**：REQ-NTF-001 记代码收口缺口。
- **CHANGELOG.md**：记录本次变更（本次随手落）。

## 参考

- `CONTEXT.md`：`消息通知（提醒非工单）`、`逾期（派生口径）` 词条
- `services/notification/scheduler.py`（`check_contract_expiry`/`check_payment_overdue`/`check_payment_due_soon`）
- 相关簇：[ADR-0007](./ADR-0007-overdue-derived-not-marked.md)（逾期派生不标记——同「派生而非标记位」方向）、[ADR-0016](./ADR-0016-wecom-per-user-push.md)（企业微信按人推送，同通知域）
