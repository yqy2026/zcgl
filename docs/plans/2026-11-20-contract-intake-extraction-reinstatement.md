# 合同录入会话接入扫描件解析（B 方案 · 面向表一物业台账填报 · DeepSeek OCR）

## Status

📋 待评审（2026-11-20 编写；目标已由用户确认为「支撑表一物业台账填报」，非通用合同补录）

## 1. 背景与结论

`flow-contract-intake.md` 主流程第 3 步把扫描件解析设计为**可选辅助步骤**，明确「解析失败/超时 → 可重试或完全手工补录继续」。但 v5 重建后该能力未迁移：`ContractIntakeSessionService.create` 固定写入 `candidates={}`、`errors=["extraction_unavailable"]`，`REQ-DOC-001` 状态为「已移除」。

**本方案恢复这条链路，并把它对准一个具体交付目标：让表一物业台账的「租赁合同信息」6 列不必再从 PDF 手工抄录。**

### 1.1 目标对齐：表一填报

表一「表一-物业台账」共 44 列，按数据来源分组后，只有「租赁合同信息」这一组（6 列）必须来自租约本身：

| 表一列 | 填报说明口径（`填报说明` 第 33–38 行） |
|---|---|
| 承租方 | 现承租人名称，**与租约一致** |
| 合同出租面积(㎡) | 该租约约定的出租面积，**单价计算的分母** |
| 租期起 / 租期止 | 租约起止日期，**按合同填写** |
| 合同月租金(元) | 该租约月度租金总额（**不含物业费等代收费用**）；填写要求「**免租期内按合同租金照填**，另填免租期截止日」→ 即取**减免前首月租金**，不因免租/折扣而调减 |
| 免租期截止日 | 当前免租优惠的截止日期 |

**关键实测结论（改变了方案范围）：**

| 事实 | 实测数据 |
|---|---|
| 表一数据行粒度 = 资产单元粒度 | 94 行 = **93 条数据 + 1 条合计**，与已导入的 93 个资产单元 1:1 对应 |
| 「合同出租面积」实际等于该行「可租赁面积」 | **67 行完全相等**（差值 <0.01）、**26 行为空**（空置行未填）、**0 行**出现「W 有值而 J 为空」 |
| 同一物业按不同承租方分行 | 42 个物业名称、**16 个物业占 68 行**（如宝业北街 54-72 号拆 11 行） |

**推论：「合同出租面积」不需要从合同识别，直接取该行资产单元的 `rentable_area` 即可。** 真正需要从合同读出的只有 **5 项**：承租方、租期起、租期止、合同月租金、免租期截止日。

### 1.2 能力预期（诚实边界）

| 分类 | 字段 | 本方案后 |
|---|---|---|
| 可直接预填 | 租期起、租期止 | ✅ 规则正则稳定 |
| 预填但需人工核 | 合同月租金（**减免前首月**） | ⚠️ 三个陷阱：①合同常写「租金 X + 管理费 Y」会带入代收费用；②常以**年租金**表述，需 ÷12；③不能填 `actual`（减免后），必须填 `base`（减免前） |
| 预填但需人工选 | 承租方 | ⚠️ 抽名称做 **PartyPicker 推荐**，必须人工点选确认（§5.4 禁止自动绑定） |
| 预填但需人工换算 | 免租期截止日 | ⚠️ 系统存 `free_rent_months`（月数）而非日期，需换算 |
| 不必识别 | 合同出租面积 | ✅ 取单元 `rentable_area` |
| 仍然人工 | 其余 38 列 | 档案、公式、收缴、风险、管理类 |

**这是「5 项少抄、其中 3 项仍需核对」，不是「表一自动生成」。** 表一的应收/实收/欠租/坪效等派生列不在本方案射程内。

### 1.3 结论

可行。**OCR 环节由本地 RapidOCR 改为 DeepSeek OCR API（`POST /v1/tools/ocr`）**，取舍见 §4.7：免去本地模型部署与 SHA256 预检、单次可吃整份 PDF（≤1000 页 / ≤100 MiB）、直接返回逐页原始文本、成本 1.5 元/千页。规则候选、候选复核服务、会话仓储、确认链路保持不变。

实际新增：

1. `OcrProvider` 抽象 + 配置开关（`DOCUMENT_OCR_PROVIDER=deepseek|local`），本地管线保留为离线与降级路径；
2. `DeepSeekOcrProvider`（约 90 行）：multipart 上传、逐页响应解析、错误码映射；
3. `ContractIntakeSessionService` 增加解析编排（约 80 行）；
4. `ExtractionSessionRepository.update_candidates`（约 20 行）；
5. **规则白名单扩 2 项**（`tenant_name` / `rent_free_until`）+ 1 项校验值（`leased_area`），见 §4.3.5；
6. `ContractIntakePage` 候选回填与证据展示（约 140 行）。

**第一优先合同类型改为 `terminal`（终端租赁）**，因为表一填的是「五羊作为出租方、租给终端租户」的租约（实测承租方为名创优品、佐登堡家具、个人房世超等）。上游承租合同不产出台一任何一列。

## 2. 现状事实（代码与数据证据）

### 2.1 v5 未解析的事实

