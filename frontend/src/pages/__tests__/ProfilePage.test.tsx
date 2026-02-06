import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
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
    hasPermission: vi.fn(),
    hasAnyPermission: vi.fn(),
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

describe('ProfilePage', () => {
  it('renders modal forms to keep useForm connected', () => {
    renderWithProviders(<ProfilePage />);

    expect(screen.getByText('个人资料')).toBeInTheDocument();
    expect(screen.getByLabelText('用户名')).toBeInTheDocument();
    expect(screen.getByLabelText('当前密码')).toBeInTheDocument();
  });
});
