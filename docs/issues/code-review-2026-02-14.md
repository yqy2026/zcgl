# 代码审查问题清单

**审查日期**: 2026-02-14
**审查范围**: 全项目（后端、前端、测试、配置）
**审查工具**: Claude Code 多维度并行审查
**问题总数**: 50+

---

## 问题统计

| 严重程度 | 数量 | 说明 |
|:--------:|:----:|------|
| 🔴 **严重** | 7 | 必须立即修复 |
| 🟠 **高危** | 12 | 尽快修复（1-2周内） |
| 🟡 **中等** | 15 | 建议修复（迭代中处理） |
| 🟢 **低危** | 4+ | 持续改进 |

---

## 🔍 复核结果（2026-02-15）

已对“已修复/已关闭”项进行代码级复核，结论如下：

- ✅ C-01：`deployment/nginx/nginx.conf` 与 `deployment/nginx/ssl/.gitkeep` 已存在
- ✅ C-03：`backend/src/security/secret_validator.py` 已移除 `print`，改为 `logger`
- ✅ C-05：`frontend/src/hooks/useContractList.ts`、`frontend/src/pages/Rental/RentLedgerPage.tsx` 空 `catch` 已改为记录 `error`
- ✅ C-06：`frontend/src/utils/highlight.ts`、`frontend/src/pages/Contract/ContractImportStatus.tsx` 已不使用 `index` 作为 key
- ✅ C-07：`frontend/tests/e2e/global-setup.ts` 会自动生成 storage state 文件，判定误报关闭
- ✅ H-11：`CLAUDE.md` 已同步完整 pytest markers
- ✅ H-12：`frontend/src/pages/Contract/ContractImportStatus.tsx` 已实现连续失败计数并在阈值后停止轮询
- ✅ C-04：`PromptDashboard` 已重构为 `hooks/usePromptDashboardData.ts`，原风险点在当前实现中不成立
- ✅ C-02：已清理 `assets.py/core.validators/security.permissions` 的重复异常定义，`exceptions.py` 改为基于 `core/exception_handler.py` 的兼容包装
- ✅ H-01：`TokenBlacklistManager` 新增生产环境分布式存储约束，未启用 Redis 时在运行期拒绝黑名单操作
- ✅ H-02：`AssetService` 已改为构造注入 `asset_crud`，移除模块级可变全局
- ✅ H-06/H-07：相关测试文件已移除 `as any` 与隐式 `any`
- ✅ H-04：`usePromptDashboardData.ts` 已改为 `useQuery` 承载 Prompt 详情数据（移除 `useState + useEffect` 拉取链路）
- ✅ H-05：当前实现中 `handleRefresh/handleDateRangeChange/handlePromptChange` 均为 `useCallback`，`loadPromptDetails` 为模块级稳定函数
- ✅ H-08：已新增 6 个缺失模型单测文件（`ownership/organization/project/contact/rbac/property_certificate`）
- ✅ H-09：已新增 `services/operation_log` 独立单测文件，覆盖核心查询与统计分支
- ✅ H-10：`vitest.config.ts` 覆盖率阈值已提升（默认 55/50），并支持严格模式 `VITEST_COVERAGE_STRICT=true`（70/65）
- ✅ M-01：`asset.py` 已抽取通用 `_invoke_result_chain()`，统一异步 result/scalars 调用链
- ✅ M-02：`crud/asset.py` 与 `asset_service.py` 已统一使用 `DataStatusValues` 常量，移除硬编码中文状态
- ✅ M-03：`middleware/auth.py`、`api/v1/__init__.py` 已移除 `sys.stderr.write` 调试输出
- ✅ M-04：已完成首轮超长文件拆分（`asset_support.py`、`token_blacklist_guard.py`、`database_url.py`），并通过黑名单/加密/资产 CRUD 回归
- ✅ M-05：`TableWithPagination` 已接入按阈值自动启用虚拟滚动（默认 `>=100` 行），覆盖资产/合同等复用列表
- ✅ M-06：`usePDFImportSession` 已保存并清理 `setTimeout` 引用，避免卸载后悬挂回调
- ✅ M-07：`unit/integration/e2e` 的事务型 `db_session` 构建与清理逻辑已抽取到共享工具，减少重复 fixture 实现
- ✅ M-08：已新增迁移命名校验脚本并接入 `lint-backend`，对历史 hash 文件做兼容白名单
- ✅ M-09：`core/config.py` 已移除 `type: ignore[call-arg]`，改为 `TYPE_CHECKING` 构造签名兼容
- ✅ M-10：`api/v1/__init__.py` 已抽取 `_load_optional_router()` 统一可选路由加载，减少重复条件导入
- ✅ M-11：`CRUDBase` 缓存键改为稳定序列化，并将 `tenant_filter/exclude_empty` 纳入 distinct 缓存隔离
- ✅ M-12：`asset.py` 已抽取 `_clean_asset_data()`，收敛 create/update 路径重复 `pop`
- ✅ M-13：已清理 `frontend/src` 中 79 处 `eslint-disable-next-line` 注释，并新增 `scan:lint-disable` 门禁脚本接入 `guard:ui`
- ✅ M-15：测试 Mock 与用例中已移除 `index` 作为 React key
- ✅ L-01：`api/v1/dependencies.py` 导入顺序已规范化
- ✅ L-02：复核为误报，`asynccontextmanager` 在 `_transaction` 中仍被实际使用
- ✅ L-03：`assets.py` 顶部注释已更新为“聚合入口+子路由分工”描述，和当前职责一致
- ✅ L-04：`ContractImportReview.tsx` 已改为统一 logger，`ContractImportStatus.tsx` 无 `console.*` 残留
- ✅ H-03：已完成第三批 Any 收敛，`database.py` / `core/exception_handler.py` / `crud/asset.py` 三个热点已清零（阶段化关闭）

