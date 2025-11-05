# Repository Guidelines

## 项目结构与模块组织

```
D:/code/zcgl/
├── backend/              # Python FastAPI 后端
│   ├── alembic/         # 数据库迁移文件
│   ├── tests/           # 后端测试
│   ├── config.yaml      # 配置文件
│   └── Dockerfile       # 后端容器化
├── frontend/            # TypeScript React 前端
│   ├── src/             # 源代码
│   ├── __tests__/       # 前端测试
│   ├── vite.config.ts   # 构建配置
│   └── package.json     # 依赖管理
├── database/            # 数据库相关
├── docs/                # 项目文档
├── tests/               # 跨模块测试
└── docker-compose.yml   # 容器编排
```

## 构建、测试和开发命令

### 前端开发
```bash
cd frontend/
npm run dev              # 启动开发服务器
npm run build           # 构建生产版本
npm test               # 运行测试
npm run test:coverage  # 生成测试覆盖率报告
npm run lint           # 代码规范检查
npm run lint:fix       # 自动修复代码规范问题
npm run type-check     # TypeScript 类型检查
```

### 后端开发
```bash
cd backend/
python -m pytest tests/     # 运行所有测试
pytest --cov=.             # 测试覆盖率分析
alembic upgrade head        # 数据库迁移
python main.py             # 启动后端服务
```

### 整体项目
```bash
docker-compose up          # 启动所有服务
docker-compose build       # 构建容器镜像
```

## 编码规范与命名约定

### 前端规范
- **语言**: TypeScript，启用严格模式
- **代码风格**: 遵循 ESLint 配置，默认 2 空格缩进
- **组件命名**: PascalCase (`PropertyManagement`)
- **文件名**: camelCase (`propertyList.ts`)
- **测试文件**: `*.test.ts` 或 `*.spec.ts`

### 后端规范
- **语言**: Python 3.8+，遵循 PEP 8
- **代码格式**: 使用 Black 自动格式化
- **类型检查**: mypy 严格模式
- **函数/类命名**: snake_case 函数，`PascalCase` 类
- **测试文件**: `test_*.py` 模式

### 通用规范
- **提交信息**: 使用中文，遵循Conventional Commits格式
- **分支命名**: `feature/功能描述`、`fix/问题描述`
- **代码注释**: 中文优先，解释复杂逻辑

## 测试指南

### 测试框架
- **前端**: Jest + Testing Library + Playwright (E2E)
- **后端**: pytest + coverage
- **类型检查**: TypeScript + mypy

### 测试类型
```bash
# 单元测试
npm run test:unit        # 前端单元测试
pytest tests/unit/       # 后端单元测试

# 集成测试  
npm run test:integration # 前端集成测试
pytest tests/integration/# 后端集成测试

# E2E测试
npm run test:e2e         # 端到端测试
```

### 测试要求
- 新功能必须包含对应测试
- 测试覆盖率保持在80%以上
- 所有测试必须通过后才能合并PR
- 测试文件放置在对应模块的 `tests/` 目录

## 提交与PR指南

### 提交信息格式
```
类型: 简短描述

详细描述（可选）

类型列表:
- feat: 新功能
- fix: 问题修复
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试相关
- chore: 构建/工具
```

### PR要求
1. **描述**: 详细说明变更内容和动机
2. **测试**: 确保所有测试通过，包含测试截图
3. **代码审查**: 至少一名审查者通过
4. **文档**: 更新相关文档（如适用）
5. **兼容性**: 确保向后兼容

### PR模板
```markdown
## 变更类型
- [ ] 新功能
- [ ] Bug修复  
- [ ] 重大变更
- [ ] 文档更新

## 测试清单
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] E2E测试通过
- [ ] 覆盖率检查通过
- [ ] 手动测试完成

## 截图（如适用）
<!-- 插入相关截图 -->

## 兼容性
- [ ] 向后兼容
- [ ] 数据库迁移（如需要）
- [ ] 环境变量更新（如需要）
```

## 开发环境配置

### 环境要求
- Node.js 16+
- Python 3.8+
- Docker & Docker Compose
- Git

### 快速开始
```bash
# 克隆项目
git clone <repository-url>
cd zcgl

# 启动开发环境
docker-compose up -d

# 前端开发
cd frontend/
npm install
npm run dev

# 后端开发  
cd backend/
pip install -r requirements.txt
python main.py
```

### 环境变量
- 前端: `.env.development`
- 后端: `config.yaml`
- Docker: `docker-compose.yml`

## 故障排除

### 常见问题
1. **端口冲突**: 检查端口3000、8000是否被占用
2. **依赖安装失败**: 清除缓存后重新安装
3. **数据库连接失败**: 确认数据库服务运行正常
4. **测试失败**: 查看详细错误信息，运行具体测试

### 调试工具
- 前端: React Developer Tools、浏览器DevTools
- 后端: Python调试器(pdb)、日志文件
- 数据库: SQLite Browser、DBeaver

---

**注意**: 首次贡献请先阅读项目的 CLAUDE.md 和 IFLOW.md 了解详细的架构设计和开发流程。
