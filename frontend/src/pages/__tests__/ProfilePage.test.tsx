import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, fireEvent } from '@/test/utils/test-helpers';
import ProfilePage from '../ProfilePage';

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      username: 'admin',
      full_name: '管理员',
      email: 'admin@test.com',
      phone: '13800000000',
      role_id: 'role-admin-id',
      role_name: 'admin',
      roles: ['admin'],
      is_active: true,
      last_login_at: '2026-02-04T00:00:00Z',
      password_last_changed: '2026-02-01T00:00:00Z',
    },
    refreshUser: vi.fn(),
    isAuthenticated: true,
    permissions: [],
    login: vi.fn(),
    logout: vi.fn(),
    clearError: vi.fn(),
  }),
}));

vi.mock('@/services/authService', () => ({
  AuthService: {
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@/services/systemService', () => ({
  userService: {
    getMyPartyScope: vi.fn(async () => ({
      user_id: 'user-1',
      source: 'explicit',
      scope_mode: 'owner',
      owner_party_ids: ['party-1'],
      manager_party_ids: [],
      organization_id: 'org-1',
      source_organization_id: null,
      next_transition_at: null,
      error_code: null,
      issues: [],
    })),
  },
}));

describe('ProfilePage', () => {
  it('renders modal forms to keep useForm connected', () => {
    renderWithProviders(<ProfilePage />);

    expect(screen.getByText('个人资料')).toBeInTheDocument();
    expect(screen.getByLabelText('用户名')).toBeInTheDocument();
    expect(screen.getByLabelText('当前密码')).toBeInTheDocument();
  });

  it('does not render the placeholder 登录历史 entry (D3)', () => {
    renderWithProviders(<ProfilePage />);

    expect(screen.queryByText('登录历史')).not.toBeInTheDocument();
    expect(screen.queryByText('查看历史')).not.toBeInTheDocument();
  });

  it('loads and renders the current user effective Party scope', async () => {
    renderWithProviders(<ProfilePage />);

    fireEvent.click(screen.getByRole('button', { name: '查看有效主体范围' }));

    expect(await screen.findByText('explicit')).toBeInTheDocument();
    expect(screen.getByText('owner')).toBeInTheDocument();
    expect(screen.getByText('party-1')).toBeInTheDocument();
  });
});