---

## 🔴 严重问题 (CRITICAL) - 必须立即修复

### C-01: Docker 部署配置缺失

| 属性 | 值 |
|------|-----|
| **位置** | `docker-compose.yml:106-107` |
| **类别** | 配置/部署 |
| **影响** | Docker Compose 启动失败 |

**问题描述**:
```yaml
volumes:
  - ./deployment/nginx/nginx.conf:/etc/nginx/nginx.conf
  - ./deployment/nginx/ssl:/etc/nginx/ssl
```
`deployment/` 目录不存在，导致容器挂载失败。

**修复方案**:
```bash
mkdir -p deployment/nginx/ssl
# 创建 nginx.conf 配置文件
# 配置 SSL 证书（开发环境可用自签名）
```

**状态**: [x] 已修复（2026-02-15）

---

### C-02: 异常类重复定义

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/api/v1/assets/assets.py:1-11`, `backend/src/exceptions.py:10-31` |
| **类别** | 后端/架构 |
| **影响** | 异常处理混乱，可能导入错误类 |

**问题描述**:
两处定义了同名异常类 `AssetNotFoundError`、`DuplicateAssetError`、`NotFoundError`。

**修复方案**:
统一使用 `core/exception_handler.py` 中的异常类，删除重复定义。

**状态**: [x] 已修复（2026-02-15）

---

### C-03: 敏感信息输出到 stdout

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/security/secret_validator.py:91-102` |
| **类别** | 后端/安全 |
| **影响** | 生产环境可能泄露敏感信息 |

**问题描述**:
```python
print(f"验证结果: {result}")  # 使用 print 而非 logger
```

**修复方案**:
改用 `logging` 模块记录日志。

**状态**: [x] 已修复（2026-02-15）

---

