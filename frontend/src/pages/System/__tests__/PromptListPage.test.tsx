/**
 * PromptListPage 页面测试
 * 验证 Prompt 列表加载、操作与筛选的核心行为
 *
 * 修复说明：
 * - 移除 antd 所有组件 mock
 * - 移除 @ant-design/icons mock
 * - 保留服务层 mock (llmPromptService)
 * - 保留组件 mock (PromptEditor) - 业务组件
 * - 保留工具类 mock (logger, dayjs, colorMap)
 * - 使用真实 antd message 和 Modal API
 * - 使用文本内容和 className 进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { act, fireEvent, screen, waitFor } from '@/test/utils/test-helpers';
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
  default: vi.fn(({ visible }) => (visible ? <div data-testid="prompt-editor" /> : null)),
}));

vi.mock('dayjs', () => ({
  default: vi.fn(() => ({
    format: vi.fn(() => '2024-01-01 12:00'),
  })),
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

const flushPromises = () =>
  new Promise<void>(resolve => {
    setTimeout(resolve, 0);
  });

const renderPromptListPage = async () => {
  await act(async () => {
    renderWithProviders(<PromptListPage />);
    await flushPromises();
  });
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(Modal, 'info').mockImplementation(
    () =>
      ({
        destroy: vi.fn(),
        update: vi.fn(),
      }) as never
  );
  vi.spyOn(message, 'success').mockImplementation(vi.fn());
  vi.spyOn(message, 'error').mockImplementation(vi.fn());
  vi.mocked(llmPromptService.getPrompts).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(llmPromptService.getStatistics).mockResolvedValue(createMockStatistics());
});

describe('PromptListPage - 基础渲染', () => {
  it('应该渲染标题和新建按钮', async () => {
    await renderPromptListPage();
    expect(screen.getByText('LLM Prompt 管理')).toBeInTheDocument();
    expect(screen.getByText('新建 Prompt')).toBeInTheDocument();
  }, 30000);

  it('应该渲染筛选器', async () => {
    await renderPromptListPage();
    expect(screen.getAllByText('文档类型').length).toBeGreaterThan(0);
    expect(screen.getAllByText('提供商').length).toBeGreaterThan(0);
    expect(screen.getAllByText('状态').length).toBeGreaterThan(0);
  });
});

describe('PromptListPage - 数据加载', () => {
  it('应该加载Prompt列表与统计数据', async () => {
    await renderPromptListPage();

    await waitFor(() => {
      expect(llmPromptService.getPrompts).toHaveBeenCalled();
      expect(llmPromptService.getStatistics).toHaveBeenCalled();
    });
  });
});

describe('PromptListPage - Prompt操作', () => {
  it('点击新建按钮应显示编辑器', async () => {
    await renderPromptListPage();
    fireEvent.click(screen.getByText('新建 Prompt'));
    expect(screen.getByTestId('prompt-editor')).toBeInTheDocument();
  });

  it('点击激活按钮应调用激活接口并提示成功', async () => {
    vi.mocked(llmPromptService.getPrompts).mockResolvedValue({
      items: [createMockPrompt({ status: PromptStatus.DRAFT })],
      total: 1,
    });
    vi.mocked(llmPromptService.activatePrompt).mockResolvedValue(undefined);

    await renderPromptListPage();

    await waitFor(() => {
      expect(llmPromptService.getPrompts).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole('button', { name: '激活' }));

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

    await renderPromptListPage();

    await waitFor(() => {
      expect(llmPromptService.getPrompts).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole('button', { name: '版本历史' }));

    await waitFor(() => {
      expect(Modal.info).toHaveBeenCalled();
    });
  });
});

describe('PromptListPage - 错误处理', () => {
  it('加载失败应提示错误', async () => {
    vi.mocked(llmPromptService.getPrompts).mockRejectedValue(new Error('Load failed'));

    await renderPromptListPage();

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('加载 Prompt 列表失败');
    });
  });
});

describe('PromptListPage - 组件契约', () => {
  it('PromptEditor 接收可见性控制', async () => {
    await renderPromptListPage();
    expect(PromptEditor).toHaveBeenCalled();
  });
});
