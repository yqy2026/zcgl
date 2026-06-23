# 2026-06-18 PRD Grill 代码收口清单

本清单汇总 2026-06-18 `/grill-with-docs docs/prd.md` 会话产出的**代码层收口项**（ADR-0015~0018 + ADR-0011/0012 修订 + 若干基线对齐）。文档基线（PRD / domain-model / CONTEXT / ADR / api-contract / trace / CHANGELOG）已在该会话对齐，以下按项跟踪代码改造状态。每项含触发决策、文件:行证据（2026-06-18 核实）、改造点与验收。

> 注：行号为 2026-06-18 快照，实施前以当前代码为准复核。
> 依赖顺序：I5 → I4（导入生成编号需 owner 先就位）；I2① → I2②；I7 可并入 I6；其余可并行。I9 与 2026-06-16 plan 的 C7 是同一机制两面，合并实施。

---

## I1. 通知幂等改「优先级档位」键

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：ADR-0015、REQ-NTF-001
- **缺口**：`scheduler.py` 三扫描跑两套去重且与 PRD 矛盾——`check_payment_overdue`（~L417-425）/`check_payment_due_soon`（~L516-525）用 `created_since=today` 按天重发（逾期日刷屏）；`check_contract_expiry`（~L315-328）用 `require_unread=True` 纯未读幂等（30→15→7 升级同 `CONTRACT_EXPIRING` 类型被去重塌缩、漏发）。
- **文件:行证据**：`backend/src/services/notification/scheduler.py`、`notification_service.find_existing_notification_pairs_async`。
- **改造点**：
  1. 幂等键改（接收人, 对象, 类型, **优先级档位**）；`find_existing_notification_pairs_async` 支持按档位过滤。
  2. 档位由 `days_overdue`/`days_remaining` 实时派生（逾期 NORMAL→HIGH≥7天→URGENT≥30天；到期 30→15→7 天），不存标记位（口径同 ADR-0007）。
  3. 删 `created_since=today` 与纯 `require_unread=True`。
- **验收**：同档位不重发、跨档位升级各发一次；逾期不日刷屏；到期升级不塌缩；单测覆盖四种场景。

## I2. 企业微信推送按人定向（删群广播）

- **状态**：🔄 I2① 已实施；I2② 应用消息代码已接入并通过 `gettoken` 凭据验证，真实发送待企业微信可信 IP / 域名配置，正式用户 ↔ 企业微信 `userid` 映射待实施
- **决策**：ADR-0016、REQ-NTF-001、§8
- **原缺口**：`wecom_service.py` 曾只往共享群机器人 `WECOM_WEBHOOK_URL` 发消息，群机器人不能按收件人隔离；`scheduler._create_and_send_notification` 曾对每个站内接收人各推一遍完整正文到共享群，造成 §8 业务正文外泄 + N 倍刷屏。当前群机器人路径已下线，应用消息代码已改 `touser` 定向。
- **文件:行证据**：`backend/src/services/notification/wecom_service.py`、`backend/src/services/notification/scheduler.py`（`_create_and_send_notification`/`_send_wecom_notification`）、`backend/src/core/config.py`（`WECOM_*`）。
- **改造点**：
  - **I2①（先止血，AFK）**：下线 `WECOM_WEBHOOK_URL` 群广播路径；推送开关默认关、未接应用消息前只发站内。
  - **I2②（目标，HITL）**：企业微信应用配置 `corpid`/`agentid`/`secret` 已接入；`wecom_service` 已改 `gettoken` + `message/send` 的 `touser` 应用消息；`scheduler` 已去「每接收人推一遍」、改按 `recipient_id` 推本人。剩余：企业微信后台可信 IP / 域名前置配置完成后复测真实发送；补正式系统用户 ↔ 企业微信 `userid` 映射，替换本地 `recipient_id == touser` 假设。
- **验收**：群广播下线；`gettoken` 凭据验证通过；应用消息发送失败不影响站内创建；真实消息发送待企业微信可信 IP / 域名配置；正式映射落地后，正文只达本人、§8 自洽，推送为个人消息提醒（无完成态/处理闭环，非企业微信待办）。

## I3. 系统通知生产者（内容中立护栏）

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：ADR-0016 簇（§8「系统通知类除外」豁免护栏）、REQ-NTF-001
- **缺口**：`SYSTEM_NOTICE` 枚举已声明但零生产者（无创建端点/service，`scheduler.py` 只跑 4 类业务扫描）；§8 广播豁免无人看守内容中立。
- **文件:行证据**：`backend/src/models/notification.py`（`NotificationType.SYSTEM_NOTICE`）、`backend/src/api/v1/system/notifications.py`。
- **改造点**：新建 admin-only 系统通知创建端点；服务端强制内容中立（无 `related_entity_id`、不挂业务实体、不含 PII，违反拒绝创建）；广播全部活跃用户；仅站内（不进定时扫描、不做档位幂等）。
- **验收**：非 `admin`/`system_admin` 发被拒；挂业务实体/带 PII 被拒；内容中立通知全员可收。

