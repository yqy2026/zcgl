# Vision LLM 配置指南

> 2026-01 更新：支持 4 个 LLM Vision 提供商

## 支持的提供商

| 提供商 | 推荐模型 | 准确率 | 价格 | 推荐 |
|:---|:---|:---|:---|:---|
| **阿里 Qwen** | `qwen3-vl-flash` | ⭐⭐⭐⭐⭐ | ¥1.5/百万 | **🏆 首选** |
| **智谱 GLM** | `glm-4.6v-flash` | ⭐⭐⭐⭐⭐ | 免费 | **免费首选** |
| **腾讯混元** | `hunyuan-vision` | ⭐⭐⭐⭐ | 免费100万 | 备选 |
| DeepSeek | `deepseek-ai/DeepSeek-VL2` | ⭐⭐ | ¥0.99/百万 | 不推荐 |

## .env 配置示例

> 建议在 `.env` 中使用提供商名：`qwen | glm | deepseek | hunyuan`。  
> 旧写法如 `glm-4v` / `qwen-vl-max` 仍兼容，但不推荐（系统会自动归一化为提供商名）。

> 如需“文档提取”使用不同提供商，可额外设置 `EXTRACTION_LLM_PROVIDER` 覆盖 `LLM_PROVIDER`。

> 默认值（未设置 `LLM_PROVIDER`）为 `hunyuan`；若你希望使用 Qwen 的更强效果，请显式设置 `LLM_PROVIDER=qwen`。

### 方案1：阿里 Qwen (推荐)

```bash
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_VISION_MODEL=qwen3-vl-flash
```

### 方案2：智谱 GLM (免费)

```bash
LLM_PROVIDER=glm
ZHIPU_API_KEY=your-api-key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_VISION_MODEL=glm-4.6v-flash
```

### 方案3：腾讯混元（默认，可改）

```bash
LLM_PROVIDER=hunyuan
HUNYUAN_API_KEY=your-api-key
HUNYUAN_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
HUNYUAN_VISION_MODEL=hunyuan-vision
```

### 方案4：硅基流动 DeepSeek (不推荐)

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-siliconflow-api-key
DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
DEEPSEEK_VISION_MODEL=deepseek-ai/DeepSeek-VL2
```

## API 获取方式

| 提供商 | 控制台地址 |
|:---|:---|
| 阿里 Qwen | https://bailian.console.aliyun.com |
| 智谱 GLM | https://open.bigmodel.cn |
| 腾讯混元 | https://console.cloud.tencent.com/hunyuan |
| 硅基流动 | https://siliconflow.cn |

## 使用方法

```python
from src.services.document import get_extraction_manager, DocumentType

# 获取管理器 (自动使用 .env 中配置的提供商)
manager = get_extraction_manager()

# 提取合同
result = await manager.extract("contract.pdf", doc_type=DocumentType.CONTRACT)

# 提取产权证
result = await manager.extract("property.pdf", doc_type=DocumentType.PROPERTY_CERT)
```

## 测试脚本

```bash
cd backend

# 测试 Qwen
python scripts/devtools/experiments/test_qwen_extract.py

# 测试智谱
python scripts/devtools/experiments/test_zhipu_extract.py

# 测试腾讯混元
python scripts/devtools/experiments/test_hunyuan_extract.py
```
