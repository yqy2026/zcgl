# RapidOCR + DeepSeek 单一 LLM 文档解析收口方案

## Status

✅ 已完成并归档（2026-07-25）

## 1. 目标与结论

本方案覆盖 REQ-DOC-001、REQ-RNT-003、REQ-AST-005 的扫描件解析辅助补录链路，并落实以下技术决策：

1. 项目 LLM provider 只保留 **DeepSeek**，删除 Qwen、GLM/Zhipu、Hunyuan 的运行时代码、配置、状态展示和测试残留。
2. **PyMuPDF 保留并升级为文档处理必需依赖**，负责 PDF 打开、逐页文本提取、页数检查和扫描页渲染。
3. **RapidOCR 作为本地 OCR 候选层**，只处理无有效文本层或文本质量不足的页面；不引入 `RapidOCRPDF`，避免与现有 PDF 路由和 PyMuPDF 渲染重复。
4. DeepSeek 只接收 OCR/数字 PDF 产生的文本，负责复杂语义字段的结构化候选提取；规则可以完成的字段不强制调用 LLM。
5. LLM 不是启动和手工补录的硬依赖。DeepSeek 未启用、超时或失败时，系统仍返回 PyMuPDF/RapidOCR/规则候选并允许完全手工补录；不得静默切换其他云 provider。
6. 当前 DeepSeek 官方托管 API 不按视觉输入设计。现有 `deepseek-vl` 云端图片调用路径必须删除，不能以“OpenAI 兼容”推定其支持图片。

目标架构：

```text
PDF/JPEG/PNG
  -> 文件签名、大小、页数与可解析性校验
  -> PyMuPDF 逐页检测
       -> 有效文本页：直接提取文本
       -> 扫描/低质量页：PyMuPDF 渲染 -> RapidOCR
  -> 文本归一化 + 确定性规则提取
  -> 可选 DeepSeek 文本结构化提取
  -> Schema/业务规则校验 + 候选合并
  -> 临时字段证据与置信度
  -> 用户逐字段确认/修正/留空
  -> 按既有字段来源契约写入，清理临时解析会话
```

## 2. 权威边界

本方案不改变以下产品事实：

- OCR/AI 只生成候选，不能自动写入或覆盖业务字段。
- 低置信候选必须逐项处理；解析失败、超时或低置信不能阻断完全手工补录。
- Party 与 Asset 只能由用户显式匹配既有记录，解析结果不得自动创建或绑定。
- 页码、片段、框坐标、OCR 分数、模型信息只存在于临时解析会话；确认、取消、失败或放弃后不得写入目标业务对象。
- MVP 只处理单件扫描件，不新增批量解析、长期 OCR 原文档案或视觉高亮产品能力。

权威文档：

- `docs/prd.md` §6.5、REQ-RNT-003、REQ-DOC-001
- `docs/specs/domain-model.md` §2、§4.22、§4.23
- `docs/specs/api-contract.md` §4.10
- `docs/traceability/requirements-trace.md` 的 REQ-DOC-001 实现证据

本方案已完成 Wayfinder 决策评审并同步目标产品契约，是后续实施 Agent 的权威执行规格。实施中发生行为、字段、API、权限、迁移或需求状态变化时，必须在对应批次同步上述 SSOT、实现证据与 `CHANGELOG.md`，不得拖到最终归档时补写。

## 3. 已确认的现状问题

### 3.1 OCR 与路由

- `OCRExtractionService` 当前硬绑定 `GLM-OCR`，扫描件可用性依赖外部 OCR API。
- `LLMContractExtractor` 仍按“扫描件优先视觉模型”路由，RapidOCR 接入后该假设不再成立。
- `pdf_analyzer.py` 仅抽查前 5 页并以整份文档给出 `text/vision` 推荐，不能正确处理数字页与扫描页混合的 PDF。
- PyMuPDF 缺失时当前会默认走视觉路径；目标态应在启用文档解析的部署中 fail loud，因为 PDF 检测和渲染均依赖它。
- `pdf2image` 与 PyMuPDF 存在重复渲染路径和额外 Poppler 运维依赖。

### 3.2 LLM provider

