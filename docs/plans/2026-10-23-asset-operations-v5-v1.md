# 资产运营 v5 V1 资产单元与合同链实施计划

> **状态**：🔄 进行中
> **日期**：2026-10-23
> **需求**：REQ-UNT-001、REQ-CTR-001、REQ-CTR-002、REQ-AUTH-002
> **产品基线**：`docs/prd.md`、`docs/specs/domain-model.md`、`docs/specs/api-contract.md`

## 1. 目标与非目标

V1 建立“上游合同 → 资产单元 → 终端合同”的唯一事实链，支持单元拆合历史、合同覆盖、续签/终止/退出记录及上游缺失、租期越界风险派生。

V1 不实现租金付款、押金、委托管理费、考核范围、报送、档案矩阵或导入提交；仅保留后续切片需要的稳定关联点。

## 2. 现有实现盘点与裁决

| 现有对象 | 实际状态 | V1 裁决 |
|---|---|---|
| Party / Organization / User / 数据范围 | 已有稳定平台能力 | 保留；新端点统一经 `EffectivePartyScope` 失败关闭 |
| `Project` / `project_assets` | 项目带状态且与 `Asset` 时态关联 | 保留 ID 与编码数据，收窄为管理归属标签；不再作为经营数字事实源 |
| `Asset` | 包含可写 `rented_area`、缓存出租率、审核态和合同嵌入字段 | 不直接扩展；新建 `AssetUnit` 事实模型，禁止写入出租状态和已租面积 |
| `PropertyCertificate` / `property_cert_assets` | 证照主档可复用，但面积为字符串且关联目标是旧 `Asset` | 复用证照主档 ID，新建 `PropertyCertificateAssetUnit`；面积规范化在后续独立迁移处理 |
| `ContractGroup` / `Contract` | 技术聚合绑定 Project，包含草稿/生效和 v4.0 关系类型 | 不复用为 v5 公开模型；分离新建 `UpstreamContract` / `TerminalContract` 与覆盖表 |
| `ContractRentTerm` | 月租金分段，与旧 Contract 强绑定 | 不双读；新建 `ContractRentSchedule`，只表达已签合同的结构化条款 |
| `ContractLedgerEntry` / `OperationalPaymentFlow` / `ServiceFeeLedger` | 包含可变 `paid_amount`、旧视图归属和旧服务费口径 | V2 将以追加式付款记录取代；V1 不修补旧表 |
| 前端 `/dashboard`、`/assets`、`/contract-center`、`/project`、`/operations/ledger` | 路由和导航反映 v4.0 多模块信息架构 | V1 建立 `/asset-operations/*` 路由树，同一切换中移除旧业务导航和别名，不做双入口 |

## 3. 一次性切换和数据原则

1. 先增加新表与定向迁移脚本，但分支在新 API、新路由和旧业务入口一次性切换前不可发布。
2. 不在运行时双读、双写或建立“新表不完整就回落旧表”的兼容分支。
3. Party、Organization、User、Project、PropertyCertificate 和 Attachment 的稳定 ID 保留；其余业务对象使用新 v5 ID。
4. `Asset` 到 `AssetUnit` 只能复制可确定映射的编码、名称、地址、产权方和项目标签；`actual_property_area` 映射建筑面积，`rentable_area` 映射可出租面积。任一必填值缺失、面积为负数或可出租面积大于建筑面积时，预检必须报错并输出待裁决清单。
5. 旧 ContractGroup/Contract/台账不做自动语义转换。切换预检先输出行数与关联摘要；非空环境必须完成经复核的导入底稿或明确重置，不得静默删除。
6. 旧业务表仅在切换验证完成后由后续破坏性迁移删除；保留期内不对应任何可达 API、前端路由或后台任务。

## 4. 失败测试清单（先写）

| 测试 ID | 预期失败条件 | 守护的意图 |
|---|---|---|
| V1-T01 | 一份终端合同覆盖三个单元时被计为一宗 | 统计粒度是资产单元，不是合同 |
| V1-T02 | 上游尚未录入时拒绝保存已签终端合同 | 事后登记不被前置门禁阻断，但风险必须可见 |
| V1-T03 | 终端租期越过上游时无风险或被拒绝保存 | 已签事实可登记，越界风险可稳定派生 |
| V1-T04 | 上游退出时仍有有效终端合同却可提交 | 退出必须先显式处理有效终端合同 |
| V1-T05 | 单元拆分后面积不守恒或旧单元在生效日后仍计宗 | 边界变化以生效日追加且可按时点重放 |
| V1-T06 | 不同上游覆盖范围的单元可被合并 | 合并不得破坏合同权利边界 |
| V1-T07 | 无 Party 范围返回空列表 | 数据范围失败关闭并返回稳定 403 |
| V1-T08 | 过期 `expected_version` 覆盖更新 | 所有可变事实使用乐观锁并返回 409 |
| V1-T09 | 重放相同幂等键创建第二条生命周期事件 | 重试不重复写入 |
| V1-T10 | 页面将 403 当作 empty 或将 error 清空成空列表 | loading / empty / 403 / error 四态不混淆 |

## 5. 文件级实施顺序

### V1-0：数据预检与迁移骨架

