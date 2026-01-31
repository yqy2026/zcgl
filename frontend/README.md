# 土地物业资产管理系统 - 前端

基于 React + TypeScript + Vite 构建的现代化前端应用。

## 技术栈

- **框架**: React 19 + TypeScript
- **构建工具**: Vite 6
- **UI组件库**: Ant Design 6
- **路由**: React Router v6
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **HTTP客户端**: Axios
- **图表**: Recharts
- **日期处理**: Day.js

## 核心功能模块

### 1. 资产管理

- 资产增删改查操作
- 58个字段的详细资产信息展示
- 批量操作支持
- 资产历史记录追踪
- 资产出租率自动计算
- 资产财务数据汇总

### 2. 统计分析

- 整体出租率统计
- 按分类的出租率分析
- 面积汇总统计
- 财务数据汇总
- 多维度数据可视化

### 3. 智能PDF导入

- PDF文件上传
- 合同信息预览
- 数据确认导入

### 4. 权限管理

- 用户登录/登出
- 角色权限控制
- 组织架构展示

### 5. 数据导入导出

- Excel导入导出
- 模板下载

## 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── components/         # 可复用组件
│   │   ├── Asset/          # 资产相关组件
│   │   ├── Layout/         # 布局组件
│   │   ├── Statistics/     # 统计相关组件
│   │   └── ...
│   ├── pages/              # 页面组件
│   │   ├── Asset/          # 资产页面
│   │   ├── Dashboard/      # 仪表板页面
│   │   ├── Login/          # 登录页面
│   │   ├── Statistics/     # 统计页面
│   │   └── ...
│   ├── services/           # API服务层
│   │   ├── api.ts          # API客户端
│   │   ├── assetService.ts # 资产服务
│   │   ├── dictionary/     # 字典服务
│   │   └── ...
│   ├── store/              # Zustand状态管理
│   ├── types/              # TypeScript类型定义
│   ├── utils/              # 工具函数
│   ├── hooks/              # 自定义Hooks
│   ├── App.tsx             # 主应用组件
│   ├── App.css             # 全局样式
│   ├── main.tsx            # 应用入口
│   └── index.css           # 基础样式
├── index.html              # HTML模板
├── package.json            # 项目配置
├── tsconfig.json           # TypeScript配置
├── vite.config.ts          # Vite配置
└── README.md               # 项目说明
```

## 功能特性

### 核心功能

- ✅ **资产管理** - 完整的CRUD操作
- ✅ **搜索筛选** - 多条件搜索和筛选
- ✅ **数据导入导出** - Excel文件处理
- ✅ **统计仪表板** - 数据可视化展示
- ✅ **变更历史** - 资产变更记录追踪
- ✅ **权限控制** - 基于角色的访问控制

### 技术特性

- ✅ **响应式设计** - 适配各种屏幕尺寸
- ✅ **类型安全** - 完整的TypeScript支持
- ✅ **状态管理** - Zustand轻量级状态管理
- ✅ **数据缓存** - React Query智能缓存
- ✅ **错误处理** - 完善的错误处理机制
- ✅ **国际化支持** - 中文界面优化

## 开发环境设置

### 前置要求

- Node.js >= 18.0.0
- npm >= 8.0.0

### 安装依赖

```bash
cd frontend
pnpm install
```

### 启动开发服务器

```bash
pnpm dev
```

应用将在 http://localhost:5173 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
pnpm preview
```

## 配置说明

### 环境变量

创建 `.env.local` 文件配置环境变量：

```env
# API基础URL
VITE_API_BASE_URL=http://localhost:8002/api

# 应用标题
VITE_APP_TITLE=土地物业资产管理系统
```

### 代理配置

开发环境下，Vite会自动代理API请求到后端服务器：

```typescript
// vite.config.ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8002',
      changeOrigin: true,
    },
  },
}
```

## 主要页面说明

### 1. 登录页面 (LoginPage)

- 用户身份验证
- 使用 httpOnly Cookie 认证（不在 localStorage 存储 token）

