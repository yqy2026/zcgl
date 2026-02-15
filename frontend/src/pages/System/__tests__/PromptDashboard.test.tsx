import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import dayjs from 'dayjs';
import { fireEvent, renderWithProviders, screen } from '@/test/utils/test-helpers';
import PromptDashboard from '../PromptDashboard';
import { DocType, LLMProvider, PromptStatus } from '@/types/llmPrompt';
import { usePromptDashboardData } from '../PromptDashboard/hooks/usePromptDashboardData';

vi.mock('../PromptDashboard/hooks/usePromptDashboardData', () => ({
  usePromptDashboardData: vi.fn(),
}));

const buildHookResult = (overrides: Record<string, unknown> = {}) => {
  return {
    prompts: [],
    statistics: {
      total_prompts: 3,
      status_distribution: [{ status: PromptStatus.ACTIVE, count: 2 }],
      doc_type_distribution: [{ doc_type: DocType.CONTRACT, count: 3 }],
      provider_distribution: [{ provider: LLMProvider.QWEN, count: 3 }],
      overall_avg_accuracy: 0.93,
      overall_avg_confidence: 0.9,
    },
    selectedPromptId: 'prompt-1',
    selectedPrompt: {
      id: 'prompt-1',
      name: '租赁合同提取模板',
      doc_type: DocType.CONTRACT,
      provider: LLMProvider.QWEN,
      description: '用于租赁合同字段提取',
      system_prompt: 'system prompt',
      user_prompt_template: 'user prompt template',
      version: 'v1.0.0',
      status: PromptStatus.ACTIVE,
      tags: ['contract'],
      avg_accuracy: 0.94,
      avg_confidence: 0.91,
      total_usage: 120,
      created_at: '2026-02-01T00:00:00Z',
      updated_at: '2026-02-01T00:00:00Z',
    },
    selectedStatusMeta: {
      label: '活跃',
      hint: '线上使用中',
      tone: 'success',
      icon: null,
    },
    performanceData: [
      {
        date: '2026-02-01',
        accuracy: 0.92,
        confidence: 0.88,
        extraction_count: 42,
        corrected_count: 3,
      },
    ],
    fieldErrorRates: [
      {
        field_name: 'monthly_rent',
        error_count: 3,
        total_count: 100,
        error_rate: 0.03,
      },
    ],
    suggestions: [
      {
        priority: 'medium',
        field_name: 'monthly_rent',
        issue: '金额字段存在格式波动',
        suggestion: '增加金额格式 few-shot 示例',
      },
    ],
    dateRange: [dayjs().subtract(7, 'days'), dayjs()],
    dateRangeLabel: '最近 7 天',
    promptOptions: [{ label: '租赁合同提取模板', value: 'prompt-1' }],
    activePromptCount: 2,
    monitoredFieldCount: 1,
    highRiskFieldCount: 0,
    accuracyTrend: 'up',
    confidenceTrend: 'stable',
    isInitialLoading: false,
    isRefreshing: false,
    hasError: false,
    errorMessage: null,
    handleRefresh: vi.fn(),
    handleDateRangeChange: vi.fn(),
    handlePromptChange: vi.fn(),
    ...overrides,
  };
};

describe('PromptDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(usePromptDashboardData).mockReturnValue(buildHookResult());
  });

  it('shows loading shell before initial data is ready', () => {
    vi.mocked(usePromptDashboardData).mockReturnValue(
      buildHookResult({
        isInitialLoading: true,
      })
    );

    renderWithProviders(<PromptDashboard />);

    expect(screen.getByText('LLM Prompt 性能监控')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '刷新监控数据' })).not.toBeInTheDocument();
  });

  it('renders dashboard cards and refresh action', () => {
    const handleRefresh = vi.fn();
    vi.mocked(usePromptDashboardData).mockReturnValue(
      buildHookResult({
        handleRefresh,
      })
    );

    renderWithProviders(<PromptDashboard />);

    expect(screen.getAllByText('租赁合同提取模板').length).toBeGreaterThan(0);
    expect(screen.getByText('优化建议')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '刷新监控数据' }));
    expect(handleRefresh).toHaveBeenCalled();
  });

  it('renders error alert when data load failed', () => {
    vi.mocked(usePromptDashboardData).mockReturnValue(
      buildHookResult({
        hasError: true,
        errorMessage: '统计服务暂不可用',
      })
    );

    renderWithProviders(<PromptDashboard />);

    expect(screen.getByText('数据加载失败')).toBeInTheDocument();
    expect(screen.getByText('统计服务暂不可用')).toBeInTheDocument();
  });
});