| 事实 | 证据 |
|---|---|
| 会话固定不解析 | `contract_intake_service.py:181-199`，`candidates={}`、`errors=["extraction_unavailable"]` 硬编码 |
| 该错误码降级为 warning | 同上 `:392-399` |
| 状态机已预留异步态 | `schemas/asset_operations.py:690-699` 含 `extracting`，实现从未进入 |
| 前端完全未用候选 | `ContractIntakePage.tsx` 全文无 `candidate_fields`，仅渲染 `warnings`（:317） |
| 页文本管线可用 | `page_text_pipeline.py:70-73`，`min_pdf_text_chars=20`、`dpi=200`、`page=10s`、`document=180s` |
| 规则候选可用 | `candidate_review.py:113` merge、`:153` build |
| 合同字段白名单 7 个 | 同上 `:91-99`，含 `payment_cycle`（LLM 那 6 个不含此项） |
| 本地 OCR 管线可用（降级路径） | 实测 venv：`rapidocr 3.9.1` / `onnxruntime 1.20.1` / `pymupdf 1.24.14`，与 `document_processing_runtime.py:16-20` 精确匹配。本方案默认改走 DeepSeek OCR，此路径保留为离线与故障降级，不删除 |
| 仓储无候选回写能力 | `extraction_sessions.py:41-127`，仅 create/get/transition/delete |

### 2.2 表一与系统数据模型的对应缺口

| 表一列 | 系统落点 | 状态 |
|---|---|---|
| 承租方 | `terminal_contracts.tenant_party_id`（`schemas.py:427`） | ✅ 有，需人工选择实体 |
| 租期起 / 租期止 | `start_date` / `end_date`（`:430-431`） | ✅ 有 |
| 合同月租金（减免前首月） | `contract_rent_schedules.base_monthly_rent`（`schemas.py:265`、`models:398`） | ✅ 有；**必须取 `base` 不取 `actual`**。`actual` 是减免后，免租期会变成 0 或被折扣调低，填进表一会把该行租金算小 |
| 免租期截止日 | `contract_rent_schedules.free_rent_months`（`:267`、`models/asset_contract.py:405`） | ⚠️ **存月数不存日期**，见 §6.2 |
| 合同出租面积 | 无合同级字段；`terminal_contract_asset_units`（`models:312-330`）只有 contract_id / asset_unit_id / 生效区间 | ✅ **不需要**，取 `asset_units.rentable_area`（§1.1 实测 67/67 相等） |

结论：**6 列中 5 列有落点，1 列不必落点。无需数据模型迁移。**

### 2.3 表一的分行规则（影响报表能否对得上）

`填报说明` 第 8 行：「一个物业（或同一物业下不同承租方/不同使用状态的部分）填一行」。

即表一分行键 = **（物业名称, 承租方, 使用状态）**，不是「合同」也不是「资产单元」。后果：

- 一份终端合同覆盖跨物业的多个单元 → 表一须拆成多行；
- 同一物业同一承租方租了多个单元 → 表一合并成一行；
- 空置单元 → 单独一行，承租方填「-」。

这条规则属报表生成器职责，**不在本方案范围**，但方案产出的数据必须能支撑它（每份终端合同必须落到明确的 `asset_unit_ids`，且 `tenant_party_id` 必填）。

## 3. 目标与非目标

### 3.1 目标

1. 上传已签**终端租赁合同**扫描件后，完成页文本抽取与规则候选并写入会话 `candidate_fields`；文本抽取默认调用 DeepSeek OCR API，可按配置回落本地管线。
2. 候选覆盖表一所需的 5 项（承租方名称、租期起、租期止、月租金、免租期截止日），前端逐字段展示值 + 页码 + 原文片段。
3. 承租方名称用于 **PartyPicker 推荐**，不给「自动选中」；主体审核流已于 2026-11-20 停用（建档即 `approved`），新增终端租户不再需要提审/审核。
4. 任何解析异常都**不阻断手工补录**，会话必须落到 `ready_for_review`。
5. 保持 `api-contract.md` §5.4 全部红线：不自动建/绑 Party 与资产、会话按操作者隔离、确认强制幂等键、扫描件不被二次消费。

### 3.2 非目标

| 不做 | 理由 |
|---|---|
| 自动创建或绑定 Party / 资产单元 | §5.4 明文禁止；主体虽已建档即生效，仍须由操作员显式选择 |
| 自动生成租金阶段（递增序列） | 解析只出首期月租，递增条款需人工判定 |
| 生成表一报表（应收/实收/欠租/坪效） | 属报表与收缴模块，非解析能力 |
| 改动数据模型（加合同级面积/免租日期字段） | 实测无必要（§1.1、§2.2）；如后续口径变化再单独立项 |
| 上游承租合同优先 | 上游不产出台一任何一列；保留支持但不作验收目标 |
| 引入对话式视觉大模型（VLM）做字段问答 | OCR 已由 DeepSeek OCR 专用接口覆盖；再叠一层 VLM 只增加外发面与成本，对 5 个正则可覆盖的字段无收益 |

## 4. 方案设计

### 4.1 总体链路

```
POST /contract-intake-sessions (multipart: file + contract_type=terminal)
  ├─ 落盘 + attachment 行（沿用现有逻辑）
  ├─ 会话 status = "extracting"，candidates = {}
  └─ BackgroundTasks 派发 _extract(session_id, storage_path, contract_type)
        │
        ├─ asyncio.to_thread:
        │    OcrProvider.extract(path)                ← DOCUMENT_OCR_PROVIDER
        │      ├ deepseek: POST /v1/tools/ocr
        │      │           multipart: file + purpose=text_recognition
        │      │           → pages[].text（逐页模型原始输出）
        │      └ local   : OrderedPageTextPipeline（PyMuPDF + RapidOCR）
        │    → list[PageText]（页码 + 行 + text_source，两条路径统一结构）
        │    CandidateReviewService.build_contract_candidates(pages)
        │    [可选] DeepSeekTextEnricher.enrich(...) → merge
        │    按 contract_type 裁剪（terminal 保留全部 5 项）
        │
        └─ repository.update_candidates(...)
           transition(session_id, "extracting", "ready_for_review")
                 │
GET /contract-intake-sessions/{id}  ← 前端轮询，拿 candidate_fields
                 │
POST /{id}/confirm-terminal        ← 不变；承租方/单元由人工选
```

