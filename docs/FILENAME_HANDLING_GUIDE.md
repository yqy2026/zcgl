# 文件名处理指南

## 概述

本系统实现了完整的文件名处理机制，用于解决PDF上传时文件名兼容性问题，特别是包含中文特殊字符的文件名。

## 问题背景

原始问题文件名：
```
【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf
```

该文件名包含中文特殊字符 `【` `】` `（` `）`，在某些操作系统或文件系统中可能导致兼容性问题。

## 解决方案

### 1. 后端文件名清理工具

位置：`backend/src/utils/filename_sanitizer.py`

#### 核心功能
- **Unicode规范化**：使用NFKC规范化确保字符一致性
- **中文特殊字符映射**：将中文特殊字符替换为标准ASCII字符
- **危险字符处理**：移除或替换系统不兼容字符
- **长度控制**：智能截断过长的文件名
- **安全验证**：检查文件名是否符合系统要求

#### 中文特殊字符映射
```python
CHINESE_SPECIAL_CHARS = {
    '【': '[', '】': ']',
    '（': '(', '）': ')',
    '《': '<', '》': '>',
    '"': '"', '"': '"',
    ''': "'", ''': "'",
    '：': ':',
    '，': ',',
    '。': '.',
    '；': ';',
    '！': '!',
    '？': '?',
    '·': '·',
    '…': '...',
    '—': '-',
    '–': '-',
    # ... 更多映射
}
```

#### 使用示例
```python
from src.utils.filename_sanitizer import sanitize_filename, validate_filename

# 验证文件名
validation = validate_filename(filename)
print(f"有效: {validation['valid']}")
print(f"问题: {validation['issues']}")

# 清理文件名
result = sanitize_filename(filename)
print(f"清理后: {result['sanitized_filename']}")
print(f"变更: {result['changes_made']}")
```

### 2. API集成

PDF上传API已集成文件名清理功能：

位置：`backend/src/api/v1/pdf_import.py`

#### 处理流程
1. 接收文件上传请求
2. 验证和清理文件名
3. 保存原始文件名和清理后文件名
4. 继续正常的PDF处理流程

#### API响应
```json
{
  "success": true,
  "message": "文件上传成功，正在处理中（文件名已优化）",
  "session_id": "uuid-string",
  "filename_info": {
    "original_filename": "【包装合字（2025）第022号】...",
    "sanitized_filename": "[包装合字(2025)第022号]...",
    "changes_made": [
      {
        "original": "【",
        "fixed": "[",
        "reason": "中文特殊字符替换为标准字符",
        "type": "replacement"
      }
    ],
    "warnings": []
  }
}
```

### 3. 前端验证组件

#### FilenameValidator 组件
位置：`frontend/src/components/Contract/FilenameValidator.tsx`

功能：
- 实时文件名验证
- 视觉化问题显示
- 提供改进建议
- 支持用户自定义修改

#### FilenameFixDialog 组件
位置：`frontend/src/components/Contract/FilenameFixDialog.tsx`

功能：
- 分步骤的文件名修复流程
- 详细的变更记录
- 用户友好的界面
- 支持手动编辑

## 最佳实践

### 1. 文件名命名建议
- 避免使用中文特殊字符 【】（）等
- 使用标准ASCII字符：[]()
- 控制文件名长度在150字符以内
- 确保以.pdf结尾
- 避免使用<>:"/\\|?*等特殊字符

### 2. 系统集成
- 上传前：前端验证组件提供实时反馈
- 上传时：后端自动清理和验证
- 处理后：返回详细的变更信息

### 3. 用户体验
- 保持原始文件名信息
- 清晰展示所有变更
- 提供手动编辑选项
- 详细的错误提示和建议

## 测试验证

### 测试用例
```python
# 测试文件名处理
test_cases = [
    "【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf",
    "normal_filename.pdf",
    "test<file>name.pdf",
    "超长文件名" * 20 + ".pdf",
    "test@#$%^&*().pdf"
]
```

### 预期结果
原始文件名：`【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf`

清理后文件名：`[包装合字(2025)第022号]租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf`

变更记录：
- Unicode规范化 (NFKC)
- 替换中文特殊字符: 【 → [
- 替换中文特殊字符: 】 → ]
- 替换中文特殊字符: （ → (
- 替换中文特殊字符: ） → )

## 性能考虑

- 文件名处理时间：< 1ms
- 内存使用：最小化
- 缓存机制：可选择性实现
- 批量处理：支持

## 扩展性

### 支持的字符集
- 中文简体/繁体
- 日文、韩文字符
- 阿拉伯数字
- 标准ASCII字符

### 可配置选项
- 最大长度限制
- 允许的字符集
- 替换策略
- 警告级别

## 故障排除

### 常见问题
1. **编码问题**：确保系统支持UTF-8编码
2. **权限问题**：检查文件系统权限
3. **长度限制**：不同操作系统的文件名长度限制

### 调试方法
```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查文件名信息
from src.utils.filename_sanitizer import filename_sanitizer
info = filename_sanitizer.get_filename_info(filename)
print(info)
```

## 维护更新

### 定期检查
- 字符映射表更新
- 新增特殊字符处理
- 性能优化
- 安全性检查

### 版本控制
- 向后兼容性
- 配置迁移
- 测试覆盖
- 文档更新

---

## 总结

本文件名处理系统提供了完整的解决方案，确保包含中文特殊字符的PDF文件名能够被正确处理，同时保持良好的用户体验和系统兼容性。通过自动化的清理流程和用户友好的界面，有效解决了文件名兼容性问题。