### C-04: useEffect 无限循环风险

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/src/pages/System/PromptDashboard/hooks/usePromptDashboardData.ts` |
| **类别** | 前端/React |
| **影响** | 可能导致无限请求或性能问题 |

**问题描述**:
```typescript
useEffect(() => {
  if (selectedPromptId != null) {
    loadPromptDetails(selectedPromptId);  // 函数每次渲染重新创建
  }
}, [selectedPromptId]); // 缺少 loadPromptDetails 依赖
```

**修复方案**:
使用 `useCallback` 包裹 `loadPromptDetails` 函数。

**状态**: [x] 已关闭（代码已重构，2026-02-15）

---

### C-05: 空 catch 块吞掉错误

| 属性 | 值 |
|------|-----|
| **位置** | 多处（详见下表） |
| **类别** | 前端/错误处理 |
| **影响** | 无法追踪问题根源，调试困难 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `hooks/useContractList.ts` | 159-162, 171-173, 192-194 |
| `pages/Rental/RentLedgerPage.tsx` | 268-270, 291-293, 311-313 |

**问题描述**:
```typescript
} catch {
  MessageManager.error('删除失败');  // 错误对象被丢弃
}
```

**修复方案**:
```typescript
} catch (error: unknown) {
  logger.error('删除失败', error);
  MessageManager.error('删除失败');
}
```

**状态**: [x] 已修复（2026-02-15）

---

### C-06: 使用 index 作为 React key

| 属性 | 值 |
|------|-----|
| **位置** | 多处（详见下表） |
| **类别** | 前端/React |
| **影响** | 列表变化时可能渲染异常 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `utils/highlight.ts` | 32-45 |
| `pages/Contract/ContractImportStatus.tsx` | 371-386 |

**问题描述**:
```typescript
items={steps.map((step, index) => ({
  key: index,  // 反模式！
}))}
```

**修复方案**:
使用唯一标识符作为 key（如 `step.id`）。

**状态**: [x] 已修复（2026-02-15）

---

### C-07: E2E 测试认证状态为空

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/tests/e2e/storage/` |
| **类别** | 测试/E2E |
| **影响** | E2E 测试无法正常运行 |

**问题描述**:
该项为误报。`frontend/tests/e2e/global-setup.ts` 会在运行前自动创建
`admin-state.json`、`asset-manager-state.json`、`asset-viewer-state.json`。

**处置说明**:
标记为“已关闭（误报）”，无需额外修复。

**状态**: [x] 已关闭（误报，2026-02-15）

---

## 🟠 高危问题 (HIGH) - 尽快修复

### H-01: Token 黑名单使用内存存储

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/security/token_blacklist.py:24-26` |
| **类别** | 后端/安全 |
| **影响** | 多实例部署时令牌撤销失效 |

**问题描述**:
```python
self._blacklisted_tokens: set[str] = set()  # 内存存储
```

**修复方案**:
生产环境强制使用 Redis，添加配置检查。

**状态**: [x] 已修复（2026-02-15）

---

### H-02: 全局变量滥用

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/services/asset/asset_service.py:26-27` |
| **类别** | 后端/架构 |
| **影响** | 测试和多线程环境状态污染 |

**问题描述**:
```python
_DEFAULT_ASSET_CRUD: object = object()
asset_crud: Any = _DEFAULT_ASSET_CRUD  # 模块级可变全局变量
```

**修复方案**:
使用依赖注入模式替代全局变量。

**状态**: [x] 已修复（2026-02-15）

---

### H-03: Any 类型过度使用

| 属性 | 值 |
|------|-----|
| **位置** | 99 个文件，共 318 处 |
| **类别** | 后端/类型安全 |
| **影响** | 绕过类型检查，隐藏潜在错误 |

**热点文件**:
| 文件 | Any 数量 |
|------|:--------:|
| `database.py` | 0（已清零） |
| `crud/asset.py` | 0（已清零） |
| `core/exception_handler.py` | 0（已清零） |

**修复方案**:
逐步替换为具体类型，优先处理核心模块。

**进展（2026-02-15）**:
- 已完成第一批收敛：`database.py` 热点中的 14 处 `Any` 已清零（事件回调、健康状态结构、Base 类型注解等）。
- 已完成第二批收敛：`core/exception_handler.py` 热点中的 11 处 `Any` 已清零（异常详情类型、辅助抛出函数与处理器签名收敛）。
- 已完成第三批收敛：`crud/asset.py` 热点中的 56 处 `Any` 已清零（CRUD 入参/过滤器/聚合返回类型与异步 result 链调用签名收敛）。

**状态**: [x] 已修复（阶段化：核心热点完成，2026-02-15）

---

