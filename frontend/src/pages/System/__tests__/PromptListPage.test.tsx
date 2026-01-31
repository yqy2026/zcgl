/**
 * PromptListPage 页面测试
 * 验证 Prompt 列表加载、操作与筛选的核心行为
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, Modal } from 'antd';

import PromptListPage from '../PromptListPage';
import { llmPromptService } from '@/services/llmPromptService';
import PromptEditor from '@/components/System/PromptEditor';
import { DocType, LLMProvider, PromptStatus } from '@/types/llmPrompt';

// Mock dependencies
vi.mock('@/services/llmPromptService', () => ({
  llmPromptService: {
    getPrompts: vi.fn(),
    getStatistics: vi.fn(),
    activatePrompt: vi.fn(),
    getPromptVersions: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: vi.fn(() => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  })),
}));

vi.mock('@/components/System/PromptEditor', () => ({
  default: vi.fn(({ visible }) =>
    visible ? <div data-testid="prompt-editor" /> : null
  ),
}));

vi.mock('dayjs', () => ({
  default: vi.fn(() => ({
    format: vi.fn(() => '2024-01-01 12:00'),
  })),
}));

// Mock Ant Design
vi.mock('antd', () => {
  const Table = vi.fn(({ columns = [], dataSource = [], rowKey }) => (
    <div data-testid="table">
      {dataSource.map((record: Record<string, unknown>, index: number) => {
        const key =
          typeof rowKey === 'function'
            ? rowKey(record)
            : rowKey
              ? record[rowKey]
              : index;
        return (
          <div key={String(key)} data-testid="table-row">
            {columns.map(
              (
                column: {
                  key?: string | number;
                  dataIndex?: string;
                  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
                },
                colIndex: number
              ) => {
                const columnKey = String(column.key ?? column.dataIndex ?? colIndex);
                if (column.render) {
                  const value = column.dataIndex ? record[column.dataIndex] : undefined;
                  return (
                    <div key={columnKey}>{column.render(value, record)}</div>
                  );
                }
                if (column.dataIndex) {
                  return <div key={columnKey}>{record[column.dataIndex]}</div>;
                }
                return <div key={columnKey} />;
              }
            )}
          </div>
        );
      })}
    </div>
  ));

  return {
    Table,
    Card: vi.fn(({ children, title, extra }) => (
      <div data-testid="card">
        <div>{title}</div>
        <div>{extra}</div>
        {children}
      </div>
    )),
    Button: vi.fn(({ children, onClick, icon, type }) => (
      <button data-testid="button" data-type={type} onClick={onClick}>
        {icon}
        {children}
      </button>
    )),
    Space: vi.fn(({ children }) => <div data-testid="space">{children}</div>),
    Tag: vi.fn(({ children }) => <span data-testid="tag">{children}</span>),
    Select: Object.assign(
      vi.fn(({ children, onChange, placeholder }) => (
        <select
          data-testid={`select-${placeholder}`}
          onChange={event => onChange?.((event.target as HTMLSelectElement).value)}
        >
          {children}
        </select>
      )),
      {
        Option: vi.fn(({ children, value }) => <option value={value}>{children}</option>),
      }
    ),
    Modal: Object.assign(vi.fn(() => null), {
      info: vi.fn(),
    }),
    Tooltip: vi.fn(({ children, title }) => (
      <span data-testid={`tooltip-${title}`}>{children}</span>
    )),
    Row: vi.fn(({ children }) => <div data-testid="row">{children}</div>),
    Col: vi.fn(({ children }) => <div data-testid="col">{children}</div>),
    Statistic: vi.fn(({ title, value }) => (
      <div data-testid={`statistic-${title}`}>{value}</div>
    )),
    Typography: {
      Title: vi.fn(({ children }) => <h4>{children}</h4>),
    },
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

// Mock icons
vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => null,
  EditOutlined: () => null,
  RocketOutlined: () => null,
  HistoryOutlined: () => null,
  ReloadOutlined: () => null,
  CheckCircleOutlined: () => null,
  FileTextOutlined: () => null,
}));

vi.mock('@/styles/colorMap', () => ({
  COLORS: {
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    primary: '#1890ff',
  },
}));

const createMockPrompt = (overrides = {}) => ({
  id: 'prompt-001',
  name: '租赁合同提取',
  version: 1,
  doc_type: DocType.CONTRACT,
  provider: LLMProvider.QWEN,
  status: PromptStatus.DRAFT,
  avg_accuracy: 0.92,
  avg_confidence: 0.88,
  total_usage: 150,
  updated_at: '2024-01-15T10:00:00Z',
  ...overrides,
});

const createMockStatistics = () => ({
  total_prompts: 10,
  status_distribution: [
    { status: PromptStatus.ACTIVE, count: 5 },
    { status: PromptStatus.DRAFT, count: 3 },
    { status: PromptStatus.ARCHIVED, count: 2 },
  ],
  overall_avg_accuracy: 0.88,
  overall_avg_confidence: 0.82,
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(llmPromptService.getPrompts).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(llmPromptService.getStatistics).mockResolvedValue(createMockStatistics());
});

describe('PromptListPage - 基础渲染', () => {
  it('应该渲染标题和新建按钮', () => {
    render(<PromptListPage />);
    expect(screen.getByText('LLM Prompt 管理')).toBeInTheDocument();
    expect(screen.getByText('新建 Prompt')).toBeInTheDocument();
  });

  it('应该渲染筛选器', () => {
    render(<PromptListPage />);
    expect(screen.getByTestId('select-文档类型')).toBeInTheDocument();
    expect(screen.getByTestId('select-提供商')).toBeInTheDocument();
    expect(screen.getByTestId('select-状态')).toBeInTheDocument();
  });
});

describe('PromptListPage - 数据加载', () => {
  it('应该加载Prompt列表与统计数据', async () => {
    render(<PromptListPage />);

    await waitFor(() => {
      expect(llmPromptService.getPrompts).toHaveBeenCalled();
      expect(llmPromptService.getStatistics).toHaveBeenCalled();
    });
  });
});

describe('PromptListPage - Prompt操作', () => {
  it('点击新建按钮应显示编辑器', () => {
    render(<PromptListPage />);
    fireEvent.click(screen.getByText('新建 Prompt'));
    expect(screen.getByTestId('prompt-editor')).toBeInTheDocument();
  });

  it('点击激活按钮应调用激活接口并提示成功', async () => {
    vi.mocked(llmPromptService.getPrompts).mockResolvedValue({
      items: [createMockPrompt({ status: PromptStatus.DRAFT })],
      total: 1,
    });
    vi.mocked(llmPromptService.activatePrompt).mockResolvedValue(undefined);

    render(<PromptListPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const activateWrapper = screen.getByTestId('tooltip-激活');
    const activateButton = activateWrapper.querySelector('button');
    fireEvent.click(activateButton!);

    await waitFor(() => {
      expect(llmPromptService.activatePrompt).toHaveBeenCalledWith('prompt-001');
      expect(message.success).toHaveBeenCalledWith('Prompt "租赁合同提取" 已激活');
    });
  });

  it('点击版本历史应弹出信息框', async () => {
    vi.mocked(llmPromptService.getPrompts).mockResolvedValue({
      items: [createMockPrompt()],
      total: 1,
    });
    vi.mocked(llmPromptService.getPromptVersions).mockResolvedValue([
      {
        id: 'version-001',
        version: 1,
        change_description: '初始版本',
        created_at: '2024-01-01T00:00:00Z',
        auto_generated: false,
      },
    ]);

    render(<PromptListPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('table-row')).toHaveLength(1);
    });

    const historyWrapper = screen.getByTestId('tooltip-版本历史');
    const historyButton = historyWrapper.querySelector('button');
    fireEvent.click(historyButton!);

    await waitFor(() => {
      expect(Modal.info).toHaveBeenCalled();
    });
  });
});

describe('PromptListPage - 错误处理', () => {
  it('加载失败应提示错误', async () => {
    vi.mocked(llmPromptService.getPrompts).mockRejectedValue(new Error('Load failed'));

    render(<PromptListPage />);

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('加载 Prompt 列表失败');
    });
  });
});

describe('PromptListPage - 组件契约', () => {
  it('PromptEditor 接收可见性控制', () => {
    render(<PromptListPage />);
    expect(PromptEditor).toHaveBeenCalled();
  });
});
