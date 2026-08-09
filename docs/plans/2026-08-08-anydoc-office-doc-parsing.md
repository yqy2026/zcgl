# anydoc（firecrawl）办公文档解析引入评估（备选方案）

## Status

⏸ 搁置（2026-08-08 记录，备选技术方案，无对应活跃 REQ，暂不实施）

## 1. 目标与结论

评估 [firecrawl/anydoc](https://github.com/firecrawl/anydoc) 对本项目文档解析链路的适用性。

**结论：当前阶段无直接用途，不建议引入；作为"非 PDF 办公文档解析"未来场景的备选方案保留。**

理由（详见 §3）：

1. 本项目文档 AI 核心链路是"扫描件 OCR + LLM 结构化字段抽取"，anydoc 只产出 Markdown 文本、不支持图片型 PDF，两者在能力方向上错位。
2. 文本型 PDF 已被现有 PyMuPDF `get_text("text")` 覆盖，引入 anydoc 的替代收益≈0。
3. 触发条件成立时（Word/PPT 附件上传、全文检索、前端本地预览），anydoc 是现成最优解之一，可低成本适配接入（§4）。

## 2. anydoc 能力边界

| 维度 | 说明 |
|------|------|
| 定位 | Firecrawl 开源纯 Rust 库，将办公文档统一转 GitHub-Flavored Markdown（LLM-ready） |
| 支持格式 | `.doc/.docx/.docm`、`.ppt/.pps/.pot/.pptx/.pttm/.ppsx/.ppsm`、`.xls/.xlsx/.xlsm/.xlsb`、`.odt/.ods/.odp`、`.rtf`、`.epub`、`.csv`、`.pdf`（14 种） |
| 性能 | 纯 Rust 无 ML 模型，中位 4.4ms/文档；格式检测基于字节内容而非扩展名 |
| PDF 能力 | 仅文本型 PDF（pdf-inspector 本地转换）；**图片型/扫描 PDF 返回 `Unsupported`**，不做 OCR |
| 绑定 | Node.js（napi）、Python（maturin/PyPI）、WebAssembly（浏览器本地）、CLI |
| 安全 | 内置 ResourceLimit（解压炸弹、嵌套、节点数防护） |
| 依赖 | Rust 核心；Python 侧为 maturin 预编译 wheel（需确认 Python 3.12 wheel 可用性） |
| 许可 | MIT |

参考基准（官方 README 数据）：anydoc 覆盖 14/14 格式、中位 4.4ms，优于 libreoffice / unstructured / markitdown / pandoc / docling / mammoth。

## 3. 与本项目现有链路的对照

本项目现有实现（`backend/src/services/document/`）：

- `page_text_pipeline.py`：PyMuPDF 逐页 `get_text("text")`，文本量不足（<20 字符）的页面 200dpi 光栅化交 RapidOCR；页数/文档超时/光栅字节三重防护。
- `contract_extraction_workflow.py` / `property_certificate_extraction_workflow.py`：OCR/文本 → 确定性规则提取 → 可选 DeepSeek 结构化候选 → Schema/业务校验 → 用户逐字段确认（参考已归档 `2026-07-15-rapidocr-deepseek-document-extraction-plan.md`）。
- Excel 有独立自研管线（`documents/excel/` + `services/excel/`，含模板/预览/导入/导出/状态机），**不得与 anydoc 重叠**。

| 对照维度 | 本项目现有管线 | anydoc | 结论 |
|----------|----------------|--------|------|
| 扫描件/图片型 PDF | RapidOCR 本地 OCR（核心场景） | 不支持（`Unsupported`） | ❌ 覆盖不了核心场景 |
| 产出形态 | 结构化字段候选 + 证据/置信度 | 仅 Markdown 文本 | ❌ 需求形态不同 |
| 文本型 PDF | PyMuPDF 已覆盖 | 转 Markdown 但丢布局 | ⚠️ 替代收益≈0 |
| Word/PPT/ODF/EPUB/RTF | 无解析管线 | 完整支持且快 | ✅ 唯一真实增益区 |

## 4. 潜在接入方案（未来触发时）

触发条件（任一成立即重新评估）：

1. REQ 新增"合同/产权证附件支持 Word/PPT 上传"。
2. 全文检索需要索引上传附件的 Word/PPT 内容。
3. 前端附件本地预览（WASM 绑定，敏感数据不出内网）。

接入方式（保持既有分层，不动 PDF 管线）：

- 依赖：`pip install firecrawl-anydoc`（Python 绑定），Docker/`uv sync` 增 Rust 原生依赖，需先验证 Python 3.12 wheel 可用性。
- 位置：`services/document/` 新增 `office_to_text` 适配层，`anydoc.to_markdown_bytes(data)`（内容自动检测格式）→ 文本行 → 复用 `page_text_pipeline` 的"文本行 → 抽取"接口。
- 边界：只做"读取为文本"，不做模板生成；与 Excel 自研管线不重叠；PDF 路径不引入 anydoc。
- 前端预览备选：`@firecrawl/anydoc-wasm` 浏览器本地转换，`init()` + `toMarkdownBytes()`。

## 5. 引入代价

- Rust 原生依赖进入后端部署面（Docker/uv），增大构建复杂度；需验证 wheel 对 Python 3.12 的可用性。
- 与 Excel 自研管线功能边界需明确，防止重复实现。
- 扫描件 PDF 仍无解，若期望"一个库解决所有格式"则会误判。

## 6. 决策记录

- 2026-08-08：评估完成，结论"当前不引入，保留备选"；无需求变更时不执行 §4 任何动作。
