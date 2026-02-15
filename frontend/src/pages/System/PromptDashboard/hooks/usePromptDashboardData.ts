import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import dayjs, { type Dayjs } from 'dayjs';
import { PromptStatus, type PromptStatistics, type PromptTemplate } from '@/types/llmPrompt';
import { llmPromptService } from '@/services/llmPromptService';
import { createLogger } from '@/utils/logger';
import { getPromptStatusMeta } from '../utils';
import {
  buildPromptOptions,
  countHighRiskFields,
  getDateRangeLabel,
  toTrendSeries,
} from '../utils';
import type {
  FieldErrorRate,
  OptimizationSuggestion,
  PerformanceMetrics,
  PromptDashboardDateRange,
} from '../types';

const logger = createLogger('PromptDashboard');

interface LoadPromptDetailsResult {
  performanceData: PerformanceMetrics[];
  fieldErrorRates: FieldErrorRate[];
  suggestions: OptimizationSuggestion[];
}

const buildMockPromptDetails = (): LoadPromptDetailsResult => {
  return {
    performanceData: [
      {
        date: dayjs().subtract(6, 'days').format('YYYY-MM-DD'),
        accuracy: 0.82,
        confidence: 0.78,
        extraction_count: 45,
        corrected_count: 8,
      },
      {
        date: dayjs().subtract(5, 'days').format('YYYY-MM-DD'),
        accuracy: 0.84,
        confidence: 0.8,
        extraction_count: 52,
        corrected_count: 8,
      },
      {
        date: dayjs().subtract(4, 'days').format('YYYY-MM-DD'),
        accuracy: 0.86,
        confidence: 0.82,
        extraction_count: 48,
        corrected_count: 7,
      },
      {
        date: dayjs().subtract(3, 'days').format('YYYY-MM-DD'),
        accuracy: 0.85,
        confidence: 0.81,
        extraction_count: 50,
        corrected_count: 7,
      },
      {
        date: dayjs().subtract(2, 'days').format('YYYY-MM-DD'),
        accuracy: 0.88,
        confidence: 0.83,
        extraction_count: 55,
        corrected_count: 6,
      },
      {
        date: dayjs().subtract(1, 'days').format('YYYY-MM-DD'),
        accuracy: 0.87,
        confidence: 0.84,
        extraction_count: 47,
        corrected_count: 6,
      },
      {
        date: dayjs().format('YYYY-MM-DD'),
        accuracy: 0.89,
        confidence: 0.85,
        extraction_count: 53,
        corrected_count: 6,
      },
    ],
    fieldErrorRates: [
      { field_name: 'contract_number', error_count: 15, total_count: 350, error_rate: 0.043 },
      { field_name: 'sign_date', error_count: 28, total_count: 350, error_rate: 0.08 },
      { field_name: 'landlord_name', error_count: 12, total_count: 350, error_rate: 0.034 },
      { field_name: 'tenant_name', error_count: 18, total_count: 350, error_rate: 0.051 },
      { field_name: 'monthly_rent', error_count: 35, total_count: 350, error_rate: 0.1 },
      { field_name: 'lease_start_date', error_count: 22, total_count: 350, error_rate: 0.063 },
      { field_name: 'lease_end_date', error_count: 25, total_count: 350, error_rate: 0.071 },
    ],
    suggestions: [
      {
        priority: 'high',
        field_name: 'monthly_rent',
        issue: '错误率 10%，为最高',
        suggestion: '租金字段识别错误较多，建议添加Few-shot示例和格式验证',
      },
      {
        priority: 'high',
        field_name: 'lease_end_date',
        issue: '错误率 7.1%',
        suggestion: '结束日期识别不准确，建议优化日期提取逻辑',
      },
      {
        priority: 'medium',
        field_name: 'lease_start_date',
        issue: '错误率 6.3%',
        suggestion: '开始日期识别需要改进，建议强调日期格式要求',
      },
      {
        priority: 'medium',
        field_name: 'sign_date',
        issue: '错误率 8.0%',
        suggestion: '签订日期格式错误，建议统一YYYY-MM-DD格式',
      },
      {
        priority: 'low',
        field_name: 'tenant_name',
        issue: '错误率 5.1%',
        suggestion: '承租方名称识别基本良好，可考虑添加更多样例',
      },
    ],
  };
};

const loadPromptDetails = async (_promptId: string): Promise<LoadPromptDetailsResult> => {
  return buildMockPromptDetails();
};

