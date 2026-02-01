# 测试覆盖率提升计划

**项目**: 土地物业资产管理系统
**创建日期**: 2026-02-01
**预计工期**: 6 个月（3 个阶段）
**执行模式**: 前后端同步推进，全部测试代码由 AI 生成

---

## 📊 现状分析

### 后端测试现状
- **测试总数**: 4,661 个
- **通过率**: 95.4% (4,056/4,252)
- **失败测试**: 196 个 ❌
- **代码覆盖率**: ~70.57%
- **零覆盖率文件**: 10+ 个

### 前端测试现状
- **测试总数**: 1,870 个
- **通过率**: 84.4% (1,579/1,870)
- **失败测试**: 291 个 ❌
- **代码覆盖率**: ~50% (估算)
- **目标覆盖率**: 50% Lines, 50% Functions

### 关键问题
1. **后端**: Analytics API (0%), PDF Import Routes (0%), System Monitoring (0%)
2. **前端**: RentContract 组件缺失测试，291 个测试失败
3. **测试质量**: Mock 策略不统一，测试模式不一致

---

## 🎯 实施策略

### 优先级排序
- **P0 - 紧急**: 零覆盖率核心业务模块 + 失败测试修复
- **P1 - 重要**: 中等覆盖率模块提升 (30-70%)
- **P2 - 必要**: 低覆盖率模块补充 (<30%)
- **P3 - 优化**: 测试质量提升和 CI/CD 集成

### 执行原则
1. **先修复失败测试，再补充新测试**
2. **前后端同步推进，按模块统筹**（例如：先完成 Analytics 后端 API → 再补充 Analytics 前端组件）
3. **模板驱动开发**：使用统一测试模板提高效率
4. **持续监控**：每个阶段完成后验证覆盖率提升

---

## 📅 Phase 1: 快速见效（第 1-2 周）

### 目标
- 修复所有失败测试（487 个：196 后端 + 291 前端）
- 补充零覆盖率核心模块（10+ 个文件）
- 覆盖率提升至：后端 75%，前端 60%
- 测试通过率：≥ 95%

### 任务清单

#### Week 1: 修复失败测试

##### 后端失败测试修复（196 个）

| 文件路径 | 失败数 | 修复重点 | 预估时间 |
|---------|--------|---------|---------|
| `tests/unit/services/document/test_pdf_analyzer.py` | 6 | Mock 配置、异步测试 | 2h |
| `tests/unit/services/rent_contract/test_rent_contract_service_coverage.py` | 11 | 依赖注入、数据库回滚 | 3h |
| `tests/unit/services/rent_contract/test_rent_contract_service_impl.py` | 4 | Ledger 生成逻辑 | 2h |
| `tests/unit/services/test_notification_scheduler.py` | 3 | 定时任务 Mock | 1h |
| `tests/unit/services/test_project.py` | 1 | 权限检查 | 0.5h |
| `tests/unit/api/v1/test_pdf_batch_routes.py` | ~15 | API 端点 Mock | 2h |
| `tests/integration/crud/test_asset_encryption.py` | ~10 | 加密解密测试 | 2h |
| 其他分散失败测试 | ~144 | 各类问题 | 12h |

**修复策略**:
1. 使用统一 Mock 模板（MockFactory）
2. 添加缺失的 fixture
3. 修复异步测试（添加 `@pytest.mark.asyncio`）
4. 修复数据库事务回滚问题
5. 更新不匹配的 Mock 返回值

##### 前端失败测试修复（291 个）

| 模块 | 失败数 | 修复重点 | 预估时间 |
|------|--------|---------|---------|
| Analytics 组件测试 | ~50 | Context Provider、Mock 配置 | 4h |
| Asset 组件测试 | ~30 | 组件渲染、API Mock | 3h |
| Pages 组件测试 | ~80 | 路由 Mock、权限检查 | 6h |
| 其他组件测试 | ~131 | 类型错误、异步处理 | 10h |

**修复策略**:
1. 统一使用 `renderWithProviders` 包装组件
2. 更新 MSW handlers 匹配新的 API 响应格式
3. 修复类型定义错误
4. 添加正确的 `waitFor` 等待异步操作
5. 修复组件 Props 类型不匹配

