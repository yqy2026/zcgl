# 前端开发指南

## 📋 Purpose
本文档详细说明土地物业管理系统的前端开发技术栈、架构设计、开发规范和最佳实践。

## 🎯 Scope
- 前端技术栈和项目结构
- 组件开发规范
- 状态管理方案
- 路由系统配置
- API 集成方式
- 性能优化策略
- 测试和调试
- 常见问题解决

## ✅ Status
**当前状态**: Active (2026-01-15 更新)
**适用版本**: v2.0.0
**技术栈**: React 19 + TypeScript + Vite 6 + Ant Design 6

---

## 🏗️ 技术架构概述

### 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **框架** | React | 19.2.0 | UI 框架 |
| **语言** | TypeScript | 5.9.3 | 类型安全 |
| **构建工具** | Vite | 6.0.0 | 开发服务器和打包 |
| **UI 库** | Ant Design | 6.2.0 | 组件库 |
| **状态管理** | Zustand | 4.4.7 | 全局状态 |
| **数据获取** | React Query | 5.90.7 | 服务端状态 |
| **路由** | React Router | 6.20.1 | 页面路由 |
| **HTTP 客户端** | Axios | 1.6.2 | API 请求 |
| **表单** | React Hook Form | 7.48.2 | 表单管理 |
| **验证** | Zod | 3.22.4 | Schema 验证 |
| **图表** | Ant Design Charts | 2.0.0 | 数据可视化 |
| **工具库** | Lodash, Day.js | - | 工具函数 |

**证据来源**: `frontend/package.json`

### 项目结构

```
frontend/
├── src/
│   ├── components/          # React 组件 (114+ TSX 文件)
│   │   ├── Asset/          # 资产管理组件
│   │   ├── Analytics/      # 分析组件
│   │   ├── Router/         # 路由管理组件
│   │   ├── Layout/         # 布局组件
│   │   ├── Charts/         # 图表组件
│   │   ├── Forms/          # 表单组件
│   │   ├── ErrorHandling/  # 错误处理
│   │   └── ...
│   ├── pages/              # 页面组件 (40个)
│   ├── routes/             # 路由配置
│   ├── store/              # Zustand 状态管理
│   ├── services/           # API 服务 (35个)
│   ├── hooks/              # 自定义 Hooks (13个)
│   ├── utils/              # 工具函数 (15个)
│   ├── types/              # TypeScript 类型定义 (15个)
│   ├── constants/          # 常量配置
│   ├── contexts/           # React Context
│   ├── monitoring/         # 性能监控
│   ├── config/             # 配置文件
│   └── main.tsx            # 应用入口
├── public/                 # 静态资源
├── package.json            # 依赖和脚本
├── vite.config.ts          # Vite 配置
├── tsconfig.json           # TypeScript 配置
└── index.html              # HTML 模板
```

**证据来源**: `frontend/CLAUDE.md`, `frontend/src/` 目录结构

---

## 🚀 快速开始

### 开发环境设置

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
pnpm install

# 3. 启动开发服务器
pnpm dev

# 4. 访问应用
# 浏览器打开: http://localhost:5173
```

### 开发命令

```bash
# 开发
pnpm dev              # 启动开发服务器 (端口 5173)

# 代码质量
pnpm type-check       # TypeScript 类型检查
pnpm lint            # ESLint 代码检查
pnpm lint:fix        # 自动修复 ESLint 问题

# 测试
pnpm test            # 运行所有测试
pnpm test:coverage   # 生成覆盖率报告
pnpm test:watch      # 监听模式

# 构建
pnpm build           # 生产环境构建
pnpm preview         # 预览生产构建
```

**证据来源**: `frontend/package.json.scripts`

---

## 📦 组件开发规范

### 组件目录结构

```
components/
├── Asset/
│   ├── AssetForm.tsx           # 组件主文件
│   ├── AssetForm.test.tsx      # 测试文件
│   ├── AssetForm.module.css    # 样式文件
│   ├── index.ts                # 导出文件
│   └── types.ts                # 类型定义
```

### 组件开发模板

```tsx
/**
 * 资产表单组件
 * 用于创建和编辑资产信息
 */

