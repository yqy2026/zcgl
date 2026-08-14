/**
 * AppLayout 组件测试
 * 测试应用布局组件的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, fireEvent } from '@/test/utils/test-helpers';
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

vi.mock('../MobileLayout', () => ({
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mobile-layout">{children}</div>
  ),
}));

vi.mock('@/services/systemService', () => ({
  userService: {
    getMyPartyScope: vi.fn(() => new Promise(() => undefined)),
  },
}));

// =============================================================================
// 测试内容组件
// =============================================================================

const TestContent = () => <div data-testid="test-content">Test Content</div>;

beforeEach(() => {
  window.innerWidth = 1280;
});

// =============================================================================
// 基础功能测试
// =============================================================================

describe('AppLayout - 基础功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正常渲染布局结构', () => {
    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
    expect(screen.getByTestId('test-content')).toBeInTheDocument();
  });

  it('应该渲染页脚', () => {
    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByText(/土地物业资产运营管理系统/)).toBeInTheDocument();
    expect(screen.getByText(/©2024/)).toBeInTheDocument();
  });

  it('应该渲染子组件内容', () => {
    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });
});

describe('AppLayout - 响应式壳层', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.innerWidth = 1280;
  });

  it('390 宽视口使用移动壳层且不渲染桌面侧栏', () => {
    window.innerWidth = 390;

    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('mobile-layout')).toBeInTheDocument();
    expect(screen.queryByTestId('app-sidebar')).not.toBeInTheDocument();
    expect(screen.getByTestId('test-content')).toBeInTheDocument();
  });

  it('767 宽视口使用移动壳层，768 宽视口使用桌面壳层', () => {
    window.innerWidth = 767;

    const { unmount } = renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('mobile-layout')).toBeInTheDocument();
    expect(screen.queryByTestId('app-sidebar')).not.toBeInTheDocument();

    unmount();
    window.innerWidth = 768;
    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.queryByTestId('mobile-layout')).not.toBeInTheDocument();
  });

  it('视口跨过移动断点时切换壳层', () => {
    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );
    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();

    window.innerWidth = 390;
    fireEvent(window, new Event('resize'));

    expect(screen.getByTestId('mobile-layout')).toBeInTheDocument();
    expect(screen.queryByTestId('app-sidebar')).not.toBeInTheDocument();
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
    renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    expect(screen.getByText(/Sidebar \(expanded\)/)).toBeInTheDocument();
  });

  it('应该显示折叠切换按钮', () => {
    renderWithProviders(
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
    const { container: _container } = renderWithProviders(
      <AppLayout>
        <TestContent />
      </AppLayout>
    );

    // 验证主要区域存在
    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText(/土地物业资产运营管理系统/)).toBeInTheDocument();
  });

  it('应该正确渲染多个子组件', () => {
    renderWithProviders(
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
    const { container: _container } = renderWithProviders(<AppLayout>{null}</AppLayout>);

    // 布局仍然应该渲染，即使内容为空
    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
  });

  it('应该处理空children', () => {
    const { container: _container } = renderWithProviders(
      <AppLayout>
        <></>
      </AppLayout>
    );

    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
  });

  it('应该处理复杂的子组件树', () => {
    renderWithProviders(
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
