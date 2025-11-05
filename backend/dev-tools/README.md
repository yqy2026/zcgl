# 后端开发工具目录

本目录包含后端项目的开发工具、脚本、测试数据和报告文件。

## 目录结构

```
dev-tools/
├── scripts/          # 通用脚本
│   ├── test_*.py     # 测试脚本
│   ├── simple_*.py   # 简单测试脚本
│   ├── analyze_*.py  # 分析脚本
│   ├── generate_*.py # 生成脚本
│   ├── ci_*.py       # CI相关脚本
│   └── *.sh          # Shell脚本
├── debug/            # 调试工具
│   ├── debug_*.py    # 调试脚本
│   ├── diagnose_*.py # 诊断脚本
│   └── demo_*.py     # 演示脚本
├── setup/            # 安装配置
│   ├── setup_*.py    # 设置脚本
│   ├── install_*.py  # 安装脚本
│   ├── configure_*.py # 配置脚本
│   ├── init_*.py     # 初始化脚本
│   └── migrate_*.py  # 迁移脚本
└── maintenance/      # 维护脚本
    ├── fix_*.py      # 修复脚本
    ├── optimize_*.py # 优化脚本
    ├── implement_*.py # 实现脚本
    └── establish_*.py # 建立脚本
```

## 使用说明

### 脚本分类
- **测试脚本**: 用于API测试、集成测试等
- **调试工具**: 用于问题诊断和调试
- **安装配置**: 用于环境设置和配置
- **维护脚本**: 用于代码修复和优化

### 注意事项
1. 这些脚本主要用于开发和测试环境
2. 生产环境请谨慎使用
3. 使用前请仔细阅读脚本注释
4. 建议在测试环境中先验证脚本功能

## 常用脚本

### 测试相关
- `test_*.py` - 各种测试脚本
- `simple_test.py` - 简单测试

### 调试相关
- `debug_statistics.py` - 统计调试
- `diagnose_500_error.py` - 500错误诊断

### 维护相关
- `fix_ruff_errors.py` - 修复Ruff错误
- `optimize_database_fts.py` - 优化数据库FTS

注意：这些文件用于开发和维护目的，不会被包含在生产部署中。
