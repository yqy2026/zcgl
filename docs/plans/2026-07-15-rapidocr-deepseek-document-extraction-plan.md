# RapidOCR + DeepSeek 单一 LLM 文档解析收口方案

## Status

📋 待评审（2026-07-15）

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

本方案是实现计划，不在当前步骤修改产品契约。实施发生 API、字段或需求状态变化时，必须在对应提交同步上述 SSOT。

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

### 3.4 依赖与文件校验

- `pymupdf` 当前位于可选 `pdf-basic` extra，但标准开发安装只包含 `dev`，部署能力容易漂移。
- `python-magic` 缺失时文件类型校验会退化为扩展名检查并返回成功，不符合 fail-loud 原则。
- `python-magic` 同时服务 Excel、压缩包等通用上传类型，不能在本方案中未经全量审计直接删除。

RapidOCR 的能力、依赖和风险基线见 [`docs/archive/2026-07-15-rapidocr-evaluation.md`](../archive/2026-07-15-rapidocr-evaluation.md)。历史 [`langextract` 灰度方案](../archive/backend-plans/2026-02-11-langextract-rollout-plan.md) 不再恢复实施；其中“先离线对照再切主链”的评测原则被本方案吸收。

## 4. 目标设计

### 4.1 页面级 PDF 路由

每页独立分类，不再以整份 PDF 的单个 `text/vision` 标签决定处理方式：

1. PyMuPDF 打开文件并检查加密、损坏、页数和尺寸限制。
2. 对每页提取有序文本，并计算字符数、可见字符比例、乱码比例等质量信号。
3. 文本质量达标时直接使用文本层；文本为空或质量不足时渲染该页并调用 RapidOCR。
4. 合并时保留页码、行文本、框坐标和 OCR 分数，供当前临时确认会话构造字段证据。
5. 不同来源的页面按原页序合并，避免混合 PDF 丢页或重复 OCR。

200 DPI 与 300 DPI 均进入离线 POC。正式值由字段准确率、P95 时延和峰值内存共同决定，不直接照搬 RapidOCRPDF 默认值。

### 4.2 RapidOCR 边界

- 直接使用 `rapidocr` 引擎和明确锁定的 ONNX Runtime 后端。
- 不安装 `rapidocr_pdf`，PDF 打开、路由、渲染、临时文件和异常治理继续由项目掌控。
- OCR 是同步 CPU 密集调用，首版使用 `anyio.to_thread.run_sync` 加进程内信号量限制并发；POC 若显示线程隔离不足，再单独评审进程池或任务队列。
- 引擎实例按进程复用，初始化失败必须可观测且使 OCR 能力明确不可用，不能每页重复加载模型或吞掉错误。
- 模型文件必须通过锁文件/镜像固定版本和校验来源；生产部署不得在首次请求时无审计地下载模型。

### 4.3 DeepSeek 文本抽取

删除 provider 枚举和选择器，保留一个职责明确的 `DeepSeekTextClient`：

- 输入只允许文本、字段 Schema、文档类型和必要上下文，不接受图片或 PDF base64。
- 输出必须经过 JSON 解析、Pydantic Schema 和业务规则验证；模型响应不得直接写库。
- `DOCUMENT_LLM_ENABLED=false` 时不要求任何 DeepSeek 配置。
- `DOCUMENT_LLM_ENABLED=true` 时，`DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL` 必须完整，否则应用配置校验失败；不设已过时的隐式模型默认值。
- `DEEPSEEK_BASE_URL` 可默认官方地址，但部署时记录实际地址；只有 DeepSeek 兼容服务可使用，不能借此重新引入通用 provider 路由。
- 429、超时、5xx、非法 JSON 和 Schema 不匹配均记录明确阶段错误，返回规则/OCR 候选并允许手工处理，不切换其他模型。
- OCR 原文可能包含提示注入文本；系统提示、用户文档和输出 Schema 必须分隔，且只信任通过校验的字段值。

