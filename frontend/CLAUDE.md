[根目录](../../CLAUDE.md) > **frontend**

# Frontend 前端应用模块

## 变更记录 (Changelog)

### 2025-10-23 10:45:44 - 模块架构初始化
- ✨ 新增：模块导航面包屑
- ✨ 新增：组件库架构文档
- ✨ 新增：页面路由系统分析
- 📊 统计：70+ 组件，15个页面，10个API服务
- 🔧 优化：Vite配置和性能优化

---

## 模块职责

Frontend模块是地产资产管理系统的用户界面层，基于React 18 + TypeScript构建，提供现代化、响应式的用户界面，支持复杂的资产管理操作、数据可视化和实时交互。

### 核心职责
- **用户界面**: 70+个React组件，15个页面，完整的用户交互体验
- **状态管理**: Zustand全局状态 + React Query服务端状态
- **数据可视化**: Ant Design Charts + 自定义图表组件
- **用户体验**: 响应式设计、错误边界、加载状态、反馈机制
- **性能优化**: 代码分割、懒加载、缓存策略、包大小优化

## 入口与启动

### 主入口文件
- **应用入口**: `src/main.tsx` - React应用初始化和全局配置
- **根组件**: `src/App.tsx` - 应用布局和路由容器
- **路由配置**: `src/routes/AppRoutes.tsx` - 页面路由和权限控制

### 启动命令
```bash
# 开发服务器
npm run dev                         # 端口 5173，热重载

# 类型检查
npm run type-check                  # TypeScript验证

# 代码检查
npm run lint                        # ESLint检查

# 生产构建
npm run build                       # 优化打包

# 预览生产构建
npm run preview                     # 本地预览
```

