/**
 * AuthGuard 组件测试
 *
 * 覆盖场景:
 * - 认证成功渲染子组件
 * - 未认证重定向
 * - 权限校验 (单个/多个)
 * - 账户禁用提示
 *
 * 修复说明：
 * - 移除 antd Result, Button 组件 mock
 * - 移除 @ant-design/icons mock
 * - 保留 useAuth hook mock (业务逻辑)
 * - 保留 react-router-dom mock (路由)
 * - 使用文本内容和 className 进行断言
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import AuthGuard from '../AuthGuard';
import { useAuth } from '@/hooks/useAuth';
import type { AuthContextType } from '@/contexts/AuthContext';

interface NavigateMockProps {
  to: string;
  state?: unknown;
  replace?: boolean;
}

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  Navigate: ({ to, state, replace }: NavigateMockProps) => (
    <div
      data-testid="navigate"
      data-to={to}
      data-replace={replace}
      data-state={JSON.stringify(state)}
    >
      Navigate to: {to}
    </div>
  ),
  useLocation: () => ({
    pathname: '/protected',
    search: '',
    hash: '',
  }),
}));

// Mock useAuth hook
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

const mockHistoryBack = vi.fn();

const renderAuthGuard = (
  props: Partial<React.ComponentProps<typeof AuthGuard>> = {},
  authState: Partial<AuthContextType> = {}
) => {
  const defaultAuthState: AuthContextType = {
    user: { id: '1', username: 'test', is_active: true } as AuthContextType['user'],
    permissions: [],
    isAuthenticated: true,
    initializing: false,
    login: vi.fn(async () => {}),
    logout: vi.fn(async () => {}),
    refreshUser: vi.fn(async () => {}),
    hasPermission: vi.fn(() => true),
    hasAnyPermission: vi.fn(() => true),
    clearError: vi.fn(),
    loading: false,
    error: null,
    ...authState,
  };
  vi.mocked(useAuth).mockReturnValue(defaultAuthState);

  const resolvedProps: React.ComponentProps<typeof AuthGuard> = {
    children: null,
    ...props,
  };
  return render(<AuthGuard {...resolvedProps} />);
};

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.back = mockHistoryBack;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when authenticated', () => {
    renderAuthGuard({
      children: <div data-testid="protected">Protected Content</div>,
    });

    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });

  it('redirects unauthenticated users with source info', () => {
    renderAuthGuard({ children: <div>Protected</div> }, { isAuthenticated: false, user: null });

    const navigate = screen.getByTestId('navigate');
    expect(navigate).toHaveAttribute('data-to', '/login');

    const state = JSON.parse(navigate.getAttribute('data-state') || '{}');
    expect(state.from).toBe('/protected');
    expect(state.message).toContain('请先登录');
  });

  it('skips permission check when not authenticated', () => {
    const hasPermission = vi.fn(() => true);
    renderAuthGuard(
      {
        requiredPermission: 'assets:read',
        children: <div>Protected</div>,
      },
      { isAuthenticated: false, user: null, hasPermission }
    );

    expect(hasPermission).not.toHaveBeenCalled();
  });

  it('parses requiredPermission with colon', () => {
    const hasPermission = vi.fn(() => true);
    renderAuthGuard(
      {
        requiredPermission: 'assets:read',
        children: <div data-testid="child">Content</div>,
      },
      { hasPermission }
    );

    expect(hasPermission).toHaveBeenCalledWith('assets', 'read');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('parses requiredPermission with space', () => {
    const hasPermission = vi.fn(() => true);
    renderAuthGuard(
      {
        requiredPermission: 'assets read',
        children: <div data-testid="child">Content</div>,
      },
      { hasPermission }
    );

    expect(hasPermission).toHaveBeenCalledWith('assets', 'read');
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('shows permission denied result and supports back button', () => {
    const hasPermission = vi.fn(() => false);
    renderAuthGuard(
      {
        requiredPermission: 'assets:delete',
        children: <div>Protected</div>,
      },
      { hasPermission }
    );

    expect(screen.getByText(/权限不足/)).toBeInTheDocument();
    expect(screen.getByText(/assets:delete/)).toBeInTheDocument();

    const buttons = screen.getAllByRole('button');
    if (buttons.length > 0) {
      fireEvent.click(buttons[0]);
      expect(mockHistoryBack).toHaveBeenCalled();
    }
  });

  it('checks requiredPermissions via hasAnyPermission', () => {
    const hasAnyPermission = vi.fn(() => true);
    const requiredPermissions = [
      { resource: 'assets', action: 'read' },
      { resource: 'contracts', action: 'read' },
    ];

    renderAuthGuard(
      {
        requiredPermissions,
        children: <div data-testid="child">Content</div>,
      },
      { hasAnyPermission }
    );

    expect(hasAnyPermission).toHaveBeenCalledWith(requiredPermissions);
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('denies when requiredPermissions are missing', () => {
    const hasAnyPermission = vi.fn(() => false);
    renderAuthGuard(
      {
        requiredPermissions: [
          { resource: 'assets', action: 'write' },
          { resource: 'contracts', action: 'approve' },
        ],
        children: <div>Protected</div>,
      },
      { hasAnyPermission }
    );

    expect(screen.getByText(/assets:write/)).toBeInTheDocument();
  });

  it('allows access when requiredPermissions is empty', () => {
    renderAuthGuard({
      requiredPermissions: [],
      children: <div data-testid="child">Content</div>,
    });

    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('shows disabled account message for inactive users', () => {
    renderAuthGuard(
      {
        children: <div>Protected</div>,
      },
      { user: { id: '1', username: 'test', is_active: false } }
    );

    expect(screen.getByText('账户已禁用')).toBeInTheDocument();
    expect(screen.getByText('重新登录')).toBeInTheDocument();
  });
});
