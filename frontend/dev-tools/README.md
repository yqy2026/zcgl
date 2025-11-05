# 开发工具目录

本目录包含前端项目的开发工具、脚本和报告文件。

## 目录结构

```
dev-tools/
├── scripts/          # 开发脚本
│   ├── fix_eslint_issues.py
│   ├── fix_eslint_simple.py
│   └── test_dictionary_fix.js
└── reports/          # 报告和测试输出
    ├── dictionary-select-test-report.md
    ├── frontend-api-consistency-report.json
    ├── test_dictionary_page.html
    └── test_dict_simple.html
```

## 使用说明

### 脚本文件
- `fix_eslint_issues.py` - ESLint问题修复脚本
- `fix_eslint_simple.py` - 简化版ESLint修复脚本
- `test_dictionary_fix.js` - 字典功能测试脚本

### 报告文件
- `*.md` - 测试报告文档
- `*.json` - 数据分析报告
- `*.html` - 测试页面输出

注意：这些文件用于开发和测试目的，不会被包含在生产构建中。
