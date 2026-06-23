# ADR-0017: `asset_code` 按产权方编码段自动生成——身份锚、生成后冻结

**状态**: 🟡 已决策，待实施（2026-06-18；**段来源经 ADR-0018 修订**：撤专用 `asset_code_prefix` 字段，改用 owner `party_code` 派生段）
**决策日期**: 2026-06-18
**相关需求**: REQ-AST-001/002（资产域）、REQ-PTY-001（主体域）；依赖 ADR-0010（owner_party_id 内在必填）；段来源统一见 ADR-0018

---

## 背景

CONTEXT「运营方单一权威轴」词条与 `models/asset.py:115` 注释都把「`asset_code` 按产权方编码段生成、资产身份锚在产权方」当**既成事实**写下，但代码核对（2026-06-18）发现这是一句没兑现的声明：

- **无任何生成器**：grep `生成|generate_asset_code|按产权方|code_segment` 全仓零实现，「按产权方编码段生成」只活在注释与文档。
- `asset_code` 在 `models/asset.py` 为 `nullable=True`、`schemas/asset.py` 为 `Field(None)`——实为**用户选填**字段，仅「填了则全局唯一」。
- 真正的唯一/重名锚是 `asset_name`（`nullable=False, unique=True`）；§9 验收只验「创建资产重名拦截」（名称），从未涉及 asset_code。

grill 确认（yellowUp）：运营上**确实**需要「按产权方自动编资产号」（台账习惯按产权方编号管理，看号即知归属）。故不软化文档，而是把它登记为正式需求并定方案。

## 决策

**`asset_code` 改为按产权方编码段自动生成、作为资产身份锚（7 项参数）：**

1. **编码段来源（经 ADR-0018 修订为 A）**：段由 owner（产权方）的 **`party_code` 经共享 `_build_*_code_segment` 派生**（与 group_code/project_code 同一套机制，operator 用其 party_code、owner 用其 party_code）；**不靠名字/地区派生**（名字会变、会重、会撞），**也不新增专用 `asset_code_prefix` 字段**（原决策的独立前缀列已撤，避免两套段来源机制）。
2. **owner 缺 party_code 时**：owner Party 必须有可派生段的 `party_code`；无法派生段的 Party 不允许作为资产 owner，资产创建/导入时校验拦截。
3. **序号分配**：每段一个**原子计数器**（DB 行锁/序列），格式 `AST-{owner_seg}-{补零序号}`（6 位，对齐 domain-model line 53 `AST-[A-Z0-9]{4,12}-[0-9]{6}`）；叠加 `asset_code` 全局唯一约束兜底并发。
4. **生成时机**：**创建即生成**（含批量导入）；因 owner_party_id 创建时已强制必填（`asset_service.py:292`，ADR-0010），前缀此刻已知，落 `draft` 时即编号。
5. **可变性 + owner 更正**：生成后**冻结、系统生成、用户只读不可改**；owner_party_id 极少更正，**更正也不重编号**——编号是身份锚，重编会断历史引用与台账固化归属（ADR-0011）。
6. **字段收紧 + 存量**：生成后 `asset_code` 改 **NOT NULL**；迁移回填存量/legacy null 行。
7. **导入模板**：模板**不含** asset_code 列（系统生成）；用户若带该列则忽略。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| 软化为「选填业务编码」（原 grill 选项 B） | yellowUp 确认运营真需按产权方自动编号；软化会丢失真实需求 |
| 段从产权方名字/地区派生 | 名字会变会重、地区粒度撞号；身份锚必须稳定，段须取自稳定的 `party_code`（ADR-0018 统一） |
| 专用 `asset_code_prefix` 字段（本 ADR 原方案） | 与 group_code/project_code 的 `party_code` 派生段并存=两套机制、多一字段；ADR-0018 选 A 统一为 owner `party_code` 派生段（除非产权方需自定义区别于 party_code 的资产前缀，本次不需要） |
| 用户可手填/覆盖 asset_code | 破坏编码段完整性与序号连续性，唯一性靠人工兜不住 |
| owner 更正时重编号以同步前缀 | 重编断历史引用/台账固化归属（ADR-0011），得不偿失；owner 更正本就罕见 |
| 全局单一序列（不分产权方段） | 丢失「看号即知归属」的运营价值，等于没按产权方编号 |

## 关键冻结决策

1. **段来自 owner `party_code` 派生（共享 `_build_*_code_segment`），非名字派生、非专用前缀字段**（ADR-0018 统一）。
2. **asset_code 生成后冻结、系统生成只读**，owner 更正不重编号。
3. **身份锚分层**：owner_party_id 是权属事实锚（ADR-0010），asset_code 是对外编号身份锚；二者都不随项目 re-org 变。

## 影响

待实施的工程项：

- **后端（段来源经 ADR-0018 修订）**：owner `party_code` 经共享 `_build_*_code_segment` 派生段（**不加 `asset_code_prefix` 字段**）；资产创建/导入处加「owner 有可派生段的 party_code」校验与每段原子序号分配器；`asset_code` 生成逻辑（`AST-{owner_seg}-{6位}`）接入 `asset_service` 创建/导入路径；schema 改 `asset_code` 为系统生成只读；model 改 `nullable=False`；Alembic 迁移回填存量 asset_code、收紧 NOT NULL；补并发分配/唯一性/导入忽略列测试。
- **前置缺口（2026-06-18 grill 修正）**：本 ADR 原写「创建/导入即生成（owner 创建已必填故前缀已知）」——该假设在**导入路径上当前不成立**：导入行级必填集 `validators.py:REQUIRED_FIELDS` 不含 owner，ownership 仅在提供时校验，且导入 create 直接调 `asset_crud.create_with_history_async` **绕过** `asset_service` 的 owner 必填校验（`asset_service.py:292`），可建无产权方资产（违反 ADR-0010、卡死本 ADR 编号生成）。故 codegen 前必须先补：导入强制 owner（无法解析到产权方 Party 的行直接拒绝）、解析到 `owner_party_id`、导入 create 走与手动创建共享的 owner 必填校验（不绕 crud）。见 ADR-0010 影响段「导入旁路」。
- **CONTEXT.md**：「运营方单一权威轴」词条把「asset_code 按产权方编码段生成」从既成事实改为「已决策待实施见 ADR-0017」（本次随手落）。
- **PRD**：REQ-AST-001/002 可不改主表述（属实现细节），如需可补一行指向 ADR-0017。
- **traceability**：REQ-AST-001/002 记代码收口缺口（开发中）。
- **CHANGELOG.md**：记录本次变更（本次随手落）。

## 参考

- `CONTEXT.md`：`运营方单一权威轴（随项目派生）`、`产权方` 词条
- `models/asset.py`（`asset_code`）、`services/asset/asset_service.py`（创建/导入/owner 校验）
- 相关簇：[ADR-0010](./ADR-0010-manager-derived-owner-intrinsic.md)（owner_party_id 内在必填——前缀来源前提）、[ADR-0011](./ADR-0011-ledger-frozen-attribution.md)（台账固化归属——asset_code 冻结的下游约束）