### H-04: useState 管理服务器数据

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/src/pages/System/PromptDashboard.tsx:202-204` |
| **类别** | 前端/状态管理 |
| **影响** | 缺少缓存、重试、同步机制 |

**问题描述**:
```typescript
// ❌ 错误 - 应使用 React Query
const [performanceData, setPerformanceData] = useState<PerformanceMetrics[]>([]);
```

**修复方案**:
改用 `useQuery` 管理服务器数据。

**状态**: [x] 已修复（2026-02-15）

---

### H-05: 缺少 useCallback 优化

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/src/pages/System/PromptDashboard.tsx` |
| **类别** | 前端/性能 |
| **影响** | 不必要的重渲染 |

**问题函数**:
- `loadPromptDetails`
- `handleRefresh`
- `handleDateRangeChange`
- `handlePromptChange`

**修复方案**:
使用 `useCallback` 包裹这些函数。

**状态**: [x] 已关闭（当前实现已满足，2026-02-15）

---

### H-06: 类型断言滥用

| 属性 | 值 |
|------|-----|
| **位置** | 多个测试文件 |
| **类别** | 前端/类型安全 |
| **影响** | 绕过类型检查 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `components/Common/__tests__/FriendlyErrorDisplay.test.tsx` | 60 |
| `components/Feedback/__tests__/ConfirmDialog.test.tsx` | 84 |

**问题描述**:
```typescript
type={type as any}
```

**修复方案**:
使用正确的类型定义或测试工具函数。

**状态**: [x] 已修复（2026-02-15）

---

### H-07: 隐式 any 类型

| 属性 | 值 |
|------|-----|
| **位置** | 多个测试文件 |
| **类别** | 前端/类型安全 |
| **影响** | 缺少类型检查 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `components/Auth/__tests__/AuthGuard.test.tsx` | 26, 50 |
| `components/Asset/__tests__/AssetExport.test.tsx` | 477 |

**修复方案**:
为测试函数添加正确的类型定义。

**状态**: [x] 已修复（2026-02-15）

---

### H-08: 模型单元测试缺失

| 属性 | 值 |
|------|-----|
| **位置** | `backend/tests/unit/models/` |
| **类别** | 测试/单元测试 |
| **影响** | 模型变更缺少验证 |

**缺失测试的模型**:
- `ownership.py`
- `organization.py`
- `project.py`
- `contact.py`
- `rbac.py`
- `property_certificate.py`

**修复方案**:
为这些模型添加单元测试。

**状态**: [x] 已修复（2026-02-15）

---

### H-09: Service 层部分缺失测试

| 属性 | 值 |
|------|-----|
| **位置** | `backend/tests/` |
| **类别** | 测试/单元测试 |
| **影响** | 业务逻辑缺少验证 |

**缺失测试的服务**:
- `services/operation_log/`（`system_settings` 已有 `test_system_settings_service.py`）

**修复方案**:
为这些服务添加独立测试文件。

**状态**: [x] 已修复（2026-02-15）

---

### H-10: 前端覆盖率阈值过低

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/vitest.config.ts` |
| **类别** | 测试/配置 |
| **影响** | 代码质量保障较弱 |

**当前状态**:
- 前端阈值（默认）: 55% (lines), 50% (branches)
- 前端阈值（严格模式）: 70% (lines), 65% (branches)（`VITEST_COVERAGE_STRICT=true`）
- 后端阈值: 70%

**修复方案**:
分阶段提升前端覆盖率阈值至 70%。

**状态**: [x] 已修复（阶段化，2026-02-15）

---

### H-11: 测试标记文档不完整

| 属性 | 值 |
|------|-----|
| **位置** | `CLAUDE.md` |
| **类别** | 文档 |
| **影响** | 开发者不知道所有可用标记 |

**文档中列出的标记** (8个):
`unit`, `integration`, `e2e`, `api`, `database`, `security`, `performance`, `slow`

**实际存在的标记** (16个):
`unit`, `integration`, `e2e`, `slow`, `database`, `api`, `vision`, `pdf`, `rbac`, `security`, `performance`, `load`, `stress`, `core`, `asyncio`, `concurrency`

**修复方案**:
更新 CLAUDE.md 文档，列出所有测试标记。

**状态**: [x] 已修复（2026-02-15）

---

### H-12: 轮询逻辑缺少失败计数

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/src/pages/Contract/ContractImportStatus.tsx:182-187` |
| **类别** | 前端/错误处理 |
| **影响** | 错误时可能无限重试或过早停止 |

