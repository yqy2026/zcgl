/**
 * useAuth Hook 测试
 * 测试认证相关的自定义Hooks（简化版本）
 */

import { describe, it, expect, vi } from 'vitest';

// =============================================================================
// Mock AuthService
// =============================================================================

vi.mock('@/services/authService', () => ({
  AuthService: {
    getLocalUser: vi.fn(() => null),
    isAuthenticated: vi.fn(() => false),
    getLocalPermissions: vi.fn(() => []),
    login: vi.fn(() =>
      Promise.resolve({
        success: true,
        data: {
          user: {
            id: '1',
            username: 'testuser',
            fullName: 'Test User',
            email: 'test@example.com',
          },
        },
      })
    ),
    logout: vi.fn(() => Promise.resolve()),
    getCurrentUser: vi.fn(() =>
      Promise.resolve({
        id: '1',
        username: 'testuser',
        fullName: 'Test User',
      })
    ),
    refreshToken: vi.fn(() => Promise.resolve()),
    hasPermission: vi.fn(() => true),
    hasAnyPermission: vi.fn(() => true),
  },
}));

// =============================================================================
// Mock localStorage
// =============================================================================

const mockLocalStorage = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// =============================================================================
// Mock antd message
// =============================================================================

vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

// =============================================================================
// useAuth Hook 测试
// =============================================================================

describe('useAuth - Hook验证', () => {
  it('应该导出useAuth hook', async () => {
    const { useAuth } = await import('../useAuth');
    expect(typeof useAuth).toBe('function');
  });
});