#### Week 2: 补充零覆盖率模块

##### 后端零覆盖率模块（优先级排序）

| 序号 | 文件路径 | 模块 | 测试类型 | 目标覆盖率 | 预估时间 |
|------|---------|------|---------|-----------|---------|
| 1 | `tests/unit/api/v1/analytics/test_analytics.py` | Analytics API | 单元 + 集成 | 70% | 4h |
| 2 | `tests/unit/api/v1/analytics/test_statistics.py` | Statistics API | 单元测试 | 75% | 3h |
| 3 | `tests/unit/api/v1/analytics/statistics_modules/test_area_stats.py` | Area Stats | 单元测试 | 75% | 2h |
| 4 | `tests/unit/api/v1/analytics/statistics_modules/test_basic_stats.py` | Basic Stats | 单元测试 | 75% | 2h |
| 5 | `tests/unit/api/v1/analytics/statistics_modules/test_financial_stats.py` | Financial Stats | 单元测试 | 75% | 2h |
| 6 | `tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats.py` | Occupancy Stats | 单元测试 | 75% | 2h |
| 7 | `tests/unit/api/v1/documents/test_pdf_import_routes.py` | PDF Import Routes | API 测试 | 70% | 3h |
| 8 | `tests/unit/api/v1/system/test_system_monitoring.py` | System Monitoring | API 测试 | 65% | 3h |

**总计**: 8 个文件，21 小时

##### 前端缺失测试组件（优先级排序）

| 序号 | 文件路径 | 组件 | 测试类型 | 目标覆盖率 | 预估时间 |
|------|---------|------|---------|-----------|---------|
| 1 | `src/pages/Contract/__tests__/RentContractList.test.tsx` | 合同列表 | 组件测试 | 80% | 4h |
| 2 | `src/pages/Contract/__tests__/RentContractDetail.test.tsx` | 合同详情 | 组件测试 | 75% | 4h |
| 3 | `src/components/Contract/__tests__/RentContractForm.test.tsx` | 合同表单 | 组件测试 | 70% | 6h |
| 4 | `src/components/Contract/__tests__/ContractFilters.test.tsx` | 合同筛选 | 组件测试 | 70% | 2h |

**总计**: 4 个组件，16 小时

### Phase 1 验收标准
- [ ] 所有 487 个失败测试已修复
- [ ] 测试通过率 ≥ 95%
- [ ] 后端覆盖率 ≥ 75%
- [ ] 前端覆盖率 ≥ 60%
- [ ] 所有新增测试通过本地验证

---

## 🏗️ Phase 2: 系统提升（第 3-8 周）

### 目标
- 中等覆盖率模块提升至 70-85%
- 补充表单组件测试
- 覆盖率提升至：后端 85%，前端 70%
- 建立统一的测试模板库

### 任务清单

#### Week 3-4: 后端中等覆盖率模块提升

| 序号 | 文件路径 | Service | 当前覆盖率 | 目标覆盖率 | 预估时间 |
|------|---------|---------|-----------|-----------|---------|
| 1 | `tests/unit/services/rent_contract/test_statistics_service_enhanced.py` | Statistics Service | 13.7% | 80% | 6h |
| 2 | `tests/unit/services/task/test_task_service_enhanced.py` | Task Service | 16.7% | 75% | 5h |
| 3 | `tests/unit/services/system_dictionary/test_service_enhanced.py` | System Dictionary | 26% | 70% | 3h |
| 4 | `tests/unit/utils/test_file_security_enhanced.py` | File Security | 16.5% | 70% | 4h |
| 5 | `tests/unit/utils/test_cache_manager_enhanced.py` | Cache Manager | 44.6% | 85% | 4h |

**总计**: 5 个文件，22 小时

#### Week 5-6: 前端表单组件测试补充