- `backend/scripts/` 增加只读预检，输出旧 Asset/Project/Contract/台账行数、缺失主体和面积冲突，默认不修改数据。
- `backend/alembic/versions/` 增加 v5 基础表迁移，不带运行时兼容触发器或双写。
- 测试先覆盖非空旧合同表、面积歧义和孤儿 Party/Project 三类预检失败。

### V1-1：领域与持久化

- `backend/src/models/asset_unit.py`：`AssetUnit`、`AssetUnitBoundaryChange`、证照关联表。
- `backend/src/models/asset_contract.py`：`UpstreamContract`、`TerminalContract`、两类覆盖表、`ContractRentSchedule`、`ContractLifecycleEvent`。
- `backend/src/schemas/asset_operations.py`：字段、列表、详情、预览与提交 schema；派生字段不进入写模型。
- `backend/src/crud/asset_unit.py` 与 `backend/src/crud/asset_contract.py`：仅数据访问，列表关联统一 `selectinload`。
- `backend/src/models/__init__.py` 显式导出新模型；完成之前不删除旧导出。

### V1-2：业务服务与 API

- `backend/src/services/asset_operations/`：单元查询、拆合预览/提交、合同链、风险派生、续签、终止和退出；不让 API 端点承载业务逻辑。
- `backend/src/api/v1/asset_operations/`：按 `asset-units`、`upstream-contracts`、`terminal-contracts` 分模块自注册，只对外公开 `docs/specs/api-contract.md` 约定的 v5 路径。
- 每个查询和写操作在 service 入口统一解析 Party 范围；预览 token、幂等键和期望版本使用共享基础设施。

### V1-3：前端纵向切片

- `frontend/src/constants/routes.ts` 与 `frontend/src/routes/AppRoutes.tsx`：注册 `/asset-operations/units`、`/asset-operations/contracts/upstream`、`/asset-operations/contracts/terminal`，使用 `asset_ops:read/write` 能力。
- `frontend/src/services/assetOperationsService.ts`：封装 v5 API，Decimal 字符串经统一转换后才交给页面。
- `frontend/src/pages/AssetOperations/`：先完成单元列表 + 常驻详情栏，再完成上游/终端合同列表和录入。服务器数据使用 React Query，表单使用 React Hook Form。
- 每页实现 loading / empty / 403 / error 四态、唯一 Primary 操作、可见 label / focus-visible，并验证 1280px、200% 缩放和 320px 重排。

### V1-4：切换与清理

- 新纵向切片通过后，在同一分支移除旧业务导航、路由别名和旧 API 注册；系统管理、Party、Organization、User 与审计不受影响。
- 核对 `rg` 无旧入口、无双写、无新端点读旧 ContractGroup/台账的残留后，再进入 V2。

## 6. 验证门槛

- 各批次按 TDD 顺序运行定向测试，然后运行受影响的 lint、type-check、前后端测试、迁移命名检查、backend-import、docs-lint 与构建。
- V1-T01–V1-T10 全部转绿，并将代码与测试证据写入 `docs/traceability/requirements-trace.md`。
- 未执行的测试、未解决的数据歧义或尚未切换的旧入口均使 V1 保持进行中，不得标记完成。

## 7. 实施记录

- 2026-10-27：真实浏览器门禁逐轮缩小到非法文件上传的单次 POST 断言（34/35 通过）。trace 先确认 422/VALIDATION_ERROR/extension_not_allowed 与页面错误提示契约；随后单次点击实际发出两次 POST 暴露 QueryClient 全局 mutation retry=1 叠加重试，不能由服务 API retry:false 控制。录入及两类续签上传 mutation 均显式禁用重试，补上游续签失败 Alert，三项新增回归先红后绿，定向 10 项与类型/lint/格式通过；未放宽 E2E 断言或全局调整重试策略，完整 CI 待新提交复核。

- 2026-10-27：最终 Standards 轴确认新合同关键状态机 REQ 尚未纳入 E2E 准入守卫，Spec 轴复现合同延期绕过资产在管截止日。两项均采纳：新增真实 HTTP 终端终止→上游退出链路（403、409 业务码、预览/提交/幂等和覆盖投影），本地 PostgreSQL + Redis DB15 实跑 1 项通过，REQ-CTR-001/002 纳入准入清单并补追踪路径；延期按实际受影响覆盖行校验在管期间，新增测试先失败 2 项后通过，资产运营服务整组 132 项通过。同期修正 CI 新暴露的旧解析 API/旧权限种子守卫，分别 10/13 项通过；完整 CI 仍待新提交复核。

- 2026-10-27：提交前复核补齐 CI 真实性：集成测试移除仅 `main` 推送执行限制，汇总显式依赖集成/lint 并拒绝任何失败、取消或跳过。采纳子代理范围隔离复核结论，在种子中新增另一产权方实际单元，管理员先确认两方有数据，再由普通用户验证隔离，避免空反例假绿。前端 lint、严格 UI、应用/E2E 类型、格式、E2E lint、35 项收集与 docs-lint 通过；真实 E2E、集成和 API 一致性结果仍待新提交 CI，不提前归档方案。

