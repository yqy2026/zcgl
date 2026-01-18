/**
 * AppLayout 组件测试
 * 测试应用布局组件的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import AppLayout from '../AppLayout';

// =============================================================================
// Mock react-router-dom
// =============================================================================

vi.mock('react-router-dom', () => ({
  useLocation: vi.fn(() => ({ pathname: '/dashboard' })),
  useNavigate: vi.fn(() => vi.fn()),
}));

// =============================================================================
// Mock 子组件
// =============================================================================

vi.mock('../AppSidebar', () => ({
  default: ({ collapsed }: { collapsed: boolean }) => (
    <div data-testid="app-sidebar">Sidebar {collapsed ? '(collapsed)' : '(expanded)'}</div>
  ),
}));

vi.mock('../AppHeader', () => ({
  default: ({
    collapsed,
    onToggleCollapsed,
  }: {
    collapsed: boolean;
    onToggleCollapsed: () => void;
  }) => (
    <div data-testid="app-header">
      Header {collapsed ? '(collapsed)' : '(expanded)'}
      <button onClick={onToggleCollapsed}>Toggle</button>
    </div>
  ),
}));

vi.mock('../AppBreadcrumb', () => ({
  default: () => <div data-testid="app-breadcrumb">Breadcrumb</div>,
}));

// =============================================================================
// 测试内容组件
// =============================================================================

const TestContent = () => <div data-testid="test-content">Test Content</div>;

// =============================================================================
// 基础功能测试
// =============================================================================

describe('AppLayout - 基础功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正常渲染布局结构', () => {
    render(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
    expect(screen.getByTestId('app-breadcrumb')).toBeInTheDocument();
    expect(screen.getByTestId('test-content')).toBeInTheDocument();
  });

  it('应该渲染页脚', () => {
    render(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByText(/土地房产资产管理系统/)).toBeInTheDocument();
    expect(screen.getByText(/©2024/)).toBeInTheDocument();
  });

  it('应该渲染子组件内容', () => {
    render(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });
});

// =============================================================================
// 侧边栏折叠状态测试
// =============================================================================

describe('AppLayout - 侧边栏状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('默认应该显示展开的侧边栏', () => {
    render(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByText(/Sidebar \(expanded\)/)).toBeInTheDocument();
  });

  it('应该显示折叠切换按钮', () => {
    render(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    const toggleButton = screen.getByRole('button', { name: 'Toggle' });
    expect(toggleButton).toBeInTheDocument();
  });
});

// =============================================================================
// 布局结构测试
// =============================================================================

describe('AppLayout - 布局结构', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该包含所有主要布局区域', () => {
    const { container: _container } = render(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    // 验证主要区域存在
    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
    expect(screen.getByTestId('app-breadcrumb')).toBeInTheDocument();
    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText(/土地房产资产管理系统/)).toBeInTheDocument();
  });

  it('应该正确渲染多个子组件', () => {
    render(
      <AppLayout>
        <div>Child 1</div>
        <div>Child 2</div>
        <div>Child 3</div>
      </AppLayout>
    );

    expect(screen.getByText('Child 1')).toBeInTheDocument();
    expect(screen.getByText('Child 2')).toBeInTheDocument();
    expect(screen.getByText('Child 3')).toBeInTheDocument();
  });
});

// =============================================================================
// 边界情况测试
// =============================================================================

describe('AppLayout - 边界情况', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理null children', () => {
    const { container: _container } = render(<AppLayout>{null}</AppLayout>);

    // 布局仍然应该渲染，即使内容为空
    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
  });

  it('应该处理空children', () => {
    const { container: _container } = render(
      <AppLayout>
        <></>
      </AppLayout>
    );

    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
  });

  it('应该处理复杂的子组件树', () => {
    render(
      <AppLayout>
        <div>
          <section>
            <h1>Title</h1>
            <p>Content</p>
          </section>
        </div>
      </AppLayout>
    );

    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });
});

// =============================================================================
// 导出测试
// =============================================================================

describe('AppLayout - 导出', () => {
  it('应该导出AppLayout组件', () => {
    expect(AppLayout).toBeDefined();
    expect(typeof AppLayout).toBe('function');
  });

  it('应该是React FC组件', () => {
    expect(AppLayout.displayName).toBeUndefined(); // FC 组件的 displayName 可选
  });
});