| 序号 | 文件路径 | 组件 | 复杂度 | 预估时间 |
|------|---------|------|--------|---------|
| 1 | `src/components/Forms/RentContract/__tests__/BasicInfoSection.test.tsx` | 基本信息表单 | 中 | 3h |
| 2 | `src/components/Forms/RentContract/__tests__/ContractPeriodSection.test.tsx` | 合同期限表单 | 中 | 3h |
| 3 | `src/components/Forms/RentContract/__tests__/TenantInfoSection.test.tsx` | 租户信息表单 | 中 | 2h |
| 4 | `src/components/Forms/RentContract/__tests__/RentTermsSection.test.tsx` | 租金条款表单 | 高 | 4h |
| 5 | `src/components/Forms/RentContract/__tests__/RentTermModal.test.tsx` | 租金条款弹窗 | 高 | 4h |
| 6 | `src/components/Forms/Asset/__tests__/AssetFormSections.test.tsx` | 资产表单 Sections | 中 | 6h |

**总计**: 6 个组件，22 小时

#### Week 7-8: 后端 CRUD 和 API 层补充

| 序号 | 模块 | 测试类型 | 预估时间 |
|------|------|---------|---------|
| 1 | `tests/unit/api/v1/assets/` - API 端点补充 | 集成测试 | 6h |
| 2 | `tests/unit/api/v1/documents/` - PDF 处理 API | 集成测试 | 8h |
| 3 | `tests/unit/crud/` - 补充边界测试 | 单元测试 | 6h |
| 4 | `tests/integration/api/` - 端到端 API 流程 | 集成测试 | 10h |

**总计**: 4 个模块，30 小时

### Phase 2 验收标准
- [ ] 后端覆盖率 ≥ 85%
- [ ] 前端覆盖率 ≥ 70%
- [ ] 表单组件测试覆盖率 ≥ 70%
- [ ] 所有新增测试通过 Code Review

---

## 🎯 Phase 3: 长期优化（第 9-24 周）

### 目标
- 覆盖率达到并维持：后端 85%+，前端 80%+
- E2E 测试覆盖核心业务流程
- 建立测试驱动开发（TDD）文化
- CI/CD 自动化测试覆盖率监控

### 任务清单

#### Week 9-12: 测试质量提升

| 任务 | 说明 | 预估时间 |
|------|------|---------|
| 重构低质量测试 | 统一为 AAA 模式 | 16h |
| 建立统一 Mock 工厂 | MockFactory, TestDataGenerator | 8h |
| 建立前端测试工具库 | renderWithProviders, MSW handlers | 8h |

#### Week 13-16: E2E 测试补充

| 场景 | 优先级 | 测试工具 | 预估时间 |
|------|--------|---------|---------|
| 用户登录流程 | P0 | Playwright | 4h |
| 资产创建-编辑-删除 | P0 | Playwright | 8h |
| 合同完整生命周期 | P0 | Playwright | 10h |
| 导入 Excel 数据 | P1 | Playwright | 6h |
| PDF 智能导入 | P1 | Playwright | 8h |

**总计**: 5 个场景，36 小时

#### Week 17-20: 前端 Pages 和其他组件测试

| 序号 | 模块 | 测试类型 | 预估时间 |
|------|------|---------|---------|
| 1 | `src/pages/Dashboard/__tests__/` | 页面测试 | 4h |
| 2 | `src/pages/Assets/__tests__/` | 页面测试 | 6h |
| 3 | `src/components/Charts/__tests__/` | 图表测试 | 6h |
| 4 | `src/components/Feedback/__tests__/` | 反馈组件 | 4h |

**总计**: 4 个模块，20 小时

#### Week 21-24: CI/CD 集成和监控

| 任务 | 说明 | 预估时间 |
|------|------|---------|
| GitHub Actions 工作流 | 自动测试 + 覆盖率报告 | 8h |
| Codecov 集成 | 覆盖率趋势图表 | 4h |
| Pre-commit Hook | 本地覆盖率检查 | 4h |
| 覆盖率监控面板 | Dashboard 显示 | 8h |

**总计**: 24 小时

### Phase 3 验收标准
- [ ] 覆盖率达到：后端 85%+，前端 80%+
- [ ] E2E 测试覆盖 5+ 个核心场景
- [ ] CI/CD 自动化测试覆盖率报告
- [ ] 测试文档完善
- [ ] 团队 TDD 实践率 ≥ 50%

---

## 📁 关键文件清单

### 后端关键文件

#### 测试配置和基础设施
- `backend/tests/conftest.py` - 测试配置和全局 Fixture
- `backend/tests/factories/mock_factory.py` - 统一 Mock 工厂（新建）
- `backend/tests/fixtures/test_data_generator.py` - 测试数据生成器（新建）
- `backend/pyproject.toml` - pytest 配置（更新覆盖率阈值）