**问题描述**:
```typescript
} catch (error: unknown) {
  console.error('获取进度失败:', error);
  // 注释说"连续多次失败时才停止"，但代码未实现
}
```

**修复方案**:
添加失败计数器，达到阈值后停止轮询。

**状态**: [x] 已修复（2026-02-15）

---

## 🟡 中等问题 (MEDIUM) - 建议修复

### M-01: 重复代码 - 异步结果辅助函数

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/crud/asset.py:37-83` |
| **类别** | 后端/代码质量 |

**问题描述**:
定义了 6 个几乎相同的辅助函数（`_result_all`, `_scalars_all` 等）。

**修复方案**:
抽取为通用工具类。

**状态**: [x] 已修复（2026-02-15）

---

### M-02: 硬编码中文字符串

| 属性 | 值 |
|------|-----|
| **位置** | 多处 |
| **类别** | 后端/可维护性 |

**问题位置**:
| 文件 | 行号 | 内容 |
|------|------|------|
| `crud/asset.py` | 253 | `data_status != "已删除"` |
| `services/asset/asset_service.py` | 575 | `asset.data_status = "已删除"` |

**修复方案**:
使用枚举或常量定义状态值。

**状态**: [x] 已修复（2026-02-15）

---

### M-03: sys.stderr.write 调试输出

| 属性 | 值 |
|------|-----|
| **位置** | 多处 |
| **类别** | 后端/日志 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `middleware/auth.py` | 244, 248 |
| `api/v1/__init__.py` | 56, 65, 117 |

**修复方案**:
移除或改用 `logging` 模块。

**状态**: [x] 已修复（2026-02-15）

---

### M-04: 过长的文件

| 属性 | 值 |
|------|-----|
| **位置** | 多处 |
| **类别** | 后端/可维护性 |

**问题文件**:
| 文件 | 行数 |
|------|:----:|
| `crud/asset.py` | 1156 |
| `middleware/auth.py` | 779 |
| `database.py` | 610 |

**修复方案**:
拆分为更小的模块。

**修复结果（2026-02-15）**:
- `backend/src/crud/asset.py` 拆出 `backend/src/crud/asset_support.py`，迁移类型别名、异步 result 调用链辅助与 `SensitiveDataHandler`，主文件行数 `1156 -> 964`。
- `backend/src/middleware/auth.py` 拆出 `backend/src/middleware/token_blacklist_guard.py`，迁移 token 黑名单熔断与降级告警逻辑，主文件行数 `776 -> 656`。
- `backend/src/database.py` 拆出 `backend/src/database_url.py`，迁移 `DATABASE_URL` 解析与校验逻辑，主文件行数 `616 -> 546`。
- 兼容性回归通过：`pytest -q -o addopts='' backend/tests/unit/core/test_blacklist.py backend/tests/unit/core/test_encryption.py backend/tests/unit/crud/test_asset.py`（`73 passed`）。

**状态**: [x] 已修复（阶段化，2026-02-15）

---

### M-05: 大列表未虚拟化

| 属性 | 值 |
|------|-----|
| **位置** | 前端全局 |
| **类别** | 前端/性能 |

**问题描述**:
项目未使用 `react-window` 或 `react-virtualized`。

**影响**:
资产列表、合同列表大数据量时性能问题。

**修复方案**:
引入虚拟滚动组件。

**修复结果（2026-02-15）**:
- 在 `frontend/src/components/Common/TableWithPagination.tsx` 引入“阈值触发”的虚拟滚动能力：
  - 默认开启 `enableVirtual=true`
  - 默认阈值 `virtualThreshold=100`
  - 自动补齐虚拟滚动窗口高度 `virtualScrollY=640`
- 通过通用组件复用路径覆盖资产、合同、系统管理等多个大列表页面，无需逐页改造。

**状态**: [x] 已修复（2026-02-15）

---

### M-06: setTimeout 未保存引用

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/src/hooks/usePDFImportSession.ts:100-102` |
| **类别** | 前端/内存泄漏 |