### 应用配置
- **端口**: 5173 (开发环境)
- **代理**: Vite代理到后端API (http://localhost:8002)
- **主题**: Ant Design主题定制
- **国际化**: 中文本地化配置

## 对外接口

### 路由系统架构

#### 路由层级结构
```
/                                   # 重定向到工作台
├── dashboard/                       # 工作台 (默认首页)
├── assets/                         # 资产管理模块
│   ├── list                        # 资产列表
│   ├── new/create                  # 创建资产
│   ├── import                      # 资产导入
│   ├── analytics                   # 资产分析
│   └── :id                         # 资产详情
│       └── edit                    # 编辑资产
├── rental/                         # 租赁管理模块
│   ├── contracts                   # 合同列表
│   ├── contracts/new               # 创建合同
│   ├── contracts/pdf-import        # PDF导入合同
│   ├── ledger                      # 租金台账
│   └── statistics                  # 租赁统计
├── ownership/                      # 权属方管理
├── project/                        # 项目管理
└── system/                         # 系统管理 (权限控制)
    ├── users                       # 用户管理 (需权限)
    ├── roles                       # 角色管理 (需权限)
    ├── organizations               # 组织架构
    ├── dictionaries                # 字典管理
    ├── templates                   # 模板管理
    ├── logs                        # 操作日志 (需权限)
    └── settings                    # 系统设置
```

#### 页面组件概览

| 页面模块 | 组件名称 | 路径路径 | 核心功能 | 权限要求 |
|----------|----------|----------|----------|----------|
| **工作台** | `DashboardPage` | `/dashboard` | 数据概览、快速操作、图表展示 | 无 |
| **资产列表** | `AssetListPage` | `/assets/list` | 资产查询、筛选、批量操作 | 资产查看 |
| **资产详情** | `AssetDetailPage` | `/assets/:id` | 资产详情、历史记录、相关文档 | 资产查看 |
| **资产创建** | `AssetCreatePage` | `/assets/new` | 58字段资产表单、验证保存 | 资产编辑 |
| **资产导入** | `AssetImportPage` | `/assets/import` | Excel导入、PDF处理、数据映射 | 资产编辑 |
| **资产分析** | `AssetAnalyticsPage` | `/assets/analytics` | 数据可视化、统计图表、报表导出 | 资产查看 |
| **合同列表** | `ContractListPage` | `/rental/contracts` | 租赁合同管理、状态跟踪 | 合同查看 |
| **合同创建** | `ContractCreatePage` | `/rental/contracts/new` | 合同信息录入、条款设置 | 合同编辑 |
| **PDF导入** | `PDFImportPage` | `/rental/contracts/pdf-import` | PDF上传、智能识别、数据确认 | 合同编辑 |
| **权属方管理** | `OwnershipManagementPage` | `/ownership` | 权属方信息、关联资产、统计分析 | 权属管理 |
| **项目管理** | `ProjectManagementPage` | `/project` | 项目层级、资产统计、项目分析 | 项目管理 |
| **用户管理** | `UserManagementPage` | `/system/users` | 用户增删改查、权限分配 | 用户管理 |
| **角色管理** | `RoleManagementPage` | `/system/roles` | 角色定义、权限配置、继承关系 | 角色管理 |
| **组织架构** | `OrganizationPage` | `/system/organizations` | 组织树形结构、部门管理 | 组织管理 |
| **字典管理** | `DictionaryPage` | `/system/dictionaries` | 数据字典、枚举值、系统配置 | 系统管理 |

### 组件库架构

#### 组件分类统计

| 组件类别 | 数量 | 核心组件 | 功能描述 |
|----------|------|----------|----------|
| **Asset资产管理** | 15 | `AssetForm`, `AssetList`, `AssetDetail` | 58字段表单、列表展示、详情页面 |
| **Layout布局** | 8 | `AppLayout`, `AppHeader`, `ResponsiveLayout` | 响应式布局、导航、面包屑 |
| **Charts图表** | 6 | `OccupancyRateChart`, `AssetDistributionChart` | 数据可视化、统计图表 |
| **ErrorHandling错误处理** | 5 | `ErrorBoundary`, `ErrorPage`, `UXProvider` | 全局错误处理、用户反馈 |
| **Loading加载状态** | 3 | `LoadingSpinner`, `SkeletonLoader` | 加载动画、骨架屏 |
| **Feedback反馈** | 4 | `EmptyState`, `SuccessNotification` | 用户操作反馈、状态提示 |
| **Analytics分析** | 8 | `AnalyticsDashboard`, `StatisticCard` | 数据分析、报表组件 |
| **Contract合同** | 4 | `RentContractForm`, `FilenameValidator` | 合同管理、文件验证 |
| **Project项目** | 4 | `ProjectForm`, `ProjectSelect` | 项目管理、选择器 |
| **Ownership权属** | 3 | `OwnershipForm`, `OwnershipSelect` | 权属方管理 |
| **Dictionary字典** | 2 | `DictionarySelect`, `EnumValuePreview` | 字典选择、枚举预览 |
| **System系统** | 4 | `PermissionGuard`, `SystemBreadcrumb` | 权限控制、系统组件 |

#### 核心组件详解

**Asset资产管理组件**
```typescript
// AssetForm - 58字段资产表单
interface AssetFormProps {
  initialValues?: Partial<Asset>;
  onSubmit: (values: AssetFormData) => void;
  mode: 'create' | 'edit';
}

// AssetList - 资产列表组件
interface AssetListProps {
  filters: AssetFilters;
  onEdit: (asset: Asset) => void;
  onDelete: (assetId: string) => void;
}

// AssetDetail - 资产详情组件
interface AssetDetailProps {
  assetId: string;
  onEdit: () => void;
  showHistory?: boolean;
}
```

**Layout布局组件**
```typescript
// AppLayout - 应用主布局
interface AppLayoutProps {
  children: React.ReactNode;
}

// ResponsiveLayout - 响应式布局
interface ResponsiveLayoutProps {
  children: React.ReactNode;
  sidebarCollapsed?: boolean;
}

// AppHeader - 应用头部
interface AppHeaderProps {
  user?: User;
  onLogout: () => void;
}
```

**Charts图表组件**
```typescript
// OccupancyRateChart - 出租率图表
interface OccupancyRateChartProps {
  data: OccupancyData[];
  timeRange: TimeRange;
}

// AssetDistributionChart - 资产分布图表
interface AssetDistributionChartProps {
  data: AssetDistributionData;
  chartType: 'pie' | 'bar' | 'area';
}
```

## 关键依赖与配置

### 核心依赖 (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1",
    "antd": "^5.12.8",
    "@ant-design/icons": "^5.2.6",
    "@ant-design/plots": "^2.0.0",
    "@tanstack/react-query": "^4.36.1",
    "zustand": "^4.4.7",
    "axios": "^1.6.2",
    "dayjs": "^1.11.10",
    "recharts": "^2.8.0",
    "xlsx": "^0.18.5",
    "zod": "^3.22.4"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.0.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^6.1.5",
    "eslint": "^8.55.0",
    "prettier": "^3.0.0"
  }
}
```

### Vite配置 (vite.config.ts)
```typescript
export default defineConfig({
  plugins: [
    react(),
    // 生产环境压缩
    compression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    // 包分析
    visualizer({
      filename: 'dist/stats.html',
      open: true,
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          antd: ['antd'],
          charts: ['recharts', '@ant-design/plots'],
        },
      },
    },
  },
});
```

### TypeScript配置
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

## 状态管理

### 状态管理架构
- **全局状态**: Zustand - 客户端状态管理
- **服务端状态**: React Query - API数据缓存和同步
- **表单状态**: React Hook Form - 表单状态管理
- **UI状态**: React useState - 组件内部状态

### Zustand Store结构
```typescript
// useAppStore - 全局应用状态
interface AppStore {
  // 用户状态
  user: User | null;
  setUser: (user: User | null) => void;