DeepSeek 调用策略：

1. 规则先提取合同号、标准日期、金额、面积等稳定字段。
2. DeepSeek 处理主体角色、跨页租期、递增租金、付款周期、服务费条款、限制信息等复杂语义。
3. 规则与 LLM 一致时提高候选可信度；冲突时保留差异并要求人工确认，任何一方都不得静默覆盖。
4. 无 DeepSeek 时仍生成规则候选；产权证若规则不足，可以返回空候选和手工补录入口，而不是伪造低质量结果。

### 4.4 候选、证据与最终字段来源

临时解析结果拆成两个概念：

- `candidate_provenance`：`pdf_text` / `rapidocr` / `rule` / `deepseek`，可含页码、片段、框坐标和分数，仅服务当前解析会话。
- `field_sources`：确认写入时仍严格使用 `manual` / `ocr_prefill_confirmed` / `ocr_prefill_corrected`，不新增 provider 枚举。

字段置信度按字段计算，至少组合以下信号：

- OCR 行分数或数字 PDF 文本质量；
- 规则/DeepSeek 是否一致；
- 类型、范围、日期顺序、金额和面积等业务校验；
- 多处候选是否冲突；
- Party/Asset 候选是否唯一匹配。

禁止继续用“已填字段数量 / 字段总数”代替正确率。具体权重必须由离线标注集校准；校准前只展示保守档位，不宣称概率含义。

### 4.5 文件校验与依赖

文档解析入口先收口 PDF/JPEG/PNG：

- 扩展名、客户端 MIME、固定文件签名三者必须一致。
- PDF 还必须能被 PyMuPDF 成功打开；图片必须能被 Pillow 解码并验证尺寸。
- 扩展名正确但签名错误、截断、加密不可读或解析器拒绝的文件直接报错。

`python-magic` 的全局去留单独处理：先盘点 Excel、CSV、JSON、压缩包等调用方并补确定性验证；在覆盖所有允许类型前保留依赖，但禁止“magic 缺失即按扩展名放行”。全部类型有可靠校验后再删除 `python-magic`，否则将它提升为对应部署的必需依赖并在启动时 fail loud。

依赖目标：

- 新建明确的 `document-processing` extra，至少包含 `pymupdf`、`rapidocr` 和选定的 ONNX Runtime 后端。
- Makefile、CI、开发安装和生产镜像均显式安装该 extra，避免本地可用、部署缺失。
- RapidOCR 验收后删除 `GLM-OCR` SDK/配置；PyMuPDF 成为必需后删除 `pdf2image` 回退及 Poppler 运维说明。
- `pdfplumber`、`markitdown` 是否删除以调用关系审计为准，不在未验证时顺手清理。

## 5. 分阶段实施

### Phase 0：真实样本基线与失败测试

- 建立脱敏标注集，至少覆盖数字合同、扫描合同、数字产权证、扫描产权证和混合页 PDF。
- 样本必须包含旋转、印章遮挡、低清晰度、多页、跨页表格、递增租金、多个主体及无可提取字段场景。
- 固化当前 GLM/视觉/规则链的字段级 precision、recall、人工修正率、P50/P95、峰值 RSS、外部调用次数和失败类型。
- 先补页面路由、无 LLM、DeepSeek 失败和手工补录不阻断的失败测试。
- 在 POC 报告中记录 CPU、内存、操作系统、RapidOCR/ONNX/PyMuPDF/模型版本，保证结果可复现。

**Phase 0 退出条件**：标注集、基线脚本、指标定义和原始结果可复跑；没有真实样本时不得直接切换生产主链。

### Phase 1：PyMuPDF + RapidOCR 独立 OCR 层

