/**
 * LoginPage 页面测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../LoginPage';

// Mock useAuth hook
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: null }),
  };
});

// Mock CSS modules
vi.mock('../LoginPage.module.css', () => ({
  default: {
    'login-page': 'login-page',
    'login-shell': 'login-shell',
    'brand-panel': 'brand-panel',
    'brand-kicker': 'brand-kicker',
    'brand-title': 'brand-title',
    'brand-description': 'brand-description',
    'brand-list': 'brand-list',
    'brand-list-item': 'brand-list-item',
    'login-card': 'login-card',
    'login-header': 'login-header',
    'login-title': 'login-title',
    'login-subtitle': 'login-subtitle',
    'login-form': 'login-form',
    'input-icon': 'input-icon',
    'remember-item': 'remember-item',
    'login-error': 'login-error',
    'login-submit-item': 'login-submit-item',
    'login-button': 'login-button',
    'login-footer': 'login-footer',
    'login-help': 'login-help',
  },
}));

import { useAuth } from '../../contexts/AuthContext';

const memoryRouterFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

describe('LoginPage', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useAuth).mockReturnValue({
      login: mockLogin,
      loading: false,
      error: null,
      user: null,
      isAuthenticated: false,
      logout: vi.fn(),
      checkAuth: vi.fn(),
    } as unknown as ReturnType<typeof useAuth>);
  });

  describe('渲染', () => {
    it('渲染登录页面标题', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByText('欢迎回来')).toBeInTheDocument();
      expect(screen.getByText('土地物业资产运营管理系统')).toBeInTheDocument();
      expect(
        screen.getByText('Real Estate Asset Management & Operations System')
      ).toBeInTheDocument();
      expect(screen.getByText('请输入您的账号密码以继续')).toBeInTheDocument();
    });

    it('渲染用户名输入框', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByPlaceholderText('请输入用户名或手机号')).toBeInTheDocument();
    });

    it('渲染密码输入框', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    });

    it('渲染记住我复选框', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByText('记住登录状态')).toBeInTheDocument();
    });

    it('渲染登录按钮', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByText('立即登录')).toBeInTheDocument();
    });

    it('渲染帮助信息', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByText('遇到问题？联系 IT 管理员')).toBeInTheDocument();
    });
  });

  describe('表单交互', () => {
    it('输入用户名', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const usernameInput = screen.getByPlaceholderText('请输入用户名或手机号');
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });

      expect(usernameInput).toHaveValue('testuser');
    });

    it('输入密码', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const passwordInput = screen.getByPlaceholderText('••••••••');
      fireEvent.change(passwordInput, { target: { value: 'password123' } });

      expect(passwordInput).toHaveValue('password123');
    });

    it('切换记住我复选框', () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const checkbox = screen.getByRole('checkbox');
      fireEvent.click(checkbox);

      expect(checkbox).toBeChecked();
    });
  });

  describe('表单提交', () => {
    it('成功登录后跳转到工作台', async () => {
      mockLogin.mockResolvedValue(undefined);

      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const usernameInput = screen.getByPlaceholderText('请输入用户名或手机号');
      const passwordInput = screen.getByPlaceholderText('••••••••');
      const submitButton = screen.getByText('立即登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          identifier: 'admin',
          password: 'password123',
          remember: false,
        });
      });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
      });
    });

    it('勾选记住登录状态后提交 remember=true', async () => {
      mockLogin.mockResolvedValue(undefined);

      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const usernameInput = screen.getByPlaceholderText('请输入用户名或手机号');
      const passwordInput = screen.getByPlaceholderText('••••••••');
      const rememberCheckbox = screen.getByRole('checkbox');
      const submitButton = screen.getByText('立即登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(rememberCheckbox);
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          identifier: 'admin',
          password: 'password123',
          remember: true,
        });
      });
    });
  });

  describe('加载状态', () => {
    it('加载中显示登录中文本', () => {
      vi.mocked(useAuth).mockReturnValue({
        login: mockLogin,
        loading: true,
        error: null,
        user: null,
        isAuthenticated: false,
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as unknown as ReturnType<typeof useAuth>);

      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByText('登录中...')).toBeInTheDocument();
    });
  });

  describe('错误处理', () => {
    it('显示登录错误信息', () => {
      vi.mocked(useAuth).mockReturnValue({
        login: mockLogin,
        loading: false,
        error: '用户名或密码错误',
        user: null,
        isAuthenticated: false,
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as unknown as ReturnType<typeof useAuth>);

      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      expect(screen.getByText('登录失败')).toBeInTheDocument();
      expect(screen.getByText('用户名或密码错误')).toBeInTheDocument();
    });
  });

  describe('表单验证', () => {
    it('用户名必填验证', async () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const submitButton = screen.getByText('立即登录');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('请输入用户名或手机号')).toBeInTheDocument();
      });
    });

    it('密码必填验证', async () => {
      render(
        <MemoryRouter future={memoryRouterFuture}>
          <LoginPage />
        </MemoryRouter>
      );

      const usernameInput = screen.getByPlaceholderText('请输入用户名或手机号');
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });

      const submitButton = screen.getByText('立即登录');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('请输入密码')).toBeInTheDocument();
      });
    });
  });
});
