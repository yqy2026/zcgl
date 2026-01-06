# PDF 智能导入技术方案

> **状态**：P2 待实施  
> **核心方案**：PaddleOCR 3.3 + PP-StructureV3  
> **更新日期**：2026-01-04

---

## 一、方案概述

采用 **PaddleOCR 3.3** (2025年5月发布) 作为核心引擎，利用 **PP-StructureV3** 直接输出结构化合同数据。

### 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| PaddleOCR | 3.3+ | OCR 引擎 |
| PP-OCRv5 | 内置 | 中文文字识别 |
| PP-StructureV3 | 内置 | 版面分析 + 表格识别 |
| PaddleOCR-VL-0.9B | 可选 | 视觉语言模型增强 |

---

## 二、核心能力

### 2.1 PP-OCRv5 (2025年5月)

| 特性 | 说明 |
|------|------|
| 模型大小 | 16.2MB (超轻量) |
| 支持文字 | 简体中文/繁体中文/中文拼音/英文/日文 |
| 精度提升 | 比 v4 提升 13% |
| 手写识别 | 支持复杂手写体 |
| CPU 支持 | ✅ 完美支持 |

### 2.2 PP-StructureV3

| 能力 | 说明 |
|------|------|
| 版面分析 | 识别标题/段落/表格/图片区域 |
| 表格识别 | 提取合同中的阶梯租金表 |
| 公式识别 | 识别租金计算公式 |
| 输出格式 | Markdown / JSON |

---

## 三、架构设计

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PDF 扫描件  │ --> │ PP-Structure │ --> │  结构化数据  │ --> │  人工校验    │
│              │     │   V3 解析    │     │  (Markdown)  │     │  + 入库      │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                           │
                           ├── 版面分析
                           ├── OCR 识别 (PP-OCRv5)
                           ├── 表格提取
                           └── 结构化输出
```

---

## 四、实施计划

### Phase 1：升级 PaddleOCR (1周)

- [ ] 升级 PaddleOCR 到 3.3+
- [ ] 验证 PP-StructureV3 表格识别
- [ ] 测试真实合同样本

### Phase 2：集成后端 (1周)

- [ ] 重构 `pdf_import_service.py`
- [ ] 使用 PP-StructureV3 替换现有逻辑
- [ ] 输出 Markdown 结构化数据

### Phase 3：字段映射 (3天)

- [ ] 设计 Markdown → 合同字段映射规则
- [ ] 开发字段提取器
- [ ] 集成校验逻辑

### Phase 4：前端集成 (1周)

- [ ] 更新 PDFImportPage 组件
- [ ] 添加结构化预览
- [ ] 字段校验与修正 UI

---

## 五、代码示例

### 5.1 安装

```bash
# 升级到 PaddleOCR 3.3+
pip install paddleocr>=3.3.0
```

### 5.2 基本使用

```python
from paddleocr import PPStructure

# 初始化 (CPU 模式)
engine = PPStructure(
    use_gpu=False,
    lang='ch',
    table=True,          # 启用表格识别
    layout=True,         # 启用版面分析
    recovery=True,       # 启用文档还原
    structure_version='PP-StructureV3'
)

# 处理合同 PDF
result = engine("contract.pdf")

# 结果解析
for item in result:
    print(f"类型: {item['type']}")
    print(f"内容: {item['res']}")
```

### 5.3 结构化输出示例

```markdown
# 租赁合同

## 合同编号
HT-2024-001

## 当事人信息

| 角色 | 名称 | 地址 |
|------|------|------|
| 甲方（出租方） | XX物业管理有限公司 | XX市XX区XX路XX号 |
| 乙方（承租方） | XX科技有限公司 | XX市XX区XX路XX号 |

## 租赁标的

| 项目 | 内容 |
|------|------|
| 物业名称 | XX大厦A栋501室 |
| 建筑面积 | 120.5平方米 |

## 租赁期限

自 2024年01月01日 起至 2026年12月31日 止

## 租金条款

| 阶段 | 起止日期 | 月租金（元） |
|------|----------|-------------|
| 第一年 | 2024.01-2024.12 | 12,000 |
| 第二年 | 2025.01-2025.12 | 12,600 |
| 第三年 | 2026.01-2026.12 | 13,200 |
```

### 5.4 字段提取

```python
import re

def extract_contract_from_markdown(md_content: str) -> dict:
    """从 PP-StructureV3 输出的 Markdown 提取合同字段"""

    fields = {}

    # 合同编号
    match = re.search(r'合同编号[：:]\s*(\S+)', md_content)
    fields['contract_number'] = match.group(1) if match else None

    # 租赁期限
    match = re.search(r'自\s*(\d{4}年\d{1,2}月\d{1,2}日)\s*起至\s*(\d{4}年\d{1,2}月\d{1,2}日)', md_content)
    if match:
        fields['start_date'] = match.group(1)
        fields['end_date'] = match.group(2)

    # 解析表格中的租金条款
    table_pattern = r'\|\s*第[一二三]年\s*\|\s*([\d./-]+)\s*\|\s*([\d,]+)\s*\|'
    rent_terms = []
    for match in re.finditer(table_pattern, md_content):
        rent_terms.append({
            'period': match.group(1),
            'monthly_rent': float(match.group(2).replace(',', ''))
        })
    fields['rent_terms'] = rent_terms

    return fields
```

---

## 六、配置参数

```python
# config/pdf_import.py

PDF_IMPORT_CONFIG = {
    "paddleocr": {
        "use_gpu": False,
        "lang": "ch",
        "show_log": False,
        "use_angle_cls": True,
        "structure_version": "PP-StructureV3",
    },
    "structure": {
        "table": True,
        "layout": True,
        "recovery": True,
        "output_format": "markdown",  # "markdown" | "json"
    },
    "extraction": {
        "required_fields": [
            "contract_number",
            "party_a", "party_b",
            "start_date", "end_date",
            "monthly_rent", "deposit",
        ],
        "confidence_threshold": 0.8,
    }
}
```

---

## 七、资源需求

| 环境 | CPU | 内存 | GPU | 说明 |
|------|-----|------|-----|------|
| 开发 | 4核+ | 4GB+ | 无需 | PP-StructureV3 纯 CPU |
| 生产 | 8核+ | 8GB+ | 可选 | GPU 可加速处理 |

---

## 八、与现有系统集成

### 替换点

| 现有模块 | 替换方案 |
|----------|----------|
| `pdf_processing_service.py` | 使用 PP-StructureV3 |
| `pdf_import_service.py` | Markdown 解析 + 字段映射 |
| 前端 `PDFImportPage.tsx` | 展示结构化 Markdown |

### API 兼容

保持现有 API 接口不变：
- `POST /api/v1/pdf-import/upload`
- `GET /api/v1/pdf-import/progress/{session_id}`
- `POST /api/v1/pdf-import/confirm_import`

---

## 九、备选方案

如果 PP-StructureV3 效果不佳，可考虑：

| 方案 | 场景 |
|------|------|
| PaddleOCR-VL-0.9B | 更复杂的版面 |
| dots.ocr (1.7B) | 极复杂的扫描件 |
| 云端 API 降级 | 开发调试用 |