- `LLMProvider`、工厂、适配器、配置和测试同时维护 Qwen、DeepSeek、GLM/Zhipu、Hunyuan。
- `LLMService` 仍存在 Hunyuan/GLM 默认值，配置优先级分散在 `VISION_MODEL`、`EXTRACTION_LLM_PROVIDER`、`LLM_PROVIDER`。
- `DeepSeekVisionService` 把开源 `DeepSeek-VL/DeepSeek-VL2` 模型名直接用于 `api.deepseek.com` 图片请求，缺少官方托管能力依据。
- 当前 `deepseek-chat` 默认模型即将退出官方服务；模型名不应继续硬编码为隐式默认。

截至 2026-07-15，DeepSeek [官方 API 文档](https://api-docs.deepseek.com/) 将托管接口描述为文本模型接口，[官方更新日志](https://api-docs.deepseek.com/updates/) 已公告旧 `deepseek-chat` / `deepseek-reasoner` 模型迁移窗口。开源 [DeepSeek-VL2](https://github.com/deepseek-ai/DeepSeek-VL2) 是需独立部署和容量评估的视觉模型，不能等同于官方托管 API。

### 3.3 置信度与证据

- 当前部分置信度由“非空字段比例”估算，不能代表字段正确率。
- OCR、规则、LLM 的临时候选来源与最终持久化的 `manual` / `ocr_prefill_confirmed` / `ocr_prefill_corrected` 混在同一概念中。
- RapidOCR 的文字置信度只能说明识别分数，不能直接当作合同金额、日期或主体匹配的业务置信度。

### 3.4 依赖、上传校验与产权证附件

- `pymupdf` 仍位于可选 `pdf-basic`，`rapidocr`/`onnxruntime` 尚未进入项目锁定依赖；`pdf2image` 和 Poppler 仍形成重复 PDF 渲染路径。
- 共享 `FileValidator` 在 magic 缺失或检测异常时会退化为扩展名放行；生产调用方还存在一次性无界读取、错误签名只告警、XLS 伪支持和 XLSX/JSON 资源上限缺失。
- 上传调用方审计已完成，目标格式固定为 PDF/JPEG/PNG/XLSX/JSON；CSV、压缩包、TIFF、GIF 无生产调用方，XLS 无解析器，均应删除声明。
- 产权证同时存在通用 `Attachment` 与专用 `PropertyCertificateAttachment`，且没有可用的域内正式附件上传 API；新建产权证还存在“先有附件 owner 还是先有产权证 ID”的死结。
- 目标态使用用途 profile + 确定性解析器失败关闭，最终删除 magic；产权证正式附件只使用通用 `Attachment`，新建场景由临时解析会话暂存文件并在人工确认时晋升。

## 4. 锁定的目标设计

### 4.1 页面级文本管线

所有 PDF/JPEG/PNG 输入统一转为有序页面集合，页面按原序处理，每页只保留一个规范正文来源：

1. PDF 由 PyMuPDF 打开并验证 `is_pdf`、加密、修复、零页、页数和尺寸；图片由 Pillow 验证并解码。
2. 数字 PDF 页直接使用 PyMuPDF 有序文本；文本为空或质量不足的页按 200 DPI 渲染并调用 RapidOCR。
3. JPEG/PNG 作为单页扫描文档进入同一 RapidOCR 页面模型。
4. 页面结果保留临时页码、正文行、短证据和 OCR 坐标/分数；正文来源只能是 `pdf_text` 或 `rapidocr`，不得重复拼入两份正文。
5. 单页失败记录结构化阶段错误并继续其他页面；资源上限、依赖/模型初始化失败和整份文件不可解析属于明确失败，不得静默降级。
6. 页面按流式/逐页方式处理并及时释放 pixmap、Pillow 图像和临时资源，不把整份 20 页渲染结果同时常驻内存。

PyMuPDF 是唯一 PDF 打开、文本提取和渲染后端；不引入 RapidOCRPDF，不保留 `pdf2image` 或“整份文档 text/vision 二选一”路由。

### 4.2 RapidOCR 固定运行配置

- 版本固定：`rapidocr==3.9.1`、`onnxruntime==1.20.1`、`pymupdf==1.24.14`。
- 模型固定为 RapidOCR 3.9.1 随包提供的 `PP-OCRv6_det_small.onnx`、`ch_ppocr_mobile_v2.0_cls_mobile.onnx`、`PP-OCRv6_rec_small.onnx`。
- 扫描页统一 200 DPI。每个服务进程预热并复用一个 RapidOCR 实例，外层线程并发上限为 1，不在多个并发线程间共享同一实例。
- 单页超时 10 秒，单文档超时 180 秒；OCR 服务进程预算 2 GiB，部署容量按 OCR 进程数线性计算。
- 依赖和三个模型随部署制品离线分发，构建时记录并校验 SHA-256；运行时不得联网下载、替换模型或在首个请求时才初始化失败。
- 20 页纯扫描样本在已记录 Windows 主机上的 200 DPI/并发 1 基线约 63.208 秒，单页 P95 约 4.001 秒、峰值 RSS 约 1600.9 MiB。该结果是可复跑基线，不冒充生产 P95，也不是采用否决门槛。

RapidOCR 已确定直接采用。真实样本用于发现实现回归、暴露识别缺口和校准资源，不重新决定是否回退其他 OCR provider；所有候选仍由人工逐字段复核。

### 4.3 候选、规则与 DeepSeek

内部候选按字段保存类型化值、`text_source`（`pdf_text`/`rapidocr`）、`extractor`（`rule`/`deepseek`）、临时短证据、保守高/中/低档位和 `pending` 复核状态。相同值只合并证据，不同值形成显式冲突且不预选。最终写入来源只由后端根据五类人工动作推导：

- `accept_candidate`
- `correct_candidate`
- `manual`
- `clear_optional`
- `keep_existing`

持久化 `field_sources` 仍只允许 `manual` / `ocr_prefill_confirmed` / `ocr_prefill_corrected`。页面证据、OCR 分数、Prompt/Schema、模型和 provider 信息只存在于临时会话。

DeepSeek 固定为可关闭的纯文本复杂语义候选阶段：

- `DOCUMENT_LLM_ENABLED=false` 为默认；关闭时不要求 key/model，阶段返回 `skipped/llm_disabled`。
- 开启时必须显式配置 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL=deepseek-v4-flash` 和可见的官方 base URL；缺配置阻止启动。
- 调用固定 `thinking={"type":"disabled"}`、`temperature=0`、`stream=false`、JSON object、`max_tokens=8192`、120 秒超时、自动重试 0 次。
- 合同 Prompt/Schema 版本为 `contract-extraction/v1`，产权证为 `property-certificate-extraction/v1`，均由代码常量持有，不读取数据库 Prompt。
- 输入最多 20 页、脱敏后 200,000 字符；不发送图片、PDF、文件名、附件 ID、坐标、OCR 分数、业务 ID 或写操作上下文。
- HTTP/完成状态、JSON、精确 Schema、版本/文档类型、白名单、类型、业务约束和证据引用任一失败，整批 DeepSeek 候选归零；规则候选和完整人工路径继续，不做 provider fallback 或自动重试。
- 日志只记录会话关联 ID、阶段、模型、Prompt/Schema 版本、耗时、token、HTTP 状态和结构化错误码，不记录请求/响应正文或原始 OCR 文本。

### 4.4 临时会话、公开 API 与产权证附件

公开文档解析面只保留：

| 方法与路径 | 目标语义 |
|---|---|
| `POST /api/v1/extraction-sessions` | 创建合同上传、产权证新建上传或既有产权证附件引用的单件临时会话 |
| `GET /api/v1/extraction-sessions/{session_id}` | 查询阶段、候选、证据、冲突和结构化错误 |
| `POST /api/v1/extraction-sessions/{session_id}/confirm` | 提交五类人工动作和显式 Party/Asset ID，后端验证并写入 |
| `POST /api/v1/extraction-sessions/{session_id}/cancel` | 取消且清理会话/暂存文件，不写业务对象 |
| `GET /api/v1/document-extraction/capabilities` | 返回目标类型、输入方式、格式/资源上限和阶段 ready/disabled，不暴露 provider |

会话存储必须进程共享，禁止 worker 内存单例；实现复用项目现有 Redis，默认 TTL 3600 秒，状态转换使用原子 compare-and-set。暂存目录按同一 TTL 清扫，确认/取消/失败立即清理；Redis 不可用按项目现有 fail-loud 启动规则阻止服务，不降级到进程内字典。会话不提供列表、历史、草稿恢复、稍后继续或 `/retry`。

产权证规则：

- 新建：`input_mode=upload`，当前资产上下文 + 恰好一个 PDF/JPEG/PNG；确认满足五项硬门槛后，通过同卷原子文件晋升与数据库事务创建产权证、资产/权利人关系和通用附件。移动失败回滚事务，提交失败删除最终文件，补偿失败记录告警。
- 既有：`input_mode=attachment_reference`，必须验证资产-产权证-附件完整 owner 链，不接收新文件。
- 正式附件唯一模型为 `Attachment(owner_type=property_certificate, owner_id=certificate_id)`。客户端不能提交 owner 或 `storage_key`。
- 域内附件 API 提供列表/追加、替换/删除、预览和下载；上传不自动解析，最后一份不可删除，预览跟随查看权限，下载使用独立 `property_certificate_attachment:download` 权限并记录轻量日志。
- 证号冲突返回 409 并保留当前会话，只允许用户显式关联既有产权证并决定是否追加本次暂存附件；不得自动绑定或新建重复证。

### 4.5 Fail-loud 上传校验

所有生产上传入口调用固定用途 profile，统一顺序为：授权与文件名 -> 上限 + 1 有界读取 -> 扩展名/MIME 一致 -> 固定签名初筛 -> 专用解析器最终验证 -> 服务端生成规范 MIME、SHA-256 和安全存储键。任一层不一致立即拒绝并清理临时文件。

| Profile | 格式与硬上限 |
|---|---|
| `contract_extraction` | PDF 50 MiB、20 页 |
| `property_certificate_extraction` | PDF/JPEG/PNG 均 20 MiB；PDF 20 页；图片 50,000,000 像素 |
| `asset_attachment` | PDF 10 MiB |
| `payment_voucher` | PDF/JPEG/PNG 20 MiB |
| `excel_preview` | XLSX 50 MiB |
| `excel_import` | XLSX 100 MiB |
| `system_settings_restore` | JSON 1 MiB |

PDF 由 PyMuPDF 拒绝加密、零页、修复和结构损坏；图片由 Pillow `verify()` 后重新打开 `load()`；XLSX 在 openpyxl 前限制最多 2,048 个成员、单成员 64 MiB、总解压 256 MiB、压缩比 100:1，并拒绝加密、路径穿越、重复成员、宏和缺失必需 OOXML 成员；JSON 严格 UTF-8、顶层对象和专用 Pydantic Schema。

全部调用方迁移到这些 profile 后，在同一批删除 `python-magic`/`python-magic-bin`、`MAGIC_AVAILABLE`、全局白名单和扩展名放行分支。PyMuPDF/RapidOCR/ONNX Runtime/模型、Pillow、openpyxl 或 defusedxml 缺失属于启动错误，不是上传时可吞掉的异常。

## 5. 五批实施顺序

实施前创建独立功能分支。每批先补会失败的意图测试，完成定向门禁并更新 `CHANGELOG.md`；行为、字段、API、权限或迁移变化必须同批同步 PRD/spec/traceability。

### 批次 1：依赖、上传校验与文件存储基础

**范围**：`backend/pyproject.toml`、锁文件、Makefile/CI/镜像、共享文件校验与存储服务、全部生产上传调用方及其定向测试。

**动作**：

- 建立并在所有标准环境显式安装 `document-processing` 依赖组，固定依赖/模型/哈希和启动检查。
- 实现用途 profile、专用解析器、XLSX 资源限制、JSON 上限与结构化错误。
- 迁移全部上传调用方，删除伪支持格式、magic 和 PyMuPDF 之外的 PDF 回退。
- 抽出共享有界读取、哈希、安全键、暂存/晋升/补偿清理；支付凭证和资产附件不得改变既有产品语义。

**退出门禁**：无通用 magic 调用或扩展名降级；依赖/模型缺失启动失败；每个格式的有效、伪装、截断、超限和清理测试通过；既有上传 API 回归通过。

### 批次 2：新的内部解析内核

**范围**：`backend/src/services/document/` 下的新页面/OCR/规则/DeepSeek/候选模块、配置、离线原型和 service tests；不注册公开路由、不改前端。

**动作**：

- 实现 §4.1~§4.3 的页面管线、RapidOCR 运行时、候选合并、代码版控 Prompt/Schema 和 DeepSeek 文本客户端。
- 用数字、扫描、混合、空白/失败页和合成 DeepSeek 响应做无网络测试。
- 保留旧公开入口继续使用旧链，仅允许新内核通过直接 service contract 测试调用；不建立第二套公开 API。

**退出门禁**：页序/单正文来源、超时/资源释放、并发 1、规则/DeepSeek 冲突、原子坏响应、PII 日志和 LLM 禁用手工路径通过；20 页样本在 180 秒/2 GiB 内可复跑。

### 批次 3：统一会话与前后端原子切换

**范围**：后端 Schema -> Service -> CRUD -> API、临时会话 repository、产权证通用附件、必要增量迁移、权限、前端服务/页面/路由和 API/E2E 测试。

**动作**：

- 注册统一四端点和能力接口，接入合同/产权证；确认载荷只允许五类动作，后端推导 `field_sources`。
- 上线产权证新建临时上传、既有附件引用、通用 Attachment 域内 API、独立下载权限和文件/事务补偿。
- 增量迁移只新增切换所需 `field_sources`、权限和约束；不删除旧表。
- 前端同批切换上传、状态、逐字段复核和附件管理。
- 注销旧 PDF/产权证导入、Prompt 和调试路由，移除菜单入口；旧源文件暂时保留为不可达死代码，旧路径必须 404。

**退出门禁**：新 API/schema/authz/生命周期/补偿/证号冲突和前端主流程通过；旧路径 404；前后端无 provider/引擎选择、客户端 `field_sources`、批量采纳或文档级百分比。

### 批次 4：旧链和旧结构物理删除

**范围**：旧后端/前端源文件、配置/环境示例、模型/CRUD/schema/权限、破坏性 Alembic 迁移及删除守卫。

**动作**：

- 删除多 provider、GLM-OCR、DeepSeek 视觉、工厂/alias/fallback、旧 PDF import/batch/system、Prompt 管理全栈和不可达测试。
- 删除产权证专用附件模型、客户端 `storage_key`、旧 `extraction_confidence/extraction_source` 及相关响应/UI。
- 迁移删除 `property_certificate_attachments`、`prompt_templates`、`prompt_versions`、`extraction_feedback`、`prompt_metrics`、旧 PDF 会话/历史表和审计确认无引用的列；不迁移旧数据，不提供 downgrade。
- 部署顺序固定为停止旧应用进程 -> 执行迁移 -> 启动新应用，禁止旧 worker 访问收缩后 schema。

**退出门禁**：活跃代码/配置/测试全库搜索旧 provider、Prompt API、旧路由/表符号为零；初始 revision 到新 head 的临时 PostgreSQL 升级通过；单 head、后端导入、前后端 lint/type/test/build 通过。

### 批次 5：最终证明、证据与归档

**范围**：真实样本回归、全量门禁、运行/部署/安全文档、traceability、计划索引和归档。

**动作**：

- 跑数字/扫描/混合合同与产权证真实回归、失败/超时/安全日志、完整人工补录、180 秒/2 GiB 资源边界。
- 运行 `make check`；Windows 无 make 时逐项运行等价门禁并记录所有跳过和环境限制。
- 更新 REQ-DOC-001、REQ-RNT-003、REQ-AST-005 的最终代码与测试证据。
- 全部完成后将本文件状态改为 ✅，立即移入 `docs/archive/backend-plans/`，同步 `docs/plans/README.md` 和 `CHANGELOG.md`。

**退出门禁**：完成标准逐项有代码/测试证据，活跃计划目录无完成态文件，未执行项为零或被明确阻断。

## 6. 固定运行与验收边界

| 项目 | 锁定值 |
|---|---|
| RapidOCR / ONNX / PyMuPDF | 3.9.1 / 1.20.1 / 1.24.14 |
| 模型 | PP-OCRv6 det small + cls mobile + rec small，离线哈希校验 |
| 渲染 / OCR 并发 | 200 DPI / 每进程单实例 / 外层并发 1 |
| 超时 / 内存 | 单页 10 秒、单文档 180 秒、每 OCR 进程 2 GiB |
| 文档上限 | 单件、最多 20 页；合同 PDF 50 MiB；产权证 PDF/JPEG/PNG 20 MiB |
| DeepSeek | 默认关闭；显式 `deepseek-v4-flash`；120 秒；0 自动重试；纯文本 |
| 人工复核 | 所有候选逐字段处理；自动写入、自动绑定、静默覆盖为 0 |
| 失败路径 | RapidOCR 页级失败可手工继续；DeepSeek 失败保留规则/人工路径；基础解析依赖缺失阻止启动 |
| 基线解释 | 20 页扫描约 63 秒只作资源回归基线；不再保留 30 秒采用门槛或 OCR 选型否决 |

当前样本没有数字 PDF、混合 PDF 或人工真值，因此不宣称 OCR 准确率，也不写 95% 等无证据百分比。批次 2 和批次 5 必须补数字/混合场景与真实业务回归，但结果只用于暴露缺口和防回归，不恢复其他 OCR provider。

## 7. 必测矩阵

- PDF：数字、纯扫描、数字/扫描混合、空白、旋转、低清、印章遮挡、跨页、20 页边界。
- 文件安全：空、超限、双扩展、MIME/签名不一致、正确签名但损坏、加密/修复/零页 PDF、图片解压炸弹、XLSX ZIP/XML 攻击、JSON 非 UTF-8/坏 Schema。
- 页面运行时：页序、单一正文来源、单页超时可恢复、整文档超时、并发上限、实例复用、冷启动、内存/临时资源释放。
- DeepSeek：关闭、缺配置启动失败、超时/429/5xx、非法/空/截断 JSON、额外字段、错误版本、业务越界、无效证据、提示注入、0 自动重试。
- 候选复核：规则/DeepSeek 一致、冲突、重复值证据合并、保守档位、五类动作、低置信未处理阻断、服务端推导字段来源、完全手工。
- 主数据：Party/Asset 只显式选择既有 ID，不自动创建/绑定；已有值不自动覆盖。
- 会话：创建/查询/确认/取消、Redis TTL、确认/取消竞争、失败/过期清理、暂存文件清扫、终结后不留历史。
- 产权证：新建临时上传、既有附件引用、五项保存门槛、文件/数据库补偿、证号冲突显式关联、通用 Attachment owner 链。
- 附件：多文件逐项结果、疑似重复、替换、最后一份删除保护、预览权限、独立下载权限与日志。
- 删除守卫：旧端点 404，活跃代码不含旧 provider/Prompt/批量 API/专用附件符号，旧配置不再读取。
- 隐私日志：不得包含 OCR 原文、模型原文、姓名/地址/条款、身份证号、手机号、API key、PDF base64 或存储路径。
- 迁移：增量迁移与破坏性迁移顺序、无旧 worker 并行、初始 revision 到 head、新数据库约束/权限/表删除。

## 8. 迁移与发布护栏

1. 批次 1、2 可分别合并，因为不改变公开契约；批次 3 必须作为一个前后端纵向切换合并，不能拆开部署。
2. 批次 3 先让代码停止读写旧表；批次 4 才删除旧表和列。项目不做兼容双写，也不允许先删 schema 再修调用方。
3. 批次 4 是停机式收缩发布：停旧进程、迁移、启新进程。若部署环境不能保证停机窗口，先暂停批次 4，不建立兼容层掩盖风险。
4. Alembic 破坏性迁移不提供 downgrade；迁移前通过调用审计和全库搜索证明无读写方，通过临时 PostgreSQL 从初始 revision 升级验证。
5. 每批只修改自己的责任范围；旧文件在批次 3 变为不可达，在批次 4 删除。不得在基础批次顺手删除尚被旧公开入口调用的服务。
6. DeepSeek 关闭时系统必须完全可用；RapidOCR/PyMuPDF 是本地文档解析基础依赖，缺失直接阻止启动，二者不能混用同一种降级策略。
7. 所有清理失败、模型校验失败、事务/文件补偿失败必须结构化记录并使请求失败；不得返回成功后留下孤儿文件或业务行。
8. 任何批次无法运行某项门禁时都要报告具体跳过项和原因；“其余通过”不能替代完整完成声明。

## 9. 完成标准

1. 五批全部完成，且每批定向门禁和最终全量门禁有可追溯结果。
2. PyMuPDF 是唯一 PDF 后端；RapidOCR 按锁定版本、模型、200 DPI、并发/超时/内存和离线哈希配置运行。
3. 运行时代码只保留可关闭的 DeepSeek 纯文本候选阶段；不存在其他 provider、视觉托管调用、fallback 或数据库 Prompt 管理。
4. 公开面只剩统一四端点解析会话、实现无关能力接口和产权证域内附件 API；旧路径返回 404，无兼容转发。
5. 所有候选必须人工逐字段处理；Party/Asset 不自动创建或绑定，已有值不自动覆盖，最终字段来源只取三值契约。
6. 会话和证据仅临时存在，确认/取消/失败/过期后清理；目标业务表不保存页码、片段、坐标、OCR 分数、模型或 provider 信息。
7. 产权证正式附件只使用通用 `Attachment`；新建文件晋升与业务事务可补偿，无专用附件表、孤儿附件或客户端存储路径。
8. 所有保留上传格式经用途 profile 和确定性解析器失败关闭；magic、伪支持格式、无界读取和依赖缺失降级均已删除。
9. Qwen、GLM/Zhipu、Hunyuan、GLM-OCR、DeepSeek 视觉、Prompt 管理、旧 PDF/产权证解析、批量自动确认及其模型/表/权限/前端/测试残留已物理删除。
10. REQ-DOC-001、REQ-RNT-003、REQ-AST-005 的 SSOT、实现证据和测试证据完整，`make check` 或等价门禁通过。
11. 本方案已移入 `docs/archive/backend-plans/`，`docs/plans/README.md` 和 `CHANGELOG.md` 已同步，活跃方案目录无完成态残留。

## 10. Final validation record (2026-07-24)

Completed evidence:

- Document regression suite: `88 passed` across runtime preflight, digital/blank/rotated image page routing, RapidOCR page failure, DeepSeek disabled/timeout/invalid response, Redis session lifecycle, explicit candidate review, attachment compensation, API route cutover, and audit logging.
- Focused backend Ruff and mypy checks passed; full-source mypy passed. Frontend `pnpm check` and `pnpm build` passed after removing stale zero-warning lint findings and a stale `SYSTEM_ROUTES.TEMPLATES` test expectation.
- REQ-DOC-001, REQ-RNT-003, and REQ-AST-005 now point to the unified extraction-session implementation and review evidence in the traceability matrix. No OCR or extraction accuracy claim is made by this record.

Blocked acceptance items:

- A user-provided real scanned contract is available for controlled local validation. Its source file is 24 pages and has no embedded text. It is now accepted as one contract submission rather than rejected or silently truncated: local OCR remains sequential and page-level, while optional DeepSeek receives consecutive batches of at most 20 pages (20 + 4 for this file). Candidates are merged into one review session only after every DeepSeek batch validates; a failed batch discards all DeepSeek candidates and leaves rule/manual review available. The temporary first-20-page derivative run on 2026-07-24 remains a resource observation only: 19 RapidOCR pages, page 18 recorded the recoverable `page_ocr_failed` state, elapsed 68.96 seconds, and sampled process peak RSS was 1624.2 MiB on an Intel Core i5-12400F (6 cores / 12 logical processors, 23.8 GiB RAM). A full current-pipeline run of the original 24-page source also completed without a page-limit rejection, truncation, or document timeout: 23 pages produced RapidOCR text and page 18 retained the explicit `page_ocr_failed` state. It does not prove field accuracy, complete-page success, stamp/low-quality coverage, or an independently reproducible benchmark corpus.
- The real sample requires a human field-by-field review record, including the explicit disposition of page 18, before it can count as accuracy acceptance evidence.
- The dedicated `zcgl_test` database was restored and Redis was started at `localhost:16379` on 2026-07-24. The authentication integration suite passed (`37 passed`), so the prior stalled run was caused by an unavailable Redis dependency rather than an asyncpg cross-event-loop failure. Four cutover-owned regressions were then fixed: retired PDF route and import-E2E guards were removed, the import-E2E Make/CI/script entrypoints were deleted, `llm_prompt` was removed from runtime permission seeds, and the property-certificate `export` permission was seeded. Their focused regression suite passed (`45 passed`). The complete backend command is now green: `4272 passed`, `28 skipped` in 177.26 seconds after aligning stale integration fixtures and full-suite test isolation/observability assertions. This clears the backend full-gate blocker but does not establish real-document field accuracy.
- The frontend full Vitest suite completed successfully: `175 passed` test files and `2101 passed` tests in 1027.48 seconds. This does not remove the backend/full-real-sample blockers.

- Page 18 of the user-supplied original contract was rendered locally at 200 DPI for non-content structure review. It is effectively blank (18 pixels below gray 240 out of 3,867,452), so its `page_ocr_failed` result cannot omit a business field. The visual viewer could not open the local PNG because of a Windows sandbox helper failure; the temporary render is retained only under `.scratch/manual-review/` for the user.

This blocking condition was cleared by the human real-sample review and authorized formal confirmation recorded in §14. The complete backend and frontend gates now pass.
## 10. 2026-07-24 Contract Page Batching Update

This section supersedes earlier wording that treated 20 pages as a whole-contract limit. A contract PDF may contain up to 50 pages and 50 MiB. The system accepts the complete document, preserves its page order, and does not ask the user to split it or silently truncate it. RapidOCR/PyMuPDF processing remains page-by-page with the existing page and whole-document resource guards. When the optional DeepSeek stage is enabled, it sends sequential text-only batches of at most 20 pages, then combines validated candidates into the same human review session. Any failed or invalid batch discards all DeepSeek candidates for that document; rule candidates and manual review continue. Property-certificate PDFs remain capped at 20 pages.

## 11. Follow-up Real-Sample Candidate Evidence (2026-07-24)

A second formal review-session run of the original 24-page scanned contract validated a targeted rule correction without exposing contract text. RapidOCR still produced text for 23 pages, page 18 remained an explicit `page_ocr_failed`, and the session stayed `ready_for_review` with no contract confirmation or contract relation write. The candidate set improved from one contract-number candidate to three: contract number, effective start, and effective end. The start/end values are emitted only when two parseable dates appear in the same rental-term OCR line; the parser accepts non-zero-padded and parenthesized date notation but does not infer missing components.

Month-rent labels occur in table layouts whose numeric cells precede the label or appear on another line. The retained rule intentionally does not associate those values heuristically, so monthly rent remains a required manual review field for this sample. This preserves the approved RapidOCR-plus-human-review boundary and avoids presenting an ungrounded amount candidate.

## 12. UI Real-Sample Review Evidence (2026-07-24)

The replacement contract-import page was exercised against the original 24-page scanned contract through the normal browser upload path. The initial live run exposed two client-boundary failures: the shared API client retained `application/json` for `FormData`, causing FastAPI to reject the missing multipart fields, and the default 30-second browser request timeout expired before synchronous RapidOCR completed. The retained fix removes the JSON content type for browser `FormData`, uses a five-minute no-retry request policy for extraction-session creation, and aligns the Vite and production Nginx proxy timeouts for the create endpoint.

After the fix, the same UI flow waited through the approximately 85-second local OCR run and opened the `ready_for_review` screen. It showed the available contract-number and effective-date candidates plus the explicit `page_ocr_failed` warning. No field action, Party/Asset reference, cancellation, or `Create contract` action was submitted. A direct read check confirmed the latest session remains temporary and `ready_for_review`, while the target project has zero rows in the formal `contracts` table. This is workflow evidence only; human field-by-field review remains the acceptance boundary.

## 13. Empty OCR Result Correction (2026-07-24)

The page-18 warning above was traced to an application normalization defect, not a RapidOCR runtime exception. For a page with no detectable text, RapidOCR returns a result object whose `txts`, `scores`, and `boxes` are `None`. The pipeline called `list(output.txts)`, raised `TypeError`, and incorrectly turned that normal empty result into `page_ocr_failed`.

The page pipeline now normalizes nullable RapidOCR result fields to empty sequences. Genuine OCR exceptions remain page-level failures and are logged with the page number and exception type. A TDD regression test covers the nullable result shape, and the existing genuine-exception test remains in place.

The original 24-page file was rerun directly after the correction: all 24 pages completed with no page errors; page 18 is represented as a successful empty RapidOCR page; elapsed time was 69.22 seconds. The normal browser upload was then repeated against the restarted development service and reached `Review extracted contract fields` with no `page_ocr_failed` warning. No field action, reference binding, cancellation, or `Create contract` action was submitted, and the target project still has zero formal contract rows. Historical temporary sessions retain their original warning state until Redis TTL expiry; they were not rewritten. Human field-by-field review remains the acceptance boundary.

## 14. Acceptance Completion Record (2026-07-25)

The supplied 24-page scanned contract completed through the normal browser path after the empty-OCR normalization correction. All pages completed without page errors; page 18 is a successful empty OCR result and is not presented as an extraction failure.

A human reviewer explicitly handled every required contract field. No candidate, Party, Asset, project binding, or contract record was created automatically. After the user's explicit authorization, the required master data and project binding were created through their normal service and review workflows, and the reviewed contract was formally confirmed.

An independent service-layer readback verified the formal contract, its approved related records, the expected project/asset association, and the compatible revenue-mode/contract-role relationship. This record deliberately excludes document text, identifiers, addresses, parties, and financial values.

The review also exposed a context-validation gap: the import UI previously showed all four contract roles for both revenue modes, while the API deferred compatibility validation until formal confirmation. The UI now exposes only compatible roles and clears an incompatible prior choice when the mode changes; the extraction-session API rejects incompatible pairs before file staging or OCR. Focused backend and frontend regression tests, Ruff, backend mypy, frontend lint/type-check, and the production build passed on 2026-07-25.
