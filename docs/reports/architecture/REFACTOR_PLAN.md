# 项目重构执行计划

## 🎯 重构目标
基于当前项目分析，制定具体的重构步骤，提升项目架构的专业性和可维护性。

## 📊 当前问题分析

### 严重问题
1. **根目录混乱** - 58个文件/目录，包含大量临时文件
2. **数据库文件重复** - 3个位置存在相同的数据库文件
3. **文档分散** - 缺乏统一的文档管理
4. **测试文件混杂** - PDF测试文件散落在根目录

### 中等问题
1. **脚本分散** - 启动脚本在多个位置
2. **配置不统一** - 环境配置分散
3. **依赖管理** - 前后端依赖管理可以优化

## 🔧 具体重构步骤

### 阶段1：创建新的目录结构（5分钟）

```bash
# 创建主要目录
mkdir -p tools/{pdf-samples,test-data,utilities}
mkdir -p database/{data,backups,init}
mkdir -p docs/{api,user,dev,deployment,reports,setup}
mkdir -p scripts/{setup,dev,deploy}
mkdir -p tests/{e2e,integration,fixtures}
```

### 阶段2：文件迁移（10分钟）

#### PDF文件迁移
```bash
# 移动PDF测试文件
mv contract_022.pdf tools/pdf-samples/
mv original_contract.pdf tools/pdf-samples/
mv packaging_contract_2025_022.pdf tools/pdf-samples/
mv test-sample.pdf tools/pdf-samples/
mv test_upload.pdf tools/pdf-samples/
mv "【包装合字（2025）第022号】租赁合同-番禺区洛浦南浦环岛西路29号1号商业楼14号铺-王军20250401-20280331.pdf" tools/pdf-samples/
```

#### 测试数据迁移
```bash
mv test-sample.txt tools/test-data/
mv test_new_upload.txt tools/test-data/
mv test_pdf_upload.html tools/test-data/
mv test_pdf_upload_fix.txt tools/test-data/
```

#### 脚本文件迁移
```bash
mv install_poppler.bat scripts/setup/
mv install_tesseract.bat scripts/setup/
mv verify_tesseract.py scripts/setup/

mv start*.bat scripts/dev/
mv start*.sh scripts/dev/
mv stop*.bat scripts/dev/
mv stop*.sh scripts/dev/
```

#### 文档迁移
```bash
mv BEST_PRACTICES_RECOMMENDATIONS.md docs/dev/
mv MANUAL_TESSERACT_INSTALL.md docs/setup/
mv POPPLER_INSTALL_GUIDE.md docs/setup/
mv TESSERACT_INSTALL_GUIDE.md docs/setup/
mv *_REPORT.md docs/reports/
mv *_GUIDE.md docs/setup/
```

#### 数据库整理
```bash
# 统一数据库文件位置
mv land_property.db database/data/
# 清理重复文件（保留backend中的作为开发用）
```

### 阶段3：配置文件更新（5分钟）

需要更新的配置：
1. 数据库连接路径
2. 脚本引用路径
3. 文档链接
4. Docker配置

### 阶段4：清理无用文件（2分钟）

```bash
# 删除空文件和临时文件
rm nul
rm -rf .playwright-mcp/traces  # 如果不需要
```

## 📋 重构后的目录结构预览

```
land-property-management/
├── README.md
├── .gitignore
├── docker-compose.yml
│
├── backend/                 # 后端服务（保持现有结构）
├── frontend/               # 前端应用（保持现有结构）
├── nginx/                  # Nginx配置（保持现有）
│
├── database/               # 🆕 数据库管理
│   ├── data/
│   │   └── land_property.db
│   ├── backups/
│   └── init/
│
├── docs/                   # 🆕 统一文档管理
│   ├── api/               # API文档
│   ├── user/              # 用户手册
│   ├── dev/               # 开发文档
│   ├── deployment/        # 部署文档
│   ├── reports/           # 各种报告
│   └── setup/             # 安装指南
│
├── scripts/               # 🆕 统一脚本管理
│   ├── setup/             # 安装脚本
│   ├── dev/               # 开发脚本
│   └── deploy/            # 部署脚本
│
├── tools/                 # 🆕 开发工具
│   ├── pdf-samples/       # PDF测试文件
│   ├── test-data/         # 测试数据
│   └── utilities/         # 工具脚本
│
├── tests/                 # 🆕 集成测试
│   ├── e2e/
│   ├── integration/
│   └── fixtures/
│
└── .kiro/                 # Kiro配置（保持现有）
```

## 🎯 重构后的优势

### 立即收益
1. **根目录清爽** - 从58个项目减少到~15个主要目录
2. **文件分类明确** - 按功能和类型组织
3. **更专业的项目形象** - 符合企业级项目标准

### 长期收益
1. **维护成本降低** - 文件易于查找和管理
2. **新人上手更快** - 清晰的项目结构
3. **CI/CD更容易** - 标准化的脚本位置
4. **文档管理更好** - 集中式文档体系

## ⚠️ 注意事项

1. **备份重要数据** - 执行前备份数据库和重要文件
2. **更新配置引用** - 修改所有硬编码的文件路径
3. **团队沟通** - 确保团队成员了解新的目录结构
4. **分步执行** - 可以分阶段执行，避免一次性大改动
5. **测试验证** - 每个阶段后验证系统功能正常

## 🚀 执行建议

1. **选择合适时机** - 在功能开发间隙执行
2. **创建分支** - 在新分支中执行重构
3. **逐步验证** - 每个阶段后测试系统功能
4. **更新文档** - 及时更新README和相关文档
5. **代码审查** - 让团队成员审查重构结果

## 📈 成功指标

- [ ] 根目录文件数量减少70%以上
- [ ] 所有文档集中在docs目录
- [ ] 所有脚本按功能分类
- [ ] 测试文件统一管理
- [ ] 数据库文件位置统一
- [ ] 系统功能正常运行
- [ ] 团队成员适应新结构