**两条 OCR 路径必须收敛到同一个 `PageText` 结构**（`page_number` / `text_lines` / `text_source`）。这是复用下游 `CandidateReviewService`、证据引用校验与前端出处展示的前提；否则规则层要分叉，维护成本翻倍。

### 4.2 关键决策：同步改异步

**必须异步。** DeepSeek OCR 单次总时长上限 **180 秒**（从开始上传算起，含上传、识别与返回），若叠加 LLM 文本增强（每批 120s × 最多 3 批）最坏 **540 秒**，远超浏览器与反代的 30–60s 超时。保持同步只会让用户看到超时、服务端仍在写一个无人认领的会话。

另有一条硬约束：上传须在 **120 秒内**完成且中途停顿不超过 30 秒，否则返回 `408`。因此不能在请求线程里「边传边等」，必须在后台任务中完成整个上传—识别周期。

实现选择 **FastAPI `BackgroundTasks` + `asyncio.to_thread`**：项目已有先例（`documents/excel/export_ops.py:166`、`system/notifications.py:274`），无新增基础设施。代价需明示：**进程重启会丢失正在解析的会话**（`extracting` 态残留至 Redis TTL 3600s 到期）。因解析是一次性辅助，影响可接受；前端轮询超时后提示重新上传。

### 4.3 后端改动点

#### 4.3.1 `ExtractionSessionRepository.update_candidates`

现有仓储只有 `create`/`get`/`transition`/`delete_*`，无法回写候选。新增：

```python
def update_candidates(
    self, session_id: str, *,
    candidates: Mapping[str, object],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """回写候选与错误码，不改变会话状态。"""
```

要点：读-改-写走 Redis `get` → `set(ex=剩余TTL)`，**不刷新 TTL**；会话不存在抛 `ExtractionSessionStateError("session_expired")`，调用方直接放弃；`errors=None` 表示解析成功（清掉 `extraction_unavailable`）。

#### 4.3.2 `ContractIntakeSessionService`

`create` 签名不变，内部改为写入 `candidates={}`、`errors=None`、状态 `extracting`；新增构造参数 `extractor: ContractIntakeExtractor | None = None`（为 `None` 时行为与现状完全一致，保证灰度可控）。

新增 `start_extraction(session_id, *, storage_path, contract_type)` 作为 BackgroundTasks 入口。

**失败降级矩阵：**

| 情形 | 错误码 | 会话状态 | 用户可见 |
|---|---|---|---|
| `DOCUMENT_OCR_ENABLED=false` | `extraction_disabled` | `ready_for_review` | warning，全手填 |
| `DEEPSEEK_API_KEY` 缺失 / provider 配置非法 | `extraction_unavailable` | `ready_for_review` | warning，手工补录 |
| `local` 模式下依赖缺失 / 模型哈希不符 | `extraction_unavailable` | `ready_for_review` | warning，手工补录 |
| 非 PDF / 超 50 页 / 超 50MiB（系统侧限流，严于服务端） | `extraction_unsupported` | `ready_for_review` | warning |
| 402 余额不足 | `ocr_insufficient_balance` | `ready_for_review` | 「OCR 服务余额不足，请联系管理员」，不重试 |
| 408 上传过慢 / 504 提交超时 | `ocr_upload_timeout` | `ready_for_review` | warning，可重试 |
| 413 文件过大 | `extraction_unsupported` | `ready_for_review` | warning |
| 429 并发超限 | `ocr_rate_limited` | `ready_for_review` | warning，可稍后重试 |
| 500 / 503 服务内部错误或繁忙 | `ocr_service_unavailable` | `ready_for_review` | 退避重试 2 次后 warning |
| HTTP 200 但 body 含 `error`（识别中途失败） | `ocr_failed` | `ready_for_review` | warning，取 `error.message` 摘要 |
| 某页 `finish_reason=length` | `ocr_page_truncated` | `ready_for_review` | 该页不参与抽取，其余页正常 |
| 规则候选为空 | 无错误码 | `ready_for_review` | 无 warning，全手填 |
| LLM 关闭 | 无错误码 | `ready_for_review` | 仅规则候选 |
| LLM 调用失败 | `llm_unavailable` | `ready_for_review` | warning，保留规则候选 |
| 会话 TTL 到期 | 放弃本次回写 | — | 前端 404，提示重传 |

**不变式：任何解析分支都不得让会话停在 `extracting` 或 `failed`。** 必须由参数化测试守住。

#### 4.3.3 API 层

`contract_intake_sessions.py`：`POST` 注入 `BackgroundTasks`，`create` 成功后 `add_task(service.start_extraction, ...)`；HTTP 状态码保持 200（不改 202，避免破坏现有前端与测试）；`GET` 与 `confirm-terminal` 零改动。

#### 4.3.4 确认时的并发闸门

操作员可能在解析未完成时点确认。策略：**不阻塞确认**（用户已有完整表单），但会话处于 `extracting` 时确认端点返回 409 `SESSION_EXTRACTION_IN_PROGRESS`，前端提示「正在识别，可稍候或跳过」。新增 `POST /{id}/skip-extraction`：仅允许 `extracting → ready_for_review`，保留已有候选，重复调用幂等。

#### 4.3.5 规则白名单扩展（本方案新增，表一导向）

现白名单 7 项（`candidate_review.py:91-99`）不足以支撑表一。新增 2 项候选 + 1 项校验值：