#### Phase 1: 零覆盖率模块测试（新建）
- `backend/tests/unit/api/v1/analytics/test_analytics.py`
- `backend/tests/unit/api/v1/analytics/test_statistics.py`
- `backend/tests/unit/api/v1/analytics/statistics_modules/test_area_stats.py`
- `backend/tests/unit/api/v1/analytics/statistics_modules/test_basic_stats.py`
- `backend/tests/unit/api/v1/analytics/statistics_modules/test_financial_stats.py`
- `backend/tests/unit/api/v1/analytics/statistics_modules/test_occupancy_stats.py`
- `backend/tests/unit/api/v1/documents/test_pdf_import_routes.py`
- `backend/tests/unit/api/v1/system/test_system_monitoring.py`

#### Phase 2: 中等覆盖率模块提升（新建/修改）
- `backend/tests/unit/services/rent_contract/test_statistics_service_enhanced.py`
- `backend/tests/unit/services/task/test_task_service_enhanced.py`
- `backend/tests/unit/services/system_dictionary/test_service_enhanced.py`
- `backend/tests/unit/utils/test_file_security_enhanced.py`
- `backend/tests/unit/utils/test_cache_manager_enhanced.py`

#### Phase 3: CI/CD 配置（新建）
- `backend/.github/workflows/test-coverage.yml`
- `backend/.git/hooks/pre-commit` (本地钩子)

### 前端关键文件

#### 测试配置和基础设施
- `frontend/vitest.config.ts` - vitest 配置（更新阈值）
- `frontend/src/test/setup.ts` - 测试环境配置
- `frontend/src/test/utils/handlers.ts` - MSW API Handlers（新建）
- `frontend/src/test/utils/test-utils.tsx` - 测试工具函数（新建）

#### Phase 1: RentContract 组件测试（新建）
- `frontend/src/pages/Contract/__tests__/RentContractList.test.tsx`
- `frontend/src/pages/Contract/__tests__/RentContractDetail.test.tsx`
- `frontend/src/components/Contract/__tests__/RentContractForm.test.tsx`
- `frontend/src/components/Contract/__tests__/ContractFilters.test.tsx`

#### Phase 2: 表单组件测试（新建）
- `frontend/src/components/Forms/RentContract/__tests__/BasicInfoSection.test.tsx`
- `frontend/src/components/Forms/RentContract/__tests__/ContractPeriodSection.test.tsx`
- `frontend/src/components/Forms/RentContract/__tests__/TenantInfoSection.test.tsx`
- `frontend/src/components/Forms/RentContract/__tests__/RentTermsSection.test.tsx`
- `frontend/src/components/Forms/RentContract/__tests__/RentTermModal.test.tsx`
- `frontend/src/components/Forms/Asset/__tests__/AssetFormSections.test.tsx`

#### Phase 3: E2E 测试（新建）
- `frontend/e2e/auth/login-flow.spec.ts`
- `frontend/e2e/assets/asset-lifecycle.spec.ts`
- `frontend/e2e/contracts/contract-lifecycle.spec.ts`
- `frontend/e2e/data-import/excel-import.spec.ts`
- `frontend/e2e/data-import/pdf-import.spec.ts`

#### Phase 3: CI/CD 配置（新建）
- `frontend/.github/workflows/test-coverage.yml`
- `frontend/playwright.config.ts` - Playwright 配置

---

## 🧪 测试模板示例

### 后端单元测试模板

```python
# tests/unit/services/test_template.py

"""
高质量单元测试模板
遵循 AAA 模式（Arrange-Act-Assert）
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime

pytestmark = pytest.mark.unit


class TestMyService:
    """服务层测试模板"""

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from src.services.my_service import MyService
        return MyService()

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return {
            "id": 1,
            "name": "Test",
            "status": "active"
        }

    def test_success_scenario(self, service, mock_db, sample_data):
        """
        测试成功场景

        Given: 有效的输入数据
        When: 调用被测试方法
        Then: 返回预期结果
        """
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_data

        # Act
        result = service.get_by_id(mock_db, 1)

        # Assert
        assert result is not None
        assert result["id"] == 1
        mock_db.query.assert_called_once()

    def test_not_found_scenario(self, service, mock_db):
        """测试资源不存在场景"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFound):
            service.get_by_id(mock_db, 999)

    def test_error_handling(self, service, mock_db):
        """测试异常处理"""
        # Arrange
        mock_db.query.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            service.get_by_id(mock_db, 1)

        assert "Database error" in str(exc_info.value)
        mock_db.rollback.assert_called_once()
```

