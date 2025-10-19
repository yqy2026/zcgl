# 项目架构优化方案

## 🎯 优化目标
- 清理根目录，提高项目可维护性
- 统一文档管理
- 规范化文件组织
- 优化开发体验

## 📁 推荐的目录结构

```
land-property-management/
├── README.md                    # 项目主文档
├── docker-compose.yml          # 容器编排
├── .gitignore                  # Git忽略规则
├── .env.example               # 环境变量模板
│
├── backend/                   # 后端服务
│   ├── src/                  # 源代码
│   ├── tests/                # 测试代码
│   ├── migrations/           # 数据库迁移
│   ├── scripts/              # 工具脚本
│   ├── requirements.txt      # Python依赖
│   ├── pyproject.toml       # 项目配置
│   └── Dockerfile           # 后端镜像
│
├── frontend/                 # 前端应用
│   ├── src/                 # 源代码
│   ├── public/              # 静态资源
│   ├── tests/               # 测试代码
│   ├── package.json         # 依赖配置
│   └── Dockerfile           # 前端镜像
│
├── database/                # 数据库相关
│   ├── data/               # 数据文件
│   ├── backups/            # 备份文件
│   └── init/               # 初始化脚本
│
├── docs/                    # 项目文档
│   ├── api/                # API文档
│   ├── user/               # 用户手册
│   ├── dev/                # 开发文档
│   └── deployment/         # 部署文档
│
├── scripts/                 # 项目脚本
│   ├── setup/              # 安装脚本
│   ├── dev/                # 开发工具
│   └── deploy/             # 部署脚本
│
├── tests/                   # 集成测试
│   ├── e2e/                # 端到端测试
│   ├── integration/        # 集成测试
│   └── fixtures/           # 测试数据
│
├── tools/                   # 开发工具
│   ├── pdf-samples/        # PDF测试文件
│   ├── test-data/          # 测试数据
│   └── utilities/          # 工具脚本
│
└── .kiro/                   # Kiro配置
    └── settings/
```

## 🔄 迁移步骤

### 第一阶段：清理根目录
1. 创建 `tools/pdf-samples/` 目录
2. 移动所有PDF文件到该目录
3. 创建 `tools/test-data/` 目录
4. 移动测试相关文件

### 第二阶段：统一数据库管理
1. 创建 `database/` 目录
2. 统一数据库文件位置
3. 整理备份文件

### 第三阶段：整合文档
1. 扩展 `docs/` 目录结构
2. 移动分散的文档文件
3. 创建文档索引

### 第四阶段：脚本整合
1. 创建 `scripts/` 目录
2. 按功能分类脚本文件
3. 统一脚本命名规范

## 📋 具体操作清单

### 需要移动的文件

#### PDF和测试文件 → `tools/pdf-samples/`
- contract_022.pdf
- original_contract.pdf
- packaging_contract_2025_022.pdf
- test-sample.pdf
- test_upload.pdf
- 【包装合字（2025）第022号】租赁合同.pdf

#### 测试数据 → `tools/test-data/`
- test-sample.txt
- test_new_upload.txt
- test_pdf_upload.html
- test_pdf_upload_fix.txt

#### 安装脚本 → `scripts/setup/`
- install_poppler.bat
- install_tesseract.bat
- verify_tesseract.py

#### 启动脚本 → `scripts/dev/`
- start.bat, start.sh
- start_uv.bat, start_uv.sh
- stop.bat, stop.sh
- stop_uv.bat, stop_uv.sh

#### 文档文件 → `docs/`
- BEST_PRACTICES_RECOMMENDATIONS.md → docs/dev/
- MANUAL_TESSERACT_INSTALL.md → docs/setup/
- POPPLER_INSTALL_GUIDE.md → docs/setup/
- TESSERACT_INSTALL_GUIDE.md → docs/setup/
- 各种报告文件 → docs/reports/

#### 数据库文件 → `database/`
- land_property.db → database/data/

### 需要删除的文件
- nul (空文件)
- 重复的数据库文件

## 🎯 优化后的好处

1. **清晰的项目结构** - 一目了然的文件组织
2. **更好的可维护性** - 文件分类明确，易于查找
3. **标准化的开发流程** - 统一的脚本和工具位置
4. **完善的文档体系** - 集中管理，便于维护
5. **更好的协作体验** - 新开发者能快速理解项目结构

## 🚀 实施建议

1. **分阶段执行** - 避免一次性大改动
2. **保留备份** - 重要文件先备份
3. **更新引用** - 修改相关配置文件中的路径
4. **团队沟通** - 确保团队成员了解变更
5. **文档更新** - 及时更新README和相关文档