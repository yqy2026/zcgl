import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import NotificationCenter from '../NotificationCenter';
import { notificationService } from '@/services/notificationService';
import { MessageManager } from '@/utils/messageManager';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/notificationService', () => ({
  notificationService: {
    getNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
    deleteNotification: vi.fn(),
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

describe('NotificationCenter legacy contract navigation retirement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(notificationService.getNotifications).mockResolvedValue({
      items: [
        {
          id: 'notif-1',
          title: '合同到期提醒',
          content: '请处理合同续签事项',
          type: 'contract_expiring',
          is_read: false,
          priority: 'normal',
          related_entity_type: 'contract',
          related_entity_id: 'contract-1',
          created_at: '2026-03-07T08:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
      unread_count: 1,
    });
    vi.mocked(notificationService.markAsRead).mockResolvedValue(undefined);
    vi.mocked(notificationService.markAllAsRead).mockResolvedValue(undefined);
    vi.mocked(notificationService.deleteNotification).mockResolvedValue(undefined);
  });

  it('shows a migration notice instead of navigating to the retired rental contract detail route', async () => {
    renderWithProviders(<NotificationCenter />);

    expect(await screen.findByText('合同到期提醒')).toBeInTheDocument();
    fireEvent.click(screen.getByText('合同到期提醒'));

    await waitFor(() => {
      expect(notificationService.markAsRead).toHaveBeenCalledWith('notif-1');
      expect(MessageManager.info).toHaveBeenCalledWith(
        '合同通知详情入口迁移中，请改从新 contract/contract-group 页面处理'
      );
    });
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