### 2. 仪表板页面 (DashboardPage)

- 关键指标展示
- 统计图表
- 快速操作入口

### 3. 资产列表页面 (AssetListPage)

- 数据表格展示
- 搜索和筛选功能
- 分页处理
- 批量操作

### 4. 资产详情页面 (AssetDetailPage)

- 详细信息展示
- 变更历史记录
- 编辑操作入口

### 5. 统计分析页面 (StatisticsPage)

- 整体出租率统计
- 分类出租率分析
- 面积汇总统计
- 财务数据汇总

### 6. PDF导入页面 (PdfImportPage)

- PDF文件上传
- 合同信息预览
- 数据确认导入

## 状态管理

### Asset Store (useAssetStore)

管理资产相关状态：

- 资产列表数据
- 搜索参数
- 分页信息
- 选中的资产

### App Store (useAppStore)

管理应用全局状态：

- 侧边栏折叠状态
- 主题设置
- 用户偏好
- 通知消息

## API服务层

### API Client (api.ts)

- Axios实例配置
- 请求/响应拦截器
- 错误处理
- 文件上传/下载

### Asset Service (assetService.ts)

- 资产CRUD操作
- 搜索和筛选
- 历史记录查询
- 数据导入导出

### Dictionary Service (dictionary/)

- 统一字典服务
- 字典数据获取和管理

## 自定义Hooks

### useAssets

- 资产列表查询
- 创建、更新、删除操作
- 批量操作
- 状态同步

### 其他Hooks

- useAssetHistory - 变更历史
- useAssetStats - 统计数据
- useValidateAsset - 数据验证
- useDictionary - 字典数据获取

## 样式和主题

### 全局样式

- 基础重置样式
- 工具类样式
- 响应式断点

### Ant Design主题

- 自定义主题色彩
- 组件样式覆盖
- 中文字体优化

## 开发规范

### 代码规范

- 使用 ESLint 进行代码检查
- 使用 TypeScript 严格模式
- 组件使用函数式组件 + Hooks
- 遵循 React 最佳实践

### 命名规范

- 组件使用 PascalCase
- 文件名使用 PascalCase
- 变量和函数使用 camelCase
- 常量使用 UPPER_SNAKE_CASE

### 目录规范

- 按功能模块组织代码
- 组件就近放置相关文件
- 公共组件放在 components 目录
- 页面组件放在 pages 目录

## 性能优化

### 代码分割

- 路由级别的代码分割
- 组件懒加载
- 第三方库按需加载

### 缓存策略

- React Query 智能缓存
- 静态资源缓存
- API响应缓存

### 打包优化

- Vite 快速构建
- Tree Shaking
- 资源压缩

## 测试

### 单元测试

```bash
pnpm test
```

### 端到端测试

```bash
pnpm test:e2e
```

## 部署

### 构建生产版本

```bash
npm run build
```

### 部署到静态服务器

构建后的文件在 `dist` 目录，可以部署到任何静态文件服务器。

### Docker部署

```dockerfile
FROM nginx:alpine
COPY dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 故障排除

### 常见问题

1. **端口冲突**
   - 修改 `vite.config.ts` 中的端口配置

2. **API请求失败**
   - 检查后端服务是否启动
   - 确认代理配置是否正确

3. **依赖安装失败**
   - 清除 node_modules 和 package-lock.json
   - 重新安装依赖

### 调试技巧

- 使用浏览器开发者工具
- 查看 Network 面板的API请求
- 使用 React Developer Tools
- 查看 Console 面板的错误信息

## 开发约定

### 前端开发

- 使用React 19和TypeScript
- Ant Design 6组件库
- Vite 6构建工具
- 遵循组件化开发模式
- 使用ESLint和Prettier进行代码检查和格式化
- 实现单元测试和端到端测试

## 系统访问

- 前端应用：http://localhost:5173
- API文档：http://localhost:8002/docs
- 健康检查：http://localhost:8002/health
