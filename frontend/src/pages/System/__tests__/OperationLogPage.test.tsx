import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import OperationLogPage from '../OperationLogPage';
import { MessageManager } from '@/utils/messageManager';
import { useOperationLogData } from '../OperationLog/hooks/useOperationLogData';

vi.mock('../OperationLog/hooks/useOperationLogData', () => ({
  useOperationLogData: vi.fn(),
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

const mockLog = {
  id: 'log-1',
  user_id: 'user-1',
  username: 'alice',
  user_name: 'Alice',
  action: 'read',
  action_name: '查询',
  module: 'asset',
  module_name: '资产管理',
  resource_type: 'asset',
  resource_id: 'asset-1',
  resource_name: '资产查询',
  ip_address: '127.0.0.1',
  user_agent: 'Mozilla/5.0',
  request_method: 'GET',
  request_url: '/api/v1/assets/asset-1',
  request_params: { page: 1 },
  request_body: null,
  response_status: 200,
  response_time: 120,
  error_message: null,
  details: { message: 'ok' },
  created_at: '2026-02-01T08:00:00Z',
};

const buildHookResult = (overrides: Record<string, unknown> = {}) => {
  return {
    logs: [mockLog],
    tablePagination: {
      current: 1,
      pageSize: 20,
      total: 1,
    },
    statistics: {
      total: 1,
      today: 1,
      this_week: 1,
      this_month: 1,
      by_action: {},
      by_module: {},
      error_count: 0,
      avg_response_time: 120,
    },
    loading: false,
    logsError: null,
    refetchLogs: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
};

describe('OperationLogPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useOperationLogData).mockReturnValue(buildHookResult());
  });

  it('renders page and supports refresh plus local filters', async () => {
    const refetchLogs = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useOperationLogData).mockReturnValue(buildHookResult({ refetchLogs }));

    renderWithProviders(<OperationLogPage />);

    expect(screen.getByText('操作日志')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '刷新操作日志列表' }));
    await waitFor(() => {
      expect(refetchLogs).toHaveBeenCalled();
    });

    fireEvent.change(screen.getByPlaceholderText('搜索用户名、资源或操作'), {
      target: { value: 'alice' },
    });

    await waitFor(() => {
      expect(screen.getByText('已启用 1 项筛选')).toBeInTheDocument();
    });
  }, 20_000);

  it('opens detail drawer from table action', async () => {
    renderWithProviders(<OperationLogPage />);

    fireEvent.click(screen.getByRole('button', { name: '查看操作日志 log-1 详情' }));
    expect(await screen.findByText('操作日志详情')).toBeInTheDocument();
  }, 30_000);

  it('surfaces load errors', async () => {
    vi.mocked(useOperationLogData).mockReturnValue(
      buildHookResult({
        logsError: new Error('load logs failed'),
      })
    );

    renderWithProviders(<OperationLogPage />);

    await waitFor(() => {
      expect(MessageManager.error).toHaveBeenCalledWith('加载操作日志失败');
    });
  });

  it('renders canonical read action with 查看 label', async () => {
    renderWithProviders(<OperationLogPage />);

    expect(await screen.findByText('查看')).toBeInTheDocument();
  });
});
