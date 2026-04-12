import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import NotificationCenter from '../NotificationCenter';
import { notificationService } from '@/services/notificationService';
import { MessageManager } from '@/utils/messageManager';

const formatStderrWrites = (calls: unknown[][]) =>
  calls.map(call => String(call[0] ?? '')).join(' ');

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

vi.mock('@/components/Common/PageContainer', () => ({
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="page-container">{children}</div>
  ),
}));

vi.mock('antd', () => ({
  Card: ({
    title,
    extra,
    children,
  }: {
    title?: React.ReactNode;
    extra?: React.ReactNode;
    children?: React.ReactNode;
  }) => (
    <section>
      <div>{title}</div>
      <div>{extra}</div>
      <div>{children}</div>
    </section>
  ),
  Typography: {
    Text: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
      <span className={className}>{children}</span>
    ),
    Paragraph: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
      <p className={className}>{children}</p>
    ),
  },
  Tag: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <span className={className}>{children}</span>
  ),
  Button: ({
    children,
    onClick,
    disabled,
    className,
    'aria-label': ariaLabel,
  }: {
    children?: React.ReactNode;
    onClick?: React.MouseEventHandler<HTMLButtonElement>;
    disabled?: boolean;
    className?: string;
    'aria-label'?: string;
  }) => (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={className}
      aria-label={ariaLabel}
    >
      {children}
    </button>
  ),
  Space: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  Empty: ({ description }: { description?: React.ReactNode }) => <div>{description}</div>,
  Tabs: ({
    items,
    onChange,
    className,
  }: {
    items?: Array<{ key: string; label: React.ReactNode }>;
    onChange?: (key: string) => void;
    className?: string;
  }) => (
    <div className={className}>
      {items?.map(item => (
        <button key={item.key} type="button" onClick={() => onChange?.(item.key)}>
          {item.label}
        </button>
      ))}
    </div>
  ),
  Badge: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Spin: () => <div>loading</div>,
  Modal: {
    confirm: vi.fn(),
  },
  Pagination: () => <div>pagination</div>,
}));

vi.mock('../NotificationCenter.module.css', () => ({
  default: new Proxy(
    {},
    {
      get: (_target, key) => String(key),
    }
  ),
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
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      renderWithProviders(<NotificationCenter />);

      expect(await screen.findByText('合同到期提醒')).toBeInTheDocument();
      fireEvent.click(screen.getByText('合同到期提醒'));

      await waitFor(() => {
        expect(notificationService.markAsRead).toHaveBeenCalledWith('notif-1');
        expect(MessageManager.info).toHaveBeenCalledWith(
          '合同通知详情入口迁移中，请改从新 contract/contract-group 页面处理'
        );
      });
      const stderr = formatStderrWrites(stderrWriteSpy.mock.calls);
      expect(stderr).not.toContain('Could not parse CSS stylesheet');
      expect(stderr).not.toContain('[antd: List]');
      expect(mockNavigate).not.toHaveBeenCalled();
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });
});