### 前端组件测试模板

```typescript
// src/components/__tests__/ComponentTemplate.test.tsx

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ComponentToTest } from '../ComponentToTest';

// Mock API
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('ComponentToTest', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render without crashing', () => {
    renderWithProviders(<ComponentToTest />);
    expect(screen.getByTestId('component')).toBeInTheDocument();
  });

  it('should handle loading state', async () => {
    renderWithProviders(<ComponentToTest />);
    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('should display data after fetch', async () => {
    const mockData = { id: 1, name: 'Test' };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData });

    renderWithProviders(<ComponentToTest />);

    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });

  it('should handle user interaction', async () => {
    renderWithProviders(<ComponentToTest />);

    const button = screen.getByRole('button', { name: /提交/i });
    await user.click(button);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled();
    });
  });
});
```

---

## ✅ 验收标准

### 量化指标

| 维度 | 当前状态 | Phase 1 目标 | Phase 2 目标 | Phase 3 目标 |
|------|---------|-------------|-------------|-------------|
| **后端覆盖率** | 70.57% | 75% | 85% | 90%+ |
| **前端覆盖率** | ~50% | 60% | 70% | 80%+ |
| **测试通过率** | 84.4% | 95% | 98% | 99%+ |
| **测试数量** | 4,661 (后端) | 5,000+ | 6,000+ | 7,000+ |
| **E2E 测试** | 0 | 0 | 0 | 30+ 场景 |
| **测试执行时间** | N/A | < 10min | < 5min | < 3min |

### 质量指标
- [ ] 所有新功能都有对应的测试
- [ ] 测试失败导致 CI 失败
- [ ] 代码审查包含测试审查
- [ ] 测试文档完善
- [ ] 团队 TDD 实践率 ≥ 50%

---

## 🔧 实施步骤

### 第 1 步：准备工作（0.5 天）
1. 创建测试基础设施文件
2. 建立统一 Mock 工厂和测试工具库
3. 更新 pytest/vitest 配置

### 第 2 步：Phase 1 执行（2 周）
1. Week 1: 修复所有失败测试
2. Week 2: 补充零覆盖率模块
3. 验收：运行完整测试套件，确认覆盖率达标

### 第 3 步：Phase 2 执行（6 周）
1. Week 3-4: 后端中等覆盖率模块提升
2. Week 5-6: 前端表单组件测试补充
3. Week 7-8: 后端 CRUD 和 API 层补充
4. 验收：生成覆盖率报告，确认目标达成

### 第 4 步：Phase 3 执行（16 周）
1. Week 9-12: 测试质量提升
2. Week 13-16: E2E 测试补充
3. Week 17-20: 前端 Pages 组件测试
4. Week 21-24: CI/CD 集成和监控
5. 验收：全面评估测试覆盖率、质量和CI/CD集成

### 第 5 步：持续监控（长期）
1. 每周审查新代码测试覆盖率
2. 每月分析覆盖率趋势
3. 每季度评估测试债务
4. 每半年优化测试策略

---

## 🚨 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 测试编写耗时 | 进度延误 | 使用测试模板、Mock 工厂 |
| Mock 配置复杂 | 维护困难 | 统一 Mock 策略、集中管理 |
| 测试不稳定 | CI 频繁失败 | 隔离测试、重试机制 |
| 团队抵触 | 执行困难 | 培训、激励机制 |

---

## 📝 备注

- 本计划采用**前后端同步推进**策略，按模块优先级统筹
- 所有测试代码由 AI 生成，包括单元测试、集成测试、组件测试和 E2E 测试
- 测试遵循 **AAA 模式**（Arrange-Act-Assert）和最佳实践
- 建立**统一测试模板库**提高开发效率
- **持续监控覆盖率**，确保持续改进