import React, { useCallback, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Form, Input, message } from 'antd';
import { assetFormSchema } from '@/schemas/assetFormSchema';
import type { AssetFormData, Asset } from '@/types/asset';

// 组件 Props 接口
interface AssetFormProps {
  initialValues?: Partial<Asset>;
  onSubmit: (values: AssetFormData) => Promise<void>;
  mode: 'create' | 'edit';
  loading?: boolean;
}

/**
 * 资产表单组件
 */
export const AssetForm: React.FC<AssetFormProps> = ({
  initialValues,
  onSubmit,
  mode,
  loading = false
}) => {
  // 表单管理
  const {
    control,
    handleSubmit,
    formState: { errors, isDirty }
  } = useForm<AssetFormData>({
    resolver: zodResolver(assetFormSchema),
    defaultValues: initialValues,
    mode: 'onChange'
  });

  // 提交处理
  const handleFormSubmit = useCallback(
    async (values: AssetFormData) => {
      try {
        await onSubmit(values);
        message.success(`${mode === 'create' ? '创建' : '更新'}成功`);
      } catch (error) {
        message.error(`操作失败: ${error.message}`);
        throw error; // 重新抛出以供调用者处理
      }
    },
    [onSubmit, mode]
  );

  // 渲染组件
  return (
    <Form
      layout="vertical"
      onFinish={handleSubmit(handleFormSubmit)}
    >
      {/* 表单字段 */}
      {/* ... */}
    </Form>
  );
};

export default AssetForm;
```

### 组件命名规范

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| **组件文件** | PascalCase | `AssetForm.tsx` |
| **样式文件** | kebab-case | `asset-form.module.css` |
| **测试文件** | 组件名 + `.test.tsx` | `AssetForm.test.tsx` |
| **类型文件** | 组件名 + `.types.ts` | `AssetForm.types.ts` |
| **索引文件** | `index.ts` | `index.ts` |

### Props 接口定义

```typescript
/**
 * 组件 Props 必须定义接口
 */
interface ComponentProps {
  // 必需属性
  id: string;
  title: string;
  onSubmit: (data: FormData) => void;

  // 可选属性（使用 ? 标记）
  subtitle?: string;
  loading?: boolean;

  // 回调函数类型
  onCancel?: () => void;
  onChange?: (value: string) => void;

  // 子节点
  children?: React.ReactNode;
}
```

---

## 🔄 状态管理

### 状态管理架构

```
┌─────────────────────────────────────────────┐
│           状态管理架构                        │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐     ┌──────────────┐    │
│  │  Client State│     │ Server State │    │
│  │   (Zustand)  │     │ (React Query)│    │
│  │              │     │              │    │
│  │ - user       │     │ - assets     │    │
│  │ - theme      │     │ - contracts  │    │
│  │ - sidebar    │     │ - users      │    │
│  │ - permissions│     │ - cache      │    │
│  └──────────────┘     └──────────────┘    │
│           │                   │            │
│           └─────────┬─────────┘            │
│                     │                      │
│              ┌──────▼──────┐               │
│              │   React UI  │               │
│              └─────────────┘               │
└─────────────────────────────────────────────┘
```

### Zustand 全局状态

**用户状态 Store** (`store/useAppStore.ts`):
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  // 用户信息
  user: User | null;
  setUser: (user: User | null) => void;

  // 主题
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;

  // 侧边栏
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // 权限
  permissions: Permission[];
  hasPermission: (resource: string, action: string) => boolean;

  // UI 状态
  loading: boolean;
  setLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      theme: 'light',
      sidebarCollapsed: false,
      permissions: [],
      loading: false,

      // Actions
      setUser: (user) => set({ user }),
      setTheme: (theme) => set({ theme }),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setPermissions: (permissions) => set({ permissions }),
      setLoading: (loading) => set({ loading }),

      // 权限检查
      hasPermission: (resource, action) => {
        const { permissions } = get();
        return permissions.some(
          p => p.resource === resource && p.actions.includes(action)
        );
      }
    }),
    {
      name: 'app-storage', // localStorage key
      partialize: (state) => ({
        user: state.user,
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed
      })
    }
  )
);
```