**问题描述**:
```typescript
setTimeout(() => {  // 返回值未保存
  setCurrentSession(prev => ...);
}, 100);
```

**修复方案**:
保存返回值并在 `useEffect` 清理函数中清除。

**状态**: [x] 已修复（2026-02-15）

---

### M-07: 测试 Fixtures 重复定义

| 属性 | 值 |
|------|-----|
| **位置** | 多个 `conftest.py` 文件 |
| **类别** | 测试/可维护性 |

**问题描述**:
`test_user` 等 fixture 在多个 `conftest.py` 中重复定义。

**修复方案**:
考虑集中管理或使用 fixture 继承。

**状态**: [x] 已修复（2026-02-15，共享事务 session fixture）

---

### M-08: 迁移文件命名不一致

| 属性 | 值 |
|------|-----|
| **位置** | `backend/alembic/versions/` |
| **类别** | 数据库/规范 |

**问题描述**:
- 有的用日期前缀: `20260211_...`
- 有的用 hash: `e4c9e4968dd7_...`

**修复方案**:
未来迁移使用统一命名规范（建议日期前缀）。

**状态**: [x] 已修复（2026-02-15，历史兼容 + 新增命名门禁）

---

### M-09: 类型忽略注解

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/core/config.py:100` |
| **类别** | 后端/类型安全 |

**问题描述**:
```python
settings = Settings()  # type: ignore[call-arg]
```

**修复方案**:
修复 Pydantic Settings 配置以消除类型错误。

**状态**: [x] 已修复（2026-02-15）

---

### M-10: 条件导入过多

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/api/v1/__init__.py:49-66` |
| **类别** | 后端/可维护性 |

**问题描述**:
大量条件导入增加代码复杂度。

**修复方案**:
使用延迟导入或重构模块依赖。

**状态**: [x] 已修复（2026-02-15）

---

### M-11: 缓存键生成可能冲突

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/crud/base.py:76-82` |
| **类别** | 后端/缓存 |

**问题描述**:
复杂对象作为值时可能生成不一致的键。

**修复方案**:
对复杂值使用 hash 或 json 序列化。

**状态**: [x] 已修复（2026-02-15）

---

### M-12: 冗余的 pop 操作

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/crud/asset.py` |
| **类别** | 后端/代码质量 |

**问题位置**:
- `create_async` (446-457)
- `create_with_history_async` (685-695)
- `update_async` (738-749)
- `update_with_history_async` (779-787)

**修复方案**:
抽取为 `_clean_asset_data()` 方法。

**状态**: [x] 已修复（2026-02-15）

---

### M-13: Lint 禁用注释过多

| 属性 | 值 |
|------|-----|
| **位置** | 前端全局 |
| **类别** | 前端/代码质量 |

**问题描述**:
共发现 70+ 处 lint 禁用注释（如 `disable-next-line`）。

**修复方案**:
审查是否真的必要，减少使用。

**修复结果（2026-02-15）**:
- 已从 `frontend/src` 清理 79 处 `eslint-disable-next-line` 注释（`no-console`、`react-hooks/exhaustive-deps`、`@typescript-eslint/*`）。
- 新增 `frontend/scripts/scan-lint-disable-comments.js`，并接入：
  - `pnpm scan:lint-disable`
  - `pnpm scan:lint-disable:report`
  - `pnpm guard:ui / guard:ui:report / guard:ui:ci`
- `external.d.ts` 通过移除不安全的 interface/class 同名声明合并，消除 `typescript-eslint(no-unsafe-declaration-merging)` 告警，不再依赖禁用注释。

**状态**: [x] 已修复（2026-02-15）

---

### M-14: useEffect 依赖数组不完整

| 属性 | 值 |
|------|-----|
| **位置** | `frontend/src/pages/System/DictionaryPage.tsx:193-196` |
| **类别** | 前端/React |

