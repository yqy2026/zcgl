# Frontend CLAUDE.md

前端开发专用指南。通用信息见根目录 `AGENTS.md`；本文件只保留前端专属、`AGENTS.md` 未覆盖的补充。

**Last Updated**: 2026-08-16

---

## 快速开始

```bash
cd frontend
pnpm install            # 安装依赖
pnpm dev                # 启动开发服务器 (port 5173)
pnpm test               # 运行测试
pnpm lint               # Oxlint 检查
pnpm type-check         # 类型检查
```

---

## 导入路径

```typescript
// ✅ 使用 @/ 别名
import { apiClient } from '@/api/client';
import { API_CONFIG } from '@/api/config';
import { AssetForm, ProjectForm } from '@/components/Forms';

// ❌ 深层相对路径 ../../../；@/services 桶仅 re-export 兼容，权威导入源是 @/api/client
```

---

## TypeScript 规范

严格布尔表达式（`??` / `!= null` / `?.` / `trim()` 字符串检查）规则见 `AGENTS.md` §前端开发要点；详细规范见 [`docs/guides/typescript-conventions.md`](../../docs/guides/typescript-conventions.md)。

---

## Decimal/Number 转换

后端常以 `Decimal` 字符串返回金额/面积字段，前端业务默认用 `number`。

- **统一入口**：服务层返回前调用 `convertBackendToFrontend`（`src/utils/dataConversion.ts`）
- **页面约束**：页面/组件层禁止用 `parseFloat` 临时兜底金额/面积字段
- **提交约束**：提交后端时按字段需要调用 `convertFrontendToBackend`
- **字段范围**：优先覆盖高频字段（`land_area`、`actual_property_area`、`rentable_area`、`monthly_rent`、`deposit/total_deposit` 等）
- **测试要求**：新增或改造服务时补转换链路测试（至少覆盖一个 Decimal 字符串 → number 场景）

---

## 状态管理与数据获取

状态分工（Zustand / AuthContext / React Query / React Hook Form / useState）见 `AGENTS.md` §前端状态管理。

```typescript
// ✅ 服务器数据用 React Query
const { data: assets, isLoading } = useQuery({
  queryKey: ['assets'],
  queryFn: () => apiClient.get('/assets'),
  staleTime: 5 * 60 * 1000,
});

// ❌ 不要用 useState + useEffect 管理服务器数据
```

---

## 路由与权限

路由常量统一定义在 `src/constants/routes.ts`；受保护路由在 `src/routes/AppRoutes.tsx` 用 `React.lazy` + 权限声明（`permissions` / `adminOnly` / `capabilityGuardBypass`）注册，渲染层由 `App.tsx` 用 `CapabilityGuard`（`src/components/System/CapabilityGuard.tsx`）统一包裹。新增页面按既有条目模式注册；`PermissionGuard` 是迁移期兼容壳，新代码一律用 `CapabilityGuard`。

---

## 环境变量

`VITE_API_BASE_URL` - API 后端地址（默认 `http://localhost:8002/api/v1`，见 `frontend/.env.example`）。

---

## 性能相关约定

图片懒加载用 `components/Common/LazyImage`。

---

## 测试与代码风格

- 测试命令与规范：[`docs/guides/testing-standards.md`](../../docs/guides/testing-standards.md)；默认 `pnpm test`
- 命名规范：[`docs/guides/naming-conventions.md`](../../docs/guides/naming-conventions.md)
- 前端指南总入口：[`docs/guides/frontend.md`](../../docs/guides/frontend.md)
