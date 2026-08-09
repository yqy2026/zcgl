# G1 验收预演抽验报告（2026-08-09）
## 1. 背景

按 [`docs/traceability/mvp-acceptance-checklist.md`](../traceability/mvp-acceptance-checklist.md) 的 G1 门槛（资产页和项目页清晰展示资产信息、租赁情况、客户摘要、项目经营摘要）执行首次预演抽验。目的：在正式产品验收前暴露阻断项。

抽验方式：浏览器实测（admin / admin123，`Development Administrator` 角色，产权方口径），资产 19 条（种子数据）。

## 2. 通过项

| 验证点 | 结果 |
|---|---|
| 登录 → 工作台 → 导航 | ✅ 正常，统计卡片渲染（资产总数 19、出租率 91.4%） |
| 资产列表页 `/assets/list` | ✅ 19 条记录完整展示（项目、物业名称、权属方、面积、确权状态、出租率），面积统计汇总与分页正常 |
| 资产详情页 `/assets/{id}` | ✅ 基本信息、面积信息、接收协议、合同信息、审核日志、租赁情况（本月出租率/活跃合同/合同角色汇总：上游承租/下游转租/委托协议/直租合同）、客户摘要区域全部渲染；空态显示正常 |
| 项目列表页 `/project` | ✅ 页面渲染与空态正常（总项目数 0） |

## 3. 发现的问题

### 3.1 资产详情页"权属方"恒显 "-"（前端契约不一致）—— ✅ 已修复（2026-08-09）

- **现象**：资产详情页基本信息中"权属方"显示 `-`；同资产在列表页显示"广州国有资产管理集团有限公司"。
- **根因**：前端 `frontend/src/components/Asset/AssetDetailInfo.tsx:98` 渲染 `asset.owner_party_name ?? '-'`，但后端详情接口（`backend/src/schemas/asset.py:419`）返回 `ownership_entity`（注释"权属方名称（动态获取）"），**不返回 `owner_party_name`**。前后端契约不一致，字段恒为空。列表页 `AssetList.tsx` 有 `owner_party_name` → `ownership_entity` 回退语义（`AssetList.ownerName.test.tsx` 固化），详情页缺失该回退。
- **修复**：`AssetDetailInfo.tsx` 改为 `asset.owner_party_name ?? asset.ownership_entity ?? '-'`，与列表页回退语义一致。TDD：先补失败测试（后端仅返回 `ownership_entity` 时详情页应显示权属方）→ red（1 failed / 46 passed）→ 修复 → green（47/47 passed）；oxlint 0 warnings、`type-check` 通过；浏览器实测详情页权属方显示"广州国有资产管理集团有限公司"。
- **影响范围**：G1（资产信息展示）、ACC-001~004 相关展示路径；不涉及数据正确性。

### 3.2 项目实体数据缺失，G1 项目部分无法抽验（种子数据缺口）—— ✅ 已补数（2026-08-09）

- **现象**：项目列表页总项目数 0；`GET /api/v1/projects` 返回空。但 19 个资产均带 `project_name`（越华路穗南大厦、人民南路等），且资产接口 `project_id` 为 `None`。
- **判断**：功能面（项目列表页渲染、空态）正常；问题在**验收/开发环境种子数据不完整**——资产有项目归属名但 `projects` 表无对应实体。属种子数据缺口，不是功能缺陷；但会阻塞 G1 项目经营摘要、ACC-005（项目绑定运营管理方）及 REQ-PRJ 系列验收。
- **修复**：新增幂等补数脚本 `backend/scripts/maintenance/seed_projects_from_assets.py`——按 `assets.project_name` 去重建 11 个项目实体（走 `ProjectService.create_project` 保证 `project_code` 按 `PRJ-{operator_seg}-{YYYYMM}-{SEQ4}` 自动生成，运营管理方使用环境唯一主体"广州国有资产管理集团有限公司" `LE-000001`），并回填 `project_assets` 活跃关联（19 条）。脚本含幂等检查（同名项目/活跃关联跳过）与显式提交。修复过程中发现隐式提交不可靠（最后一个项目的关联在 scope 退出时未提交），已改为循环后显式 `db.commit()`，重跑确认全量幂等（0 created / 19 existing）。
- **验证**：项目 API 返回 11 个项目（编码 `PRJ-LE000001-202608-0001~0011`，状态 active）；资产详情派生 `manager_party_id` 从 None 恢复为 `27ef9966`（REQ-AST-002 收口语义生效）；浏览器实测项目详情页完整渲染——关联资产 1 个、可出租总面积 2,097.96 ㎡、收付款摘要五项、空置资产风险派生（长提大马路 空置 2,097.96㎡）、关联资产表与租赁情况（合同口径）表。
- **影响范围**：G1 项目侧已可抽验；ACC-005、REQ-PRJ-002/003 验收前置条件满足。

