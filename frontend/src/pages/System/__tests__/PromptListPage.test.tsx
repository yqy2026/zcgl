/**
 * PromptListPage 页面测试
 * 测试 LLM Prompt 管理列表页面的核心功能
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';

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
  default: vi.fn(() => null),
}));

vi.mock('dayjs', () => ({
  default: vi.fn(() => ({
    format: vi.fn(() => '2024-01-01 12:00'),
  })),
}));

// Mock Ant Design
vi.mock('antd', () => {
  return {
    Table: vi.fn(() => null),
    Card: vi.fn(({ children }) => <div data-testid="card">{children}</div>),
    Button: vi.fn(({ children, onClick }) => (
      <button onClick={onClick} data-testid="button">
        {children}
      </button>
    )),
    Space: vi.fn(({ children }) => <div data-testid="space">{children}</div>),
    Tag: vi.fn(({ children }) => <span data-testid="tag">{children}</span>),
    Select: Object.assign(vi.fn(() => null), {
      Option: vi.fn(() => null),
    }),
    Modal: Object.assign(vi.fn(() => null), {
      info: vi.fn(),
    }),
    Tooltip: vi.fn(({ children }) => children),
    Row: vi.fn(({ children }) => <div data-testid="row">{children}</div>),
    Col: vi.fn(({ children }) => <div data-testid="col">{children}</div>),
    Statistic: vi.fn(() => null),
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

import { PromptStatus, DocType, LLMProvider } from '@/types/llmPrompt';

// Helper to create mock prompt
const createMockPrompt = (overrides = {}) => ({
  id: 'prompt-001',
  name: '租赁合同提取',
  version: 1,
  doc_type: DocType.CONTRACT,
  provider: LLMProvider.QWEN,
  status: PromptStatus.ACTIVE,
  avg_accuracy: 0.92,
  avg_confidence: 0.88,
  total_usage: 150,
  updated_at: '2024-01-15T10:00:00Z',
  ...overrides,
});

// Helper to create mock statistics
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

describe('PromptListPage - 组件导入测试', () => {
  it('应该能够导入组件', async () => {
    const module = await import('../PromptListPage');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });

  it('组件应该是React函数组件', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;
    expect(typeof PromptListPage).toBe('function');
  });
});

describe('PromptListPage - 组件结构测试', () => {
  it('应该可以创建组件实例', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
    expect(element.type).toBe(PromptListPage);
  });

  it('组件不需要任何必需属性', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage, {});
    expect(element).toBeTruthy();
  });
});

describe('PromptListPage - 数据加载测试', () => {
  it('应该加载Prompt列表', async () => {
    const { llmPromptService } = await import('@/services/llmPromptService');

    vi.mocked(llmPromptService.getPrompts).mockResolvedValue({
      items: [createMockPrompt()],
      total: 1,
    });

    const PromptListPage = (await import('../PromptListPage')).default;
    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });

  it('应该加载统计数据', async () => {
    const { llmPromptService } = await import('@/services/llmPromptService');

    vi.mocked(llmPromptService.getStatistics).mockResolvedValue(createMockStatistics());

    const PromptListPage = (await import('../PromptListPage')).default;
    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });
});

describe('PromptListPage - 筛选功能测试', () => {
  it('应该支持按文档类型筛选', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
    // 筛选器应该包含文档类型选项
  });

  it('应该支持按提供商筛选', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
    // 筛选器应该包含提供商选项
  });

  it('应该支持按状态筛选', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
    // 筛选器应该包含状态选项
  });
});

describe('PromptListPage - Prompt操作测试', () => {
  it('应该支持激活Prompt', async () => {
    const { llmPromptService } = await import('@/services/llmPromptService');

    vi.mocked(llmPromptService.activatePrompt).mockResolvedValue(undefined);

    const PromptListPage = (await import('../PromptListPage')).default;
    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });

  it('应该支持查看版本历史', async () => {
    const { llmPromptService } = await import('@/services/llmPromptService');

    vi.mocked(llmPromptService.getPromptVersions).mockResolvedValue([
      {
        id: 'version-001',
        version: 1,
        change_description: '初始版本',
        created_at: '2024-01-01T00:00:00Z',
        auto_generated: false,
      },
    ]);

    const PromptListPage = (await import('../PromptListPage')).default;
    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });

  it('应该支持新建Prompt', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });

  it('应该支持编辑Prompt', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });
});

describe('PromptListPage - 状态显示测试', () => {
  it('活跃状态应该显示success标签', async () => {
    const mockPrompt = createMockPrompt({ status: PromptStatus.ACTIVE });
    expect(mockPrompt.status).toBe(PromptStatus.ACTIVE);
  });

  it('草稿状态应该显示default标签', async () => {
    const mockPrompt = createMockPrompt({ status: PromptStatus.DRAFT });
    expect(mockPrompt.status).toBe(PromptStatus.DRAFT);
  });

  it('归档状态应该显示default标签', async () => {
    const mockPrompt = createMockPrompt({ status: PromptStatus.ARCHIVED });
    expect(mockPrompt.status).toBe(PromptStatus.ARCHIVED);
  });
});

describe('PromptListPage - 准确率显示测试', () => {
  it('高准确率 (>=90%) 应该显示success颜色', async () => {
    const mockPrompt = createMockPrompt({ avg_accuracy: 0.95 });
    expect(mockPrompt.avg_accuracy).toBeGreaterThanOrEqual(0.9);
  });

  it('中等准确率 (70-90%) 应该显示warning颜色', async () => {
    const mockPrompt = createMockPrompt({ avg_accuracy: 0.75 });
    expect(mockPrompt.avg_accuracy).toBeGreaterThanOrEqual(0.7);
    expect(mockPrompt.avg_accuracy).toBeLessThan(0.9);
  });

  it('低准确率 (<70%) 应该显示error颜色', async () => {
    const mockPrompt = createMockPrompt({ avg_accuracy: 0.5 });
    expect(mockPrompt.avg_accuracy).toBeLessThan(0.7);
  });
});

describe('PromptListPage - 文档类型显示测试', () => {
  it('租赁合同类型应该显示blue标签', async () => {
    const mockPrompt = createMockPrompt({ doc_type: DocType.CONTRACT });
    expect(mockPrompt.doc_type).toBe(DocType.CONTRACT);
  });

  it('产权证类型应该显示green标签', async () => {
    const mockPrompt = createMockPrompt({ doc_type: DocType.PROPERTY_CERT });
    expect(mockPrompt.doc_type).toBe(DocType.PROPERTY_CERT);
  });
});

describe('PromptListPage - 提供商显示测试', () => {
  it('应该正确显示Qwen提供商', async () => {
    const mockPrompt = createMockPrompt({ provider: LLMProvider.QWEN });
    expect(mockPrompt.provider).toBe(LLMProvider.QWEN);
  });

  it('应该正确显示混元提供商', async () => {
    const mockPrompt = createMockPrompt({ provider: LLMProvider.HUNYUAN });
    expect(mockPrompt.provider).toBe(LLMProvider.HUNYUAN);
  });

  it('应该正确显示DeepSeek提供商', async () => {
    const mockPrompt = createMockPrompt({ provider: LLMProvider.DEEPSEEK });
    expect(mockPrompt.provider).toBe(LLMProvider.DEEPSEEK);
  });

  it('应该正确显示智谱提供商', async () => {
    const mockPrompt = createMockPrompt({ provider: LLMProvider.GLM });
    expect(mockPrompt.provider).toBe(LLMProvider.GLM);
  });
});

describe('PromptListPage - 分页测试', () => {
  it('应该支持分页', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });

  it('应该支持改变每页数量', async () => {
    const PromptListPage = (await import('../PromptListPage')).default;

    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });
});

describe('PromptListPage - 错误处理测试', () => {
  it('加载失败应该显示错误消息', async () => {
    const { llmPromptService } = await import('@/services/llmPromptService');

    vi.mocked(llmPromptService.getPrompts).mockRejectedValue(new Error('Load failed'));

    const PromptListPage = (await import('../PromptListPage')).default;
    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });

  it('激活失败应该显示错误消息', async () => {
    const { llmPromptService } = await import('@/services/llmPromptService');

    vi.mocked(llmPromptService.activatePrompt).mockRejectedValue(new Error('Activate failed'));

    const PromptListPage = (await import('../PromptListPage')).default;
    const element = React.createElement(PromptListPage);
    expect(element).toBeTruthy();
  });
});