  // 主题状态
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;

  // 侧边栏状态
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // 权限状态
  permissions: Permission[];
  hasPermission: (resource: string, action: string) => boolean;
}

// useAssetStore - 资产管理状态
interface AssetStore {
  assets: Asset[];
  selectedAssets: string[];
  filters: AssetFilters;
  setAssets: (assets: Asset[]) => void;
  setSelectedAssets: (ids: string[]) => void;
  setFilters: (filters: AssetFilters) => void;
}
```

### React Query配置
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5分钟缓存
      cacheTime: 10 * 60 * 1000, // 10分钟缓存
    },
  },
});
```

## 数据模型

### 前端数据模型
```typescript
// Asset - 资产数据模型
interface Asset {
  id: string;
  ownershipEntity: string;
  ownershipCategory?: string;
  projectName?: string;
  propertyName: string;
  address: string;
  ownershipStatus: string;
  propertyNature: string;
  usageStatus: string;

  // 面积字段
  landArea?: number;
  actualPropertyArea?: number;
  rentableArea?: number;
  rentedArea?: number;
  unrentedArea?: number;
  occupancyRate?: number;

  // 财务字段
  annualIncome?: number;
  annualExpense?: number;
  netIncome?: number;

  // 合同字段
  leaseContractNumber?: string;
  contractStartDate?: string;
  contractEndDate?: string;

  // 自动计算字段
  createdAt: string;
  updatedAt: string;
}

// AssetFilters - 资产筛选条件
interface AssetFilters {
  keyword?: string;
  ownershipStatus?: string;
  propertyNature?: string;
  usageStatus?: string;
  dateRange?: [string, string];
  areaRange?: [number, number];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// User - 用户模型
interface User {
  id: string;
  username: string;
  email?: string;
  fullName: string;
  roles: Role[];
  organization: Organization;
  permissions: Permission[];
}
```

### API服务类型
```typescript
// API响应类型
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  code?: string;
}

// 分页响应类型
interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}
```

## 测试与质量

### 测试架构
- **测试框架**: Jest + Testing Library
- **测试类型**: 单元测试、集成测试、组件测试
- **测试覆盖**: 核心组件、API服务、工具函数

### 测试文件结构
```
src/
├── components/
│   ├── Asset/
│   │   ├── __tests__/
│   │   │   ├── AssetForm.test.tsx
│   │   │   ├── AssetList.test.tsx
│   │   │   └── AssetDetailInfo.test.tsx
│   │   └── ...
│   ├── ErrorHandling/
│   │   ├── __tests__/
│   │   │   └── GlobalErrorBoundary.test.tsx
│   │   └── ...
│   └── ...
├── services/
│   ├── __tests__/
│   │   └── assetService.test.ts
│   └── ...
├── pages/
│   ├── __tests__/
│   │   ├── AssetDashboardPage.test.tsx
│   │   └── AssetFormPage.test.tsx
│   └── ...
└── test/
    └── setup.ts                    # 测试配置
```