**问题描述**:
```typescript
useEffect(() => {
  fetchTypes();
  fetchAllEnumData();
}, []); // 空依赖数组
```

**修复方案**:
添加缺失的依赖或使用 `useCallback`。

**状态**: [x] 已关闭（重构后不成立，2026-02-15）

---

### M-15: 测试文件中使用 index 作为 key

| 属性 | 值 |
|------|-----|
| **位置** | 多个测试文件 |
| **类别** | 前端/测试 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `test-utils/mocks/antdMocks.tsx` | 351 |
| `components/Layout/__tests__/AppBreadcrumb.test.tsx` | 41 |

**修复方案**:
测试中也应养成良好习惯。

**状态**: [x] 已修复（2026-02-15）

---

## 🟢 低危问题 (LOW) - 持续改进

### L-01: 导入顺序不规范

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/api/v1/dependencies.py` |
| **类别** | 后端/规范 |

**修复方案**:
按标准库、第三方库、本地模块顺序组织导入。

**状态**: [x] 已修复（2026-02-15）

---

### L-02: 未使用的导入

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/services/asset/asset_service.py:1` |
| **类别** | 后端/代码质量 |

**问题描述**:
`asynccontextmanager` 导入但可能未在外部使用。

**修复方案**:
移除未使用的导入。

**状态**: [x] 已关闭（误报，2026-02-15）

---

### L-03: 注释与文档不一致

| 属性 | 值 |
|------|-----|
| **位置** | `backend/src/api/v1/assets/assets.py:17-20` |
| **类别** | 后端/文档 |

**问题描述**:
注释提到"批量操作、导入功能已拆分到独立模块"，但文件仍有约 389 行。

**修复方案**:
更新注释以反映实际状态。

**状态**: [x] 已修复（2026-02-15）

---

### L-04: 过多的 console.log

| 属性 | 值 |
|------|-----|
| **位置** | 前端业务组件 |
| **类别** | 前端/日志 |

**问题位置**:
| 文件 | 行号 |
|------|------|
| `pages/Contract/ContractImportReview.tsx` | 279 |
| `pages/Contract/ContractImportStatus.tsx` | 184 |

**修复方案**:
生产环境使用统一的 logger。

**状态**: [x] 已修复（2026-02-15）

---

## ✅ 项目亮点

以下是审查中发现做得好的地方：

### 安全方面
- ✅ CORS 禁止通配符配置
- ✅ PII 字段 AES-256 加密
- ✅ SQL 注入防护（参数化查询）
- ✅ Cookie-only 认证（防 XSS）

### 架构方面
- ✅ API → Service → CRUD → Model 分层清晰
- ✅ 业务逻辑正确放置在 Service 层

### 前端方面
- ✅ 大部分 API 调用已使用 React Query
- ✅ 空值处理规范（`??` 和 `!= null`）
- ✅ TypeScript 类型定义较为完善
- ✅ 核心组件已使用 React.memo

### 工具方面
- ✅ Ruff + mypy 配置完善
- ✅ Oxlint + Tsgo 严格模式
- ✅ 测试标记分类完善

---

## 📊 修复进度跟踪

| 严重程度 | 总数 | 已修复 | 进度 |
|:--------:|:----:|:------:|:----:|
| 🔴 严重 | 7 | 7（含2条关闭） | 100% |
| 🟠 高危 | 12 | 12 | 100% |
| 🟡 中等 | 15 | 15 | 100% |
| 🟢 低危 | 4+ | 4 | 100% |

---

## 📅 建议修复计划

### 第一周（严重问题）
- [x] C-01: Docker nginx 配置
- [x] C-02: 异常类重复定义
- [x] C-03: stdout 敏感信息
- [x] C-04: useEffect 无限循环（重构关闭）
- [x] C-05: 空 catch 块
- [x] C-06: index 作为 key
- [x] C-07: E2E 测试状态（误报关闭）