### React Query 服务端状态

```typescript
// services/assetService.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { enhancedApiClient } from './enhancedApiClient';

// 获取资产列表
export function useAssets(filters?: AssetFilters) {
  return useQuery({
    queryKey: ['assets', filters],
    queryFn: async () => {
      const response = await enhancedApiClient.get('/assets', { params: filters });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
  });
}

// 创建资产
export function useCreateAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AssetFormData) => {
      const response = await enhancedApiClient.post('/assets', data);
      return response.data;
    },
    onSuccess: () => {
      // 使缓存失效，触发重新获取
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      message.success('资产创建成功');
    },
    onError: (error) => {
      message.error(`创建失败: ${error.message}`);
    }
  });
}
```

**证据来源**: `frontend/src/store/`, `frontend/src/services/`

---

## 🧭 路由系统

### 路由配置

```typescript
// routes/AppRoutes.tsx
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppRoutes } from '@/constants/routes';
import { PermissionGuard } from '@/components/Router/PermissionGuard';
import { RoutePerformanceMonitor } from '@/components/Router/RoutePerformanceMonitor';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to={AppRoutes.DASHBOARD} replace />
      },
      {
        path: AppRoutes.DASHBOARD,
        element: <DashboardPage />
      },
      {
        path: AppRoutes.ASSETS_LIST,
        element: <AssetListPage />
      },
      {
        path: AppRoutes.ASSETS_CREATE,
        element: (
          <PermissionGuard resource="assets" action="create">
            <AssetCreatePage />
          </PermissionGuard>
        )
      },
      // ... 更多路由
    ]
  }
]);
```

### 路由常量

```typescript
// constants/routes.ts
export const AppRoutes = {
  // 根路径
  ROOT: '/',

  // 主要模块
  DASHBOARD: '/dashboard',
  ASSETS: '/assets',
  RENTAL: '/rental',
  SYSTEM: '/system',

  // 资产管理
  ASSETS_LIST: '/assets/list',
  ASSETS_CREATE: '/assets/new',
  ASSETS_EDIT: '/assets/:id/edit',
  ASSETS_IMPORT: '/assets/import',
  ASSETS_ANALYTICS: '/assets/analytics',

  // 系统管理
  SYSTEM_USERS: '/system/users',
  SYSTEM_ROLES: '/system/roles',
  SYSTEM_ORGANIZATIONS: '/system/organizations',

  // 认证
  LOGIN: '/login',
  LOGOUT: '/logout'
} as const;
```

### 懒加载路由

```typescript
// 使用 React.lazy 进行代码分割
import { lazy, Suspense } from 'react';
import { LoadingSpinner } from '@/components/Loading/LoadingSpinner';

const AssetListPage = lazy(() => import('@/pages/Assets/AssetListPage'));
const AssetCreatePage = lazy(() => import('@/pages/Assets/AssetCreatePage'));

// 包装 Suspense
function withLazyLoading(Component: React.LazyExoticComponent<React.ComponentType<any>>) {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Component />
    </Suspense>
  );
}
```

**证据来源**: `frontend/src/routes/AppRoutes.tsx`, `frontend/src/constants/routes.ts`

---

## 🌐 API 集成

### API 客户端配置

```typescript
// services/enhancedApiClient.ts
import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

class EnhancedApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1', // Vite 代理到后端
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // 请求拦截器 - 添加认证 token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 响应拦截器 - 统一错误处理
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response.data,
      async (error) => {
        // Token 过期自动刷新
        if (error.response?.status === 401 && !error.config._retry) {
          error.config._retry = true;
          try {
            const newToken = await this.refreshToken();
            error.config.headers.Authorization = `Bearer ${newToken}`;
            return this.client.request(error.config);
          } catch {
            // 刷新失败，跳转登录
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.client.get(url, config);
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.client.post(url, data, config);
  }

  // ... 其他方法
}

export const enhancedApiClient = new EnhancedApiClient();
```

### API 服务模块