export const usePromptDashboardData = () => {
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<PromptDashboardDateRange>([
    dayjs().subtract(30, 'days'),
    dayjs(),
  ]);

  const promptsQuery = useQuery({
    queryKey: ['llm-prompts', 'list', { page_size: 100 }],
    queryFn: async () => {
      try {
        return await llmPromptService.getPrompts({ page_size: 100 });
      } catch (error) {
        logger.error('加载 Prompt 列表失败', error);
        throw error;
      }
    },
  });

  const statisticsQuery = useQuery({
    queryKey: ['llm-prompts', 'statistics'],
    queryFn: async () => {
      try {
        return await llmPromptService.getStatistics();
      } catch (error) {
        logger.error('加载统计数据失败', error);
        throw error;
      }
    },
  });

  const promptDetailsQuery = useQuery({
    queryKey: ['llm-prompts', 'details', selectedPromptId],
    queryFn: async () => {
      if (selectedPromptId == null) {
        return buildMockPromptDetails();
      }

      try {
        return await loadPromptDetails(selectedPromptId);
      } catch (error) {
        logger.error('加载Prompt详情失败', error);
        throw error;
      }
    },
    enabled: selectedPromptId != null,
  });

  const prompts = useMemo<PromptTemplate[]>(
    () => promptsQuery.data?.items ?? [],
    [promptsQuery.data?.items]
  );
  const statistics: PromptStatistics | null = statisticsQuery.data ?? null;
  const promptDetails = promptDetailsQuery.data;
  const performanceData: PerformanceMetrics[] = promptDetails?.performanceData ?? [];
  const fieldErrorRates: FieldErrorRate[] = promptDetails?.fieldErrorRates ?? [];
  const suggestions: OptimizationSuggestion[] = promptDetails?.suggestions ?? [];
  const isInitialLoading =
    promptsQuery.isLoading === true ||
    statisticsQuery.isLoading === true ||
    (selectedPromptId != null && promptDetailsQuery.isLoading === true);
  const isRefreshing =
    promptsQuery.isFetching === true ||
    statisticsQuery.isFetching === true ||
    (selectedPromptId != null && promptDetailsQuery.isFetching === true);
  const hasError =
    promptsQuery.isError === true ||
    statisticsQuery.isError === true ||
    (selectedPromptId != null && promptDetailsQuery.isError === true);
  const errorMessage =
    (promptsQuery.error instanceof Error ? promptsQuery.error.message : null) ??
    (statisticsQuery.error instanceof Error ? statisticsQuery.error.message : null) ??
    (promptDetailsQuery.error instanceof Error ? promptDetailsQuery.error.message : null);

  const handleDateRangeChange = useCallback((value: [Dayjs | null, Dayjs | null] | null) => {
    if (value != null && value[0] != null && value[1] != null) {
      setDateRange([value[0], value[1]]);
      return;
    }
    setDateRange(null);
  }, []);

  const handlePromptChange = useCallback((value: string) => {
    setSelectedPromptId(value);
  }, []);

  const handleRefresh = useCallback(() => {
    const refreshTasks: Array<Promise<unknown>> = [
      promptsQuery.refetch(),
      statisticsQuery.refetch(),
    ];

    if (selectedPromptId != null) {
      refreshTasks.push(promptDetailsQuery.refetch());
    }

    void Promise.all(refreshTasks);
  }, [promptDetailsQuery, promptsQuery, selectedPromptId, statisticsQuery]);

  useEffect(() => {
    if (selectedPromptId == null && prompts.length > 0) {
      const activePrompt = prompts.find(prompt => prompt.status === PromptStatus.ACTIVE);
      const nextPromptId = activePrompt?.id ?? prompts[0]?.id ?? null;
      if (nextPromptId != null) {
        setSelectedPromptId(nextPromptId);
      }
    }
  }, [prompts, selectedPromptId]);

  const selectedPrompt = useMemo(() => {
    return prompts.find(prompt => prompt.id === selectedPromptId);
  }, [prompts, selectedPromptId]);

  const selectedStatusMeta = useMemo(() => {
    if (selectedPrompt == null) {
      return null;
    }
    return getPromptStatusMeta(selectedPrompt.status);
  }, [selectedPrompt]);

  const activePromptCount = useMemo(() => {
    return (
      statistics?.status_distribution.find(item => item.status === PromptStatus.ACTIVE)?.count ?? 0
    );
  }, [statistics]);

  const monitoredFieldCount = fieldErrorRates.length;
  const highRiskFieldCount = useMemo(() => {
    return countHighRiskFields(fieldErrorRates);
  }, [fieldErrorRates]);

  const dateRangeLabel = useMemo(() => getDateRangeLabel(dateRange), [dateRange]);
  const { accuracyTrend, confidenceTrend } = useMemo(
    () => toTrendSeries(performanceData),
    [performanceData]
  );
  const promptOptions = useMemo(() => buildPromptOptions(prompts), [prompts]);

  return {
    prompts,
    statistics,
    selectedPromptId,
    selectedPrompt,
    selectedStatusMeta,
    performanceData,
    fieldErrorRates,
    suggestions,
    dateRange,
    dateRangeLabel,
    promptOptions,
    activePromptCount,
    monitoredFieldCount,
    highRiskFieldCount,
    accuracyTrend,
    confidenceTrend,
    isInitialLoading,
    isRefreshing,
    hasError,
    errorMessage,
    handleRefresh,
    handleDateRangeChange,
    handlePromptChange,
  };
};