### 测试命令
```bash
# 运行所有测试
npm test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 监听模式运行测试
npm run test:watch

# 运行特定测试文件
npm test -- AssetForm.test.tsx

# 调试模式运行测试
npm run test:debug
```

### 代码质量工具
```bash
# TypeScript类型检查
npm run type-check

# ESLint代码检查
npm run lint

# 自动修复ESLint问题
npm run lint:fix

# Prettier代码格式化
npm run format

# 构建分析
ANALYZE=true npm run build
```

## 常见问题 (FAQ)

### Q: 如何添加新的页面？
A: 在 `src/pages/` 目录创建页面组件，然后在 `AppRoutes.tsx` 中添加路由配置。

### Q: 如何处理API错误？
A: 使用React Query的error handling，配合ErrorBoundary组件进行全局错误处理。

### Q: 如何实现权限控制？
A: 使用PermissionGuard组件包装需要权限的页面，结合Zustand中的权限状态。

### Q: 如何优化大列表性能？
A: 使用虚拟滚动（react-window）或分页加载，避免一次性渲染大量数据。

### Q: 如何自定义Ant Design主题？
A: 在main.tsx中的ConfigProvider中配置theme对象，支持token和components级别的定制。

### Q: 如何处理PDF文件上传？
A: 使用axios上传文件，配合进度显示组件，后端使用统一的PDF导入API。

## 相关文件清单

### 核心文件
- `src/main.tsx` - 应用入口和全局配置
- `src/App.tsx` - 根组件和布局容器
- `src/routes/AppRoutes.tsx` - 路由配置和权限控制
- `package.json` - 依赖管理和脚本配置
- `vite.config.ts` - Vite构建配置

### 页面组件
- `src/pages/Dashboard/DashboardPage.tsx` - 工作台页面
- `src/pages/Assets/AssetListPage.tsx` - 资产列表页面
- `src/pages/Assets/AssetCreatePage.tsx` - 资产创建页面
- `src/pages/Rental/ContractListPage.tsx` - 合同列表页面
- `src/pages/System/UserManagementPage.tsx` - 用户管理页面

### 核心组件
- `src/components/Asset/AssetForm.tsx` - 资产表单组件
- `src/components/Asset/AssetList.tsx` - 资产列表组件
- `src/components/Layout/AppLayout.tsx` - 应用布局组件
- `src/components/Charts/OccupancyRateChart.tsx` - 出租率图表
- `src/components/ErrorHandling/ErrorBoundary.tsx` - 错误边界组件

### 状态管理
- `src/store/useAppStore.ts` - 全局应用状态
- `src/hooks/useAssets.ts` - 资产相关钩子
- `src/hooks/useErrorHandler.ts` - 错误处理钩子

### API服务
- `src/services/index.ts` - API服务配置
- `src/services/assetService.ts` - 资产API服务
- `src/services/config.ts` - API配置

### 类型定义
- `src/types/api.ts` - API响应类型
- `src/types/asset.ts` - 资产相关类型
- `src/vite-env.d.ts` - Vite环境类型

### 工具函数
- `src/utils/highlight.ts` - 高亮工具
- `src/schemas/assetFormSchema.ts` - 表单验证模式

### 测试文件
- `src/test/setup.ts` - 测试配置
- `src/components/**/__tests__/` - 组件测试
- `src/services/__tests__/` - 服务测试

### 配置文件
- `index.html` - HTML模板
- `tsconfig.json` - TypeScript配置
- `tsconfig.node.json` - Node.js TypeScript配置
- `nginx.conf` - Nginx配置（生产环境）

---

**模块状态**: 🟢 生产就绪，组件丰富，用户体验良好。

**最后更新**: 2025-10-23 10:45:44 (模块架构初始化)