### 第二周（高危问题）
- [x] H-01: Token 黑名单分布式约束
- [x] H-02: AssetService 依赖注入替代全局变量
- [x] H-03: 后端 Any 收敛（阶段化完成：热点 `database.py`/`core.exception_handler.py`/`crud.asset.py` 已清零）
- [x] H-04: PromptDashboard 详情数据改为 React Query
- [x] H-05: useCallback 优化（现状满足）
- [x] H-06: 测试类型断言清理
- [x] H-07: 测试隐式 any 清理
- [x] H-08: 补齐缺失模型单元测试
- [x] H-09: 补齐 operation_log 服务单元测试
- [x] H-10: 前端覆盖率阈值阶段提升
- [x] H-11: 测试标记文档
- [x] H-12: 轮询失败计数

### 第三周（中等问题）
- [x] M-01 ~ M-03: 代码质量与常量治理（含 stderr 清理）
- [x] M-04: 过长文件拆分（阶段化：asset/auth/database 均完成首轮模块抽取）
- [x] M-05: 大列表虚拟滚动（通用表格组件阈值化接入）
- [x] M-06: setTimeout 引用与清理
- [x] M-07: 测试 Fixtures 收敛
- [x] M-08: 迁移命名规范门禁
- [x] M-09: 类型忽略注解清理
- [x] M-10: 条件导入复杂度治理
- [x] M-11 ~ M-12: 缓存键稳定与重复 pop 收敛
- [x] M-13: Lint 禁用注释治理（清理 79 处 + 新增门禁脚本）
- [x] M-14: 依赖数组问题（重构后关闭）
- [x] M-15: 测试 key 规范化

### 持续改进
- [x] 低危问题逐步处理（L-01~L-04 已完成/关闭）
- [ ] 前端覆盖率提升

---

## 📝 更新日志

| 日期 | 变更 |
|------|------|
| 2026-02-14 | 初始版本，完成全项目审查 |
| 2026-02-15 | 修复并回填已核实问题：C-01/C-03/C-05/C-06、H-11/H-12；关闭 C-07 误报；修正统计口径与 H-09 描述 |
| 2026-02-15 | 复核已修复项并更新状态一致性：新增复核结论区，细化第二周高危计划状态 |
| 2026-02-15 | 新增修复并复核：C-02、H-01/H-02/H-04/H-06/H-07/H-08/H-09/H-10、M-03/M-06/M-15、L-01/L-03/L-04；关闭 H-05、M-14、L-02 误报/迁移项 |
| 2026-02-15 | 继续修复并复核：M-01/M-02/M-07/M-08/M-09/M-10/M-11/M-12；同步新增缓存键稳定性单测（嵌套过滤顺序稳定、租户缓存隔离、字符串/数字 ID 区分）、迁移命名门禁与共享事务 fixture 工具，并更新中等问题进度为 12/15 |
| 2026-02-15 | H-03 首批收敛：`backend/src/database.py` 移除热点 14 处 `Any`（状态标记为“进行中”） |
| 2026-02-15 | H-03 第二批收敛：`backend/src/core/exception_handler.py` 移除热点 11 处 `Any`，与首批合计清零 25 处热点 `Any` |
| 2026-02-15 | H-03 第三批收敛：`backend/src/crud/asset.py` 移除热点 56 处 `Any`，三批合计清零 81 处热点 `Any`；按“核心模块优先”策略阶段化关闭 H-03 |
| 2026-02-15 | M-13 修复：清理 `frontend/src` 中 79 处 `eslint-disable-next-line` 注释，新增 `scripts/scan-lint-disable-comments.js` 并接入 `guard:ui`/`guard:ui:ci` 门禁，更新中等问题进度为 13/15 |
| 2026-02-15 | M-05 修复：`TableWithPagination` 新增阈值触发虚拟滚动（`enableVirtual/virtualThreshold/virtualScrollY`），并通过通用组件复用覆盖资产/合同等列表，更新中等问题进度为 14/15 |
| 2026-02-15 | M-04 修复：完成超长文件首轮拆分（`asset_support.py`、`token_blacklist_guard.py`、`database_url.py`），并通过黑名单/加密/资产 CRUD 回归（73 passed），中等问题进度更新为 15/15 |

---

*此文档由 Claude Code 自动生成，请根据实际修复情况更新状态。*