```typescript
// services/assetService.ts
import { enhancedApiClient } from './enhancedApiClient';
import type { Asset, AssetFormData, AssetFilters, PaginatedResponse } from '@/types/asset';

export const assetService = {
  // 获取资产列表
  getAssets: (filters?: AssetFilters): Promise<PaginatedResponse<Asset>> => {
    return enhancedApiClient.get('/assets', { params: filters });
  },

  // 获取单个资产
  getAsset: (id: string): Promise<Asset> => {
    return enhancedApiClient.get(`/assets/${id}`);
  },

  // 创建资产
  createAsset: (data: AssetFormData): Promise<Asset> => {
    return enhancedApiClient.post('/assets', data);
  },

  // 更新资产
  updateAsset: (id: string, data: Partial<AssetFormData>): Promise<Asset> => {
    return enhancedApiClient.put(`/assets/${id}`, data);
  },

  // 删除资产
  deleteAsset: (id: string): Promise<void> => {
    return enhancedApiClient.delete(`/assets/${id}`);
  }
};
```

**证据来源**: `frontend/src/services/`

---

## 🎨 样式和主题

### Ant Design 主题定制

```typescript
// main.tsx
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';

const appTheme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
    fontSize: 14,
  },
  components: {
    Button: {
      borderRadius: 4,
    },
    Input: {
      borderRadius: 4,
    },
  },
};

<ConfigProvider
  theme={appTheme}
  locale={zhCN}
>
  <App />
</ConfigProvider>
```

### CSS Modules

```tsx
// ComponentName.module.css
.container {
  display: flex;
  gap: 16px;
  padding: 24px;
}

.title {
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

// ComponentName.tsx
import styles from './ComponentName.module.css';

export const ComponentName = () => {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>标题</h1>
    </div>
  );
};
```

---

## 🧪 测试

### 组件测试

```tsx
// AssetForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AssetForm } from './AssetForm';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

const wrapper = ({ children }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);

describe('AssetForm', () => {
  it('应该渲染表单字段', () => {
    render(<AssetForm onSubmit={jest.fn()} mode="create" />, { wrapper });

    expect(screen.getByLabelText('资产名称')).toBeInTheDocument();
    expect(screen.getByLabelText('地址')).toBeInTheDocument();
  });

  it('应该在提交时调用 onSubmit', async () => {
    const mockSubmit = jest.fn();
    render(<AssetForm onSubmit={mockSubmit} mode="create" />, { wrapper });

    fireEvent.change(screen.getByLabelText('资产名称'), {
      target: { value: '测试资产' }
    });

    fireEvent.click(screen.getByRole('button', { name: '提交' }));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ propertyName: '测试资产' })
      );
    });
  });
});
```

### 测试命令

```bash
# 运行所有测试
npm test

# 监听模式
npm run test:watch

# 生成覆盖率报告
npm run test:coverage

# 运行特定测试文件
npm test -- AssetForm.test.tsx
```

**证据来源**: `frontend/package.json.scripts`

---

## ⚡ 性能优化

### 代码分割

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // React 核心
          'react-core': ['react', 'react-dom'],
          // Ant Design
          'antd-core': ['antd', '@ant-design/icons'],
          // 路由
          'react-router': ['react-router-dom'],
          // 状态管理
          'state-management': ['zustand', '@tanstack/react-query'],
          // 工具库
          'utils': ['lodash', 'dayjs'],
          // 图表
          'charts': ['recharts', '@ant-design/plots'],
        }
      }
    }
  }
});
```

### 懒加载和预加载

```typescript
// 路由懒加载
const AssetListPage = lazy(() => import('@/pages/Assets/AssetListPage'));

