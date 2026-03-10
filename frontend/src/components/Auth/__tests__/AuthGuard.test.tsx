import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AuthGuard from '../AuthGuard';
import type { AuthContextType } from '@/contexts/AuthContext';

interface NavigateMockProps {
  to: string;
  state?: unknown;
}

const mockUseAuth = vi.hoisted(() => vi.fn());
const mockUseCapabilities = vi.hoisted(() => vi.fn());

vi.mock('react-router-dom', () => ({
  Navigate: ({ to, state }: NavigateMockProps) => (
    <div data-testid="navigate" data-to={to} data-state={JSON.stringify(state)}>
      Navigate to: {to}
    </div>
  ),
  useLocation: () => ({
    pathname: '/protected',
    search: '',
    hash: '',
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: mockUseAuth,
}));

vi.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: mockUseCapabilities,
}));

const renderAuthGuard = (
  props: Partial<React.ComponentProps<typeof AuthGuard>> = {},
  authState: Partial<AuthContextType> = {},
  capabilityState: { canPerform?: ReturnType<typeof vi.fn>; loading?: boolean } = {}
) => {
  mockUseAuth.mockReturnValue({
    user: { id: '1', username: 'test', is_active: true },
    permissions: [],
    capabilities: [],
    capabilitiesLoading: false,
    isAuthenticated: true,
    isAdmin: false,
    initializing: false,
    login: vi.fn(async () => {}),
    logout: vi.fn(async () => {}),
    refreshUser: vi.fn(async () => {}),
    refreshCapabilities: vi.fn(async () => {}),
    hasPermission: vi.fn(() => true),
    hasAnyPermission: vi.fn(() => true),
    clearError: vi.fn(),
    loading: false,
    error: null,
    ...authState,
  });

  mockUseCapabilities.mockReturnValue({
    canPerform: vi.fn(() => true),
    loading: false,
    ...capabilityState,
  });

  return render(
    <AuthGuard {...props}>
      <div data-testid="protected">Protected Content</div>
    </AuthGuard>
  );
};

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when authenticated and authorized', () => {
    renderAuthGuard();
    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });

  it('redirects unauthenticated users with source info', () => {
    renderAuthGuard({}, { isAuthenticated: false, user: null });

    const navigate = screen.getByTestId('navigate');
    expect(navigate).toHaveAttribute('data-to', '/login');
    const state = JSON.parse(navigate.getAttribute('data-state') ?? '{}');
    expect(state.from).toBe('/protected');
  });

  it('parses requiredPermission and delegates to canPerform', () => {
    const canPerform = vi.fn(() => true);
    renderAuthGuard({ requiredPermission: 'rental:view' }, {}, { canPerform });

    expect(canPerform).toHaveBeenCalledWith('read', 'contract');
    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });

  it('denies when requiredPermissions are missing', () => {
    const canPerform = vi.fn(() => false);
    renderAuthGuard(
      {
        requiredPermissions: [
          { resource: 'asset', action: 'read' },
          { resource: 'project', action: 'read' },
        ],
      },
      {},
      { canPerform }
    );

    expect(screen.getByText(/权限不足/)).toBeInTheDocument();
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
  });

  it('renders loading state when capabilities are loading', () => {
    renderAuthGuard({}, {}, { loading: true });
    expect(screen.getByText('权限检查中...')).toBeInTheDocument();
  });

  it('shows disabled account message for inactive users', () => {
    renderAuthGuard({}, { user: { id: '1', username: 'test', is_active: false } });
    expect(screen.getByText('账户已禁用')).toBeInTheDocument();
  });

  it('supports back button on denied result', () => {
    const historyBackSpy = vi.spyOn(window.history, 'back').mockImplementation(() => {});

    renderAuthGuard({ requiredPermission: 'asset:delete' }, {}, { canPerform: vi.fn(() => false) });
    const backButton = screen.getByRole('button', { name: '返回上一页' });
    fireEvent.click(backButton);
    expect(historyBackSpy).toHaveBeenCalled();

    historyBackSpy.mockRestore();
  });
});
