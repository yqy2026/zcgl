/**
 * NotificationCenter 组件测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import NotificationCenter from '../NotificationCenter';

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

// Mock notificationService
vi.mock('@/services/notificationService', () => ({
  notificationService: {
    getNotifications: vi.fn(),
    getUnreadCount: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
    deleteNotification: vi.fn(),
  },
}));

import { notificationService } from '@/services/notificationService';

// 创建测试用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

// 渲染辅助函数
const renderWithProviders = (props = {}) => {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <NotificationCenter {...props} />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('NotificationCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(notificationService.getNotifications).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });
    vi.mocked(notificationService.getUnreadCount).mockResolvedValue(0);
    vi.mocked(notificationService.markAsRead).mockResolvedValue(undefined);
    vi.mocked(notificationService.markAllAsRead).mockResolvedValue(undefined);
    vi.mocked(notificationService.deleteNotification).mockResolvedValue(undefined);
  });

  describe('渲染', () => {
    it('渲染铃铛图标', async () => {
      renderWithProviders();

      await waitFor(() => {
        expect(document.querySelector('.anticon-bell')).toBeInTheDocument();
      });
    });

    it('有未读消息时显示徽章数量', async () => {
      vi.mocked(notificationService.getUnreadCount).mockResolvedValue(5);

      renderWithProviders();

      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument();
      });
    });

    it('超过99条时显示99+', async () => {
      vi.mocked(notificationService.getUnreadCount).mockResolvedValue(150);

      renderWithProviders();

      await waitFor(() => {
        expect(screen.getByText('99+')).toBeInTheDocument();
      });
    });
  });

  describe('下拉菜单', () => {
    it('点击铃铛打开下拉菜单', async () => {
      renderWithProviders();

      await waitFor(() => {
        expect(document.querySelector('.anticon-bell')).toBeInTheDocument();
      });

      fireEvent.click(document.querySelector('.anticon-bell')!);

      await waitFor(() => {
        expect(screen.getByText('消息通知')).toBeInTheDocument();
      });
    });

    it('无通知时显示空状态', async () => {
      renderWithProviders();

      fireEvent.click(document.querySelector('.anticon-bell')!);

      await waitFor(() => {
        expect(screen.getByText('暂无通知')).toBeInTheDocument();
      });
    });

    it('显示通知列表', async () => {
      vi.mocked(notificationService.getNotifications).mockResolvedValue({
        items: [
          {
            id: 'notif_1',
            title: '合同到期提醒',
            content: '合同将在7天后到期',
            type: 'contract_expiring',
            is_read: false,
            priority: 'normal',
            created_at: '2026-01-30T08:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      });

      renderWithProviders();

      fireEvent.click(document.querySelector('.anticon-bell')!);

      await waitFor(() => {
        expect(screen.getByText('合同到期提醒')).toBeInTheDocument();
      });
    });

    it('does not emit framework or antd deprecation warnings when opening the list', async () => {
      vi.mocked(notificationService.getNotifications).mockResolvedValue({
        items: [
          {
            id: 'notif_1',
            title: '合同到期提醒',
            content: '合同将在7天后到期',
            type: 'contract_expiring',
            is_read: false,
            priority: 'normal',
            created_at: '2026-01-30T08:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      });
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      try {
        renderWithProviders();

        fireEvent.click(document.querySelector('.anticon-bell')!);

        await waitFor(() => {
          expect(screen.getByText('合同到期提醒')).toBeInTheDocument();
        });

        const messages = `${formatConsoleMessages(consoleErrorSpy.mock.calls)} ${formatConsoleMessages(
          consoleWarnSpy.mock.calls
        )}`;

        expect(messages).not.toContain('[antd: List]');
        expect(messages).not.toContain('React Router Future Flag Warning');
      } finally {
        consoleErrorSpy.mockRestore();
        consoleWarnSpy.mockRestore();
      }
    });
  });

  describe('标记已读', () => {
    it('点击全部已读调用服务', async () => {
      vi.mocked(notificationService.getUnreadCount).mockResolvedValue(3);
      vi.mocked(notificationService.getNotifications).mockResolvedValue({
        items: [
          {
            id: 'notif_1',
            title: '未读消息',
            content: '内容',
            type: 'system_notice',
            is_read: false,
            priority: 'normal',
            created_at: '2026-01-30T08:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      });

      renderWithProviders();

      fireEvent.click(document.querySelector('.anticon-bell')!);

      await waitFor(() => {
        expect(screen.getByText('全部已读')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('全部已读'));

      await waitFor(() => {
        expect(notificationService.markAllAsRead).toHaveBeenCalled();
      });
    });
  });

  describe('通知类型', () => {
    it('正确显示合同即将到期类型', async () => {
      vi.mocked(notificationService.getNotifications).mockResolvedValue({
        items: [
          {
            id: 'notif_1',
            title: '合同提醒',
            content: '内容',
            type: 'contract_expiring',
            is_read: false,
            priority: 'normal',
            created_at: '2026-01-30T08:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      });

      renderWithProviders();

      fireEvent.click(document.querySelector('.anticon-bell')!);

      await waitFor(() => {
        expect(screen.getByText('合同即将到期')).toBeInTheDocument();
      });
    });
  });

  describe('回调函数', () => {
    it('点击时调用 onClick 回调', async () => {
      const onClick = vi.fn();

      renderWithProviders({ onClick });

      fireEvent.click(document.querySelector('.anticon-bell')!);

      expect(onClick).toHaveBeenCalled();
    });
  });
});