// 预加载关键资源
useEffect(() => {
  // 预加载用户可能访问的页面
  const prefetchPages = ['/assets/new', '/assets/import'];
  prefetchPages.forEach(path => {
    import(`@/pages${path}`);
  });
}, []);
```

### React Query 缓存策略

```typescript
// 全局配置
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,     // 5分钟内数据新鲜
      gcTime: 10 * 60 * 1000,       // 10分钟后清理缓存
      retry: 1,                      // 失败重试1次
      refetchOnWindowFocus: false,   // 窗口聚焦不重新获取
    },
  },
});
```

**证据来源**: `frontend/vite.config.ts`, `frontend/src/main.tsx`

---

## 🐛 调试技巧

### React DevTools

```bash
# 安装 React DevTools 浏览器扩展
# Chrome: https://chrome.google.com/webstore
# Firefox: https://addons.mozilla.org/firefox/
```

### 控制台调试

```typescript
// 开发环境日志
if (import.meta.env.DEV) {
  console.log('组件状态:', state);
  console.log('API 响应:', response);
}

// 性能测量
console.time('ComponentRender');
// ... 组件渲染代码
console.timeEnd('ComponentRender');
```

### 网络调试

```typescript
// 拦截器中记录请求
this.client.interceptors.request.use((config) => {
  if (import.meta.env.DEV) {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
  }
  return config;
});

this.client.interceptors.response.use((response) => {
  if (import.meta.env.DEV) {
    console.log(`[API Response] ${response.config.url}`, response.data);
  }
  return response;
});
```

---

## 🚨 常见问题

### Q1: 端口被占用
**问题**: `Port 5173 is already in use`
**解决**:
```bash
# 查找占用端口的进程
lsof -i :5173  # macOS/Linux
netstat -ano | findstr :5173  # Windows

# 终止进程或更改端口
# vite.config.ts 中修改 server.port
```

### Q2: 类型错误
**问题**: TypeScript 报错 `Cannot find module`
**解决**:
```bash
# 检查 tsconfig.json paths 配置
# 确保路径别名正确
# 运行类型检查
npm run type-check
```

### Q3: 代理错误
**问题**: API 请求失败，CORS 错误
**解决**:
```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8002',
      changeOrigin: true,
    }
  }
}
```

### Q4: 构建失败
**问题**: `npm run build` 失败
**解决**:
```bash
# 清理缓存
rm -rf node_modules dist
npm install

# 检查类型错误
npm run type-check

# 检查 ESLint
npm run lint
```

---

## 📋 开发检查清单

### 开发前
- [ ] 已拉取最新代码
- [ ] 已安装依赖 (`npm install`)
- [ ] 已配置环境变量
- [ ] 后端服务运行中

### 开发中
- [ ] 遵循组件命名规范
- [ ] Props 定义完整接口
- [ ] 使用 TypeScript 严格模式
- [ ] 添加必要的错误处理
- [ ] 性能考虑（懒加载、缓存）

### 提交前
- [ ] 代码通过 ESLint 检查
- [ ] 类型检查无错误
- [ ] 添加或更新测试
- [ ] 更新相关文档

---

## 🔗 相关链接

### 文档
- [环境配置指南](environment-setup.md)
- [数据库指南](database.md)
- [API 文档](../integrations/api-overview.md)
- [开发工作流程](development-workflow.md)

### 外部资源
- [React 文档](https://react.dev/)
- [TypeScript 文档](https://www.typescriptlang.org/docs/)
- [Vite 文档](https://vitejs.dev/)
- [Ant Design 文档](https://ant.design/)

### 代码位置
- [前端源码](../../frontend/src/)
- [组件库](../../frontend/src/components/)
- [页面组件](../../frontend/src/pages/)
- [API 服务](../../frontend/src/services/)
- [类型定义](../../frontend/src/types/)

## 📋 Changelog

### 2025-12-23 v1.0.0 - 初始版本
- ✨ 新增：前端开发完整指南
- 🏗️ 新增：技术架构和项目结构说明
- 📦 新增：组件开发规范和模板
- 🔄 新增：状态管理方案详解
- 🧭 新增：路由系统配置说明
- 🌐 新增：API 集成方式
- 🎨 新增：样式和主题定制
- ⚡ 新增：性能优化策略
- 🧪 新增：测试和调试指南

## 🔍 Evidence Sources
- **项目配置**: `frontend/package.json`
- **TypeScript配置**: `frontend/tsconfig.json`
- **Vite配置**: `frontend/vite.config.ts`
- **前端文档**: `frontend/CLAUDE.md`
- **源码结构**: `frontend/src/` 目录