## I5. 导入 owner 必填（I4 前置）

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：ADR-0010/0017 前置、REQ-AST-001/002
- **缺口**：手动创建已强制 owner（`asset_service.py:292`），但导入未卡——`validators.py:REQUIRED_FIELDS`（L22-28）不含产权方（仅 `ownership_status` 性质字段）；ownership 仅在提供时校验（`import_service.py:L109/L125`）；导入 create 直接调 `asset_crud.create_with_history_async`（`import_service.py:180`）绕过 service owner 校验，可建无产权方资产。
- **文件:行证据**：`backend/src/services/asset/validators.py:22-28`、`backend/src/services/asset/import_service.py:104-190`、`backend/src/services/asset/asset_service.py:292`。
- **改造点**：`REQUIRED_FIELDS` 加产权方；导入产权方输入解析到既有 Party 的 `owner_party_id`（legacy `ownership_id` 在 Party 迁移收口前作兼容入口）；导入 create 走与手动创建共享的 owner 必填校验，不绕 crud；无法解析到产权方的行直接拒绝。
- **验收**：无产权方导入行被拒，不再建无 `owner_party_id` 资产；导入与手动创建共用 owner 地基。

## I4. 资产/项目编码自动生成（统一段来源）

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：ADR-0017 + ADR-0018、REQ-AST-001 / REQ-PRJ-001
- **缺口**：`asset_code` 零生成器、`models/asset.py:111-116` 为 `nullable`；`project_code` `generate_project_code`（`project/service.py:533-550`）按**年月段** `PRJ-{YYYYMM}-{NNNNNN}`，非 domain-model 声明的运营方段；`group_code`（`contract_group_service.py:723-743` + `_build_operator_code_segment` ~L77-78）已按运营方 `party_code` 段。
- **文件:行证据**：`backend/src/models/asset.py:111-116`、`backend/src/services/asset/asset_service.py`（创建路径）、`backend/src/services/project/service.py:533-550`、`backend/src/services/contract/contract_group_service.py:723-743`、`backend/src/schemas/asset.py`、`backend/src/schemas/project.py`。
- **改造点**：
  1. 段来源统一由相关主体 `party_code` 经共享 `_build_*_code_segment` 派生（owner→asset、operator→project/group），**不新增 `asset_code_prefix` 字段**。
  2. `asset_code`=`AST-{owner_seg}-{6位}` 接入创建/导入路径、每段原子序号、生成后冻结只读、`schema` 只读、`model` 改 `NOT NULL`、Alembic 回填存量、导入模板不含该列。
  3. `project_code` 改 `PRJ-{operator_seg}-{YYYYMM}-{SEQ4}`（复用 `_build_operator_code_segment`），序号按运营方+月计；存量历史编码冻结不回改、仅新建按新格式。
- **验收**：并发同段不撞号；`asset_code`/`project_code` 生成后只读不可改；owner/运营方变更不重编；存量历史编码不回改；导入带 asset_code 列被忽略。

## I6. 产权证保存闸门重指 + 5 门槛

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：PRD §7.2 REQ-AST-005、§9（对齐基线，地址补为第 5 门槛）
- **缺口**：手动创建 API 用 `validate_extracted_fields`（本为解析字段提示）当保存硬闸门（`property_certificate.py:446-453`，`is_valid()` 不过即 422），它硬卡 `property_address` 却漏卡 ≥1资产/≥1附件/权利人已审核；`service.create_certificate`（`service.py:126-147`）裸 dump 无门槛校验，证号唯一仅 DB 约束硬报错。
- **文件:行证据**：`backend/src/api/v1/assets/property_certificate.py:446-453`、`backend/src/services/property_certificate/service.py:126-147`、`backend/src/services/property_certificate/validator.py:31-74`。
- **改造点**：保存路径（create + 解析确认写主数据）改为只卡 5 门槛——证号全局唯一且非空、≥1 既有资产、≥1 附件、权利人引用已审核 Party、坐落/地址非空（不动产权/房屋/土地证类型；其他证照类型按证号）；面积/期限/限制为空降 `warning` 补录完整性提示、不阻断；`validate_extracted_fields` 退回仅作解析页字段提示、不当保存门禁。
- **验收**：缺资产/附件/权利人被拒；缺面积/期限/限制只提示；缺坐落/地址（房产类）被拒；解析提示不再作为保存 422。

