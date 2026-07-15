# RapidOCR 评估（2026-07-15）

> 范围：仅依据 RapidAI/RapidOCR 官方仓库、官方文档、PyPI 元数据，以及必要的上游官方模型资料。下文将“已验证事实”与“推断/建议”分开；未对本项目内部代码做调研。

## 结论摘要

**已验证事实**

- `rapidocr` 是图像级的文本检测（Det）→ 文本行方向分类（Cls）→ 文本识别（Rec）流水线，默认支持中英文，并可切换 PP-OCRv4/v5/v6 与多种语言模型；它不是完整的 PDF/合同结构化解析器。[官方概览](https://rapidai.github.io/RapidOCRDocs/latest/) [模型列表](https://rapidai.github.io/RapidOCRDocs/main/model_list/)
- 核心 Python API 接收路径/URL、`bytes`、NumPy 数组、PIL 图像等**图像输入**，内部用 Pillow/OpenCV 载入；依赖中没有 PDF 渲染库。因此核心包没有文档化的原生 PDF 分页、渲染或文本层提取能力。[输入加载源码](https://github.com/RapidAI/RapidOCR/blob/main/python/rapidocr/utils/load_image.py) [核心依赖](https://github.com/RapidAI/RapidOCR/blob/main/python/requirements.txt)
- 官方伴生项目 `RapidOCRPDF` 才负责 PDF：先用 PyMuPDF 提取已有文本层；无文本或 `force_ocr=True` 时按页渲染，默认 `200 DPI`，再交给 RapidOCR，输出 `[页码, 文本, 平均置信度]`。[RapidOCRPDF 说明](https://github.com/RapidAI/RapidOCRPDF#readme) [PDF 实现](https://github.com/RapidAI/RapidOCRPDF/blob/main/rapidocr_pdf/main.py)
- RapidOCR 的原生结果是文本行四点框、文本、置信度、可选词/字框及阶段耗时；不包含段落、标题、键值、表格单元格、跨页关系或业务字段语义。官方也只称 Markdown 导出为“粗略支持”。[输出说明](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) [Markdown 说明](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/how_to_convert_to_markdown/)

**推断/建议**

- 对“扫描合同转可搜索文本/坐标”而言，RapidOCR 是合适的本地 OCR 基座；对“合同字段、表格、印章关系、条款语义直接结构化”而言，RapidOCR 单独使用能力不足。
- 推荐将它定位为可替换的 OCR 层：`PDF 安全校验与分页渲染 → RapidOCR → 版面/表格层 → 规则或 LLM 字段抽取 → 人工复核`，而不是让其直接承担合同抽取全流程。

## 能力与边界

### 扫描 PDF 与中文 OCR

| 项目 | 已验证事实 | 边界 |
|---|---|---|
| 中文 | 默认配置支持中英文；`rapidocr>=3.9.0` 默认采用 PP-OCRv6 small 检测/识别与 PP-OCRv4 mobile 方向分类。[使用文档](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) | 项目未发布针对中文房地产合同、低清扫描件、印章遮挡或手写补充条款的专用准确率。 |
| PDF | 核心包没有 PDF 页面对象或渲染参数；官方将 PDF 提取放在独立 `RapidOCRPDF` 项目。[周边项目](https://rapidai.github.io/RapidOCRDocs/main/related_projects/) | 调用方必须自行渲染，或引入 `RapidOCRPDF`/其他解析层。DPI、页数限制、加密处理、超时与并发均不属于核心 RapidOCR。 |
| 文本型 PDF | `RapidOCRPDF` 默认优先用 PyMuPDF `page.get_text("text", sort=True)`；只有无文本页或强制模式才 OCR。[实现源码](https://github.com/RapidAI/RapidOCRPDF/blob/main/rapidocr_pdf/main.py) | 文本层存在但质量差时，默认可能不会 OCR；需要基于质量判定决定是否 `force_ocr`。这是实施建议。 |
| 扫描型 PDF | `RapidOCRPDF` 通过 PyMuPDF `page.get_pixmap(dpi=...)` 渲染，默认 200 DPI，逐页 OCR。[实现源码](https://github.com/RapidAI/RapidOCRPDF/blob/main/rapidocr_pdf/main.py) | 200 DPI 不是合同场景质量结论；应以 200/300 DPI 在真实样本上评测准确率、内存和时延。 |

### 引擎、模型与平台

- Python 主包支持 ONNX Runtime、OpenVINO、PaddlePaddle、PyTorch、MNN、TensorRT；Det/Cls/Rec 可分别选择引擎，默认及官方首选起点为 ONNX Runtime CPU。具体模型与引擎组合并非全部互通，例如 PP-OCRv6 的 TensorRT 支持存在组合限制。[引擎文档](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/how_to_use_infer_engine/) [模型矩阵](https://rapidai.github.io/RapidOCRDocs/main/model_list/)
- ONNX Runtime 路径还文档化了 CPU、CANN NPU、Windows DirectML 和实验性 CoreML；TensorRT 首次运行会把 ONNX 转为设备相关 `.engine`，首次启动较慢。[引擎文档](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/how_to_use_infer_engine/)
- 官方架构列出 Python/C++/Java/C# 部署，以及 Windows x86/x64、Linux、Android、Web、Raspberry Pi；这些语言组件现已分散到不同仓库，功能/版本一致性应逐端验证。[官方概览](https://rapidai.github.io/RapidOCRDocs/latest/) [仓库说明](https://github.com/RapidAI/RapidOCR#readme)
- PyPI wheel 标记为 `py3-none-any`，但实际推理依赖 OpenCV 与所选原生运行时，因此“any”不等于所有目标平台零适配。[PyPI 元数据](https://pypi.org/project/rapidocr/)（后半句为工程推断。）

### 输出、版面、表格与表单

- `RapidOCROutput` 提供 `boxes (N,4,2)`、`txts`、`scores`、`word_results`、`elapse_list` 和总耗时；可导出 JSON、Markdown 或可视化图。[输出文档](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) [结果类源码](https://github.com/RapidAI/RapidOCR/blob/main/python/rapidocr/utils/output.py)
- 核心输出没有版面类别、阅读顺序模型、表格结构、公式、键值对或跨页合并。RapidAI 将这些能力放在 `RapidDoc`，其明确增加版面分析、公式/表格识别和阅读顺序恢复；这反证不能把 RapidOCR 的文本框输出等同于文档解析。[RapidDoc 官方仓库](https://github.com/RapidAI/RapidDoc#readme)
- 表单字段可通过坐标规则或后续模型映射，但这是应用层能力；多栏、复杂表格、合并单元格、骑缝章、复选框、手写内容及跨页表格不应宣称由 RapidOCR 原生解决。

## 性能与资源证据

**已验证事实**

- 官方一次对比在 Apple M2、Python 3.10、RapidOCR 3.6.0、ONNX Runtime 1.22.0 上，用单张图片、PP-OCRv5 mobile、10 次串行执行；RapidOCR 约 `0.93–1.26 s`，同脚本中的 PaddleOCR CPU 约 `1.75–1.93 s`。作者明确称该测试“比较粗糙，仅供初步参考”。[官方对比记录](https://rapidai.github.io/RapidOCRDocs/v3.7.0/blog/2026/02/06/rapidocr-vs-paddleocr/)
- 该证据没有报告扫描 PDF 吞吐、并发、峰值内存、中文合同准确率、端到端字段准确率，也不是当前 3.9.1 默认 PP-OCRv6 small 的结果，因此不能外推为生产 SLA。
- PyPI 的 `rapidocr 3.9.1` wheel 为 `27.3 MB`；官方说明包内含检测、方向分类、识别三个默认模型。自 2.0.6 起推理引擎需另装，因此实际镜像/内存占用会显著取决于 ONNX Runtime、OpenVINO、Paddle、PyTorch 或 TensorRT。[PyPI 文件元数据](https://pypi.org/project/rapidocr/) [安装文档](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/install/)
- 非默认模型可自动下载且托管于 ModelScope；默认模型随 wheel 提供。[模型列表](https://rapidai.github.io/RapidOCRDocs/main/model_list/)

**建议的本地基准**

至少按 200/300 DPI、单页/多页、纯中文/中英混排、印章遮挡、旋转、低对比度、表格和手写样本分层，记录字符错误率、关键字段完全匹配率、漏检率、页级 P50/P95、峰值 RSS、冷启动和并发吞吐。任何采用决策应以真实合同集结果为准。

## 许可证、维护与部署安全

### 许可证与商用

- 仓库工程代码采用 Apache-2.0，包含版权许可、专利许可及再分发条件，原则上允许商业使用、修改和分发；再分发仍需履行许可证/版权/NOTICE 等义务，且软件不提供保证。[LICENSE](https://github.com/RapidAI/RapidOCR/blob/main/LICENSE)
- 官方同时声明“OCR 模型版权归百度所有，其他工程代码版权归仓库所有者”。[官方概览](https://rapidai.github.io/RapidOCRDocs/latest/)
- **建议（非法律意见）**：商用上线前按实际锁定的每个模型文件核对来源、模型许可证和 NOTICE，不要仅凭仓库顶层 Apache-2.0 推定所有转换模型的权利链完全相同。

### 维护状态

- 截至 2026-07-15，PyPI 最新稳定版为 `3.9.1`（2026-07-02）；2026 年已有连续多个 3.x 版本，主包处于活跃维护状态。[PyPI 发布历史](https://pypi.org/project/rapidocr/) [GitHub Releases](https://github.com/RapidAI/RapidOCR/releases)
- 官方明确称旧的 `rapidocr_onnxruntime`、`rapidocr_openvino`、`rapidocr_paddle` 将逐渐停止维护，应采用统一的 `rapidocr` 包。[安装文档](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/install/)
- `RapidOCRPDF` 最新 GitHub release 为 0.4.0（2025-05-07），其发布节奏明显慢于主包；若依赖它，应单独做兼容性和错误处理评估。[RapidOCRPDF Releases](https://github.com/RapidAI/RapidOCRPDF/releases)

### 隐私与安全

**已验证事实**

- RapidOCR 支持完全本地离线推理；本地图像加随包默认模型不要求上传文档。[官方概览](https://rapidai.github.io/RapidOCRDocs/latest/) [模型列表](https://rapidai.github.io/RapidOCRDocs/main/model_list/)
- 传入 URL 时，加载器会直接用 `requests.get(..., timeout=60)` 获取内容；非默认模型会自动从外部模型托管下载；调用可视化还可能自动下载字体。[输入加载源码](https://github.com/RapidAI/RapidOCR/blob/main/python/rapidocr/utils/load_image.py) [模型列表](https://rapidai.github.io/RapidOCRDocs/main/model_list/) [快速开始](https://rapidai.github.io/RapidOCRDocs/main/quickstart/)
- GitHub 未检测到项目级 `SECURITY.md`，当前页面也没有已发布安全公告；这不构成无漏洞证明。[Security 页面](https://github.com/RapidAI/RapidOCR/security)

**推断/建议**

- 对外提供服务时不要把任意用户 URL 原样传给 RapidOCR，否则存在 SSRF、超大响应和恶意图像解码风险；只接收已落盘/对象存储白名单内容，并限制格式、字节数、像素数、页数、超时和并发。
- 隔离部署应预置并校验模型/字体哈希、禁用运行时下载、固定依赖版本、以无网络低权限容器运行，并把 PDF 解析和图像解码放在资源受限的工作进程。

## 与云端多模态 LLM 的能力边界

以下为**架构层推断，不是特定供应商基准**：

| 维度 | RapidOCR | 云端多模态 LLM 提取 |
|---|---|---|
| 核心能力 | 字符/文本行定位与识别，输出坐标和置信度。 | 可按提示理解页面语义并直接生成字段/JSON，但格式遵循和事实准确性需验证。 |
| PDF | 核心不处理；需外部渲染或 `RapidOCRPDF`。 | 是否原生接收 PDF、页数/DPI限制取决于具体 API。 |
| 版面/表格/表单 | 不原生理解结构；需 RapidDoc、规则或其他模型。 | 通常更擅长弱模板、跨区域语义和字段归一化，但可能漏项或幻觉。 |
| 可审计性 | 文本框、置信度和图像坐标便于逐项回溯。 | 应强制返回页码/证据区域；仅有生成文本时可追溯性较弱。 |
| 成本与时延 | 本地算力成本，模型较小，可离线；吞吐由自有部署控制。 | 按调用/Token/页面计费并受网络、限流和服务可用性影响。 |
| 隐私 | 可完全内网运行；需管理模型下载与输入 URL 出网。 | 文档会离开本地边界，需审查供应商的数据保留、训练使用、地域和合规条款。 |

## 采用建议

1. **可采用** RapidOCR 作为扫描件 OCR 候选基线，优先验证 `rapidocr 3.9.1 + ONNX Runtime CPU + 默认 PP-OCRv6 small`。
2. **不要将其单独定义为合同智能提取方案**；字段抽取、表格结构、跨页条款和业务校验应由后续层承担。
3. 建议并行评测两条链路：`RapidOCR/版面层 + 文本 LLM` 与 `云端多模态 LLM 直接提取`，统一用字段级精确率/召回率、证据可追溯率、P95、单页成本和人工复核率决策。
4. 在真实样本评测、模型许可证核验、离线镜像固化和安全限制完成前，结论应保持为“候选”，不宜直接进入生产。
