# ADR-0018: project_code 按运营方编码段生成；业务编码段统一由 party_code 派生

**状态**: 🟡 已决策，待实施（2026-06-18）
**决策日期**: 2026-06-18
**相关需求**: REQ-PRJ-001（项目绑定运营管理方）、REQ-AST-001（资产主数据）、REQ-RNT-001（合同关系）；修订 ADR-0017（asset_code 段来源统一）

---

## 背景

grill 复核 `asset_code`（ADR-0017）时核三类业务编码的实现，发现 domain-model §2「编码规则/格式」是一套**对不上代码的理想化声明**：

| 编码 | 实际实现 | 与 domain-model 声明对比 |
|------|----------|--------------------------|
| `asset_code` | **零生成器**（`nullable`） | 「按产权方编码段」未实现（ADR-0017 待实施） |
| `project_code` | `generate_project_code`：`PRJ-{YYYYMM}-{NNNNNN}`，**段=年月** | 声明「**按运营方编码段**」**factually 错**——实际无运营方段，纯按年月 |
| `group_code` | `generate_group_code`：`GRP-{运营方段}-{YYYYMM}-{SEQ4}`，段取 `_build_operator_code_segment(operator_party_code)`、序号按运营方+月计 | 声明「按经营主责方编码段」大致对，但格式（4 段、4 位序、按运营方+月）不符 line 19「统一 `<TYPE>-<SEGMENT>-<SERIAL>` 6 位单调」 |

即：line 18「project_code 按运营方编码段」纯属虚构，line 19「统一 6 位格式」三码无一完全符合；且 `asset_code`(ADR-0017) 与 `group_code` 的**段来源机制不统一**——前者拟立专用 `Party.asset_code_prefix` 字段，后者用 `party_code` 派生段。yellowUp 确认 project_code **要**按运营方编段，并选 **A（统一段来源）**。

## 决策

### 1. project_code 按运营方编码段生成（5 项参数）

1. **段来源**：复用 group_code 现成的 `_build_operator_code_segment(operator_party_code)`——项目创建必绑运营方（REQ-PRJ-001），运营方已有 `party_code`，**不新建字段**。
2. **格式**：`PRJ-{运营方段}-{YYYYMM}-{SEQ4}`，序号按运营方+月计——对齐 group_code 家族（同为「运营方键」编码，内部一致）；替换现有 `PRJ-{YYYYMM}-{NNNNNN}` 里的「年月段」为「运营方段」。
3. **生成时机**：创建项目即生成（项目创建已强制绑运营方，段已知）。
4. **冻结/运营方变更**：生成后冻结只读；项目运营方若变更**不重编 project_code**（编码是标识锚，重编断引用）。
5. **唯一性**：保持全局唯一（`project_crud.get_by_code` 已有）。

### 2. 业务编码段统一由 party_code 派生（A，修订 ADR-0017）

三类业务编码的「段」**统一由相关主体的 `party_code` 经共享 `_build_*_code_segment` 派生**：asset 用 owner、project 与 group 用 operator。

- **撤销 ADR-0017 的专用 `Party.asset_code_prefix` 字段**：asset_code 段改用 **owner 的 `party_code` 派生段**（与 group_code/project_code 同一套机制），不再新增独立前缀列。ADR-0017 其余决策（生成后冻结、系统生成只读、owner 更正不重编号、`asset_code` NOT NULL、导入模板不含该列、原子序号）不变。
- 三码段来源一套逻辑、一个机制，符合减法。

### 实际格式（更正 domain-model line 18-19 的虚构统一声明）

| 编码 | 段来源 | 目标格式 |
|------|--------|----------|
| `asset_code` | owner `party_code` 段 | `AST-{owner_seg}-{NNNNNN}`（6 位序，按段单调；ADR-0017） |
| `project_code` | operator `party_code` 段 | `PRJ-{operator_seg}-{YYYYMM}-{SEQ4}`（本 ADR） |
| `group_code` | operator `party_code` 段 | `GRP-{operator_seg}-{YYYYMM}-{SEQ4}`（已实现） |

**不强求三码格式完全统一**：运营方键编码（project/group）带 `YYYYMM` + 4 位月序，资产编码（owner 键）无月、6 位段序。统一的是**段来源机制**（party_code 派生），不是字面格式。

## 被否决的方案

| 方案 | 否决原因 |
|------|----------|
| (B) asset_code 保留专用 `asset_code_prefix`、operator 用 party_code 段 | 两套段来源机制并存，多一字段、多一套逻辑；除非产权方需自定义区别于 party_code 的资产前缀，否则违反减法。yellowUp 选 A |
| project_code 维持按年月段 | domain-model 已声明按运营方、且运营方是项目主轴；年月段无法表达「这是谁运营的项目」，与 group_code 不一致 |
| project_code 另立专用 operator 前缀字段 | group_code 已用 `party_code` 派生段，再造字段是重复；复用即可 |
| 强行三码字面格式完全统一（都去掉月/都加月） | 改动面大、收益低；段来源统一已足够，格式按键角色分两族可接受 |

## 关键冻结决策

1. **project_code 按运营方 `party_code` 派生段生成**，格式 `PRJ-{operator_seg}-{YYYYMM}-{SEQ4}`，生成后冻结、运营方变更不重编。
2. **三类业务编码段统一由 party_code 派生**（owner→asset，operator→project/group），**撤 ADR-0017 的 `asset_code_prefix` 字段**。
3. **段来源统一、字面格式按键角色分两族**（operator 码带月、asset 码不带月），不强求字面统一。

## 影响

待实施的工程项：

- **后端（project_code）**：`generate_project_code` 改按 `_build_operator_code_segment(operator_party_code)` 生成 `PRJ-{seg}-{YYYYMM}-{SEQ4}`，序号按运营方+月计；项目创建处传入运营方 `party_code`；存量 `PRJ-{YYYYMM}-{NNNNNN}` 历史编码冻结不回改（标识锚不重编），仅新建按新格式。
- **后端（统一段，修订 ADR-0017）**：asset_code 段改用 owner `party_code` 派生段（共享 `_build_*_code_segment`），**不新增 `Party.asset_code_prefix` 字段**；ADR-0017 其余（冻结、只读、NOT NULL、原子序号、导入模板不含）不变。
- **domain-model**：§2 line 18-19 改为按实际段来源（party_code 派生）与两族格式表述，删除「project_code 按运营方」原虚构与「统一 6 位单调」误述；line 53 `asset_code` 格式保持 `AST-{SEGMENT}-{6位}`（段来自 owner party_code）。
- **CONTEXT.md**：「运营方单一权威轴」词条把 asset_code 段来源从 `asset_code_prefix` 改为 owner `party_code` 派生段。
- **traceability**：REQ-PRJ-001 记 project_code 收口缺口；REQ-AST-001 段来源更正。
- **CHANGELOG.md**：记录本次变更。

## 参考

- `services/project/service.py`（`generate_project_code`）、`services/contract/contract_group_service.py`（`generate_group_code` / `_build_operator_code_segment`）、`models/asset.py`（`asset_code`）
- domain-model §2 编码规则/格式、§3 line 53
- 相关簇：[ADR-0017](./ADR-0017-asset-code-owner-segment-generation.md)（asset_code 按 owner 编段——本 ADR 统一其段来源、撤专用 prefix）、[ADR-0010](./ADR-0010-manager-derived-owner-intrinsic.md)（运营方权威轴在项目——project_code 段来源前提）
