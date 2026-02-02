/**
 * ApiMonitor 组件测试
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ApiMonitor from '../ApiMonitor';

// Mock apiHealthCheck
vi.mock('../../../services/apiHealthCheck', () => ({
  apiHealthCheck: {
    checkCriticalEndpoints: vi.fn(),
    getResults: vi.fn(),
    getHealthSummary: vi.fn(),
  },
}));

// Mock logger
vi.mock('../../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  }),
}));

vi.mock('@/components/Common/TableWithPagination', () => ({
  TableWithPagination: ({
    columns,
    dataSource,
  }: {
    columns?: Array<{
      key?: string;
      title?: React.ReactNode | ((props: Record<string, unknown>) => React.ReactNode);
      dataIndex?: string;
      render?: (value: unknown, record: Record<string, unknown>, index: number) => React.ReactNode;
    }>;
    dataSource?: Array<Record<string, unknown>>;
  }) => (
    <div data-testid="table">
      <div data-testid="table-header">
        {columns?.map((column, colIndex) => {
          const title =
            typeof column.title === 'function' ? column.title({}) : column.title ?? '';
          return <span key={column.key ?? `header-${colIndex}`}>{title}</span>;
        })}
      </div>
      {dataSource?.map((record, rowIndex) => (
        <div key={String(record.endpoint ?? rowIndex)} data-testid={`row-${rowIndex}`}>
          {columns?.map((column, colIndex) => {
            const value = column.dataIndex ? record[column.dataIndex] : undefined;
            return (
              <span key={column.key ?? `${colIndex}`}>
                {column.render ? column.render(value, record, rowIndex) : String(value ?? '')}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  ),
}));

import { apiHealthCheck } from '../../../services/apiHealthCheck';

describe('ApiMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 默认 mock 返回值
    vi.mocked(apiHealthCheck.checkCriticalEndpoints).mockResolvedValue(undefined);
    vi.mocked(apiHealthCheck.getResults).mockReturnValue(
      new Map([
        [
          '/api/v1/health',
          {
            endpoint: '/api/v1/health',
            status: 'healthy',
            responseTime: 150,
            lastChecked: new Date('2026-01-30T08:00:00Z'),
          },
        ],
        [
          '/api/v1/assets',
          {
            endpoint: '/api/v1/assets',
            status: 'healthy',
            responseTime: 320,
            lastChecked: new Date('2026-01-30T08:00:00Z'),
          },
        ],
      ])
    );
    vi.mocked(apiHealthCheck.getHealthSummary).mockReturnValue({
      total: 2,
      healthy: 2,
      unhealthy: 0,
      unknown: 0,
      healthPercentage: 100,
    });
  });

  describe('渲染', () => {
    it('渲染标题和刷新按钮', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('API健康监控')).toBeInTheDocument();
        expect(screen.getByText('刷新状态')).toBeInTheDocument();
      });
    });

    it('渲染统计卡片', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('总体健康度')).toBeInTheDocument();
        expect(screen.getByText('健康端点')).toBeInTheDocument();
        expect(screen.getByText('异常端点')).toBeInTheDocument();
        expect(screen.getByText('未知状态')).toBeInTheDocument();
      });
    });

    it('渲染端点详细状态表格', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('端点详细状态')).toBeInTheDocument();
        expect(screen.getByText('端点')).toBeInTheDocument();
        expect(screen.getByText('状态')).toBeInTheDocument();
        expect(screen.getByText('响应时间')).toBeInTheDocument();
      });
    });

    it('渲染监控说明', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('监控说明')).toBeInTheDocument();
        expect(screen.getByText(/每30秒自动刷新一次/)).toBeInTheDocument();
      });
    });
  });

  describe('健康状态显示', () => {
    it('显示 100% 健康度时不显示警告', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.queryByText('API健康状况需要关注')).not.toBeInTheDocument();
        expect(screen.queryByText('API健康状况严重')).not.toBeInTheDocument();
      });
    });

    it('健康度低于 80% 时显示警告', async () => {
      vi.mocked(apiHealthCheck.getHealthSummary).mockReturnValue({
        total: 10,
        healthy: 7,
        unhealthy: 3,
        unknown: 0,
        healthPercentage: 70,
      });

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('API健康状况需要关注')).toBeInTheDocument();
      });
    });

    it('健康度低于 60% 时显示严重警告', async () => {
      vi.mocked(apiHealthCheck.getHealthSummary).mockReturnValue({
        total: 10,
        healthy: 5,
        unhealthy: 5,
        unknown: 0,
        healthPercentage: 50,
      });

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('API健康状况严重')).toBeInTheDocument();
      });
    });
  });

  describe('端点状态表格', () => {
    it('显示健康端点状态', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('/api/v1/health')).toBeInTheDocument();
        expect(screen.getAllByText('HEALTHY')).toHaveLength(2);
      });
    });

    it('显示异常端点状态', async () => {
      vi.mocked(apiHealthCheck.getResults).mockReturnValue(
        new Map([
          [
            '/api/v1/broken',
            {
              endpoint: '/api/v1/broken',
              status: 'unhealthy',
              responseTime: undefined,
              error: 'Connection refused',
              lastChecked: new Date('2026-01-30T08:00:00Z'),
            },
          ],
        ])
      );
      vi.mocked(apiHealthCheck.getHealthSummary).mockReturnValue({
        total: 1,
        healthy: 0,
        unhealthy: 1,
        unknown: 0,
        healthPercentage: 0,
      });

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('/api/v1/broken')).toBeInTheDocument();
        expect(screen.getByText('UNHEALTHY')).toBeInTheDocument();
        expect(screen.getByText('Connection refused')).toBeInTheDocument();
      });
    });

    it('显示未知状态端点', async () => {
      vi.mocked(apiHealthCheck.getResults).mockReturnValue(
        new Map([
          [
            '/api/v1/timeout',
            {
              endpoint: '/api/v1/timeout',
              status: 'unknown',
              responseTime: undefined,
              lastChecked: new Date('2026-01-30T08:00:00Z'),
            },
          ],
        ])
      );

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
      });
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮重新加载状态', async () => {
      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(1);
      });

      const refreshButton = screen.getByRole('button', { name: /刷新状态/ });
      await waitFor(() => {
        expect(refreshButton).not.toHaveClass('ant-btn-loading');
      });
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(2);
      });
    });

    it('自动每 30 秒刷新一次', async () => {
      vi.useFakeTimers();
      renderWithProviders(<ApiMonitor />);

      await vi.runAllTicks();
      expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(1);

      // 前进 30 秒
      await vi.advanceTimersByTimeAsync(30000);
      await vi.runAllTicks();

      expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(2);

      // 再前进 30 秒
      await vi.advanceTimersByTimeAsync(30000);
      await vi.runAllTicks();

      expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(3);
      vi.useRealTimers();
    });
  });

  describe('响应时间格式化', () => {
    it('显示毫秒格式的响应时间', async () => {
      vi.mocked(apiHealthCheck.getResults).mockReturnValue(
        new Map([
          [
            '/api/v1/fast',
            {
              endpoint: '/api/v1/fast',
              status: 'healthy',
              responseTime: 150,
              lastChecked: new Date('2026-01-30T08:00:00Z'),
            },
          ],
        ])
      );

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('150ms')).toBeInTheDocument();
      });
    });

    it('显示秒格式的响应时间（超过1秒）', async () => {
      vi.mocked(apiHealthCheck.getResults).mockReturnValue(
        new Map([
          [
            '/api/v1/slow',
            {
              endpoint: '/api/v1/slow',
              status: 'healthy',
              responseTime: 2500,
              lastChecked: new Date('2026-01-30T08:00:00Z'),
            },
          ],
        ])
      );

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        expect(screen.getByText('2.50s')).toBeInTheDocument();
      });
    });
  });

  describe('错误处理', () => {
    it('加载失败时不崩溃', async () => {
      vi.mocked(apiHealthCheck.checkCriticalEndpoints).mockRejectedValue(
        new Error('Network error')
      );

      renderWithProviders(<ApiMonitor />);

      await waitFor(() => {
        // 组件应该正常渲染，不崩溃
        expect(screen.getByText('API健康监控')).toBeInTheDocument();
      });
    });
  });

  describe('清理', () => {
    it('卸载时清理定时器', async () => {
      vi.useFakeTimers();
      const { unmount } = renderWithProviders(<ApiMonitor />);

      await vi.runAllTicks();
      expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(1);

      unmount();

      // 前进时间后不应该再调用
      await vi.advanceTimersByTimeAsync(60000);
      await vi.runAllTicks();

      // 调用次数应该还是 1
      expect(apiHealthCheck.checkCriticalEndpoints).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });
});