- 引入页面级分析结果和统一 `DocumentTextPage` 内部模型。
- 让数字页走 PyMuPDF 文本、扫描页走 RapidOCR；移除“整份文档默认 vision”决策。
- 实现有界并发、超时、临时资源清理、阶段日志和指标。
- 使用 200/300 DPI 跑离线对照，选择正式渲染参数。
- 此阶段 DeepSeek 可关闭，先证明本地 OCR 和规则链独立可用。

**Phase 1 退出条件**：混合 PDF 不漏页、不重复；OCR 失败返回明确阶段错误；事件循环不被同步推理阻塞；真实扫描件指标达到 Phase 0 冻结的采用门槛。

### Phase 2：DeepSeek 单一文本 LLM

- 将现有通用 provider 工厂收缩为单一 DeepSeek 文本客户端。
- 为合同与产权证分别定义结构化输出 Schema，修复当前乱码 Prompt，并补版本化 Prompt 测试。
- 实现规则优先、DeepSeek 补充、冲突显式返回的候选融合。
- 增加超时、429/5xx、非法 JSON、字段越界、提示注入和 PII 日志脱敏测试。
- 配置启用时验证 key/model；禁用时验证零外部请求和完整手工路径。

**Phase 2 退出条件**：代码不存在图片发往 DeepSeek 托管 API 的路径；不存在 provider fallback；模型输出不能绕过 Schema/业务校验。

### Phase 3：端到端解析会话接入

- 合同与产权证统一接入新文本管线，保持既有上传、状态、确认和重试 API 语义。
- 前端继续逐字段确认；只消费临时候选、证据和保守置信档位。
- 确认后只保留既有业务字段与字段来源快照，验证页码、片段、框坐标、OCR/模型信息已清理。
- 将 provider 型系统状态响应改为实现无关的阶段能力状态，或删除无产品用途的调试入口。

**Phase 3 退出条件**：合同和产权证真实端到端用例通过；DeepSeek/RapidOCR 任一失败时仍可完全手工补录；没有自动 Party/Asset 绑定或自动覆盖。

### Phase 4：旧 provider 与重复依赖物理删除

- 删除 Qwen、GLM/Zhipu、Hunyuan 的 service、adapter、factory 分支、配置字段、环境变量、状态文案和专属测试。
- 删除错误的 `DeepSeekVisionService` / `deepseek-vl` 托管路径，只保留 DeepSeek 文本客户端。
- 删除 `LLM_PROVIDER`、`VISION_MODEL`、`EXTRACTION_LLM_PROVIDER` 等 provider 选择配置；环境示例只保留 DeepSeek 与本地 OCR 配置。
- 删除 GLM-OCR 主链与配置；RapidOCR/PyMuPDF 通过依赖门禁后删除 `pdf2image` 回退。
- 全库搜索旧 provider 名称。历史归档可保留事实记录，活跃代码、配置、运行文档和测试不得残留。

**Phase 4 退出条件**：启动、状态接口和日志中不存在可选 provider 概念；旧 API key 不会被读取；运行文档只描述 RapidOCR/PyMuPDF/DeepSeek。

### Phase 5：SSOT、发布与归档

- 按最终行为更新 `docs/integrations/pdf-processing.md`、环境、部署、架构和安全文档。
- 若 API 响应或端点发生变化，同步 `docs/specs/api-contract.md`；若内部临时结构影响字段契约，同步 `docs/specs/domain-model.md`。
- 更新 `docs/traceability/requirements-trace.md` 的 REQ-DOC-001、REQ-RNT-003、REQ-AST-005 代码与测试证据。
- 跑全量门禁和真实样本回归，记录已执行、跳过项和环境限制。
- 完成后将本文件移入 `docs/archive/backend-plans/`，同步 `docs/plans/README.md` 和 `CHANGELOG.md`。

## 6. 采用门槛

Phase 0 必须在看见基线结果后冻结最终数值。初始建议门槛如下：