| 新增键 | 类型 | 抽取规则要点 | 对应表一列 |
|---|---|---|---|
| `tenant_name` | str | 标签命中「承租方/乙方/承租人」，取冒号后至行末，剔除括号内统一社会信用代码 | 承租方 |
| `rent_free_until` | date | 标签「免租期/装修期/免租」；支持两种形态：①直接给出「至 YYYY-MM-DD」；②「自 X 起免租 N 个月」→ 换算为 X + N 月 − 1 天 | 免租期截止日 |
| `leased_area` | Decimal | 标签「出租面积/租赁面积/计租面积」，**不取**「建筑面积/套内面积」；单位须为 ㎡ 或 平方米 | 仅作交叉校验（与单元 `rentable_area` 比对，差异 >5% 标记待核） |

红线遵守：三者都只是候选。`tenant_name` 只驱动前端 PartyPicker 的搜索预填，**不写入任何 Party ID**；`leased_area` 只做校验提示，不落库。

**`monthly_rent` 必须按「减免前首月租金」口径清洗。** 这是表一最容易填错的一列（填报说明第 36 行：免租期内按合同租金照填）。三条规则：

| 规则 | 触发 | 处理 |
|---|---|---|
| R1 剔除代收费用 | 同页命中「管理费 / 物业费 / 服务费 / 综合管理费 / 综合费」 | 只保留租金部分；`confidence_tier` 降 `medium`，前端提示「可能含代收费用」 |
| R2 年/季租金折月 | 命中「年租金 / 年度租金 / 租金总额」且金额明显大于月度量级 | ÷12（季租 ÷3），`value` 写折算后月额，`derivation` 记「年租金 XXX ÷ 12」 |
| R3 只取首阶段 | 合同含「第二年起递增 / 每两年递增 N%」等条款 | 只取**首个租金阶段**的减免前金额，不取均值、不取末期；递增条款交由人工在 RentScheduleEditor 补后续阶段 |

对 `management_agreement` 仍剔除 `monthly_rent` 与 `rent_free_until`（委托管理协议无租金阶段，§5.5 明文）。

#### 4.3.6 OCR Provider 抽象与 DeepSeek 接入

```python
class OcrProvider(Protocol):
    def extract(
        self, path: Path, *, document_type: Literal["contract"]
    ) -> list[PageText]: ...
```

| 实现 | 触发配置 | 行为 |
|---|---|---|
| `DeepSeekOcrProvider`（默认） | `DOCUMENT_OCR_PROVIDER=deepseek` | `POST {DEEPSEEK_BASE_URL}/tools/ocr`，multipart 仅 `file` + `purpose`，把 `pages[].text` 按行切为 `PageText` |
| `LocalRapidOcrProvider` | `=local` | 复用现有 `OrderedPageTextPipeline`（PyMuPDF 取文本，单页 <20 字转 RapidOCR） |

DeepSeek 调用要点：

| 项 | 取值 | 依据 |
|---|---|---|
| 端点 | `POST /v1/tools/ocr` | 官方 OCR 指南 |
| 认证 | `Authorization: Bearer <DEEPSEEK_API_KEY>` | 沿用现有 Key |
| 表单字段 | 仅 `file`（需带文件名）+ `purpose`；**传其他字段一律 400** | 同上 |
| `purpose` | `text_recognition` | `rich_layout_recognition` 输出含 `<｜ref｜>`/`<｜box｜>` 与归一化坐标，对规则抽取是噪音；若后续要做「框选定位」再切 |
| 响应解析 | 响应体前置大量换行用于保活，**整体可直接按 JSON 解析**；`pages[].index` 从 0 开始，需 +1 对齐会话页码 | 同上 |
| 截断处理 | `pages[].finish_reason == "length"` 表示该页输出不完整 → 该页 `text_source=None`，记 `ocr_page_truncated` warning，**不参与字段抽取** | 避免用半页文本抽租金 |
| 客户端超时 | `httpx.Timeout(connect=15, read=None, write=120, pool=10)` + 外层 200s 硬中止 | 服务端 180s 兜底，客户端略宽以免误杀 |
| 错误识别 | 状态码 200 后仍可能是 `{"error": {...}}` 对象，须先判 `error` 键 | 官方：识别开始后状态码已是 200 |

成本：1.5 元/1000 页（按成功页数计）。本批 64 份合同约 1000 页量级，全量重跑约 **1.5 元**，可忽略；仍在文档备案，避免日后无法解释外部支出。

并发：账号级最多 15 个同时识别。本方案用 `asyncio.Semaphore(1)` 串行，不会触顶，也避免与人工录入争抢带宽。

### 4.4 候选数据契约

`ContractIntakeSessionResponse.candidate_fields` 现为 `dict[str, object]`（`schemas.py:700`），**不改 schema**，内部约定：

```json
{
  "tenant_name": {
    "value": "名创优品（广州）有限责任公司",
    "extractor": "rule",
    "confidence_tier": "high",
    "evidence": { "page_number": 1, "text": "承租方（乙方）：名创优品（广州）有限责任公司" },
    "party_match_hint": { "query": "名创优品", "candidates": 2 }
  },
  "monthly_rent": {
    "value": "44900.00",
    "extractor": "rule",
    "confidence_tier": "high",
    "evidence": { "page_number": 2, "text": "首年租金总额人民币伍拾叁万捌仟捌佰元整" },
    "derivation": "年租金 538,800 ÷ 12",
    "basis": "base_monthly_rent"
  },
  "rent_free_until": {
    "value": "2025-11-07",
    "extractor": "rule",
    "confidence_tier": "medium",
    "evidence": { "page_number": 2, "text": "自交付之日起免租 12 个月" },
    "derivation": "2024-11-08 + 12 月 - 1 天"
  }
}
```

约定：

