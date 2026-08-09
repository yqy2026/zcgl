import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import App from '@/App';
import { createTestQueryClient } from '@/test/test-utils';

/**
 * 回归（2026-08-09 点检）：访问不存在的受保护路由（如 /contracts、/parties、/ledger、/system
 * 这类非路由表路径）时，React Router 无匹配渲染 null → main 静默空白、无任何提示。
 * 本测试锁死行为：死路由必须渲染 404 页而非空白。
 */

vi.mock('@/contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    isAuthenticated: true,
    isAdmin: true,
    loading: false,
    initializing: false,
    user: { id: '1', username: 'admin', display_name: 'Development Administrator' },
    permissions: [],
  }),
}));

vi.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: () => ({ canPerform: () => true, loading: false }),
}));

describe('App 404 兜底路由', () => {
  it('访问不存在的受保护路由应渲染 404 页而非空白 main', async () => {
    window.history.pushState({}, '', '/no-such-page');

    // App 内部自带 BrowserRouter，外层只需 QueryClientProvider
    // （AppLayout → AppHeader → NotificationCenter 消费 React Query）
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <App />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/页面不存在/)).toBeInTheDocument();
    });

    const main = document.querySelector('main');
    expect(main?.childElementCount ?? -1).toBeGreaterThan(0);
  });
});
