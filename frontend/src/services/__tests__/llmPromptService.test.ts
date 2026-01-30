/**
 * LLM Prompt Service 测试
 * 测试 LLM Prompt 管理服务的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: vi.fn(() => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  })),
}));

import { DocType, PromptStatus, LLMProvider } from '@/types/llmPrompt';

// Helper to create mock prompt
const createMockPrompt = (overrides = {}) => ({
  id: 'prompt-001',
  name: '租赁合同提取',
  version: 1,
  doc_type: DocType.CONTRACT,
  provider: LLMProvider.QWEN,
  status: PromptStatus.ACTIVE,
  content: 'Mock prompt content',
  avg_accuracy: 0.92,
  avg_confidence: 0.88,
  total_usage: 150,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  ...overrides,
});

describe('LLMPromptService - 模块导入测试', () => {
  it('应该能够导入服务', async () => {
    const module = await import('../llmPromptService');
    expect(module).toBeDefined();
    expect(module.llmPromptService).toBeDefined();
  });

  it('应该导出 LLMPromptService 类', async () => {
    const module = await import('../llmPromptService');
    expect(module.LLMPromptService).toBeDefined();
  });

  it('应该导出便捷方法', async () => {
    const module = await import('../llmPromptService');
    expect(module.getPrompts).toBeDefined();
    expect(module.getPrompt).toBeDefined();
    expect(module.createPrompt).toBeDefined();
    expect(module.updatePrompt).toBeDefined();
    expect(module.activatePrompt).toBeDefined();
    expect(module.rollbackPrompt).toBeDefined();
    expect(module.getPromptVersions).toBeDefined();
    expect(module.getStatistics).toBeDefined();
    expect(module.submitFeedback).toBeDefined();
    expect(module.getActivePrompt).toBeDefined();
    expect(module.testPrompt).toBeDefined();
  });
});

describe('LLMPromptService - getPrompts 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该调用正确的 API 端点', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [createMockPrompt()], total: 1 },
    });

    await llmPromptService.getPrompts();

    expect(apiClient.get).toHaveBeenCalledWith('/llm-prompts', expect.any(Object));
  });

  it('应该支持分页参数', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await llmPromptService.getPrompts({ page: 2, pageSize: 20 });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/llm-prompts',
      expect.objectContaining({
        params: expect.objectContaining({ page: 2 }),
      })
    );
  });

  it('应该支持筛选参数', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    await llmPromptService.getPrompts({
      doc_type: DocType.CONTRACT,
      provider: LLMProvider.QWEN,
      status: PromptStatus.ACTIVE,
    });

    expect(apiClient.get).toHaveBeenCalled();
  });
});

describe('LLMPromptService - getPrompt 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该获取单个 Prompt 详情', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockPrompt = createMockPrompt();
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPrompt });

    const result = await llmPromptService.getPrompt('prompt-001');

    expect(apiClient.get).toHaveBeenCalledWith('/llm-prompts/prompt-001');
    expect(result.id).toBe('prompt-001');
  });
});

describe('LLMPromptService - createPrompt 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该创建新 Prompt', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockPrompt = createMockPrompt();
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockPrompt });

    const createData = {
      name: '新建 Prompt',
      doc_type: DocType.CONTRACT,
      provider: LLMProvider.QWEN,
      content: 'New prompt content',
    };

    const result = await llmPromptService.createPrompt(createData);

    expect(apiClient.post).toHaveBeenCalledWith('/llm-prompts', createData);
    expect(result).toBeDefined();
  });
});

describe('LLMPromptService - updatePrompt 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该更新 Prompt', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockPrompt = createMockPrompt({ version: 2 });
    vi.mocked(apiClient.put).mockResolvedValue({ data: mockPrompt });

    const updateData = {
      content: 'Updated content',
      change_description: '更新内容',
    };

    const result = await llmPromptService.updatePrompt('prompt-001', updateData);

    expect(apiClient.put).toHaveBeenCalledWith('/llm-prompts/prompt-001', updateData);
    expect(result.version).toBe(2);
  });
});

describe('LLMPromptService - activatePrompt 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该激活 Prompt', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockPrompt = createMockPrompt({ status: PromptStatus.ACTIVE });
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockPrompt });

    const result = await llmPromptService.activatePrompt('prompt-001');

    expect(apiClient.post).toHaveBeenCalledWith('/llm-prompts/prompt-001/activate', {});
    expect(result.status).toBe(PromptStatus.ACTIVE);
  });
});

describe('LLMPromptService - rollbackPrompt 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该回滚 Prompt 到指定版本', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockPrompt = createMockPrompt({ version: 1 });
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockPrompt });

    const rollbackRequest = { target_version: 1, reason: '回滚到稳定版本' };
    const result = await llmPromptService.rollbackPrompt('prompt-001', rollbackRequest);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/llm-prompts/prompt-001/rollback',
      rollbackRequest
    );
    expect(result.version).toBe(1);
  });
});

describe('LLMPromptService - getPromptVersions 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该获取版本历史', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockVersions = [
      { id: 'v1', version: 1, created_at: '2024-01-01' },
      { id: 'v2', version: 2, created_at: '2024-01-15' },
    ];
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersions });

    const result = await llmPromptService.getPromptVersions('prompt-001');

    expect(apiClient.get).toHaveBeenCalledWith('/llm-prompts/prompt-001/versions');
    expect(result).toHaveLength(2);
  });
});

describe('LLMPromptService - getStatistics 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该获取统计概览', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockStats = {
      total_prompts: 10,
      status_distribution: [],
      overall_avg_accuracy: 0.85,
      overall_avg_confidence: 0.8,
    };
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockStats });

    const result = await llmPromptService.getStatistics();

    expect(apiClient.get).toHaveBeenCalledWith('/llm-prompts/statistics/overview');
    expect(result.total_prompts).toBe(10);
  });
});

describe('LLMPromptService - submitFeedback 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该提交用户反馈', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { success: true, feedback_id: 'fb-001' },
    });

    const feedbackData = {
      prompt_id: 'prompt-001',
      extraction_id: 'ext-001',
      rating: 5,
      comment: '提取结果很准确',
    };

    const result = await llmPromptService.submitFeedback(feedbackData);

    expect(apiClient.post).toHaveBeenCalledWith('/llm-prompts/feedback', feedbackData);
    expect(result.success).toBe(true);
    expect(result.feedback_id).toBe('fb-001');
  });
});

describe('LLMPromptService - getActivePrompt 测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该获取活跃的 Prompt', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    const mockPrompt = createMockPrompt({ status: PromptStatus.ACTIVE });
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [mockPrompt], total: 1 },
    });

    const result = await llmPromptService.getActivePrompt(DocType.CONTRACT);

    expect(result).not.toBeNull();
    expect(result?.status).toBe(PromptStatus.ACTIVE);
  });

  it('没有活跃 Prompt 应该返回 null', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], total: 0 },
    });

    const result = await llmPromptService.getActivePrompt(DocType.CONTRACT);

    expect(result).toBeNull();
  });
});

describe('LLMPromptService - 错误处理测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getPrompts 失败应该抛出错误', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

    await expect(llmPromptService.getPrompts()).rejects.toThrow();
  });

  it('createPrompt 失败应该抛出错误', async () => {
    const { apiClient } = await import('@/api/client');
    const { llmPromptService } = await import('../llmPromptService');

    vi.mocked(apiClient.post).mockRejectedValue(new Error('Create failed'));

    await expect(
      llmPromptService.createPrompt({
        name: 'Test',
        doc_type: DocType.CONTRACT,
        provider: LLMProvider.QWEN,
        content: 'Test content',
      })
    ).rejects.toThrow();
  });
});