- `value` 一律字符串（date 用 ISO，金额用十进制字符串），前端按字段类型转换，避免浮点误差；
- 同 `field_key` 多值时按 `confidence_tier` 取最高，同档取首次；其余进 `alternatives[]`（最多 2 条）；
- `evidence.text` 截断 240 字符（沿用 `deepseek_text_enrichment.py:226`）；
- `party_match_hint` 只含查询串与命中数，**不含 Party ID**（防止前端误用为绑定）；
- `derivation` 仅在使用换算规则时出现（R2 折月、免租期换算），让操作员看得见推算过程；
- `basis` 仅 `monthly_rent` 携带，固定 `base_monthly_rent`，**显式声明该值为减免前金额**，防止前端误取 `actual`（D12）；
- **页码与证据确认后不入库**（归档方案红线）。

### 4.5 前端改动点

`ContractIntakePage.tsx`（446 行）四处改动：

1. **轮询**：`create` 返回 `status === 'extracting'` 时启动 2s 间隔轮询，上限 90 次（180s），状态离开 `extracting` 或组件卸载即停。
2. **候选回填 + 推荐**：`tenant_name` 只写入 PartyPicker 的初始搜索词并展开候选列表（**不 setValue 到 `tenantPartyId`**）；`startDate`/`endDate`/`rentFreeUntil` 直接填；`monthlyRent` 填入 `rentSchedules[0]`。**已有用户输入不覆盖**（仅填空字段）。
3. **出处展示**：每个已回填字段下方显示「来自第 N 页 ·『原文片段』」；`medium` 档加 `Tag color="gold"` 「待核对」；`rent_free_until` 有 `derivation` 时显示推算式。
4. **跳过入口**：`extracting` 期间显示「跳过识别，直接录入」，调 `skip-extraction`。

`WARNING_LABELS`（:29-34）补充新错误码文案。

### 4.6 数据外发与合规边界

**本方案把外发等级从「文本」提升到「合同原件」。** 这是必须显式确认的变更，不能藏在实现细节里。

| 阶段 | 外发对象 | 外发内容 |
|---|---|---|
| OCR（默认开启） | DeepSeek OCR API | **整份 PDF / 图片原件**，含公章、手写批注、甲乙方全称、租金金额、产权信息 |
| 字段增强（默认关闭） | DeepSeek 对话 API | OCR 产出的纯文本；脱敏仅覆盖身份证号与手机号，主体名称、地址、金额原样发出 |

官方隐私条款（`api-docs.deepseek.com/zh-cn/guides/ocr`）：「文件不会存入 Files API，也不会交给对话模型」。这是有利条件，但**不等于「不出内网」，也不构成数据出境或保密审查的合规依据**。

必须落实的四项措施：

1. **可切换**：`DOCUMENT_OCR_PROVIDER=local` 可完全断网运行，供涉密或断网环境使用。默认值由部署方显式指定，不在代码里硬编码 `deepseek`。
2. **知情**：会话 `warnings` 返回 `EXTRACTION_FILE_SENT_TO_THIRD_PARTY`（severity=`info`），文案「本次识别已将合同扫描件上传至外部 OCR 服务」。**当前实现无此提示，属需补齐的合规缺口。**
3. **留痕**：每次 OCR 调用记录 `provider`、`page_count`、响应 `id`、耗时、`usage` 到审计日志；**不记录文件内容**。
4. **可关闭**：`DOCUMENT_OCR_ENABLED=false` 时整条解析链路跳过，会话直接进入 `ready_for_review` + `extraction_disabled` warning，行为与当前完全一致。

LLM 文本增强维持原结论：`DOCUMENT_LLM_ENABLED` 默认 `false`——表一的 5 项靠规则抽取即可覆盖，无需为此再引入第二处外发。

**判断边界**：本方案只保证「技术上可切换、行为上可告知、审计上可追溯」，不替代数据出境与保密审查的结论。国资合同如涉及保密条款或敏感产权，部署时应默认 `local`。

### 4.7 为什么换 OCR：本地 RapidOCR 与 DeepSeek OCR 对照

| 维度 | 本地 RapidOCR（现状，保留为降级） | DeepSeek OCR（本方案默认） |
|---|---|---|
| 数据流向 | 全本地，零外发 | **整份文件上传 `api.deepseek.com`** |
| 服务端上限 | 无（系统自限 50 页 / 50 MiB） | 1000 页 / 100 MiB |
| 耗时 | 单页 10s、整卷 180s（占本地 CPU） | 单次总时长 180s（含上传，超时返 `504`） |
| 成本 | 0 | 1.5 元 / 1000 页 |
| 本地依赖 | `rapidocr` + `onnxruntime` + 3 个 ONNX 模型 + 启动 SHA256 预检 | 仅 `httpx` + API Key |
| 启动脆弱性 | 模型缺失或哈希不符 → 整机拒绝启动（fail loud） | 无本地模型，启动不受影响 |
| 识别质量 | PP-OCRv6 small，表格线与手写易丢 | 服务端模型，「模型原始输出不做清理」，表格与版式更强 |
| 失败模式 | CPU 抢占、单页超时 | 网络、余额（402）、限速（429）、服务繁忙（503） |
| 离线可用 | 是 | 否 |

选择 DeepSeek OCR 的四条理由：

1. 免去本地模型部署与哈希校验带来的启动脆弱性——当前预检是 fail loud，模型缺失会让整个后端起不来；
2. 支持整份 PDF 一次提交，无需本地光栅化与逐页调度，代码路径更短；
3. 识别质量对表格类合同更有利，而表一恰恰要从租金表里抽数；
4. 成本极低（本批约 1.5 元）。

必须接受的代价：**合同原件离开内网**。缓解与判断边界见 §4.6；不接受该代价的场景切 `local` 即可，下游逻辑完全一致。

## 5. 决策汇总