## I7. 删僵尸产权证校验器（删而非冻）

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：同 I6（与 PRD 放宽冲突的死代码）
- **缺口**：`validator.py` 的 `validate_certificate_data`（L150-）及 `validate_certificate_number`（18位，L76-83）/`validate_area`（必填，L85-）/`validate_issue_date`/`validate_expiry_date`/`validate_address`/`validate_asset_name` 实例方法**生产零引用、仅测试调用**，编码减法前旧硬必填、与 PRD「面积/期限/限制为空只 warning」冲突。
- **文件:行证据**：`backend/src/services/property_certificate/validator.py:76-164`、`backend/tests/unit/services/test_property_certificate_validator.py`、`backend/tests/unit/services/property_certificate/test_validator.py`。
- **改造点**：删 `validate_certificate_data` 及上述硬必填实例方法 + 其「保佑违规」测试（保留生产实际使用的 `validate_extracted_fields`，仅作解析提示）。
- **验收**：全库无该批实例硬必填方法及测试残留；无生产引用。

## I8. 产权证多资产关联/附件管理 + ≥1 floor

- **状态**：✅ 已实施（I2② 仅剩外部验证/正式映射）
- **决策**：REQ-AST-005（≥1 资产/≥1 附件/不得删最后一个）+ §8 并发口径
- **缺口**：无增删单个资产关联/附件端点；PUT `update_certificate` 走 `crud.update` 裸更新、无 ≥1 floor 校验；多资产关联管理基本未实现。
- **文件:行证据**：`backend/src/api/v1/assets/property_certificate.py`（`update_certificate` 路径）、`backend/src/services/property_certificate/service.py:149-161`。
- **改造点**：提供资产关联/附件的增删/替换；以**整体替换语义**实现 floor——PUT 传完整 `asset_ids`/`attachments`、服务端校验非空（每写各校验自身完整列表，使「≥1」下限天生 TOCTOU 安全：并发合法写至多 last-write-wins、凑不出 0）；并发丢更新按 §8 接受（乐观锁仅 Asset）。如将来提供「删单个」增量操作，再为产权证加版本号/同事务行锁。
- **验收**：删到 0 资产关联或 0 附件被拒；并发整体替换凑不出 0。

## I9. 合同号复合唯一 + 共享扫描件（ADR-0012 决策点 6）

- **状态**：✅ 已实施（与 2026-06-16 plan C7 合并实施；I2② 仅剩外部验证/正式映射）
- **决策**：ADR-0012 决策点 6、REQ-RNT-001
- **已改造**：`contracts.contract_number` 去全局唯一，新增 `Contract.project_id` 并建 `UNIQUE(contract_number, project_id)`；迁移 `20260620_contract_number_project_scan_documents.py` 先从 `contract_groups.project_id` 回填项目，再检测正常合同缺项目与同项目重号冲突并失败暴露，并创建 `ck_contracts_active_project_id_required` 持续拦截未来正常合同缺项目。共享扫描件新增文档表与链接表，按 `storage_key` 复用文档行，多条同委托协议 `Contract` 可共享引用；附件替换/删除只联动同合同号 + 同委托方 + 同受托方 + 正常代运营受托角色的兄弟合同，并在写入前逐条校验全部受影响合同 `contract:update` 权限；复用既有 `storage_key` 时若扫描件已链接到受影响集合外合同则拒绝；删除受「每合同 ≥1 盖章扫描件」保护。更正草稿复制来源扫描件，后续更正仍按记录独立。
- **文件:行证据**：`backend/src/models/contract_group.py`、`backend/src/crud/contract.py`、`backend/src/services/contract/contract_group_service.py`、`backend/src/api/v1/contracts/contract_groups.py`、`backend/alembic/versions/20260620_contract_number_project_scan_documents.py`。
- **验收证据**：`backend/tests/unit/models/test_contract_group_model.py` 覆盖去全局唯一、复合唯一和共享扫描件模型；`backend/tests/unit/services/contract/test_contract_group_service.py` 覆盖跨项目同号允许、同项目重号拒绝、共享作用域收窄、既有 `storage_key` 范围外链接拒绝、附件替换和删除 floor；`backend/tests/unit/crud/test_contract.py` 覆盖共享扫描范围排除软删合同组；`backend/tests/unit/api/v1/test_contract_groups_layering.py` 覆盖全部受影响合同逐条鉴权；`backend/tests/unit/migration/test_contract_number_project_scan_documents_migration.py` 覆盖迁移链、列/约束/表创建、存量冲突检测、缺项目 fail-loud 与持续 check constraint。Ruff check/format 已通过；pytest 受本地 venv/uv 环境阻塞。
