# 目录重组计划

**创建日期**: 2025-12-24
**状态**: 规划中，暂未执行
**原因**: 高风险，需要全面测试验证

---

## 前端目录重组建议

### 当前问题
1. Asset 组件分散在多个位置
2. 缺少专门的 API 目录
3. CSS 文件混合使用 `.css` 和 `.module.css`
4. Form 组件未统一组织

### 建议的新结构

```
frontend/src/
├── api/                    # 新增：API层统一
│   ├── client.ts          # 合并后的API客户端
│   ├── endpoints.ts       # 端点定义
│   └── config.ts          # API配置
│
├── components/
│   ├── Asset/             # 所有Asset组件整合
│   ├── Layout/            # 布局组件（已整合）
│   ├── Charts/            # 图表组件
│   ├── ErrorHandling/     # 错误处理（已整合）
│   └── Forms/             # 所有表单组件（新增）
│       ├── AssetForm.tsx
│       ├── ContractForm.tsx
│       └── ...
│
├── pages/
│   ├── Assets/            # Asset相关页面
│   ├── Dashboard/         # Dashboard页面
│   ├── Rental/            # Rental相关页面
│   └── System/            # System相关页面
│
├── services/              # 业务逻辑服务
│   ├── asset/             # Asset服务
│   ├── rental/            # Rental服务
│   └── analytics/         # Analytics服务
│
├── styles/                # 新增：样式管理
│   ├── global.css         # 全局样式（从 App.css, index.css 迁移）
│   ├── variables.css      # CSS变量
│   └── themes/            # 主题文件
│
├── hooks/                 # 自定义 hooks（保持）
├── utils/                 # 工具函数（保持）
├── contexts/              # React contexts（保持）
├── store/                 # Zustand stores（保持）
├── types/                 # TypeScript 类型（保持）
└── constants/             # 常量（保持）
```

---

## 后端目录重组建议

### 当前问题
1. services/ 子目录过深
2. document/ 服务过多
3. 部分服务 shim 文件未清理

### 建议的新结构

```
backend/src/
├── api/
│   └── v1/                # 清理后的34个模块
│
├── core/                  # 核心功能
│   ├── config.py          # 统一配置
│   ├── di.py              # 依赖注入
│   └── router_registry.py # 路由注册
│
├── services/              # 扁平化结构
│   ├── auth/              # 认证服务
│   ├── document/          # 文档处理（6个核心文件）
│   │   ├── pdf_import_service.py
│   │   ├── pdf_processing_service.py
│   │   ├── pdf_quality_assessment.py
│   │   ├── parallel_pdf_processor.py
│   │   ├── pdf_processing_cache.py
│   │   └── pdf_session_service.py
│   ├── analytics/         # 分析服务
│   ├── permission/        # 权限服务
│   └── monitoring/        # 监控服务
│
├── crud/                  # 数据访问层（保持）
├── models/                # 数据模型（保持）
├── schemas/               # Pydantic模式（保持）
└── middleware/            # 中间件（7个已清理）
```

---

## 迁移步骤

### 阶段 A：前端重组
1. **创建新目录**
   ```bash
   mkdir -p frontend/src/api
   mkdir -p frontend/src/styles/themes
   mkdir -p frontend/src/components/Forms
   ```

2. **移动 API 文件**
   ```bash
   # 从 services/enhancedApiClient.ts → api/client.ts
   # 合并所有 API 相关配置
   ```

3. **移动样式文件**
   ```bash
   # 合并 App.css, index.css → styles/global.css
   # 转换 .css 文件为 .module.css
   ```

4. **更新导入路径** (需要更新 50+ 文件)
   - 使用 IDE 的重构功能
   - 运行 `npm run type-check` 验证
   - 运行 `npm test` 验证

### 阶段 B：后端重组
1. **扁平化 services 目录**
   ```bash
   # 合并 services/core/* → core/
   # 移动服务到合适的子目录
   ```

2. **更新 Python 导入**
   ```bash
   # 更新导入路径
   # 运行 pytest 验证
   ```

---

## 风险评估

| 操作 | 风险级别 | 影响范围 | 缓解措施 |
|------|----------|----------|----------|
| 创建新目录 | 低 | 无 | 无 |
| 移动 API 文件 | 中 | ~30 文件 | 使用 IDE 重构 |
| 更新导入路径 | 高 | ~100 文件 | 分批执行，充分测试 |
| 移动后端文件 | 中 | ~20 文件 | 运行 pytest |

---

## 执行建议

1. **创建功能分支**: `git checkout -b refactor/directory-reorg`
2. **分批执行**: 每次只移动一个模块
3. **持续测试**: 每批移动后运行测试
4. **提交频繁**: 每个成功的小步骤都提交

---

## 当前状态

✅ **已完成**:
- Phase 1: 快速清理
- Phase 2: 前端重构（标记废弃组件）
- Phase 3: 后端重构（删除冗余文件）

⏳ **待执行** (此文档):
- 前端目录重组
- 后端目录重组

⏭️ **后续阶段**:
- Phase 5: 验证与文档

---

**备注**: 此重组计划需要在有时间窗口时执行，建议安排在功能开发间隙进行。