- 2026-10-23：V1-0 只读预检模块完成首个红绿循环。新增 `collect_preflight()`、`evaluate_preflight()` 和 `overall_result()` 三个对外接口，隐藏表扫描、隐私过滤和问题编码实现。当缺表/缺列、资产必填映射不完整或旧合同/台账非空时失败关闭；输出只含对象 ID、问题码和行数，不包含名称或地址。定向测试 5 项通过。
- 2026-10-23：V1-1 完成资产单元部分的首个红绿循环。新增 `AssetUnit`、`AssetUnitBoundaryChange`、`PropertyCertificateAssetUnit` 及首个 v5 Alembic 迁移；数据库约束锁定经营模式、面积、在管时间、空置原因、边界变更幂等和证照关联时间。模型明确不存储 `rental_status`、`rented_area`、`occupancy_rate` 或 `upstream_risk` 等派生值。模型、迁移和字段漂移定向测试 12 项通过；下一步是上游/终端合同事实模型。
- 2026-10-23：V1-1 完成合同事实模型的红绿循环。新增 `UpstreamContract`、`TerminalContract`、两类资产单元覆盖、`ContractRentSchedule` 和追加式 `ContractLifecycleEvent` 及第二个 v5 Alembic 迁移。状态、到期和风险继续派生；终端合同允许上游暂缺；同一资产单元的终端覆盖时间重叠由 PostgreSQL `EXCLUDE USING gist` 约束拒绝；撤销事件显式记录 `reversed_event_id`，不覆盖原事件。下一步进入 schema/CRUD，并在 service 层实现 V1-T01–V1-T09 的行为规则。
- 2026-10-23：V1-1 schema 完成首个红绿循环。新增资产单元、上游合同、终端合同、租金阶段和生命周期事件的严格写入/响应 schema；写入端 `extra=forbid`，拒绝出租状态、合同状态和风险等派生字段，更新请求强制 `expected_version`，上游暂缺仍是合法终端合同输入。schema 定向测试 7 项通过。
- 2026-10-23：V1-2 启动纯业务投影。新增终端合同状态/风险和按统计日计算已出租资产单元集合的纯函数，V1-T01–V1-T03 首批转绿：一份合同覆盖三单元计三宗；缺上游只产生 warning 且仍计出租；租期越界只产生 warning；终止与撤销通过追加事件重放，不覆盖原事实。投影定向测试 5 项通过；CRUD、范围过滤、写服务和 API 尚未实现。
- 2026-10-23：V1-1 范围化 CRUD 与 V1-2 首批服务守卫完成红绿循环。资产单元产权方范围读取 `owner_party_id`，运营方范围经 `project_id → Project.manager_party_id`；上游合同按 `owner_party_id` / `operator_party_id`，终端合同按覆盖资产单元的产权方/项目运营方过滤并使用 `EXISTS` 避免重复。资产单元及两类合同的列表/详情查询均在 service 入口按 `scope_mode` 对应轴校验，缺失或失效范围返回稳定 403，repository 仅作防御性失败关闭。V1-T04–V1-T07 转绿：上游退出阻断有效终端合同；拆分至少两个结果、合并至少两个来源，且源单元在生效日前一日结束、结果单元从生效日起算并保持面积守恒；合并有效上游范围同时检查覆盖区间、合同期限和未撤销退出事件；无 Party 范围不伪装为空列表。写入提交、预览 token、乐观锁、幂等和 API 尚未实现。
- 2026-10-23：V1-2 完成资产单元“拆分”预览—提交纵向服务。预览校验未来生效日、源单元在边界日仍有效且未被其他边界事件消费、结果编号全局唯一、面积守恒、有效上游覆盖和跨界终端合同，返回绑定操作者/范围/提议/版本/上游覆盖期间/状态指纹的 10 分钟不透明 token，且不写库。提交按源单元与相关覆盖加锁并重新计算，原子截止源单元与原有效上游覆盖、创建结果单元及逐单元新覆盖、追加边界事件和唯一 `AssetUnitBoundarySource`；结果单元只接受编号/名称/面积并继承源单元业务归属。拆分路径完成 V1-T08，并为后续 V1-T09 提供了边界命令的幂等基础设施证据：源单元版本即使结束日未变化也会推进，ORM 乐观锁漂移返回 `VERSION_CONFLICT`；幂等键按操作者隔离、保存请求指纹和首次响应，并处理幂等、结果编号及源单元消费三类并发唯一键争用；token 只在提交成功或确认并发提交已成功后删除。V1-T09 仍需生命周期事件命令自身的重放测试。终端合同跨界返回 `ASSET_UNIT_PERIOD_OVERLAP`，不静默迁移已签合同。当前证据为 fake session/repository 行为测试和 SQL 语句测试，尚未完成 PostgreSQL 集成测试；后续合同覆盖写服务必须先锁同一 AssetUnit，未固化该协议前不得接 API。合并提交、API 路由、产权证/考核范围联动和页面仍待实现，V1 保持进行中。
- 2026-10-24：拆分纵向链路进入真实 PostgreSQL 与 HTTP 边界。新增 PostgreSQL 集成测试，确认提交后源单元截止并升版、结果单元继承归属、边界事件/来源关系各唯一一条，同请求幂等重放不重复写；新增共享 `AssetUnitRepository.lock_for_write()`，边界提交和合同覆盖写入按排序后的资产单元 ID 获取同一 `FOR UPDATE` 行锁，真实锁超时用例证明协议生效。新增自注册 `POST /api/v1/asset-units/{unit_id}/split/preview` 与 `POST /api/v1/asset-units/{unit_id}/split`，请求路径绑定源单元，提交强制 `Idempotency-Key`，并接入当前用户、`asset_ops:write` 与服务端 Party 范围；预览 token 不能跨资源路径重放。新增五类 `asset_ops` 能力及权限迁移，`ops_admin` / `system_admin` 获得完整映射，能力快照支持 owner/manager 视角。V1 仍未完成：合并提交、合同写服务、证照/考核联动、列表/详情/更新 API 与前端页面待实现。
- 2026-10-24：V1-T06 从纯规则推进为资产单元“合并”预览—提交纵向链路。新增严格合并 schema、范围化多源上下文、确定性排序行锁、预览 token、完整版本集合、乐观锁、幂等回放和 HTTP 端点；结果面积完全由服务端汇总，源单元必须具有一致归属元数据、相同非空有效上游集合及一致的未来覆盖截止边界，生效日及之后的终端合同覆盖继续失败关闭。晚于边界日开始的上游覆盖必须先调整，恰在边界日开始的覆盖直接迁移而不制造空有效期；生效日校验使用 `Asia/Shanghai` 业务日，不受 UTC 跨日窗口影响。提交原子截止全部源单元与原覆盖、创建一个接续单元和每份上游合同的一条新覆盖，并写入逐源唯一消费关系。真实 PostgreSQL 红绿循环暴露结果单元/覆盖同批 flush 的外键排序问题，改为同事务分阶段 flush 后验证双源升版、面积守恒、同日覆盖迁移和幂等无重复。V1 仍未完成：合同写服务、证照/考核联动、列表/详情/更新 API 与前端页面待实现。
- 2026-10-24：V1-2 完成“确认已签合同”的共享写服务与 PostgreSQL 持久化闭环。上游/终端创建统一先做 Party scope 失败关闭并按 ID 排序锁定全部资产单元，校验扫描件、在管期间、产权方、租金阶段和所选上游在终端开始日的覆盖；合同、逐单元覆盖、租金阶段及 `AssetContractWriteReceipt` 在同一事务提交。终端上游缺失、租期早于或晚于上游仍只返回稳定 warning；模式、出租方或所选上游覆盖不一致失败关闭；同期终端覆盖在锁内预检并由 PostgreSQL GiST 排斥约束兜底。幂等键按操作者隔离并保存规范化请求指纹和首次响应，重复确认不产生第二份合同。真实 PostgreSQL 验证上游/终端覆盖、两份写回执、warning、幂等重放和重叠拒绝均无残留。合同录入会话确认 API 尚未接线，不能另开直接创建端点；续签、终止/退出、证照/考核联动、列表/详情/更新 API 与前端页面仍待实现。
- 2026-10-24：V1-2 接通合同录入会话 HTTP 边界，保留唯一创建入口。新增上传、读取、确认上游、确认终端和取消五个自注册端点；会话使用 Redis TTL/CAS 按操作者隔离，扫描件经统一文件校验后进入私有存储和 Attachment，自动提取不可用以 warning 降级到手工核对。确认请求不能写合同类型或扫描件 ID，由会话注入后调用共享合同写服务，强制 `asset_ops:write`、服务端 Party scope 与 `Idempotency-Key`；成功后会话标记 confirmed，扫描件在合同事务内改绑正式合同，同请求可经持久回执重放。取消仅允许未确认会话，并补偿删除附件和文件。未开放绕过会话的直接合同创建端点。续签、终止/退出、证照/考核联动、列表/详情/更新 API 与前端页面仍待实现。
- 2026-10-24：合同录入独立复核的五项 P1 已全部收口。并发相同幂等键在资产单元锁后复查持久回执；所选上游按 Party scope 与请求覆盖单元查询；附件改绑使用 `FOR UPDATE` 且要求当前 owner 仍是录入会话，防止 confirmed/confirming 重入或跨会话重复消费扫描件；普通录入确认移除 `renewed_from_id`，续签链保留给独立 `/renewals` 命令；追踪表不再提前宣称 V1-T09 生命周期幂等已完成。真实 PostgreSQL 用例覆盖同键并发只创建一份合同、第二合同复用扫描件返回 `SCAN_DOCUMENT_ALREADY_BOUND` 且无残留。
- 2026-10-25：最终复核补齐终端合同出租方关系的失败关闭。无上游直签按已锁单元唯一产权方校验，无上游转租按这些单元所属项目的唯一运营 Party 校验；缺失、多主体或请求出租方不一致统一返回 `ASSET_CONTRACT_COVERAGE_INVALID` 409。已选上游的合同模式/上游类型和出租方不一致也从 422 收口为同一稳定 409。`TERMINAL_TERM_EXCEEDS_UPSTREAM` 同时覆盖转租承租合同和直签委托管理协议，保持规格的通用越界风险口径。
- 2026-10-25：V1-T09 的生命周期事件幂等核心完成首个纵向红绿循环。新增终端终止提议/事件响应 schema、生命周期事件 CRUD 和 `ContractLifecycleCommandService.terminate_terminal()`；命令按 Party scope 锁定目标终端合同，锁前/锁后复查全局幂等键，原子追加 `terminated` 事件并映射并发唯一键争用，同键同请求返回首次事件且 `idempotent=true`，同键改写返回 `IDEMPOTENCY_CONFLICT`。真实 PostgreSQL 双会话并发只产生一条事件。该切片尚未公开 HTTP 端点，也未处理终止对覆盖期间的影响；必须在终止预览—提交端点接线前补齐影响预览、覆盖冲突和撤销语义。
- 2026-10-25：终端终止的影响模型与预览—提交端点完成红绿循环。裁定口径：生命周期事件 `effective_date` 为新状态首日（与拆合生效日同义），终端终止最后有效日为前一日；终止提交在同一事务把仍延伸到生效日之后的 `TerminalContractAssetUnit` 覆盖行截止到前一日，后继合同最早可从生效日开始且不触发 GiST 排斥约束；`effective_date` 不晚于合同 `start_date` 时失败关闭；同一合同存在未撤销 `terminated` 事件时返回 `TERMINAL_CONTRACT_ALREADY_TERMINATED` 409，撤销后可重新终止。`terminate_terminal()` 在锁内执行双终止阻断与覆盖截止，幂等回放不重复截止；新增 `preview_terminal_termination()` / `commit_terminal_termination()`：预览返回逐单元覆盖截止、`deposit_unsettled` warning 和绑定操作者/范围/提议/合同版本/状态指纹的 10 分钟 token；提交按 token 重放提议，锁定合同后校验版本与状态指纹，漂移返回 `VERSION_CONFLICT` / `PREVIEW_STALE`，成功消费 token，同键重试经持久事件回放。新增 `POST /api/v1/terminal-contracts/{contract_id}/termination/preview` 与 `POST .../termination` 自注册端点，统一 `asset_ops:write`、服务端 Party scope 与 `Idempotency-Key`。真实 PostgreSQL 验证覆盖截止到 2026-06-29、后继合同从 2026-06-30 插入成功、起租 2026-06-29 仍被排斥约束拒绝、预览后状态变化提交返回 `state_changed`；同时把 `asset_ops` 补入权限种子守卫测试的 `later_backfill_resources`（交接前工作区引入该资源但守卫测试未同步，属既有缺口非本切片引入）。终止撤销、上游退出、续签命令、列表/详情和页面仍待实现，V1 保持进行中。
- 2026-10-25：终止撤销命令与端点完成红绿循环。撤销定位为纠错事实：请求显式携带 `target_event_id`，目标不存在、非本合同 `terminated` 事件或已被撤销返回 `TERMINATION_REVERSAL_TARGET_INVALID` 409；存在指向后继合同的 `renewed` 事件或其他合同在同单元 `[终止生效日, 合同 end_date]` 的覆盖返回 `TERMINATION_REVERSAL_BLOCKED` 409。提交在同一事务把被该终止截止的覆盖行（`effective_to` 等于生效日前一日的行）恢复到合同 `end_date`，恢复精确依赖「创建时 `effective_to` 恒等于 `end_date` 且除终止外无其他变更者」不变式并追加 `reversed` 事件；幂等回放复用全局键机制，改写内容返回 `IDEMPOTENCY_CONFLICT`。新增 `POST /api/v1/terminal-contracts/{contract_id}/termination-reversal` 自注册端点。真实 PostgreSQL 验证：终止→覆盖截止、撤销→覆盖恢复到 12-31 且事件链 `reversed_event_id` 正确、同键回放幂等、撤销后可再次终止并再次截止、插入后继合同后第二次撤销被阻断且覆盖不受影响。切片完成后双轴复核（Standards + Spec 并行 sub-agent）：采纳提交回放改为回执+活 token 双查并全量比对提议（同键不同提议 409 而非误报幂等）、命令方法补 `_require_actor_scope`、两处拒绝用例补 token 保留断言、`PREVIEW_STALE` 提示语泛化与 §5.6 提交字段措辞对齐实现；驳回命令骨架抽取、`unit_id` 键改名与测试守卫匹配方式（均为既有惯例）。上游退出、续签命令、列表/详情和页面仍待实现，V1 保持进行中。
- 2026-10-25：上游退出预览/提交/撤销完成红绿循环，与终端终止同口径：`effective_date` 为新状态首日（上游合同不再有效的第一天），退出提交在同一事务把仍延伸到生效日之后的 `UpstreamContractAssetUnit` 覆盖行截止到前一日；`effective_date` 不晚于 `start_date` 失败关闭；同一合同存在未撤销 `exited` 事件返回 `UPSTREAM_CONTRACT_ALREADY_EXITED` 409。退出前的有效终端合同阻断复用 `validate_upstream_exit` 纯规则：按退出生效日重放终端生命周期事件后仍为 `active`/`expiring` 的终端合同返回 `ACTIVE_TERMINAL_CONTRACTS_BLOCK_EXIT`，且 `list_terminal_by_upstream` 不做 Party 范围过滤——操作者看不到的有效终端合同同样阻断（失败关闭全局检查）。预览/提交复用终止的 token 协议（action=`upstream_exit`，状态指纹泛化为 `_lifecycle_state_fingerprint` 供两类合同共用，提交回放做回执+活 token 双查全量比对）；退出撤销与终止撤销同构（`EXIT_REVERSAL_TARGET_INVALID` / `EXIT_REVERSAL_BLOCKED`，恢复被截止覆盖行到 `end_date`）。新增三个自注册端点 `POST /api/v1/upstream-contracts/{id}/exit/preview`、`POST .../exit`、`POST .../exit-reversal`。真实 PostgreSQL 验证：有效终端在列时预览 409、先终止终端后退出成功且上游覆盖截止到 2026-06-29（终端覆盖独立保持 06-14）、同键回放幂等、撤销恢复到 12-31 且二次撤销被拒。两类续签命令、列表/详情和页面仍待实现，V1 保持进行中。
- 2026-10-25：上游与终端续签命令完成红绿循环，交接第三步全部落地。续签只创建后继不改旧合同：请求只提交后继已签条款（编号、期限、租金阶段、押金、扫描件及其录入会话 owner），各方/类型/模式/覆盖单元由前驱带出（终端可显式指定新上游，先续上游再续终端时必填，旧上游覆盖不到新起点由既有 `_resolve_upstream` 校验拒绝）；后继起租日必须晚于前驱全部覆盖截止日（`renewal_overlaps_predecessor`，含 NULL 覆盖视为违规），防后继与前驱覆盖重叠。同一合同存在未撤销 `renewed` 事件返回 `CONTRACT_ALREADY_RENEWED` 409。实现上给 `AssetContractCommandService.create_upstream/create_terminal` 加可选 `lifecycle_event` 事务缝：后继合同、逐单元覆盖、租金阶段、扫描件绑定、写回执与 `renewed` 事件（`successor_contract_id` 在合同 ID 生成后回填）同一事务提交；续签幂等复用写回执——同键回放直接走 create 回放路径，不重复追加事件也不重跑守卫。新增 `POST /api/v1/{upstream,terminal}-contracts/{id}/renewals` 自注册端点。真实 PostgreSQL 验证：上游续签建链（事件 `successor_contract_id` 正确、旧覆盖不动、后继覆盖 2027-01-01 起、扫描件绑定后继、回执落库）、同键回放幂等、第二后继 409、终端续签带出各方并指定新上游、不指定新上游时旧上游覆盖缺口失败且扫描件未被消费（事务回滚验证）。合同列表/详情和页面仍待实现，V1 保持进行中。
- 2026-10-25：上游与终端合同列表/详情端点完成红绿循环（交接第四步）。`AssetOperationsQueryService` 从 ORM 透传升级为聚合读：列表行按生命周期事件重放派生状态（终端重算 `upstream_missing`/`term_exceeds_upstream`/`scan_missing` 公共码 warning，上游后继生效后转 `historical`），详情聚合逐单元覆盖、租金阶段、版本链（前驱-当前-后继，经 `renewed_from_id` 与未撤销 `renewed` 事件双向拼接）、关联终端合同与全部事件；两类合同的事件/租金阶段/前驱后继均走新增范围化批量方法（`get_upstreams_by_ids`/`get_terminals_by_ids`/`list_lifecycle_events_by_contract_ids`/`list_rent_schedules`）防 N+1，`list_terminal_lifecycle_events` 收口为批量方法委托，`public_warning` 映射下沉到 projections 与创建服务共用。新增 `GET /api/v1/{upstream,terminal}-contracts`（`asset_ops:read`、分页、类型/产权方/模式/上游/搜索过滤）与 `GET .../{contract_id}` 详情端点；Detail schema 放宽继承自 Create 的 `asset_unit_ids`/`rent_schedules` 写入约束为读投影形态。真实 PostgreSQL 验证：终止后列表行 `ended` + 越界 warning、详情覆盖截止 06-29 与事件重放正确、上游详情 `expiring` + 关联终端 + 链 `[current]`。`rent_unpaid`/`deposit_unsettled` 等台账类筛选与到期区间/项目过滤待 V2 台账与后续切片（api-contract 行已对齐实际参数）。切片后双轴复核：采纳 `_business_today` 统一 `Asia/Shanghai`、后继探测按 as_of 重放合并（未来撤销不摘链、未来后继不触发 historical）、上游详情关联终端改范围化查询、每页单次取 today、删 `get_terminals_by_ids` 死方法、api-contract 补范围相对性口径。合同更新端点、资产单元列表/更新端点和页面仍待实现，V1 保持进行中。
- 2026-10-25：上游与终端合同更新端点（PATCH）完成红绿循环。S0 预定义的 Update schema 圈定可编辑字段：上游为 `name`/`end_date`/付款字段/押金/`oa_reference`，终端为绑上游/`end_date`/押金；编号、类型、各方、租期起点、扫描件、覆盖单元均不可改（PATCH 不提供即不改，不支持清空已选上游）。统一乐观锁：范围化行锁取合同，`expected_version` 漂移返回 `VERSION_CONFLICT`，`StaleDataError` 映射同码，ORM 版本由单次 flush 推进（修复初版 deposit 字段 setattr 落在 flush 后导致版本双跳）。`end_date` 变更在同一事务把仍等于旧 `end_date` 的覆盖行重定向到新值（复用「创建时 effective_to == end_date」不变式，生命周期截止行不动），`end_date` 早于 `start_date` 返回 `ASSET_CONTRACT_COVERAGE_INVALID`（reason=`end_date_before_start`），延长后与他合同重叠由 GiST 排斥约束兜底并映射为同一 409（reason=`coverage_overlap_after_extension`）、覆盖行随事务回滚。终端改绑上游复用 `_resolve_upstream` 抽出的 `_validate_upstream_link`（类型/出租方/在终端起始日覆盖三查），响应重算 `upstream_missing`/越界/缺扫描件 warning。新增 `PATCH /api/v1/{upstream,terminal}-contracts/{contract_id}` 自注册端点。真实 PostgreSQL 验证：版本冲突 409、期限倒挂 409、合法延长同步覆盖行且版本 +1、与后继重叠延长被约束拒绝且回滚。资产单元列表/更新端点和页面仍待实现，V1 保持进行中。
- 2026-10-25：资产单元列表/详情/更新/空置备注端点完成红绿循环（交接第四步服务端收官）。新增 `list_rented_unit_ids` 批量判定（活跃覆盖 join 合同 + 排除未撤销 terminated/renewed 生效合同，两步查询防自引用 alias 坑），`AssetOperationsQueryService._unit_detail` 统一派生 rental_status/rented_area/occupancy_rate（non_rentable=!is_operating 或 rentable==0 → rented=覆盖 → vacant）；列表支持 filter（本切片 all/non_rentable，其余待联动）并返回 `AssetUnitDetail` 行；详情附加当前有效终端合同 ID。新建 `AssetUnitCommandService`：PATCH 手工字段走乐观锁 + 可租≤建筑面积（新 422 `ASSET_UNIT_AREA_INVALID`）+ 在管期变化与覆盖冲突 `ASSET_UNIT_PERIOD_OVERLAP`；PUT vacancy-note 记录原因与预计起租。四个端点接 `asset_ops:read/write`。真实 PostgreSQL 验证：租出派生与占用率 1、详情终端合同、版本 409、面积 422、备注落库、在管期变化被覆盖阻断。生产前端页面仍待实现，V1 保持进行中。
- 2026-10-25：V1-3 前端第一纵向切片落地。新增 `/asset-operations/units` 路由（`asset_ops:read` 能力门控）与 `src/pages/AssetOperations/AssetUnitsPage`：列表（编号/名称/派生出租状态/可租面积/出租率）+ 常驻详情栏（地址、三类面积、在管起始、当前终端合同、改名保存带 `expected_version`）；选中行经 `useSearchParams` 同步到 URL，刷新恢复同一对象。`assetOperationsService` 封装 v5 端点并把后端 Decimal 字符串统一转 number。四态分离：PARTY_SCOPE_MISSING/ASSET_OPS_PERMISSION_DENIED 映射为范围警告而非空列表，错误/空态互不吞并。React Query 管服务器数据，编辑用受控表单（页面测试 5 项：加载渲染/403 警告/错误/空态/保存调用参数）。上游与终端合同列表页、录入页、1280/200%/320px 与 E2E 仍待后续批次，V1 保持进行中。
- 2026-10-25：首个 v5 提交点形成（整体双轴复核五项采纳后 117 文件入库），前端切片②落地——`/asset-operations/contracts/upstream` 与 `.../terminal` 两路由复用 `ContractListsPage` 骨架（共享 Shell：四态分离、按 `AssetOperationsError.code` 路由恢复动作、URL 选中行同步），表格行展示类型/模式/派生状态/期限与 warning Tag，常驻详情栏聚合条款、押金、覆盖单元、关联终端与版本链（前驱←当前→后继视觉编码）；`assetOperationsService` 扩展四端点与 normalize。页面测试 9 项全过、oxlint/tsc 通过。录入页（经 contract-intake-sessions 会话流）、生命周期操作交互、缩放走查与 E2E 仍待后续批次，V1 保持进行中。
- 2026-10-25：V1-3 录入向导页落地。新增 `/asset-operations/contracts/intake` 路由（`asset_ops:write` 门控）与 `ContractIntakePage` 三步会话流：类型选择+扫描件上传（FormData multipart）→候选核对（`EXTRACTION_UNAVAILABLE` 等警告降级、按合同类型切换字段集、不暴露类型/扫描件/续签前驱）→确认（前端生成 UUID 幂等键）或取消补偿；`assetOperationsService` 扩展会话五端点；`AuthzAction` 类型补 `write/report/archive/import`。页面测试 4 项。
- 2026-10-25：V1-3 生命周期操作页落地。新增 `/asset-operations/contracts/terminal/:contractId/actions` 与 `.../upstream/:contractId/actions`（`asset_ops:write` 门控）与 `LifecycleActionsPage`：终止/退出预览→确认两步（覆盖截止「现值→新值」核对表 + token + 合同版本 + 前端生成幂等键；`PREVIEW_STALE`/`VERSION_CONFLICT` 呈现「请重新预览」），撤销显式指向原事件，续签经录入会话上传新扫描件取 `document_id`+`session.id` 提交后继条款；列表详情栏加操作入口；`assetOperationsService` 扩展 8 个生命周期方法。页面测试 2 项。
- 2026-10-25：切片⑤静态加固与构建验证。四页表格统一 `scroll={{ x: 640 }}` 兜底 320px 重排（栅格 960px 断点已就位）；前端生产构建首次跑通。诚实边界：真实浏览器 200% 缩放/320px 视觉走查与 HTTP E2E 依赖 Playwright + dev 环境（Redis Docker，本会话 Docker 引擎未运行），以组件级加固+构建门禁代替、不宣称视觉走查通过。
- 2026-10-25：V1-4 一次性切换考古完成，执行底稿如下（本体留给具备完整上下文的会话执行，需配套全量回归）：**前端移除**——`menuConfig.tsx` 导航项 `/dashboard`（v4 工作台，默认登录页改跳 `/asset-operations/units`）、`/asset-files` 组（`/assets/list`、`/property-certificates`、`/system/templates`、`/contract-center/import`）、`/operations/ledger`、`/customer-center`；`AppRoutes.tsx` 对应条目（DASHBOARD/ASSET_ROUTES 全组/CONTRACT_CENTER/CONTRACT_GROUP/CUSTOMER/OPERATIONS.LEDGER/PROJECT/ANALYTICS 等）与对应 pages/services；`breadcrumb.ts` 对应项。**前端保留**——`/system/*`、profile、login、v5 路由族。**后端移除 include_router**：analytics、statistics、assets、occupancy、project、history、excel、contract_groups、ledger；对应 api 模块注册删除但 services/models 保留（删表是最后一步）。**保留**：auth、system 系列、party、authz、search、v5 自注册模块。**顺序依赖警示**：切换后到 v5 导入底稿执行前系统无业务数据可看；删除旧 API 前必须 `rg` 扫尾确认无前端调用残留。**回归底线**：切换后跑全套门禁 + 登录冒烟（菜单只剩系统管理/Party/资产运营）。
- 2026-10-26：V1-4 一次性切换执行完成（前端 9be1a5c4 + 后端本提交）。后端移除旧域 `include_router`（analytics/statistics/assets/occupancy/project/history/excel/contract_groups/ledger/custom_fields），保留 auth/system 系列/party/authz/search/v5 自注册；应用路由 186 条、旧业务前缀清零。测试损面清理：删除旧域 API/集成/e2e 测试约 30 个文件（analytics/ledger/occupancy/project/contract-groups/excel/assets 系），legacy 退役守卫限定 rent 专名（v5 合法复用 PaymentCycle/ContractType）、runtime-retired 守卫反转为断言旧路径不存在、init_rbac 种子补 `asset_ops` read/write、query-param-drift 契约收敛到保留域（parties）、exception-handling 探针从已下线 `/api/v1/assets/*` 改到 `/api/v1/asset-units` 且 503 契约按 v5 `internal_error` 缝隙改为 500 `INTERNAL_SERVER_ERROR`。全量后端 4402 passed；唯一残留为 `test_asset_unit_boundary` 2 例在特定全量排序下失败（既有跨文件污染，隔离/配对/定向均绿，非本切换引入，另开专项）。生产前端走查 18/18（登录落点 units、无旧菜单）。旧业务表与 src 内旧 services 的删除留待后续破坏性迁移；录入 HTTP E2E 待 Docker 修复。
- 2026-10-26：录入会话 HTTP E2E 完成（8/8）。Docker GUI（computer-use）显示引擎实际 running——CLI 挂起仅是管道问题，`zcgl` compose 栈的 redis 一直在线（16379 PONG）。后端带 Redis 起动后执行 `backend/scripts/dev_intake_e2e.py`：真实 PDF（pymupdf 生成）上传→ready_for_review→确认（唯一编号 + 不重叠期间 2027-07-02 起）→同键重放 `idempotent=true`→会话 confirmed→扫描件绑定→取消置 cancelled，8/8 通过。脚本内建重跑 hygiene（上轮事实先 preview→commit 终止）。三个 HTTP 契约事实在 E2E 中确认：confirm 需带 `contract_mode`/`rent_collector`（会话只注入类型/扫描件/前驱）、取消后会话保留为 cancelled 状态（删除的是附件与文件）、PDF 校验拒收手造字节流（须真实结构）。
- 2026-10-26：PR #95 合并前最终双轴复核收口。标准轴采纳两项 P1：走查密码改为 `V5_WALKTHROUGH_PASSWORD` 环境变量且缺失失败关闭；资产运营 Decimal 双向统一走共享转换入口，补齐 v5 字段并对非法响应失败关闭。规格轴采纳两项：资产单元、录入和生命周期表单全部改用 React Hook Form；REQ-UNT-001 不再提前标为“已有证据”，生产端空置备注、拆合操作/历史和合同时间轴明确留作合并后产品验收跟进。判断性 P2“合并终端/上游生命周期页面重复状态机”不影响本次正确性，按外科手术原则不在合并门禁中重构。
- 2026-10-27：PR #95 首轮修复 CI 暴露 V1-4 的 E2E 基线遗漏：前端生产路由已切到 v5，但 24 个 Playwright 用例仍访问旧工作台、旧 Asset、旧合同中心、经营台账和产权证，造成前端 E2E 确定性失败并让集成/API 一致性任务跳过。修复不恢复旧入口：认证落点、资产单元搜索、合同录入、移动端、主页面和用户可用性改验 `/asset-operations/*`；旧路径改为明确 404 守卫；无 v5 对应范围的旧域 E2E 与孤儿 Page Object 删除；组织范围用例改验 `asset-units` 的产权方隔离。CI 种子补 `asset_ops:read/write`、普通角色只读能力和最小 v5 事实。静态验证通过，等待新一轮 GitHub 前端 E2E 与被其解锁的集成/API 一致性任务真实执行。
