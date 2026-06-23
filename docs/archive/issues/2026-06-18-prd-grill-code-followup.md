# 2026-06-18 PRD Grill 代码收口跟踪

`/grill-with-docs docs/prd.md`（2026-06-18）产出的代码层实施与验证项。文档基线（PRD / domain-model / CONTEXT / ADR-0015~0018 + ADR-0011/0012 修订 / api-contract / trace / CHANGELOG）已对齐，本记录跟踪**代码改造**进度（逐项进度以 git commit 追溯）。

详细文件:行证据、改造点与验收见实施详单：[`docs/plans/2026-06-18-prd-grill-code-followup.md`](../plans/2026-06-18-prd-grill-code-followup.md)。

本轮主题是「**PRD↔代码缺口补齐 + 契约对齐**」：grill 抓到一批文档吹了但代码没有/反着来的点——通知幂等与外泄、编码空头声明、产权证保存门槛指错、导入可建无主资产、合同号约束与跨项目机制冲突——逐项补齐。竖切为可独立认领的 tracer bullet；AFK 代码项已收口，I2② 的应用消息代码已接入，剩余真实发送验证受企业微信可信 IP / 域名前置配置阻塞，正式用户 ↔ 企业微信 `userid` 映射待实施。

## 通知域

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| I1 | 通知幂等改「优先级档位」键（接收人,对象,类型,档位）：`scheduler.py` 三扫描统一，`find_existing_notification_pairs_async` 支持档位过滤，删 `created_since=today` 与纯 `require_unread` | AFK | — | ADR-0015 | ✅ 已完成 |
| I2① | 企业微信先止血：下线 `WECOM_WEBHOOK_URL` 群广播路径，推送开关默认关、未接应用消息前只发站内 | AFK | — | ADR-0016 | ✅ 已完成 |
| I2② | 企业微信按人定向：建 `corpid/agentid/secret` 配置 + 系统用户↔企业微信 userid 映射，`wecom_service` 改 `touser` 应用消息，`scheduler` 去「每接收人推一遍」 | HITL（真实发送需企业微信可信 IP / 域名；正式映射需 userid 数据源） | I2① | ADR-0016 | 🔄 部分完成：应用消息代码与凭据 `gettoken` 已验证；真实发送被可信 IP 拦截（`errcode=60020`）；正式用户↔企业微信 `userid` 映射待实施 |
| I3 | 系统通知生产者：新建 admin-only 创建端点 + 服务端强制内容中立（无 `related_entity_id`/不挂业务实体/无 PII，违反拒绝）+ 广播全活跃用户 + 仅站内 | AFK | — | ADR-0016 簇（§8 豁免护栏） | ✅ 已完成 |

## 资产域

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| I5 | 导入 owner 必填：`validators.py:REQUIRED_FIELDS` 加产权方，导入 create 走与手动创建共享的 owner 校验、不绕 `asset_crud.create_with_history_async`，解析到 `owner_party_id`，无主行直接拒绝 | AFK | — | ADR-0010/0017 前置 | ✅ 已完成 |
| I4 | 资产/项目编码自动生成：共享 `_build_*_code_segment`（`party_code` 派生）；`asset_code`=`AST-{owner_seg}-{6位}` 接入创建/导入、原子序号、冻结只读、`NOT NULL`、迁移回填；`project_code` 改 `PRJ-{op_seg}-{YYYYMM}-{SEQ4}`；schema 只读、导入模板不含；**不加** `asset_code_prefix` 字段 | AFK | I5 | ADR-0017+0018 | ✅ 已完成 |

## 产权证

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| I6 | 保存闸门重指 + 5 门槛：create（`property_certificate.py:446`）与解析确认路径只卡证号唯一非空、≥1资产、≥1附件、权利人已审核、坐落/地址；面积/期限/限制降 `warning`；`validate_extracted_fields` 退回仅解析提示、不当保存门禁 | AFK | — | PRD §7.2 REQ-AST-005（对齐基线） | ✅ 已完成 |
| I7 | 删僵尸校验器（删而非冻）：删 `validate_certificate_data` 及 18位/面积/发证/到期必填实例方法 + 其「保佑违规」测试（可与 I6 同 PR） | AFK | — | 同上 | ✅ 已完成 |
| I8 | 多资产关联/附件管理 + ≥1 floor 整体替换语义：增删/替换端点；PUT 传完整 `asset_ids`/`attachments` + 服务端校验非空（避 TOCTOU） | AFK | — | REQ-AST-005 + §8 并发口径 | ✅ 已完成 |

## 合同

| 项 | 内容 | 类型 | 依赖 | 决策 | 状态 |
|---|---|---|---|---|---|
| I9 | 合同号复合唯一 + 共享扫描件：`contract_number` 去全局 `unique=True` 改 `UNIQUE(contract_number, project_id)`（Alembic 含存量冲突检测、正常合同缺项目 fail-loud 与持续 check constraint）；共享扫描件文档单存、多 `Contract` 引用，替换/删除只联动同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟记录并逐条鉴权，复用既有 `storage_key` 时拒绝范围外链接，删除受「每合同 ≥1 扫描件」保护；更正按记录独立、只重算本项目台账 | AFK | — | ADR-0012 决策点 6 | ✅ 已实施 |

> 关联：I9 与 2026-06-16 followup 的 C7（代理合同跨项目共享扫描件）是同一机制的两面——C7 管「扫描件共享引用 + 补录引导」，I9 补「合同号复合唯一约束」这一 C7 落地前提；实施时应合并考虑。

## 验收

- **I1**：同档位不重复生成、跨档位升级各发一次；逾期不再按天刷屏；合同到期 30→15→7 天升级不塌缩。
- **I2**：①群广播路径下线、关推送时只走站内、无业务正文外发到不可隔离通道；②应用消息代码按 `recipient_id`→`touser` 定向发送，`gettoken` 已验证；真实发送待企业微信可信 IP / 域名配置；正式用户 ↔ 企业微信 `userid` 映射落地后，正文只达本人（落其数据范围）、§8 自洽、推送为个人消息提醒（无完成态/处理闭环、非企业微信待办）。
- **I3**：非 `admin`/`system_admin` 发系统通知被拒；带 `related_entity_id`/业务实体/PII 的系统通知被拒；内容中立的系统通知广播到全部活跃用户。
- **I5**：无法解析到产权方 Party 的导入行被拒，不再建无 `owner_party_id` 资产；导入与手动创建共用同一道 owner 必填地基。
- **I4**：并发创建同段不撞号；`asset_code`/`project_code` 生成后只读不可改；owner/运营方变更不重编；存量历史编码不回改；导入模板带 asset_code 列被忽略。
- **I6**：缺资产/附件/权利人保存被拒；缺面积/期限/限制只出补录完整性提示、不拦保存；缺坐落/地址（不动产权/房屋/土地证）被拒；`validate_extracted_fields` 不再作为保存 422 门禁。
- **I7**：全库无 `validate_certificate_data`/18位证号/面积日期硬必填实例方法及其测试残留；无生产引用。
- **I8**：删到 0 资产关联或 0 附件被拒；并发整体替换写至多 last-write-wins、凑不出 0。
- **I9**：同 `contract_number` 合同可在 N 个项目各建一条，同项目重号被拒，正常合同缺项目由 DB 约束持续拦截；共享扫描件只存一份、替换同步到同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟合同并逐条鉴权，复用既有 `storage_key` 时范围外链接会失败暴露，删除时每个受影响合同仍至少保留 1 份扫描件；更正某项目记录只复制来源扫描件并保持台账独立。