| # | 决策 | 选项 | 结论 | 理由 |
|---|---|---|---|---|
| D1 | 同步/异步 | 同步 / BackgroundTasks / worker | **BackgroundTasks** | 最坏 540s 必然超时；项目有先例；单机无需新设施 |
| D2 | 解析失败进什么状态 | `failed` / `ready_for_review` | **`ready_for_review`** | 文档红线；`failed` 留给会话级故障 |
| D3 | 候选是否带证据 | 只有值 / 值+页码+片段 | **值+页码+片段** | 人工核对需溯源 |
| D4 | 是否覆盖用户已填 | 覆盖 / 只填空 | **只填空** | 轮询可能在输入中途返回 |
| D5 | LLM 默认开关 | 开 / 关 | **关** | 国资合同文本外发需单独授权 |
| D6 | 是否改 `candidate_fields` schema | 强类型 / dict | **保持 dict** | 不破坏 §5.4 已发布契约 |
| D7 | 解析中确认 | 等待 / 409+跳过 | **409 + skip-extraction** | 尊重「解析仅辅助」，避免候选被作废 |
| D8 | 承租方是否自动绑定 | 自动匹配 / 只推荐 | **只推荐** | §5.4 红线；主体有审核流 |
| D9 | 免租期语义 | 存日期 / 存月数 | **候选出日期，落库存月数** | 系统模型是 `free_rent_months`；不改模型，换算过程可见 |
| D10 | 合同出租面积 | 识别 / 取单元面积 | **取单元 `rentable_area`** | 实测 67 行 W=J、0 行反例；识别多值反而引入错误 |
| D11 | 第一优先合同类型 | upstream / terminal | **terminal** | 表一是终端租赁口径，上游不产出台一任何列 |
| D12 | 合同月租金取哪个字段 | `actual_monthly_rent` / `base_monthly_rent` | **`base_monthly_rent`（减免前）** | 表一要求「免租期内按合同租金照填」；`actual` 在免租期为 0、有折扣时被调低，填表会把该行租金与坪效算小 |
| D13 | OCR 实现选型 | 本地 RapidOCR / DeepSeek OCR | **DeepSeek OCR 默认，本地保留为降级** | 免本地模型运维与启动脆弱性；整份 PDF 一次提交；表格识别更强；成本 1.5 元/千页。代价是原件外发，见 §4.6 |
| D14 | OCR `purpose` 取值 | `text_recognition` / `rich_layout_recognition` | **`text_recognition`** | 只要文本；后者输出含 `<｜ref｜>`/`<｜box｜>` 与归一化坐标，污染规则抽取。后续要做框选定位再切 |
| D15 | 合同原件外发是否接受 | 接受 / 拒绝 | **接受（用户决策），但须可切换+告知+留痕** | 用户明确要求接入 DeepSeek OCR；技术上以 provider 开关兜住不接受该代价的场景 |
| D16 | OCR 与 LLM 是否级联 | OCR 后必调 LLM / 仅规则 | **仅规则；LLM 默认关** | 表一 5 项均为正则可覆盖的结构化字段；避免第二处外发与额外成本 |

## 6. 字段映射表

### 6.1 终端合同（表一主路径）

| 解析键 | 前端 FormState | 确认请求字段 | 表一列 | 处理 |
|---|---|---|---|---|
| `contract_number` | `contractNumber` | `contract_number` | —（表一无此列） | 直接回填，系统必填 |
| `effective_from` | `startDate` | `start_date` | 租期起 | 直接回填 |
| `effective_to` | `endDate` | `end_date` | 租期止 | 直接回填 |
| `tenant_name` | （PartyPicker 搜索词） | `tenant_party_id` | 承租方 | **只推荐，人工点选** |
| `monthly_rent`（**减免前首月**） | `rentSchedules[0].base_monthly_rent` | `rent_schedules[0].base_monthly_rent` | 合同月租金 | **填 `base`，不填 `actual`**；按 §4.3.5 的 R1–R3 清洗；`actual_monthly_rent` 由人工按免租/折扣条款另填 |
| `rent_free_until` | `rentFreeUntil`（新增展示态） | 换算为 `rent_schedules[0].free_rent_months` | 免租期截止日 | 见 §6.2 |
| `leased_area` | — | — | 合同出租面积 | **不落库**；与单元面积比对，差异 >5% 提示 |
| `payment_cycle` | `paymentCycle` | `rent_schedules[].payment_cycle` | —（表一无需） | 回填 |
| `sign_date` / `contract_notes` | — | — | — | **丢弃**：确认请求无此字段 |

### 6.2 免租期换算（D9 的具体算法）

系统 `free_rent_months` 是**月数**，表一要**截止日**。两个方向：

- **录入方向**：候选 `rent_free_until`（日期）→ 人工确认后，换算 `free_rent_months = (截止日 − 首阶段起租日) 折算月数`，四舍五入保留 2 位（字段是 `Numeric(8,2)`）。
- **报表方向**：`免租期截止日 = 首阶段 stage_start + free_rent_months 个月 − 1 天`。

**已知语义缺口**：合同常写「自交付之日起免租 N 个月」，交付日未必等于 `stage_start`，此时两个方向都会产生少则数天、多则整月的偏差。处理：

- 候选 `rent_free_until` 若能从合同直接读到确切日期（形态①），**以合同日期为准**，不依赖推算；
- 若只能读到月数（形态②），`confidence_tier` 固定 `medium`，前端显示推算式，由人工判断；
- 报表方向偏差超出 ±15 天时，提示「与合同免租条款不一致，请核对」，不自动修正。

不改数据模型是本轮选择（§3.2）；若后续发现形态②占比高，再评估新增 `free_rent_until` 字段。

### 6.3 上游合同（保留支持，非验收目标）