### 3.3 项目列表"关联资产"恒 0 + "待补绑定"标签（服务端未填充 asset_count）—— ✅ 已修复（2026-08-09）

- **现象**：项目列表页每行"关联资产"显示 0、状态标签"待补绑定"；项目 API 返回 `asset_count: 0`。项目详情页关联资产计数正常（1 个）。
- **根因**：`ProjectResponse.asset_count` 默认 0，schema validator 仅在 ORM 对象存在 `asset_count` 属性时填充（`backend/src/schemas/project.py:252`），但 `search_projects`（`backend/src/services/project/service.py:678`）返回的 ORM Project 无该属性，且未调用 `project_crud.get_asset_count`（该 crud 方法存在且逻辑正确）。前端 `ProjectList.tsx` 的"待补绑定"判定 `asset_count === 0` 随之误报。
- **修复**：crud 新增 `get_asset_counts(db, project_ids)` 批量分组计数（活跃关联、单 SQL 避免 N+1）；`search_projects` 对 items 批量填充 `setattr(item, "asset_count", ...)`。TDD：先补 service 失败测试（red：列表项目必须带活跃关联资产数）→ 修复 → green；crud 补 2 个单元测试（分组映射 + 空输入）；适配旧测试 2 个（mock 新调用）。验证：crud+service 相关测试 79/79、API 层 33/33、ruff 通过；浏览器实测列表页"待补绑定"标签消失、关联资产数正确（松柏东街 5、长堤 1…）。
- **排查备注（环境）**：修复生效前 API 仍返回 0 的原因——`make dev` 旧后端进程（reloader 父进程 1872）未被 `taskkill` 真正终止，与重启的新进程**同时监听 8002**，请求路由到旧进程。`Stop-Process -Force` 清理旧进程后生效。后续遇到"改了代码 API 没变"，先查端口监听者数量。
- **另注（展示口径待确认，不修）**：项目列表"所有方主体"列读已下线的 `party_relations`（`ProjectList.tsx:276`），收口后项目主体关系由资产派生，该列恒空——显示口径需产品确认（改为显示运营管理方或资产产权方）。

## 4. 结论与建议

- G1 资产侧展示 ✅ 基本通过（除 3.1 缺陷）；项目侧因 3.2 数据缺口暂无法验收。
- 建议：3.1 修复（低风险，前端一行）；3.2 补种子数据后重跑本报告 2 节路径完成 G1 闭环。
- 本次为预演抽验，G1 状态仍为 ⏳ 待验收，最终认定由产品负责人按 PRD §3.2 执行。

---

## 5. 附录：G2 预演追加发现（2026-08-09）

### 5.1 合同创建 API 返回 500 但数据已落库（ContractDetail 枚举校验缺陷）—— ✅ 已修复（2026-08-09）

- **现象**：`POST /api/v1/contract-groups/{group_id}/contracts`（补录上游承租合同，承租转租）返回 **500 内部服务器错误**，但合同、租金条款、经营台账（12 条月账）**实际全部落库**（contracts/contract_rent_terms/contract_ledger_entries 三表确认）。前端将显示失败，用户重试会撞 `contract_number` 唯一约束——**"创建成功但返回失败"的不一致**，可稳定复现（UP-001/UP-002 两次均 500）。
- **根因**（完整定位）：
  1. `contract_crud.create` 用 data dict 直接构造 ORM 对象，其中 `contract_direction`/`group_relation_type`/`status` 为**英文枚举名**（`LESSEE`/`UPSTREAM`/`ACTIVE`，来自 `obj_in.xxx.name`）；
  2. 同一 session 内端点随即调用 `get_contract_detail`，`contract_crud.get` 从 **session identity map 命中缓存对象**（字符串属性）；
  3. `ContractDetail.model_validate` 的枚举字段（`'出租'/'承租'` 等**中文值**）校验失败 → ValidationError → 端点 `internal_error("添加合同失败")` 包装 → 500。
  4. 单独调用 `get_contract_detail`（新 session 从 DB 加载）成功——SQLAlchemy `Enum(values_callable=name)` 加载时转回枚举对象，故旧数据/列表接口不受影响。