| 指标 | 初始门槛 |
|------|----------|
| 合同号、主体、起止日期、金额/比例、产权证号等关键字段 precision | 不低于 95% |
| 关键字段 recall | 不低于当前链路，且不得以降低 precision 换取表面覆盖率 |
| 扫描页 OCR 空结果率 | 不高于当前链路 |
| 单文档 P95 | 在约定生产 CPU/内存规格和 20 页上限下不高于 30 秒 |
| 解析失败后的手工路径 | 100% 可用，不要求 LLM key |
| 自动写入、自动绑定、静默覆盖 | 0 次 |
| 旧 provider 外部调用 | 0 次 |

若 200/300 DPI、不同 RapidOCR 模型或 ONNX 后端都不能达标，应停止接入并保留基线报告，不用额外 LLM 兜底掩盖 OCR 问题。

## 7. 关键测试清单

- 数字 PDF、纯扫描 PDF、数字/扫描混合 PDF、JPG/PNG。
- 空白页、旋转页、低清页、印章遮挡、跨页条款、表格和多租金阶段。
- 损坏、截断、加密、超页数、超大小、扩展名/MIME/签名不一致。
- PyMuPDF、RapidOCR 或模型初始化失败；OCR 空结果；临时文件清理失败。
- DeepSeek 禁用、缺配置、超时、429、5xx、非法 JSON、Schema 外字段和提示注入文本。
- 规则与 DeepSeek 一致、冲突、单边缺失、多个 Party/Asset 候选和无匹配候选。
- 低置信未处理阻断确认；确认、修正、显式留空和完全手工补录。
- 确认后不持久化页码、片段、坐标、OCR 分数、模型名或供应商。
- 并发上限、事件循环响应、P95、峰值 RSS、模型冷启动和重复请求资源释放。
- 日志不包含完整 OCR 原文、身份证号、手机号、API key 或 PDF base64。

## 8. 主要风险与决策点

| 风险 | 控制 |
|------|------|
| RapidOCR 对印章、表格或低清中文识别不足 | 真实样本字段级评测；未达门槛不切主链 |
| CPU 推理拖慢 API | 有界并发、线程卸载、资源指标；必要时另评进程隔离 |
| DeepSeek 模型名和服务能力变更 | 模型显式配置，发布前按官方文档验证，不硬编码过时默认值 |
| OCR 文本含敏感信息 | 最小化外发、日志脱敏、超时与保留策略审计；不发送图片 |
| LLM 输出看似合法但业务错误 | Schema + 业务规则 + 冲突展示 + 人工逐字段确认 |
| 一次性删除多 provider 造成大范围回归 | 新链先通过端到端测试，再物理删除旧链；不长期保留双运行时 |
| `python-magic` 去留扩大任务范围 | 文档类型先确定性校验；其他上传类型单独审计后决策 |
| 自托管 DeepSeek-VL2 资源需求过高 | 不纳入本方案；确有视觉需求时新建 ADR/POC 和容量预算 |

## 9. 完成标准

1. RapidOCR 在真实扫描合同和产权证上通过冻结的字段级采用门槛。
2. PyMuPDF 是唯一 PDF 检测、文本提取和渲染后端；混合 PDF 页面级路由可用。
3. 项目运行时代码只保留 DeepSeek 文本 LLM，且 LLM 可关闭、失败可手工继续。
4. Qwen、GLM/Zhipu、Hunyuan 和错误的 DeepSeek 托管视觉路径已物理删除，无兼容别名或静默回退。
5. 候选证据只存在临时会话，最终字段来源符合现有三值契约。
6. 合同与产权证端到端、失败模式、并发性能、安全和 PII 日志测试通过。
7. 受影响 SSOT、环境/部署/架构/安全文档、`CHANGELOG.md` 已同步。
8. `make check` 或 Windows 等价门禁通过，所有跳过项和真实样本环境已显式记录。
9. 方案完成后已移入 `docs/archive/backend-plans/`，活跃方案索引无完成态残留。