| 解析键 | 上游确认字段 | 说明 |
|---|---|---|
| `contract_number` / `effective_from` / `effective_to` | 同名 | 直接回填 |
| `monthly_rent`（减免前首月） | `rent_schedules[0].base_monthly_rent` | 同样取 `base`；R1–R3 清洗一致 |
| `payment_cycle` | 合同级 `payment_cycle` | 仅规则产出 |
| `tenant_name` / `rent_free_until` / `leased_area` | — | 上游无对应语义，**丢弃** |

## 7. 测试与验收

### 7.1 单元测试

| 用例 | 断言 |
|---|---|
| 上传后立即返回 | `status == "extracting"`、`candidate_fields == {}` |
| 解析完成 | `ready_for_review`；5 个键存在且各含 `value`/`extractor`/`evidence` |
| **响应前置换行** | mock 返回 `"\n\n\n{...}"` 仍能解析成功（保活换行属前导空白） |
| **页码对齐** | mock `pages[].index=0..n-1` → `PageText.page_number` 为 `1..n` |
| **provider 同构** | `deepseek` 与 `local` 两个 provider 对同一份样例产出结构一致的 `list[PageText]`（仅文本内容可不同） |
| **402 余额不足** | `ocr_insufficient_balance`，`ready_for_review`，**不重试**（mock 调用次数 = 1） |
| **408 / 504 超时** | `ocr_upload_timeout`，`ready_for_review` |
| **429 / 503** | 退避重试 2 次后 `ocr_rate_limited` / `ocr_service_unavailable`，`ready_for_review` |
| **200 但 body 含 error** | 识别出 `ocr_failed`，不误判为成功 |
| **`finish_reason=length`** | 该页 `text_source=None`、记 `ocr_page_truncated`，其余页仍产出候选 |
| **OCR 关闭** | `DOCUMENT_OCR_ENABLED=false` → `extraction_disabled`，无任何 HTTP 调用 |
| `local` 模式依赖缺失（mock 预检抛错） | `ready_for_review` + `EXTRACTION_UNAVAILABLE` + `candidates == {}` |
| 非 PDF / 超页数 | `ready_for_review` + `extraction_unsupported` |
| `management_agreement` | 候选**不含** `monthly_rent`、`rent_free_until` |
| `tenant_name` 不产生 Party ID | 断言 `candidate_fields` 内任何层级无 UUID 形态字符串 |
| 免租期形态②换算 | 「自 2024-11-08 起免租 12 个月」→ `2025-11-07`，`tier=medium`，含 `derivation` |
| `monthly_rent` 取减免前 | 合同同时含「月租金 44,900」与「免租 12 个月」→ 候选值 **44,900**，不得为 0、不得取 `actual` |
| 年租金折月（R2） | 「年租金 600,000 元」→ `value=50000.00`，`derivation` 含「÷ 12」 |
| 含代收费用降级（R1） | 同页出现「综合管理费」→ `tier=medium`，且提示文案含「可能含代收费用」 |
| 递增条款只取首阶段（R3） | 「首年 50,000，第二年起递增 5%」→ `value=50000.00`，不含 52,500 |
| `leased_area` 与单元面积差异 >5% | 校验提示被触发，且 `leased_area` 不出现在确认请求 |
| 会话过期后回写 | 抛 `session_expired`，不向上抛 500 |
| 跨操作者读取 | 404 |
| `skip-extraction` | `extracting → ready_for_review`；重复调用幂等 |
| 解析中确认 | 409 `SESSION_EXTRACTION_IN_PROGRESS` |
| **不变式**（参数化跑全部失败分支） | 无任何分支使状态停在 `extracting` 或 `failed` |

### 7.2 集成测试

取 3 份真实终端租赁合同（建议：名创优品北京路 245/249 号、佐登堡松柏东街、房世超松柏东街——均可在表一找到对应行）。走完整链路：上传 → 轮询 → 候选出现 → 人工选主体/单元 → `confirm-terminal` → 校验合同落库、扫描件改绑；再把这 3 行的 5 个字段与表一现有值逐项比对。

该轮**走真实 DeepSeek OCR**（需有效 Key 与余额），逐份记录页数、耗时、响应 `id` 与 `usage`，作为 A1 与预算备案的实测依据。单元测试一律 mock `httpx`，CI 不依赖外部服务。

### 7.3 验收标准

| # | 标准 | 判定 |
|---|---|---|
| A1 | 3 份真实合同 OCR 全流程在 **180s 服务端上限**内完成并出候选 | 逐份计时；超限即判失败（映射 `ocr_upload_timeout` 不算通过） |
| A2 | `DOCUMENT_OCR_PROVIDER=local` + LLM 关闭时全链路零外网请求 | 日志核对 `httpx` 调用数 = 0 |
| A3 | 关闭解析（`DOCUMENT_OCR_ENABLED=false`）后录入链路与当前完全一致 | 既有 `ContractIntakePage` 测试全绿 |
| A4 | 解析失败不影响任何合同录入 | 手工补录端到端通过 |
| A5 | 承租方、资产单元均为用户显式选择 | 检查确认请求无自动绑定痕迹 |
| A6 | 3 份真实合同与表一比对：租期起止 **3/3 一致**、合同月租金**按 `base_monthly_rent` 比对 3/3 一致**、承租方 **3/3 被正确推荐** | 人工比对表 |
| A7 | 免租期换算偏差 ≤15 天或明确标记待核；存在 `finish_reason=length` 的页不得贡献候选 | 逐份核 |
| A8 | 默认配置下会话必带 `EXTRACTION_FILE_SENT_TO_THIRD_PARTY` 告知 | 响应体断言 |
| A9 | 单份合同 OCR 成本与页数可核算（`page_count × 1.5/1000`） | 审计日志抽查 |