- **修复**：`ContractSummary`/`ContractDetail` 增加共享 `_coerce_enum_name` + `field_validator(mode="before")`（枚举 name 字符串归一化为 `.value`，枚举对象透传，不改 ORM 对象；与 `ProjectResponse.coerce_project_model` 同模式）。TDD：新增 `TestContractDetailEnumCoercion`（2 用例，SimpleNamespace 模拟同 session 字符串对象）→ red（ValidationError 复现）→ green；合同 service 67/67、API layering 14/14、ruff 通过；HTTP 复验 **201** 且返回中文枚举（`承租/上游/生效`）。
- **排查附加发现（环境，重要）**：修复后 HTTP 仍 500 的根因是 **3 个不同时期的 uvicorn worker 幽灵并存**——reloader 父进程已死但 worker 存活，各自加载不同时期代码，请求随机路由（netstat 显示已死 reloader 的 PID 为"幽灵 socket 条目"，tasklist 才能看到真实 worker）。`taskkill //F //T` 全部清理后单实例启动即生效。经验：Windows 下改后端代码后 API 行为异常，先核对 `tasklist` python 进程数 vs 端口监听者。
- **可观测性改进（随修复落地）**：`add_contract_to_group` 端点 `except Exception` 增加 `logger.exception(..., exc_info=exc)`，原始异常堆栈现在进日志（原 `internal_error(original_error=...)` 不落日志导致排障困难）。
- **影响范围**：G2 合同补录主路径（已修复）；台账生成正常（数据正确性无问题，仅响应异常）。

### 5.2 合同中心列表页"新建合同关系"按钮进入无项目上下文受限页（UX）

- 列表页按钮 → `/contract-center/new`（无 `project_id`）→ 页面提示"请先从项目详情发起新建合同关系"，无法提交。属入口 UX 瑕疵（按钮应隐藏或跳转项目选择），不影响从项目详情发起的正常路径。见验收清单 G2 行。

### 5.3 收付流水创建 500（occurred_on 被字符串化，asyncpg 拒绝）—— ✅ 已修复（2026-08-09）

- **现象**：`POST /api/v1/ledger/payment-flows`（upstream_cost_payment 50000）返回 500；本地复现堆栈：`asyncpg.exceptions.DataError: invalid input for query argument $3: '2026-08-05' ('str' object has no attribute 'toordinal')`。
- **根因**：`create_payment_flow` 端点调用 service 时用 `payload.model_dump(mode="json")`——把 `occurred_on`（date）序列化为字符串 `'2026-08-05'`，service 透传给 asyncpg DATE 列参数被拒（Decimal 金额字符串被 NUMERIC 接受、date 字符串不被接受）。
- **修复**：端点改 `payload.model_dump()`（python 模式保留 date/Decimal 原生类型）。TDD：新增 `test_create_payment_flow_passes_native_date_to_service`（断言传给 service 的 `occurred_on` 是 `date` 对象）→ red（str）→ green；ledger API + payment-flow service 51/51、ruff 通过；HTTP 复验创建流水 200。
- **验证闭环**：流水创建 200 → 分摊到 2026-08 账期（`contract_ledger_entry`）200 → 台账条目实付 50000、状态 `paid`（G2 实收登记链路 ✅）。
- **同类风险提示**：`model_dump(mode="json")` 传给 service 的模式在别处也存在（`ledger.py` 其他端点已排查无 date 字段透传；后续新增端点应避免 json dump 直传 DB 参数）。

### 5.4 ACC-023 多账期分摊验收（2026-08-09）—— ✅ 通过

- 补录下游转租合同 `CT-2026-DN-001`（出租/下游，月租 50000，12 条台账视图 `terminal_collection + operator_income`）→ 201；承租转租上下游结构完整。
- 一笔 `terminal_rent_receipt` 100000 流水 → 分摊 2026-08（94078f09）+ 2026-09（b468947b）各 50000 → 两条目均 `paid`。
- 项目 ledger-summary 派生正确：terminal_collection 应收 600000/实收 100000/未收 500000；received_amount 100000、paid_amount 50000。
- 结论：ACC-023（一笔收款多账期分摊、实收由流水汇总派生）验收通过；G2 全链路（合同→条款→台账→实收→分摊→汇总派生）本地验证完成。
