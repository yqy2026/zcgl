# 在现有 PDF 导入链路中灰度并行接入 `langextract` 的实施方案（不破坏主流程）

## Summary

目标是在你现有“`OCR/Vision -> LLM抽字段 -> 合并验证 -> 入库`”链路中，引入 `langextract` 作为**并行抽取器**，先做线上灰度 A/B 与可观测评估，再决定是否切换主链路。  
本方案默认采用你的决策：

- **改造范围**：灰度并行（保留现链路）
- **模型策略**：复用现有云模型（通过 OpenAI 兼容方式优先复用你当前供应商）

---

## 1) 架构设计（决策完成版）

### 1.1 新增角色定位

新增 `LangExtractTextExtractor`，定位为**OCR 文本后的替代抽取器**（不是 OCR 替换器）：

- 输入：`ocr_text`（来自现有 `OCRExtractionService`）
- 输出：与你现有 `smart_result` 对齐的结构（`extracted_fields`、`confidence`、`field_evidence`、`field_sources`、`usage`）
- 不改动上传 API、会话模型、确认导入接口的对外协议

### 1.2 并行运行策略（灰度）

在 `pdf_import_service` 的智能流程中，保留现有主抽取器（vision/ocr-llm），并按灰度条件并行执行 `langextract`：

- 主结果：仍使用现有链路结果作为写库依据
- 对照结果：`langextract` 结果仅记录，不写库
- 可选增强：当主结果低置信度时，允许 `langextract` 结果参与“建议值”但不自动覆盖

### 1.3 路由开关策略

新增配置开关（默认安全）：

- `LANGEXTRACT_ENABLED=false`（总开关）
- `LANGEXTRACT_SHADOW_MODE=true`（只旁路对照）
- `LANGEXTRACT_CANARY_PERCENT=10`（按会话哈希灰度）
- `LANGEXTRACT_TRIGGER=ocr_only`（先只在 OCR 路径触发）
- `LANGEXTRACT_LOW_CONFIDENCE_THRESHOLD=0.70`（低置信触发增强）
- `LANGEXTRACT_PROVIDER=openai_compatible`
- `LANGEXTRACT_MODEL_ID=<你的兼容模型名>`
- `LANGEXTRACT_BASE_URL=<兼容网关地址>`
- `LANGEXTRACT_API_KEY=<密钥>`

---

## 2) 接口与数据契约变更

### 2.1 内部接口新增（不破坏外部 API）

新增内部服务接口：

- `extract_from_ocr_text(ocr_text: str, context: dict) -> LangExtractResult`

新增内部结果模型（映射后落地到现有格式）：

- `LangExtractResult`
  - `success: bool`
  - `extracted_fields: dict[str, Any]`
  - `confidence: float`
  - `field_evidence: dict[str, Any]`（包含字符区间或文本片段）
  - `field_sources: dict[str, str]`（`langextract` / `ocr_llm` / `regex`）
  - `raw_provider_payload: dict[str, Any]`

### 2.2 存储结构兼容扩展

在现有 `processing_result` JSON 中新增可选块（不影响旧消费者）：

- `comparison.langextract`: 对照抽取结果
- `comparison.diff`: 字段差异（主链路 vs langextract）
- `comparison.metrics`: 每份文档的精简评估指标（覆盖率、冲突率等）

---

## 3) 抽取规范（你项目定制）

### 3.1 字段集合

严格对齐现有合同字段（避免下游改造）：

- `contract_number`, `sign_date`
- `landlord_*`, `tenant_*`
- `property_address`, `property_area`
- `lease_start_date`, `lease_end_date`
- `deposit`, `payment_cycle`
- `rent_terms[]`

### 3.2 结果融合规则（灰度阶段）

- 不覆盖主链路写库值
- 对每个字段计算：
  - `agree`（一致）
  - `conflict`（冲突）
  - `missing_in_primary`
  - `missing_in_langextract`
- 仅生成“建议补全字段清单”，供后续是否切换决策

### 3.3 失败与回退

- `langextract` 超时/失败不影响主链路成功
- 所有异常降级为“comparison unavailable”
- 严格限制并发与超时（避免拖慢主任务）

---

## 4) 测试与验收标准

### 4.1 测试场景

- 单元测试
  - 结果映射正确（`langextract -> 现有 ExtractionResult`）
  - 差异计算正确（一致/冲突/缺失）
  - 开关控制生效（禁用、灰度、触发条件）
- 集成测试
  - OCR 文本输入下并行链路可运行
  - 主链路失败/成功时对照链路不影响事务
- 回归测试
  - 现有 `/pdf-import/upload` 到会话状态查询全流程无破坏

### 4.2 验收指标（切换决策门槛）

以 2 周灰度样本为准，满足才进入主链路候选：

- 关键字段 F1 提升 ≥ 5%
- 冲突率 ≤ 8%
- 单文档处理耗时 P95 增幅 ≤ 20%
- 失败率（langextract链路）≤ 3%
- 无新增 P0/P1 数据错误事故

---

## 5) 分阶段落地计划

### Phase A：离线基线（3-5 天）

- 用历史合同样本跑对照
- 产出字段级准确率报告与冲突热图
- 固化 Prompt 与 few-shot 示例

### Phase B：线上影子灰度（5-7 天）

- `LANGEXTRACT_ENABLED=true + SHADOW_MODE=true + 10%`
- 监控指标与日志看板上线
- 每日汇总差异报告

### Phase C：受控增强（3-5 天）

- 对低置信样本启用“建议补全”
- 仍不自动覆盖写库字段
- 评估业务侧复核成本变化

### Phase D：切换决策（评审会）

- 达标：进入“主链路候选方案”
- 不达标：保留为质检工具，终止主链路切换

---

## 6) 风险与控制

- **Provider 兼容风险**：通过显式 provider 配置 + 健康检查规避误路由
- **PII 合规风险**：仅传必要字段文本、日志脱敏、密钥隔离
- **成本风险**：灰度比例与最大并发硬限制
- **稳定性风险**：超时熔断、失败不阻塞主链路

---

## 7) 默认假设（已锁定）

- 不替换现有 OCR 服务
- 不修改前端 API 协议
- 不改变最终写库路径与审批流程
- `langextract` 初期仅用于 OCR 文本场景，不覆盖 vision 直出路径
- 切换决策由量化指标驱动，不主观拍板