## 8. 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| **合同原件外发第三方，且不可撤回** | **高** | provider 可切 `local`；会话返回外发告知 warning；审计只记元数据不记内容；涉密合同部署侧默认 `local`（§4.6） |
| 月租金含代收费用直接填表一导致偏高 | **高** | 命中「管理费/物业费」即降 `medium` 并提示；A6 逐份核 |
| 误填 `actual`（减免后）导致免租期行为 0、租金与坪效偏小 | **高** | D12 把映射固定为 `base_monthly_rent`；R3 只取首阶段；A6 按 `base` 逐份比对 |
| 年租金未折月导致该行租金放大 12 倍 | **高** | R2 强制折算并在 `derivation` 留痕；A6 检查量级（与同物业其他行单价对比，偏离 >20% 告警） |
| DeepSeek OCR 与既有复核表 OCR 引擎不同（服务端模型 vs 复核表 RapidOCR PP-OCRv4） | 中 | **不做机器比对**；复核表以人工核对为准，系统识别仅作录入辅助 |
| 单次 180s 总时长上限导致长合同超时（`504` / `OCR did not finish in time`） | 中 | 系统侧仍限 50 页；超时映射 `extraction_timeout` 并回落手工补录；A1 实测 20 页合同耗时 |
| `finish_reason=length` 页文本被截断，据此抽字段会出错 | 中 | 截断页置 `text_source=None` 并记 `ocr_page_truncated`，不参与抽取；A7 核 |
| 余额不足（402）导致全部解析失败 | 中 | 错误映射 `ocr_insufficient_balance` 并在前端提示联系管理员；不重试 |
| 服务繁忙（503）/ 限速（429） | 低 | 指数退避重试 2 次（间隔 2s/8s），仍失败则降级手工补录 |
| 上传带宽被大文件占满，影响同期人工录入 | 低 | `asyncio.Semaphore(1)` 串行 + 50 页上限；必要时错峰 |
| 进程重启丢解析会话 | 中 | 轮询超时提示重传；解析为一次性辅助 |
| 免租期换算偏差 | 中 | 形态①优先取合同日期；形态②标 `medium` 并显示推算式 |
| 用户把承租方推荐当已选中 | 中 | PartyPicker 不预置 ID；未选中时确认按钮校验报错 |
| Redis TTL 与后台任务竞态 | 低 | `update_candidates` 捕获过期直接放弃，不重试 |

## 9. 实施步骤

| 步 | 内容 | 依赖 |
|---|---|---|
| 1 | `OcrProvider` 抽象 + `DeepSeekOcrProvider`（multipart 上传、前置换行解析、页码 +1、9 类错误映射、`finish_reason` 截断处理）+ mock 单测 | — |
| 2 | `LocalRapidOcrProvider` 包装现有 `OrderedPageTextPipeline` + `DOCUMENT_OCR_PROVIDER` 开关 + 两 provider 同构断言 | 1 |
| 3 | 白名单扩 2 项 + `monthly_rent` 降级规则（R1–R3）+ 单测（纯规则，可独立验） | — |
| 4 | `ExtractionSessionRepository.update_candidates` + 单测 | — |
| 5 | `ContractIntakeExtractor`（provider + 规则 + 可选 LLM + 类型裁剪）+ 单测 | 1,2,3,4 |
| 6 | `ContractIntakeSessionService` 异步编排、降级矩阵、`skip-extraction` + 单测 | 5 |
| 7 | API 层注入 `BackgroundTasks`、新增端点、外发告知 warning + OCR 审计日志 | 6 |
| 8 | 前端轮询、候选回填、PartyPicker 推荐、出处展示、跳过入口 + 组件测试 | 7 |
| 9 | 集成测试（3 份真实终端合同，走真实 OCR）+ 验收 A1–A9 | 8 |
| 10 | 部署三件套：`DOCUMENT_OCR_PROVIDER` 显式指定、`DOCUMENT_OCR_ENABLED`、`DOCUMENT_LLM_ENABLED=false`；同步 `.env.example` | 7 |

建议 1–7 为后端 PR（可独立验收），8–9 为前端 + 端到端 PR。

**前置条件**：表一填报需要 `tenant_party_id` 有值。**主体审核流已于 2026-11-20 停用（建档即生效）**，终端租户（名创优品、佐登堡等）直接建档即可用于合同录入，不必再走提审/审核；A6 前需先完成这批租户建档。

**另需前置**：`DEEPSEEK_API_KEY` 可用余额（402 会直接导致全部解析失败），以及部署方对「合同原件外发」的书面确认（§4.6）。

## 10. 引用锚点

- **DeepSeek OCR 指南**：<https://api-docs.deepseek.com/zh-cn/guides/ocr>（端点 `POST /v1/tools/ocr`、`purpose` 两取值、100 MiB / 1000 页 / 180s 限制、1.5 元每千页计费、15 并发限速、错误码表、「文件不存 Files API 且不交对话模型」隐私条款）
- `docs/design/flows/flow-contract-intake.md` 主流程第 3 步、「关键 UX 约束」
- `docs/specs/api-contract.md` §5.4、§5.5、§5.6
- `docs/integrations/pdf-processing.md`
- `docs/prd.md` §6.3、§6.5
- `docs/traceability/requirements-trace.md` REQ-DOC-001（已移除）
- `docs/archive/backend-plans/2026-07-15-rapidocr-deepseek-document-extraction-plan.md`（四条红线）
- ADR-0013（补录即生效）
- 数据：`【以此为准】集团物业经营管理台账（表一+表二）2026.11.19(五羊).xlsx` → `填报说明` 第 8/33–38 行、`表一-物业台账` 94 行实测
- 代码：`contract_intake_service.py:181-199`、`extraction_sessions.py:41-127`、`page_text_pipeline.py:70-73`、`candidate_review.py:91-99,113,153`、`schemas/asset_operations.py:262-282,422-452,686-702`、`models/asset_contract.py:312-330,405`、`ContractIntakePage.tsx:317`
