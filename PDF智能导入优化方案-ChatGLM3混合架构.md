# PDF智能导入优化方案 - ChatGLM3-6B Few-Shot学习

## 一、方案概述

### 1.1 核心目标
- **准确率提升**: 70% → 90%+
- **处理速度优化**: 30s → 6-8s
- **人工复核率降低**: 50% → 15%
- **通用性增强**: 支持2类完全不同的合同模板

### 1.2 技术架构
```
规则提取器（快速通道）+ ChatGLM3-6B（智能通道）+ 结果融合验证
```

### 1.3 关键特性
- ✅ 本地CPU推理（无API依赖）
- ✅ Few-Shot学习（2份标注即可）
- ✅ 渐进式降级（规则→LLM→人工）
- ✅ 字段关系验证（逻辑一致性）
- ✅ 流式内存管理（支持100MB+大文件）
- ✅ **用户反馈持续学习（系统越用越准）**

---

## 二、系统架构设计

### 2.1 整体流程图

```
┌─────────────────────────────────────────────────────────────┐
│                     PDF文档上传                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  OCR文本提取（流式处理）                      │
│  - PaddleOCR (扫描件)                                        │
│  - PyMuPDF (电子文档)                                        │
│  - 分块处理避免内存溢出                                       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              文本预处理与模板识别                             │
│  - 清洗OCR噪音                                               │
│  - 关键词匹配识别模板A/B                                      │
│  - 文本分段（合同头/正文/附件）                               │
└────────────────────────┬────────────────────────────────────┘
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
┌─────────────────────┐   ┌─────────────────────┐
│   规则快速提取       │   │  ChatGLM3-6B        │
│  (RuleExtractor)    │   │  Few-Shot提取       │
│                     │   │  (LLMExtractor)     │
│ • 正则表达式         │   │                     │
│ • 关键词定位         │   │ • CPU推理           │
│ • 格式化字段         │   │ • 2类模板Prompt     │
│                     │   │ • JSON结构化输出    │
│ 耗时: <1s           │   │ 耗时: 5-8s          │
│ 准确率: 95%(简单)   │   │ 准确率: 85%(复杂)   │
└──────────┬──────────┘   └──────────┬──────────┘
           │                         │
           └──────────┬──────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                  智能结果融合                                │
│  • 规则结果优先（高置信度）                                  │
│  • LLM补充缺失字段                                           │
│  • 交叉验证一致性                                            │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  字段关系验证                                │
│  • 日期逻辑检查（起租日 < 终止日）                           │
│  • 金额一致性（押金 ≈ 月租×N）                              │
│  • 必填字段完整性                                            │
│  • 格式规范化                                                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  结果输出                                    │
│  • 提取字段 + 置信度                                         │
│  • 低置信度字段标记（人工复核）                               │
│  • 验证错误提示                                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              用户确认/修正 【反馈收集点】                     │
│  • 用户确认正确字段                                          │
│  • 修正错误字段                                              │
│  • 自动收集修正数据                                          │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              持续学习引擎（闭环优化）                         │
│  1. 规则库自动更新（立即生效）                               │
│  2. Prompt模板优化（1周）                                    │
│  3. Few-Shot示例扩充（持续）                                 │
│  4. 增量微调（积累100+样本后）                               │
└────────────────────────┬────────────────────────────────────┘
                         ↓
                   系统准确率提升
                （90% → 95% → 98%）
```

### 2.2 模块职责

| 模块 | 职责 | 输入 | 输出 | 耗时 |
|------|------|------|------|------|
| **TemplateClassifier** | 识别合同类型 | OCR文本 | 'A'/'B'/'unknown' | <0.1s |
| **RuleExtractor** | 规则提取 | 文本+模板类型 | 字段+置信度 | 0.5-1s |
| **ChatGLM3Extractor** | LLM提取 | 文本+Few-Shot示例 | 字段JSON | 5-8s |
| **ResultMerger** | 结果融合 | 规则结果+LLM结果 | 合并结果 | <0.1s |
| **FieldValidator** | 字段验证 | 提取结果 | 验证报告 | <0.2s |
| **FeedbackLearner** | 反馈学习 | 用户修正数据 | 新规则/优化 | 异步 |
| **PromptOptimizer** | Prompt优化 | 高频错误统计 | 优化后的Prompt | 定期 |
| **IncrementalTrainer** | 增量训练 | 训练样本 | 微调模型 | 周期 |

---

## 三、核心模块实现

### 3.1 模板识别器 (TemplateClassifier)

**文件路径**: `backend/src/services/template_classifier.py`

**功能**: 快速判断合同属于哪类模板

**实现原理**:
```python
class TemplateClassifier:
    """合同模板识别器"""
    
    def __init__(self):
        # 从标注模板学习的特征词
        self.template_a_features = {
            'keywords': [
                '广州饮食服务企业集团有限公司',
                '锦洲国际商务中心',
                '解放北路899号',
                '粤房地权证穗字第',
            ],
            'structure_patterns': [
                r'第一条\s*租赁标的',
                r'第二条\s*租赁期限',
                r'第三条\s*租金、保证金',
            ]
        }
        
        self.template_b_features = {
            # 第二类模板的特征（需要补充）
            'keywords': [],
            'structure_patterns': []
        }
    
    def classify(self, text: str) -> dict:
        """
        识别模板类型
        
        Returns:
            {
                'template_type': 'A' | 'B' | 'unknown',
                'confidence': float,
                'matched_features': list
            }
        """
        score_a = self._calculate_score(text, self.template_a_features)
        score_b = self._calculate_score(text, self.template_b_features)
        
        if score_a > score_b and score_a >= 0.6:
            return {
                'template_type': 'A',
                'confidence': score_a,
                'matched_features': self._get_matches(text, self.template_a_features)
            }
        elif score_b > score_a and score_b >= 0.6:
            return {
                'template_type': 'B',
                'confidence': score_b,
                'matched_features': self._get_matches(text, self.template_b_features)
            }
        else:
            return {
                'template_type': 'unknown',
                'confidence': max(score_a, score_b),
                'matched_features': []
            }
    
    def _calculate_score(self, text: str, features: dict) -> float:
        """计算模板匹配分数"""
        # 关键词匹配 (70%权重)
        keyword_score = sum(
            1 for kw in features['keywords'] if kw in text
        ) / len(features['keywords']) if features['keywords'] else 0
        
        # 结构模式匹配 (30%权重)
        pattern_score = sum(
            1 for pattern in features['structure_patterns']
            if re.search(pattern, text)
        ) / len(features['structure_patterns']) if features['structure_patterns'] else 0
        
        return keyword_score * 0.7 + pattern_score * 0.3
    
    def _get_matches(self, text: str, features: dict) -> list:
        """获取匹配到的特征"""
        matches = []
        
        for kw in features['keywords']:
            if kw in text:
                matches.append({'type': 'keyword', 'value': kw})
        
        for pattern in features['structure_patterns']:
            if re.search(pattern, text):
                matches.append({'type': 'pattern', 'value': pattern})
        
        return matches
```

**关键点**:
1. 基于标注模板提取的特征词库
2. 关键词匹配（70%权重）+ 结构模式匹配（30%权重）
3. 置信度阈值0.6，低于则判定为unknown

---

### 3.2 ChatGLM3-6B提取器 (LLMExtractor)

**文件路径**: `backend/src/services/llm_extractor.py`

**功能**: 使用Few-Shot学习提取复杂字段

**核心代码**:

```python
import torch
from transformers import AutoTokenizer, AutoModel
import json
import logging

logger = logging.getLogger(__name__)


class ChatGLM3Extractor:
    """基于ChatGLM3-6B的Few-Shot提取器"""
    
    def __init__(self, model_path: str = "THUDM/chatglm3-6b"):
        """
        初始化LLM提取器
        
        Args:
            model_path: 模型路径（支持本地路径或HF模型ID）
        """
        logger.info(f"正在加载ChatGLM3模型: {model_path}")
        
        # CPU推理配置（关键优化）
        self.device = "cpu"
        torch.set_num_threads(8)  # 根据CPU核心数调整
        
        # 加载tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        
        # 加载模型（CPU优化）
        self.model = AutoModel.from_pretrained(
            model_path,
            trust_remote_code=True,
            device_map="cpu",
            torch_dtype=torch.float16,  # 降低内存
            low_cpu_mem_usage=True,
        ).eval()
        
        logger.info("模型加载完成")
        
        # 加载Few-Shot模板
        self.few_shot_examples = self._load_few_shot_examples()
    
    def _load_few_shot_examples(self) -> dict:
        """加载2份标注模板作为Few-Shot示例"""
        return {
            'A': {
                'text_sample': self._load_template_a_sample(),
                'extracted_json': self._load_template_a_annotation()
            },
            'B': {
                'text_sample': self._load_template_b_sample(),
                'extracted_json': self._load_template_b_annotation()
            }
        }
    
    def _load_template_a_sample(self) -> str:
        """加载模板A的文本示例（从tools/承租合同模版-标注.pdf提取）"""
        return """
租赁合同
合同编号：GZ2024001

出租方（甲方）：广州饮食服务企业集团有限公司
法定代表人：朱明
统一社会信用代码：91440101190494485U
联系地址：广州市越秀区解放北路899号四楼409房
联系人：陈慧君
联系电话：020-83335768

承租方（乙方）：广州五羊产城投资有限公司
法定代表人：吴华军
统一社会信用代码：9144010119048579XP
联系地址：广州市越秀区解放北路899号锦洲国际商务中心408室
联系人：于冠增
联系电话：02083178453

第一条 租赁标的
租赁物业位于广州市越秀区解放北路899号四楼412-413室的房地产
权属证号：粤房地权证穗字第0150069957号
出租面积为295平方米
证载用途为餐厅
租赁用途：办公

第二条 租赁期限
本合同租赁期限3年，自2024年11月1日起至2026年9月30日止

第三条 租金、保证金
租赁期限              月租金额（人民币）元    租金年增幅
2024年11月1日至
2025年9月30日         11832                  /
2025年10月1日至
2026年9月30日         12187                  3%

保证金：人民币叁万陆仟伍佰陆拾壹元整（¥36561）

签订日期：2024年10月15日
"""
    
    def _load_template_a_annotation(self) -> str:
        """模板A的标注结果（JSON格式）"""
        return json.dumps({
            "contract_number": "GZ2024001",
            "landlord_name": "广州饮食服务企业集团有限公司",
            "tenant_name": "广州五羊产城投资有限公司",
            "property_address": "广州市越秀区解放北路899号四楼412-413室",
            "property_area": 295,
            "property_certificate": "粤房地权证穗字第0150069957号",
            "property_usage": "餐厅",
            "rental_purpose": "办公",
            "start_date": "2024-11-01",
            "end_date": "2026-09-30",
            "lease_period_1": "2024年11月1日至2025年9月30日",
            "lease_period_2": "2025年10月1日至2026年9月30日",
            "monthly_rent_1": 11832,
            "monthly_rent_2": 12187,
            "rent_increase_rate": 3,
            "total_deposit": 36561,
            "signing_date": "2024-10-15"
        }, ensure_ascii=False, indent=2)
    
    def _load_template_b_sample(self) -> str:
        """加载模板B的文本示例（需要补充第二类模板）"""
        # TODO: 补充第二类模板的示例
        return ""
    
    def _load_template_b_annotation(self) -> str:
        """模板B的标注结果（需要补充）"""
        # TODO: 补充第二类模板的标注
        return "{}"
    
    def build_prompt(self, text: str, template_type: str, focus_fields: list = None) -> str:
        """
        构建Few-Shot Prompt
        
        Args:
            text: 待提取的合同文本
            template_type: 'A' | 'B' | 'unknown'
            focus_fields: 需要重点提取的字段列表
        """
        # 选择对应的Few-Shot示例
        if template_type in self.few_shot_examples:
            example = self.few_shot_examples[template_type]
        else:
            # 未知模板，使用模板A作为通用示例
            example = self.few_shot_examples['A']
        
        # 构建提示词
        prompt = f"""你是专业的租赁合同信息提取助手。

【参考示例 - {template_type}类合同】
合同原文:
{example['text_sample']}

提取结果:
{example['extracted_json']}

【提取规则】
1. 严格提取以下15个字段，字段名必须与示例一致
2. 找不到的字段返回null（不要猜测或推理）
3. 日期格式统一为: YYYY-MM-DD
4. 金额仅保留数字，单位：元
5. 保持原文表述，不要改写
6. 仅返回JSON，不要任何解释文字

【待提取合同】
{text[:3000]}

【输出】纯JSON格式:
```json
"""
        
        if focus_fields:
            prompt += f"\n# 重点关注字段: {', '.join(focus_fields)}\n"
        
        return prompt
    
    def extract(
        self, 
        text: str, 
        template_type: str = 'unknown',
        focus_fields: list = None
    ) -> dict:
        """
        提取合同信息
        
        Returns:
            提取的字段字典
        """
        try:
            # 构建prompt
            prompt = self.build_prompt(text, template_type, focus_fields)
            
            # 模型推理
            logger.info("开始LLM推理...")
            response, history = self.model.chat(
                self.tokenizer,
                prompt,
                max_length=2048,
                temperature=0.1,  # 降低随机性
                top_p=0.7
            )
            
            logger.info(f"LLM原始输出: {response[:200]}...")
            
            # 解析JSON结果
            extracted = self._parse_json_response(response)
            
            return extracted
            
        except Exception as e:
            logger.error(f"LLM提取失败: {e}")
            return {}
    
    def _parse_json_response(self, response: str) -> dict:
        """从LLM响应中提取JSON"""
        try:
            # 提取JSON代码块
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            # 解析JSON
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始响应: {response}")
            return {}
```

**性能优化要点**:
1. `torch.set_num_threads(8)`: 利用多核CPU
2. `torch_dtype=torch.float16`: 降低内存占用50%
3. `temperature=0.1`: 降低输出随机性，提升稳定性
4. 文本截断3000字符: 避免超出token限制

---

### 3.3 混合提取协调器 (HybridExtractor)

**文件路径**: `backend/src/services/hybrid_extractor.py`

**功能**: 协调规则和LLM提取，智能融合结果

```python
class HybridContractExtractor:
    """规则+LLM混合提取协调器"""
    
    def __init__(self):
        self.template_classifier = TemplateClassifier()
        self.rule_extractor = ContractExtractor()  # 复用现有
        self.llm_extractor = ChatGLM3Extractor()
        self.validator = FieldValidator()
    
    def extract(self, text: str) -> dict:
        """
        混合提取主流程
        
        Returns:
            {
                'extracted_fields': {...},
                'metadata': {
                    'template_type': 'A',
                    'extraction_method': 'hybrid',
                    'rule_fields_count': 10,
                    'llm_fields_count': 5,
                    'total_confidence': 0.89,
                    'processing_time': 6.5
                },
                'validation_errors': [...]
            }
        """
        import time
        start_time = time.time()
        
        # 1. 模板识别
        template_info = self.template_classifier.classify(text)
        template_type = template_info['template_type']
        
        logger.info(f"识别为{template_type}类模板，置信度: {template_info['confidence']:.2f}")
        
        # 2. 规则快速提取
        rule_result = self.rule_extractor.extract_contract_info(text)
        rule_fields = rule_result.get('extracted_fields', {})
        
        # 3. 判断是否需要LLM增强
        need_llm = self._should_use_llm(rule_fields)
        
        llm_fields = {}
        if need_llm:
            # 识别低置信度字段
            focus_fields = self._identify_focus_fields(rule_fields)
            
            logger.info(f"启动LLM增强，关注字段: {focus_fields}")
            
            # LLM提取
            llm_fields = self.llm_extractor.extract(
                text,
                template_type=template_type,
                focus_fields=focus_fields
            )
        
        # 4. 结果融合
        merged = self._merge_results(rule_fields, llm_fields)
        
        # 5. 字段验证
        validation_errors = self.validator.validate(merged)
        
        # 6. 构建结果
        processing_time = time.time() - start_time
        
        return {
            'extracted_fields': merged,
            'metadata': {
                'template_type': template_type,
                'extraction_method': 'hybrid' if need_llm else 'rule_only',
                'rule_fields_count': len(rule_fields),
                'llm_fields_count': len(llm_fields),
                'total_confidence': self._calculate_avg_confidence(merged),
                'processing_time': processing_time
            },
            'validation_errors': validation_errors
        }
    
    def _should_use_llm(self, rule_fields: dict) -> bool:
        """判断是否需要LLM增强"""
        # 必填字段列表
        required_fields = [
            'contract_number', 'landlord_name', 'tenant_name',
            'property_address', 'property_area', 
            'start_date', 'end_date', 'monthly_rent'
        ]
        
        # 检查必填字段缺失数量
        missing_count = sum(
            1 for field in required_fields 
            if field not in rule_fields or 
               rule_fields[field].get('confidence', 0) < 0.6
        )
        
        # 缺失>=3个必填字段，启用LLM
        return missing_count >= 3
    
    def _identify_focus_fields(self, rule_fields: dict) -> list:
        """识别需要LLM重点提取的字段"""
        focus = []
        
        for field, data in rule_fields.items():
            if data.get('confidence', 0) < 0.6:
                focus.append(field)
        
        # 补充缺失的必填字段
        required = [
            'contract_number', 'landlord_name', 'tenant_name',
            'property_address', 'start_date', 'end_date'
        ]
        
        for field in required:
            if field not in rule_fields and field not in focus:
                focus.append(field)
        
        return focus
    
    def _merge_results(self, rule_fields: dict, llm_fields: dict) -> dict:
        """
        融合规则和LLM结果
        
        策略:
        1. 规则高置信度(>0.8) → 优先使用
        2. 规则低置信度(<0.6) → LLM覆盖
        3. 规则中等(0.6-0.8) → 比较一致性
        4. 规则缺失 → 使用LLM
        """
        merged = {}
        
        # 处理规则结果
        for field, data in rule_fields.items():
            conf = data.get('confidence', 0)
            value = data.get('value')
            
            if conf >= 0.8:
                # 高置信度，直接采用
                merged[field] = {
                    'value': value,
                    'confidence': conf,
                    'source': 'rule',
                    'source_text': data.get('source_text', '')
                }
            elif conf >= 0.6:
                # 中等置信度，待LLM验证
                merged[field] = {
                    'value': value,
                    'confidence': conf,
                    'source': 'rule_pending',
                    'source_text': data.get('source_text', '')
                }
            # 低置信度，等待LLM覆盖
        
        # 处理LLM结果
        for field, value in llm_fields.items():
            if value is None:
                continue
            
            if field not in merged:
                # 规则未提取，使用LLM
                merged[field] = {
                    'value': value,
                    'confidence': 0.75,  # LLM默认置信度
                    'source': 'llm'
                }
            elif merged[field].get('source') == 'rule_pending':
                # 中等置信度，比较一致性
                rule_value = str(merged[field]['value']).strip()
                llm_value = str(value).strip()
                
                if rule_value == llm_value:
                    # 一致，提升置信度
                    merged[field]['confidence'] = 0.95
                    merged[field]['source'] = 'rule+llm'
                else:
                    # 不一致，使用LLM（通常更准确）
                    merged[field] = {
                        'value': value,
                        'confidence': 0.8,
                        'source': 'llm_override',
                        'rule_value': rule_value  # 保留规则值供调试
                    }
            elif merged[field].get('confidence', 0) < 0.6:
                # 低置信度，LLM覆盖
                merged[field] = {
                    'value': value,
                    'confidence': 0.75,
                    'source': 'llm_override'
                }
        
        return merged
    
    def _calculate_avg_confidence(self, fields: dict) -> float:
        """计算平均置信度"""
        if not fields:
            return 0.0
        
        total = sum(f.get('confidence', 0) for f in fields.values())
        return total / len(fields)
```

**融合策略关键点**:
- 规则置信度>0.8: 直接采用（快速通道）
- 规则置信度0.6-0.8: 与LLM交叉验证
- 规则置信度<0.6: LLM覆盖
- 一致性验证: 规则+LLM结果相同时，置信度提升至0.95

---

### 3.4 字段验证器 (FieldValidator)

**文件路径**: `backend/src/services/field_validator.py`

**功能**: 验证字段逻辑一致性，标记异常

```python
from datetime import datetime
import re

class FieldValidator:
    """字段关系验证器"""
    
    def validate(self, fields: dict) -> list:
        """
        验证提取的字段
        
        Returns:
            错误列表 [{field, error, severity}]
        """
        errors = []
        
        # 提取字段值（简化访问）
        values = {k: v.get('value') for k, v in fields.items()}
        
        # 1. 必填字段检查
        required = [
            'contract_number', 'landlord_name', 'tenant_name',
            'property_address', 'start_date', 'end_date'
        ]
        
        for field in required:
            if field not in values or not values[field]:
                errors.append({
                    'field': field,
                    'error': '必填字段缺失',
                    'severity': 'error'
                })
        
        # 2. 日期逻辑验证
        if 'start_date' in values and 'end_date' in values:
            try:
                start = self._parse_date(values['start_date'])
                end = self._parse_date(values['end_date'])
                
                if start >= end:
                    errors.append({
                        'field': 'start_date,end_date',
                        'error': f'起租日({start})不能晚于终止日({end})',
                        'severity': 'error'
                    })
            except:
                errors.append({
                    'field': 'start_date,end_date',
                    'error': '日期格式错误',
                    'severity': 'warning'
                })
        
        # 3. 租金一致性验证
        if all(k in values for k in ['monthly_rent_1', 'monthly_rent_2', 'rent_increase_rate']):
            try:
                rent1 = float(values['monthly_rent_1'])
                rent2 = float(values['monthly_rent_2'])
                rate = float(values['rent_increase_rate']) / 100
                
                expected_rent2 = rent1 * (1 + rate)
                
                if abs(rent2 - expected_rent2) > 10:  # 允许10元误差
                    errors.append({
                        'field': 'monthly_rent_2',
                        'error': f'第二期租金({rent2})与增幅({rate:.1%})不一致，预期:{expected_rent2:.2f}',
                        'severity': 'warning'
                    })
            except:
                pass
        
        # 4. 押金合理性
        if 'total_deposit' in values and 'monthly_rent_1' in values:
            try:
                deposit = float(values['total_deposit'])
                monthly_rent = float(values['monthly_rent_1'])
                
                # 押金通常是1-6个月租金
                if deposit < monthly_rent * 0.5 or deposit > monthly_rent * 12:
                    errors.append({
                        'field': 'total_deposit',
                        'error': f'押金({deposit})不在合理范围（{monthly_rent*0.5:.0f}-{monthly_rent*12:.0f}）',
                        'severity': 'warning'
                    })
            except:
                pass
        
        # 5. 面积合理性
        if 'property_area' in values:
            try:
                area = float(values['property_area'])
                if area < 10 or area > 100000:
                    errors.append({
                        'field': 'property_area',
                        'error': f'面积({area})超出合理范围',
                        'severity': 'warning'
                    })
            except:
                pass
        
        return errors
    
    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        # 支持多种格式
        formats = [
            '%Y-%m-%d',
            '%Y年%m月%d日',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except:
                continue
        
        raise ValueError(f"无法解析日期: {date_str}")
```

**验证规则**:
1. 必填字段完整性检查
2. 日期逻辑验证（起租日<终止日）
3. 租金递增一致性（rent2 = rent1 × (1+rate)）
4. 押金合理范围（0.5-12倍月租金）
5. 面积合理范围（10-100000㎡）

---

## 四、集成到现有系统

### 4.1 修改PDF处理服务

**文件**: `backend/src/services/pdf_processing_service.py`

```python
class PDFProcessingService:
    def __init__(self):
        # ... 现有代码 ...
        
        # 新增混合提取器
        self.hybrid_extractor = HybridContractExtractor()
    
    async def process_contract_pdf(self, file_path: str, **kwargs) -> dict:
        """
        处理合同PDF（集成混合提取）
        """
        try:
            # 1. OCR提取文本（复用现有逻辑，支持流式处理）
            ocr_result = await self._extract_with_ocr(file_path, **kwargs)
            text = ocr_result.get('text', '')
            
            # 2. 使用混合提取器
            extraction_result = self.hybrid_extractor.extract(text)
            
            # 3. 格式化返回
            return {
                'success': True,
                'text': text,
                'extracted_fields': extraction_result['extracted_fields'],
                'metadata': extraction_result['metadata'],
                'validation_errors': extraction_result['validation_errors'],
                'ocr_confidence': ocr_result.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"PDF处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
```

### 4.2 API层调整

**文件**: `backend/src/api/v1/pdf_import_unified.py`

```python
@router.post("/{session_id}/extract")
async def extract_contract_info(
    session_id: str,
    use_llm: bool = Query(default=True, description="是否启用LLM增强"),
    db: Session = Depends(get_db)
):
    """
    提取合同信息（支持LLM增强）
    """
    # ... 现有验证逻辑 ...
    
    # 调用混合提取
    result = await pdf_service.process_contract_pdf(
        file_path=session.file_path,
        use_llm=use_llm  # 可控制是否启用LLM
    )
    
    # 更新session
    session.extracted_info = result['extracted_fields']
    session.extraction_metadata = result['metadata']
    
    # 标记低置信度字段需要人工复核
    if result['validation_errors']:
        session.validation_errors = result['validation_errors']
        session.requires_review = True
    
    db.commit()
    
    return {
        'success': result['success'],
        'extracted_fields': result['extracted_fields'],
        'metadata': result['metadata'],
        'validation_errors': result['validation_errors']
    }
```

---

## 五、部署配置

### 5.1 环境依赖

**文件**: `backend/requirements.txt`

```txt
# 现有依赖...

# LLM相关（新增）
torch>=2.0.0
transformers>=4.35.0
sentencepiece>=0.1.99
protobuf>=3.20.0
accelerate>=0.24.0
```

### 5.2 模型下载与部署

#### 方案A: 自动下载（推荐）
```bash
# 首次运行时自动下载到 ~/.cache/huggingface/
# 无需手动操作
```

#### 方案B: 手动下载（网络受限环境）
```bash
# 1. 在有网络的机器下载
git lfs install
git clone https://huggingface.co/THUDM/chatglm3-6b

# 2. 拷贝到服务器
scp -r chatglm3-6b server:/app/models/

# 3. 修改模型路径
# llm_extractor.py 中修改：
model_path = "/app/models/chatglm3-6b"
```

### 5.3 性能调优配置

**文件**: `backend/config/llm_config.py`

```python
LLM_CONFIG = {
    # CPU线程数（根据服务器核心数调整）
    'cpu_threads': 8,
    
    # 最大输入长度（token）
    'max_input_length': 2048,
    
    # 温度参数（控制随机性）
    'temperature': 0.1,
    
    # Top-P采样
    'top_p': 0.7,
    
    # 是否启用LLM（可动态关闭降级到纯规则）
    'enable_llm': True,
    
    # LLM超时时间（秒）
    'llm_timeout': 15,
    
    # 触发LLM的阈值
    'llm_trigger_threshold': {
        'missing_required_fields': 3,  # 缺失必填字段数
        'low_confidence_threshold': 0.6  # 低置信度阈值
    },
    
    # 流式内存管理
    'stream_processing': {
        'chunk_size_mb': 10,  # 每次处理10MB
        'max_memory_mb': 1000  # 最大内存限制1GB
    }
}
```

### 5.4 启动脚本

**文件**: `scripts/start_with_llm.sh`

```bash
#!/bin/bash

# 设置环境变量
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export TRANSFORMERS_CACHE=/app/models/cache

# 启动服务
python -m uvicorn backend.src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --timeout-keep-alive 300
```

---

## 六、测试与验证

### 6.1 单元测试

**文件**: `tests/test_hybrid_extractor.py`

```python
import pytest
from backend.src.services.hybrid_extractor import HybridContractExtractor
from backend.src.services.field_validator import FieldValidator

def test_template_a_extraction():
    """测试模板A提取"""
    extractor = HybridContractExtractor()
    
    # 使用标注模板的文本
    test_text = """
    租赁合同
    合同编号：GZ2024001
    出租方（甲方）：广州饮食服务企业集团有限公司
    ...
    """
    
    result = extractor.extract(test_text)
    
    # 验证关键字段
    assert result['metadata']['template_type'] == 'A'
    assert 'contract_number' in result['extracted_fields']
    assert result['extracted_fields']['contract_number']['value'] == 'GZ2024001'
    assert result['metadata']['total_confidence'] > 0.85

def test_field_validation():
    """测试字段验证"""
    validator = FieldValidator()
    
    # 错误的日期逻辑
    fields = {
        'start_date': {'value': '2024-12-01'},
        'end_date': {'value': '2024-01-01'}  # 早于起租日
    }
    
    errors = validator.validate(fields)
    
    assert len(errors) > 0
    assert any('起租日' in e['error'] for e in errors)

def test_rule_llm_merge():
    """测试规则和LLM结果融合"""
    extractor = HybridContractExtractor()
    
    rule_fields = {
        'contract_number': {'value': 'GZ001', 'confidence': 0.9},
        'landlord_name': {'value': '广州饮食', 'confidence': 0.5}  # 低置信度
    }
    
    llm_fields = {
        'landlord_name': '广州饮食服务企业集团有限公司'
    }
    
    merged = extractor._merge_results(rule_fields, llm_fields)
    
    # 规则高置信度字段保留
    assert merged['contract_number']['value'] == 'GZ001'
    assert merged['contract_number']['source'] == 'rule'
    
    # 低置信度被LLM覆盖
    assert merged['landlord_name']['value'] == '广州饮食服务企业集团有限公司'
    assert merged['landlord_name']['source'] == 'llm_override'
```

### 6.2 性能基准测试

**文件**: `tests/benchmark_extraction.py`

```python
import time
from pathlib import Path
import json

def benchmark_extraction():
    """性能基准测试"""
    extractor = HybridContractExtractor()
    
    test_pdfs = list(Path("tests/fixtures/contracts").glob("*.pdf"))
    
    results = {
        'rule_only': [],
        'hybrid': [],
        'accuracies': [],
        'llm_usage': 0
    }
    
    for pdf in test_pdfs:
        # 提取文本
        text = extract_text_from_pdf(pdf)
        
        # 测试规则提取
        start = time.time()
        rule_result = extractor.rule_extractor.extract_contract_info(text)
        results['rule_only'].append(time.time() - start)
        
        # 测试混合提取
        start = time.time()
        hybrid_result = extractor.extract(text)
        results['hybrid'].append(time.time() - start)
        
        # 统计LLM使用
        if hybrid_result['metadata']['extraction_method'] == 'hybrid':
            results['llm_usage'] += 1
        
        # 计算准确率（与人工标注对比）
        ground_truth = load_ground_truth(pdf)
        accuracy = calculate_accuracy(hybrid_result, ground_truth)
        results['accuracies'].append(accuracy)
    
    # 输出报告
    print("========== 性能测试报告 ==========")
    print(f"测试样本数: {len(test_pdfs)}")
    print(f"规则提取平均耗时: {sum(results['rule_only'])/len(results['rule_only']):.2f}s")
    print(f"混合提取平均耗时: {sum(results['hybrid'])/len(results['hybrid']):.2f}s")
    print(f"LLM使用率: {results['llm_usage']/len(test_pdfs):.1%}")
    print(f"平均准确率: {sum(results['accuracies'])/len(results['accuracies']):.2%}")
    
    # 保存详细结果
    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def calculate_accuracy(result: dict, ground_truth: dict) -> float:
    """计算准确率"""
    extracted = result['extracted_fields']
    
    correct = 0
    total = len(ground_truth)
    
    for field, expected_value in ground_truth.items():
        if field in extracted:
            actual_value = extracted[field].get('value')
            if str(actual_value).strip() == str(expected_value).strip():
                correct += 1
    
    return correct / total if total > 0 else 0.0
```

---

## 七、运维监控

### 7.1 性能监控指标

**文件**: `backend/src/monitoring/extraction_metrics.py`

```python
from dataclasses import dataclass
from typing import Dict
import time

@dataclass
class ExtractionMetrics:
    """提取性能指标"""
    
    # 处理速度
    avg_processing_time: float = 0.0
    rule_only_ratio: float = 0.0  # 纯规则处理占比
    llm_usage_ratio: float = 0.0  # LLM使用占比
    
    # 准确率
    field_accuracy: Dict[str, float] = None  # 各字段准确率
    overall_confidence: float = 0.0
    
    # 资源使用
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    
    # 错误率
    validation_error_rate: float = 0.0
    llm_timeout_rate: float = 0.0

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics_history = []
    
    def record_extraction(self, result: dict):
        """记录单次提取指标"""
        metrics = {
            'timestamp': time.time(),
            'processing_time': result['metadata']['processing_time'],
            'extraction_method': result['metadata']['extraction_method'],
            'confidence': result['metadata']['total_confidence'],
            'field_count': len(result['extracted_fields']),
            'validation_errors': len(result['validation_errors'])
        }
        
        self.metrics_history.append(metrics)
    
    def get_statistics(self, time_window: int = 3600) -> dict:
        """获取统计数据（默认最近1小时）"""
        current_time = time.time()
        recent = [
            m for m in self.metrics_history 
            if current_time - m['timestamp'] < time_window
        ]
        
        if not recent:
            return {}
        
        return {
            'total_requests': len(recent),
            'avg_processing_time': sum(m['processing_time'] for m in recent) / len(recent),
            'llm_usage_ratio': sum(1 for m in recent if m['extraction_method'] == 'hybrid') / len(recent),
            'avg_confidence': sum(m['confidence'] for m in recent) / len(recent),
            'error_rate': sum(1 for m in recent if m['validation_errors'] > 0) / len(recent)
        }
```

### 7.2 日志记录

**文件**: `backend/src/services/hybrid_extractor.py`（添加日志）

```python
import logging
import json

logger = logging.getLogger(__name__)

# 在extract方法中添加结构化日志
def extract(self, text: str) -> dict:
    # ... 现有代码 ...
    
    # 记录提取完成日志
    logger.info(
        "提取完成",
        extra={
            'template_type': template_info['template_type'],
            'extraction_method': 'hybrid' if need_llm else 'rule_only',
            'processing_time': processing_time,
            'field_count': len(merged),
            'confidence': self._calculate_avg_confidence(merged),
            'validation_errors': len(validation_errors),
            'llm_used': need_llm
        }
    )
    
    # 如果有验证错误，记录警告
    if validation_errors:
        logger.warning(
            "字段验证发现问题",
            extra={
                'errors': validation_errors
            }
        )
    
    return result
```

### 7.3 监控面板配置（Grafana）

```json
{
  "dashboard": {
    "title": "PDF智能提取监控",
    "panels": [
      {
        "title": "处理速度",
        "targets": [
          {"metric": "avg_processing_time"}
        ]
      },
      {
        "title": "LLM使用率",
        "targets": [
          {"metric": "llm_usage_ratio"}
        ]
      },
      {
        "title": "提取准确率",
        "targets": [
          {"metric": "avg_confidence"}
        ]
      },
      {
        "title": "错误率",
        "targets": [
          {"metric": "validation_error_rate"}
        ]
      }
    ]
  }
}
```

---

## 八、持续学习与反馈优化

### 8.1 数据闭环架构

**核心思想**: 基于用户确认阶段的反馈信息，让系统持续学习改进，越用越准。

```
用户上传PDF
    ↓
系统自动提取（LLM+规则）
    ↓
用户确认/修正 ←【关键反馈点】
    ↓
┌─────────────────────────────┐
│   反馈数据收集与标注         │
│  - 原始提取结果              │
│  - 用户修正后的正确值         │
│  - 修正字段、修正类型         │
└────────────┬─────────────────┘
             ↓
┌─────────────────────────────┐
│   持续学习引擎               │
│  1. 规则库自动更新           │
│  2. Prompt模板优化           │
│  3. 错误模式识别             │
│  4. Few-Shot示例扩充         │
└────────────┬─────────────────┘
             ↓
         系统优化
   （90% → 95% → 98%）
```

### 8.2 三级学习策略

#### 策略A: 规则库自动扩充（短期，立即见效）

**文件**: `backend/src/services/feedback_learner.py`

**原理**: 从用户修正中学习新的提取规则

```python
class FeedbackLearner:
    """基于反馈的规则学习器"""
    
    def __init__(self):
        self.learned_rules = defaultdict(list)
        self.db = get_db()
    
    def learn_from_correction(self, correction_data: dict) -> bool:
        """
        从用户修正中学习
        
        Args:
            correction_data: {
                'field_name': 'contract_number',
                'original_value': 'GZ001',  # 系统提取的
                'corrected_value': 'GZ-2024-001',  # 用户修正的
                'source_text': '合同编号：GZ-2024-001',  # 原文
                'extraction_method': 'rule'
            }
        """
        field = correction_data['field_name']
        source_text = correction_data['source_text']
        correct_value = correction_data['corrected_value']
        
        # 1. 分析修正模式
        pattern = self._extract_pattern(source_text, correct_value)
        
        if not pattern:
            return False
        
        # 2. 生成新规则
        new_rule = self._generate_rule(field, pattern)
        
        # 3. 验证规则质量（避免过拟合）
        if self._validate_rule(new_rule, field):
            # 4. 添加到规则库
            self._add_to_rule_base(field, new_rule)
            
            # 5. 持久化存储
            self._persist_rule(field, new_rule, correction_data)
            
            logger.info(f"学习到新规则: {field} -> {new_rule}")
            return True
        
        return False
    
    def _extract_pattern(self, source_text: str, value: str) -> str:
        """从原文和正确值中提取模式"""
        # 找到值在原文中的位置
        idx = source_text.find(value)
        if idx == -1:
            return None
        
        # 提取前缀和后缀
        prefix = source_text[max(0, idx-20):idx]
        suffix = source_text[idx+len(value):idx+len(value)+20]
        
        # 推断值的格式模式
        value_pattern = self._infer_value_pattern(value)
        
        # 构建正则模式
        return f"{re.escape(prefix[-10:])}({value_pattern})"
    
    def _infer_value_pattern(self, value: str) -> str:
        """推断值的格式模式"""
        # GZ-2024-001 -> [A-Z]+-\d{4}-\d+
        if re.match(r'^[A-Z]+-\d{4}-\d+$', value):
            return r'[A-Z]+-\d{4}-\d+'
        # 日期格式
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return r'\d{4}-\d{2}-\d{2}'
        # 数字
        elif value.replace('.', '').isdigit():
            return r'\d+(?:\.\d+)?'
        # 默认：非空白字符
        else:
            return r'\S+'
    
    def _validate_rule(self, new_rule: str, field: str) -> bool:
        """验证规则质量（防止过度拟合）"""
        # 检查是否与现有规则重复
        existing_rules = self.learned_rules.get(field, [])
        if new_rule in existing_rules:
            return False
        
        # 检查规则是否过于宽泛
        if len(new_rule) < 10:  # 太短的规则可能误匹配
            return False
        
        return True
    
    def _add_to_rule_base(self, field: str, rule: str):
        """添加到运行时规则库"""
        self.learned_rules[field].append(rule)
        
        # 更新ContractExtractor的规则
        from .contract_extractor import ContractExtractor
        extractor = ContractExtractor()
        
        if field not in extractor.extraction_rules:
            extractor.extraction_rules[field] = []
        
        extractor.extraction_rules[field].insert(0, rule)  # 插入到前面，优先匹配
    
    def _persist_rule(self, field: str, rule: str, correction: dict):
        """持久化存储学到的规则"""
        learned_rule = LearnedRule(
            id=str(uuid.uuid4()),
            field_name=field,
            rule_pattern=rule,
            source_correction_id=correction.get('id'),
            confidence_score=0.8,  # 初始置信度
            usage_count=0,
            success_count=0,
            created_at=datetime.now()
        )
        
        self.db.add(learned_rule)
        self.db.commit()
```

**效果**:
- ✅ 立即生效，每次修正后规则库自动增强
- ✅ 无需人工干预
- ✅ 适合修正频繁的字段
- 📈 预期准确率提升10-20次修正后 +5%

---

#### 策略B: Prompt模板动态优化（中期）

**文件**: `backend/src/services/prompt_optimizer.py`

**原理**: 基于高频错误更新Few-Shot示例

```python
class PromptOptimizer:
    """Prompt模板优化器"""
    
    def __init__(self):
        self.error_patterns = defaultdict(list)  # 错误模式统计
        self.correction_examples = []  # 修正示例库
        self.optimization_threshold = 10  # 触发优化的阈值
    
    def collect_correction(self, correction: dict):
        """收集修正案例"""
        field = correction['field_name']
        
        # 记录错误模式
        self.error_patterns[field].append({
            'wrong': correction['original_value'],
            'correct': correction['corrected_value'],
            'source': correction['source_text'],
            'timestamp': datetime.now()
        })
        
        # 达到阈值后优化Prompt
        if len(self.error_patterns[field]) >= self.optimization_threshold:
            self._optimize_prompt(field)
    
    def _optimize_prompt(self, field: str):
        """优化特定字段的Prompt"""
        errors = self.error_patterns[field]
        
        # 1. 分析高频错误类型
        error_types = self._analyze_error_types(errors)
        
        # 2. 生成针对性的提示
        hints = []
        for error_type, examples in error_types.items():
            if error_type == 'format_error':
                # 格式错误：如 "GZ001" 应为 "GZ-2024-001"
                correct_format = examples[0]['correct']
                hints.append(f"{field}的标准格式示例：{correct_format}")
            
            elif error_type == 'incomplete':
                # 不完整：如只提取了公司名的前半部分
                hints.append(f"{field}需要完整提取，包含所有部分")
            
            elif error_type == 'extra_content':
                # 多余内容：如包含了标点符号
                hints.append(f"{field}仅提取核心内容，不包含标点符号")
        
        # 3. 更新Prompt模板
        self._update_prompt_template(field, hints)
        
        # 4. 选择最佳示例加入Few-Shot
        best_examples = self._select_best_examples(errors, top_k=3)
        self._add_to_few_shot(field, best_examples)
        
        logger.info(f"Prompt优化完成: {field}, 添加{len(hints)}条提示")
    
    def _analyze_error_types(self, errors: list) -> dict:
        """分析错误类型"""
        categorized = defaultdict(list)
        
        for error in errors:
            wrong = str(error['wrong']).strip()
            correct = str(error['correct']).strip()
            
            # 判断错误类型
            if len(wrong) < len(correct) * 0.5:
                categorized['incomplete'].append(error)
            elif len(wrong) > len(correct) * 1.5:
                categorized['extra_content'].append(error)
            elif wrong.replace('-', '') == correct.replace('-', ''):
                categorized['format_error'].append(error)
            else:
                categorized['other'].append(error)
        
        return categorized
    
    def _update_prompt_template(self, field: str, hints: list):
        """更新Prompt模板"""
        from .llm_extractor import ChatGLM3Extractor
        extractor = ChatGLM3Extractor()
        
        # 在Prompt中添加针对性提示
        field_hints = "\n".join(f"  - {hint}" for hint in hints)
        
        # 更新全局Prompt配置
        # (实际实现时修改ChatGLM3Extractor.build_prompt方法)
        extractor.field_specific_hints[field] = field_hints
    
    def _select_best_examples(self, errors: list, top_k: int = 3) -> list:
        """选择最佳示例加入Few-Shot"""
        # 选择最近的、最典型的错误案例
        recent_errors = sorted(errors, key=lambda x: x['timestamp'], reverse=True)
        return recent_errors[:top_k]
    
    def _add_to_few_shot(self, field: str, examples: list):
        """添加到Few-Shot示例库"""
        for example in examples:
            self.correction_examples.append({
                'field': field,
                'input': example['source'],
                'output': example['correct']
            })
        
        logger.info(f"添加{len(examples)}个Few-Shot示例：{field}")
    
    def get_stats(self) -> dict:
        """获取优化统计"""
        return {
            'total_corrections': sum(len(v) for v in self.error_patterns.values()),
            'optimized_fields': [k for k, v in self.error_patterns.items() if len(v) >= self.optimization_threshold],
            'few_shot_examples': len(self.correction_examples)
        }
```

**效果**:
- 🎯 针对高频错误字段强化Prompt
- 📈 动态扩充Few-Shot示例库
- 🚀 预期准确率提升50-100次修正后 +8%

---

#### 策略C: 增量微调（长期，最佳效果）

**文件**: `backend/src/services/incremental_trainer.py`

**原理**: 积累足够反馈数据后，微调LLM模型

```python
from peft import LoraConfig, get_peft_model, TaskType

class IncrementalTrainer:
    """增量训练器（使用LoRA轻量级微调）"""
    
    def __init__(self):
        self.training_buffer = []  # 训练数据缓冲
        self.min_samples = 100  # 最小训练样本数
        self.db = get_db()
    
    def add_training_sample(self, correction: dict, original_text: str):
        """添加训练样本"""
        # 构建训练样本
        sample = {
            'input': original_text[:3000],  # 限制长度
            'output': {
                correction['field_name']: correction['corrected_value']
            },
            'timestamp': datetime.now()
        }
        
        self.training_buffer.append(sample)
        
        # 达到阈值触发训练
        if len(self.training_buffer) >= self.min_samples:
            self._trigger_incremental_training()
    
    def _trigger_incremental_training(self):
        """触发增量训练"""
        logger.info(f"开始增量训练，样本数: {len(self.training_buffer)}")
        
        try:
            # 1. 准备训练数据
            train_data = self._prepare_training_data()
            
            # 2. LoRA微调（轻量级）
            self._lora_finetune(train_data)
            
            # 3. 验证新模型
            if self._validate_new_model():
                # 4. 热更新模型
                self._update_model()
                
                # 5. 清空缓冲区
                self._archive_buffer()
                self.training_buffer = []
                
                logger.info("增量训练完成，模型已更新")
            else:
                logger.warning("新模型验证失败，保持原有模型")
        
        except Exception as e:
            logger.error(f"增量训练失败: {e}")
    
    def _prepare_training_data(self) -> list:
        """准备训练数据"""
        # 转换为模型训练格式
        train_data = []
        
        for sample in self.training_buffer:
            # 构建输入Prompt
            input_text = self._build_training_prompt(sample['input'])
            
            # 构建输出JSON
            output_json = json.dumps(sample['output'], ensure_ascii=False)
            
            train_data.append({
                'input': input_text,
                'output': output_json
            })
        
        return train_data
    
    def _lora_finetune(self, train_data: list):
        """使用LoRA进行轻量级微调"""
        from .llm_extractor import ChatGLM3Extractor
        extractor = ChatGLM3Extractor()
        
        # LoRA配置（仅训练少量参数）
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=8,  # LoRA秩
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["query_key_value"],  # ChatGLM3特定模块
        )
        
        # 创建PEFT模型
        peft_model = get_peft_model(extractor.model, lora_config)
        
        # 训练配置
        training_args = {
            'learning_rate': 1e-4,
            'num_train_epochs': 3,
            'per_device_train_batch_size': 1,
            'gradient_accumulation_steps': 4,
            'save_steps': 100,
            'logging_steps': 10
        }
        
        # 执行训练（约5-10分钟）
        # (实际实现时使用transformers.Trainer)
        # trainer = Trainer(
        #     model=peft_model,
        #     args=training_args,
        #     train_dataset=train_data
        # )
        # trainer.train()
        
        # 保存LoRA权重（仅几MB）
        peft_model.save_pretrained("./models/lora_weights")
        
        logger.info("LoRA微调完成")
    
    def _validate_new_model(self) -> bool:
        """验证新模型效果"""
        # 使用验证集测试新模型
        # 如果准确率提升，则接受新模型
        
        # TODO: 实际验证逻辑
        return True
    
    def _update_model(self):
        """热更新模型（无需重启服务）"""
        from .llm_extractor import ChatGLM3Extractor
        
        # 加载LoRA权重
        # extractor = ChatGLM3Extractor()
        # extractor.model = PeftModel.from_pretrained(
        #     extractor.model,
        #     "./models/lora_weights"
        # )
        
        logger.info("模型已热更新")
    
    def _archive_buffer(self):
        """归档已使用的训练数据"""
        # 将已使用的训练数据存储到数据库
        for sample in self.training_buffer:
            training_record = TrainingRecord(
                id=str(uuid.uuid4()),
                input_text=sample['input'],
                output_json=json.dumps(sample['output']),
                used_in_training=True,
                created_at=sample['timestamp']
            )
            self.db.add(training_record)
        
        self.db.commit()
```

**效果**:
- 🎯 效果最佳，准确率可提升10-20%
- ⚡ LoRA微调快速（5-10分钟）
- 💾 存储小（仅需保存LoRA权重，几MB）
- 🔄 可热更新，无需重启服务
- 📈 预期准确率提升100-500次修正后 +15%

---

### 8.3 反馈数据收集

**文件**: `backend/src/api/v1/pdf_import_unified.py`

```python
@router.post("/{session_id}/confirm")
async def confirm_extraction(
    session_id: str,
    confirmed_data: dict,
    db: Session = Depends(get_db)
):
    """
    用户确认提取结果（收集反馈）
    """
    session = db.query(PDFImportSession).filter_by(id=session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取系统原始提取结果
    original_extraction = session.extracted_info
    
    # 对比用户修正
    corrections = []
    for field, user_value in confirmed_data.items():
        original_data = original_extraction.get(field, {})
        original_value = original_data.get('value')
        
        if str(original_value) != str(user_value):
            # 发现修正
            correction = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'field_name': field,
                'original_value': original_value,
                'corrected_value': user_value,
                'source_text': session.text,  # 原始PDF文本
                'extraction_method': original_data.get('source'),
                'template_type': session.template_type,
                'confidence': original_data.get('confidence'),
                'timestamp': datetime.now()
            }
            corrections.append(correction)
    
    # 保存反馈数据
    if corrections:
        feedback_service = FeedbackService()
        feedback_service.save_corrections(session_id, corrections)
        
        # 触发学习
        learning_service = LearningService()
        learning_service.learn_from_corrections(corrections)
        
        logger.info(f"收集到{len(corrections)}条修正反馈，已触发学习")
    
    # 更新session为已确认
    session.status = 'confirmed'
    session.confirmed_data = confirmed_data
    session.correction_count = len(corrections)
    db.commit()
    
    return {
        'success': True,
        'corrections_count': len(corrections),
        'learning_triggered': len(corrections) > 0,
        'message': f"已收集{len(corrections)}条修正反馈"
    }
```

---

### 8.4 反馈数据模型

**文件**: `backend/src/models/extraction_feedback.py`

```python
class ExtractionFeedback(Base):
    """提取反馈表"""
    __tablename__ = 'extraction_feedbacks'
    
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('pdf_import_sessions.id'))
    
    # 修正信息
    field_name = Column(String)  # 字段名
    original_value = Column(String)  # 系统提取值
    corrected_value = Column(String)  # 用户修正值
    source_text = Column(Text)  # 原文片段
    extraction_method = Column(String)  # rule/llm
    template_type = Column(String)  # A/B/unknown
    confidence = Column(Float)  # 原始置信度
    
    # 学习状态
    is_learned = Column(Boolean, default=False)  # 是否已学习
    learned_at = Column(DateTime, nullable=True)
    learned_rule = Column(String, nullable=True)  # 学到的规则
    learned_method = Column(String, nullable=True)  # rule/prompt/training
    
    created_at = Column(DateTime, default=datetime.now)


class LearnedRule(Base):
    """学到的规则表"""
    __tablename__ = 'learned_rules'
    
    id = Column(String, primary_key=True)
    field_name = Column(String)
    rule_pattern = Column(String)  # 正则表达式
    source_correction_id = Column(String, ForeignKey('extraction_feedbacks.id'))
    
    # 规则评估
    confidence_score = Column(Float, default=0.8)
    usage_count = Column(Integer, default=0)  # 使用次数
    success_count = Column(Integer, default=0)  # 成功次数
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

---

### 8.5 学习服务编排

**文件**: `backend/src/services/learning_service.py`

```python
class LearningService:
    """持续学习服务编排器"""
    
    def __init__(self):
        self.feedback_learner = FeedbackLearner()
        self.prompt_optimizer = PromptOptimizer()
        self.incremental_trainer = IncrementalTrainer()
    
    def learn_from_corrections(self, corrections: list):
        """从修正中学习（多级策略）"""
        for correction in corrections:
            # 1. 规则学习（立即生效）
            rule_learned = self.feedback_learner.learn_from_correction(correction)
            
            # 2. Prompt优化（收集统计）
            self.prompt_optimizer.collect_correction(correction)
            
            # 3. 增量训练（积累样本）
            self.incremental_trainer.add_training_sample(
                correction,
                correction['source_text']
            )
            
            # 4. 记录学习状态
            self._mark_as_learned(correction, rule_learned)
    
    def _mark_as_learned(self, correction: dict, rule_learned: bool):
        """标记为已学习"""
        db = get_db()
        feedback = db.query(ExtractionFeedback).filter_by(
            id=correction['id']
        ).first()
        
        if feedback:
            feedback.is_learned = True
            feedback.learned_at = datetime.now()
            feedback.learned_method = 'rule' if rule_learned else 'prompt'
            db.commit()
    
    def get_learning_stats(self, time_window: int = 86400) -> dict:
        """获取学习统计（默认24小时）"""
        db = get_db()
        
        # 统计最近时间窗口内的数据
        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        
        total_corrections = db.query(ExtractionFeedback).filter(
            ExtractionFeedback.created_at >= cutoff_time
        ).count()
        
        learned_corrections = db.query(ExtractionFeedback).filter(
            ExtractionFeedback.created_at >= cutoff_time,
            ExtractionFeedback.is_learned == True
        ).count()
        
        rules_learned = db.query(LearnedRule).filter(
            LearnedRule.created_at >= cutoff_time
        ).count()
        
        return {
            'total_corrections': total_corrections,
            'learned_corrections': learned_corrections,
            'learning_rate': learned_corrections / total_corrections if total_corrections > 0 else 0,
            'rules_learned': rules_learned,
            'prompt_optimizations': self.prompt_optimizer.get_stats(),
            'training_samples': len(self.incremental_trainer.training_buffer),
            'accuracy_improvement': self._calculate_improvement()
        }
    
    def _calculate_improvement(self) -> float:
        """计算准确率提升"""
        # 对比最近的提取准确率与基准线
        # TODO: 实际实现
        return 0.05  # 示例: 5%提升
```

---

### 8.6 效果预期

#### 准确率提升曲线

```
准确率
  │
98%├─────────────────────── 增量微调后
  │                    ╭───
95%├────────────────╭──╯
  │             ╭──╯
92%├────────────╭╯ Prompt优化后
  │       ╭───╯
90%├──────╭╯ 规则学习后
  │  ╭──╯
88%├─╭╯ 初始状态
  │
  └────────────────────────> 时间
    0   20  50  100 200 500 (修正次数)
```

#### 量化收益

| 学习阶段 | 时间 | 准确率提升 | 所需反馈数 | 实施难度 |
|---------|------|-----------|-----------|----------|
| **规则学习** | 立即 | +5% | 每字段10-20次 | ⭐⭐ |
| **Prompt优化** | 1周 | +8% | 每字段50-100次 | ⭐⭐⭐ |
| **增量微调** | 1月 | +15% | 全局100-500次 | ⭐⭐⭐⭐ |

---

## 九、实施时间表（更新）

### Week 1: 基础设施（5天）

#### Day 1-2: ChatGLM3-6B部署与测试
- [ ] 安装依赖（torch, transformers等）
- [ ] 下载ChatGLM3-6b模型
- [ ] CPU推理测试
- [ ] 性能基准测试（推理速度、内存占用）

#### Day 3-4: Few-Shot示例准备
- [ ] 从`tools/承租合同模版-标注.pdf`提取完整文本
- [ ] 准备模板A的标注JSON
- [ ] 收集模板B样本并标注
- [ ] 构建Prompt模板库

#### Day 5: 模板分类器开发
- [ ] 提取模板A特征词
- [ ] 提取模板B特征词
- [ ] 实现`TemplateClassifier`
- [ ] 单元测试

### Week 2: 核心开发（5天）

#### Day 1-2: LLM提取器开发
- [ ] 实现`ChatGLM3Extractor`基础框架
- [ ] 实现Few-Shot Prompt构建逻辑
- [ ] 实现JSON解析逻辑
- [ ] Prompt工程优化（测试不同temperature/top_p）

#### Day 3: 混合提取协调器
- [ ] 实现`HybridContractExtractor`
- [ ] 实现规则/LLM结果融合逻辑
- [ ] 实现LLM触发条件判断
- [ ] 集成测试

#### Day 4: 字段验证器 + 反馈收集
- [ ] 实现`FieldValidator`
- [ ] 实现各类验证规则
- [ ] **实现反馈数据收集API**
- [ ] **创建反馈数据表**

#### Day 5: API集成 + 规则学习
- [ ] 修改`PDFProcessingService`
- [ ] 更新API接口
- [ ] **实现`FeedbackLearner`（规则学习）**
- [ ] 集成测试

### Week 3: 测试与优化（5天）

#### Day 1-2: 功能测试 + 反馈验证
- [ ] 模板A合同测试（20份）
- [ ] 模板B合同测试（20份）
- [ ] 非标合同测试（10份）
- [ ] **测试反馈收集流程**
- [ ] **验证规则学习效果**

#### Day 3: 性能优化 + Prompt优化器
- [ ] CPU推理调优（线程数、batch size）
- [ ] 流式内存管理优化
- [ ] **实现`PromptOptimizer`**
- [ ] 压力测试

#### Day 4: 准确率测试 + 学习统计
- [ ] 对比人工标注计算准确率
- [ ] 错误案例分析
- [ ] Prompt迭代优化
- [ ] **学习统计面板开发**

#### Day 5: 上线准备
- [ ] 部署脚本编写
- [ ] 监控配置（添加学习指标）
- [ ] 日志配置
- [ ] 发布文档

### Week 4+: 持续优化（长期）

#### Month 1: 数据积累与规则优化
- [ ] 收集50-100条用户反馈
- [ ] 监控规则学习效果
- [ ] 优化低质量规则
- [ ] 生成学习效果报告

#### Month 2-3: Prompt优化与训练准备
- [ ] Prompt模板全面优化
- [ ] 积累100+训练样本
- [ ] 准备增量微调环境
- [ ] 实现`IncrementalTrainer`

#### Month 4+: 增量微调与深度优化
- [ ] 执行首次LoRA微调
- [ ] A/B测试新旧模型
- [ ] 建立定期重训机制
- [ ] 持续优化学习策略

---

## 九、风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **LLM推理速度慢** | 用户体验差 | 中 | 1. 增加规则覆盖率降低LLM调用频率<br>2. 异步处理+WebSocket实时进度<br>3. 缓存常见合同结果<br>**4. 规则学习自动减少LLM依赖** |
| **模型占用内存过大** | 服务器OOM | 中 | 1. 监控内存使用<br>2. 限制并发数（建议2-3个）<br>3. 考虑INT8/INT4量化 |
| **LLM输出不稳定** | 准确率下降 | 低 | 1. 降低temperature至0.1<br>2. 多次采样取最优（3次投票）<br>3. 规则验证兜底<br>**4. 反馈学习修正Prompt** |
| **模板B特征不足** | 识别率低 | 高 | 1. 尽快收集5-10份模板B样本<br>2. 人工补充特征词库<br>3. 降级到通用处理<br>**4. 反馈学习自动扩充特征** |
| **CPU推理超时** | 请求失败 | 中 | 1. 设置15s超时<br>2. 超时降级到纯规则<br>3. 考虑异步队列处理 |
| **学习样本不足** | 持续优化受限 | 中 | 1. 鼓励用户反馈<br>2. 内测期主动收集<br>3. 人工标注补充 |

---

## 十、预期收益

### 10.1 量化指标

| 指标 | 当前 | 目标 | 提升幅度 | 说明 |
|------|------|------|---------|------|
| **整体准确率** | 70% | 90%+ (初始) → 98% (学习后) | **+29% → +40%** | 基于Few-Shot学习+持续优化 |
| **模板A准确率** | 75% | 95%+ → 99% | **+27% → +32%** | 规则+LLM双保险+反馈学习 |
| **模板B准确率** | 65% | 90%+ → 96% | **+38% → +48%** | LLM通用性强+自动特征扩充 |
| **非标合同准确率** | 40% | 75%+ → 88% | **+88% → +120%** | LLM处理能力+持续学习 |
| **平均处理时间** | 30s | 6-8s → 4-6s | **-73% → -80%** | 规则快速通道+学习减少LLM调用 |
| **人工复核率** | 50% | 15% → 8% | **-70% → -84%** | 验证器自动检测+准确率提升 |
| **必填字段完整度** | 60% | 95% → 98% | **+58% → +63%** | LLM补充缺失+反馈优化 |
| **支持模板类型** | 有限 | 通用 → 自动扩展 | **无限** | Few-Shot扩展+自动特征学习 |

### 10.2 业务价值

#### 成本节约
- **人力成本**: 复核工作量减少70%，每天节约2-3人时
- **时间成本**: 处理速度提升4倍，可支持更大规模业务
- **返工成本**: 准确率提升减少错误返工
- **标注成本**: 用户日常使用即产生训练数据，**零标注成本**

#### 效率提升
- **处理能力**: 从每天处理50份提升至200份
- **响应速度**: 从30秒降至6-8秒，用户等待时间大幅减少
- **自动化率**: 从50%提升至85%

#### 系统增强
- **鲁棒性**: 支持非标准合同，适应性强
- **扩展性**: 新模板仅需1份标注即可接入
- **可维护性**: 模块化设计，易于调试优化
- **自进化能力**: **系统越用越准，持续学习不断进步**

---

## 十一、后续优化方向

### 11.1 短期优化（1-3个月）

#### 1. 模型性能优化
- [ ] 评估INT8量化（进一步降低内存）
- [ ] 尝试模型蒸馏（减小模型体积）
- [ ] 优化Prompt模板（基于错误案例）

#### 2. 数据闭环建设
- [ ] 收集人工复核数据
- [ ] 建立错误案例库
- [ ] 定期更新特征词库

#### 3. 功能增强
- [ ] 支持更多合同类型（3-5类）
- [ ] 实现断点续传（大文件）
- [ ] 添加批量处理接口

### 11.2 中期优化（3-6个月）

#### 1. 模型升级
- [ ] 评估ChatGLM4或Qwen2等更新模型
- [ ] 尝试LayoutLM处理复杂表格
- [ ] 研究多模态模型（文字+图像）

#### 2. 性能提升
- [ ] 引入GPU加速（如资源允许）
- [ ] 实现智能缓存（相似合同复用结果）
- [ ] 优化并发处理策略

#### 3. 智能增强
- [ ] 合同条款风险识别
- [ ] 异常条款检测
- [ ] 合同类型自动分类

### 11.3 长期规划（6-12个月）

#### 1. 平台化建设
- [ ] 支持多语言合同处理
- [ ] 构建合同知识图谱
- [ ] 开发合同比对功能

#### 2. AI能力深化
- [ ] 微调专用合同模型
- [ ] 实现合同摘要生成
- [ ] 智能问答系统

#### 3. 业务扩展
- [ ] 支持更多文档类型（发票、证书等）
- [ ] 提供API服务对外开放
- [ ] 建立行业标准库

---

## 十二、关键文件清单

### 新增文件

```
backend/src/services/
├── template_classifier.py      # 模板识别器
├── llm_extractor.py           # ChatGLM3提取器
├── hybrid_extractor.py        # 混合提取协调器
├── field_validator.py         # 字段验证器
├── feedback_learner.py        # 反馈学习器 ⭐️
├── prompt_optimizer.py        # Prompt优化器 ⭐️
├── incremental_trainer.py     # 增量训练器 ⭐️
└── learning_service.py        # 学习服务编排 ⭐️

backend/config/
└── llm_config.py              # LLM配置

backend/src/monitoring/
└── extraction_metrics.py      # 性能监控

backend/src/models/
├── extraction_feedback.py     # 反馈数据模型 ⭐️
└── learned_rule.py            # 学到的规则模型 ⭐️

tests/
├── test_hybrid_extractor.py   # 单元测试
└── benchmark_extraction.py    # 性能测试

scripts/
└── start_with_llm.sh          # 启动脚本

tools/
├── 承租合同模版-标注.pdf        # 模板A标注（已有）
└── 模板B标注.pdf               # 模板B标注（待补充）
```

### 修改文件

```
backend/src/services/
└── pdf_processing_service.py  # 集成混合提取器

backend/src/api/v1/
└── pdf_import_unified.py      # 添加LLM控制参数

backend/requirements.txt       # 添加LLM依赖
```

---

## 十三、总结

### 核心优势

✅ **准确率提升20%** (70%→90%+)  
✅ **速度提升4倍** (30s→6-8s)  
✅ **人工复核减少70%**  
✅ **零API依赖，完全本地部署**  
✅ **流式内存管理，支持100MB+大文件**

### 技术亮点

1. **Few-Shot学习**: 仅需2份标注，标注成本极低
2. **混合架构**: 规则+LLM互补，性能与准确率兼顾
3. **智能降级**: 规则→LLM→人工，三级保障
4. **本地部署**: 数据安全可控，无外部依赖
5. **易于扩展**: 新模板1份标注即可快速接入
6. **持续学习**: 用户反馈自动优化，系统越用越准 ⭐️

### 实施建议

**优先级排序**:
1. **P0（立即启动）**: Week 1基础设施 + 模板A提取
2. **P1（1周内）**: Week 2核心开发 + 模板B补充
3. **P2（2周内）**: Week 3测试优化 + 上线部署

**成功关键**:
- 尽快补充模板B的标注样本
- CPU推理性能调优（线程数、内存管理）
- Prompt工程迭代（基于实际测试反馈）

---

**建议立即启动Phase 1实施！** 🚀

预计3周内完成开发、测试和部署，实现PDF智能导入功能的质的飞跃。
