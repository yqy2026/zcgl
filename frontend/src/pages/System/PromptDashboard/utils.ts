import { PromptStatus } from '@/types/llmPrompt';
import type { Dayjs } from 'dayjs';
import { PRIORITY_META_MAP, PROMPT_STATUS_META_MAP } from './constants';
import type {
  MetricTone,
  OptimizationSuggestion,
  PerformanceMetrics,
  PromptStatusMeta,
  SuggestionPriorityMeta,
} from './types';

export const getAccuracyTone = (value: number): MetricTone => {
  if (value >= 0.85) {
    return 'success';
  }
  if (value >= 0.75) {
    return 'warning';
  }
  return 'error';
};

export const getConfidenceTone = (value: number): MetricTone => {
  if (value >= 0.8) {
    return 'success';
  }
  if (value >= 0.7) {
    return 'warning';
  }
  return 'error';
};

export const getErrorRateTone = (value: number): MetricTone => {
  if (value > 0.08) {
    return 'error';
  }
  if (value > 0.05) {
    return 'warning';
  }
  return 'success';
};

export const getToneColor = (tone: MetricTone): string => {
  if (tone === 'success') {
    return 'var(--color-success)';
  }
  if (tone === 'warning') {
    return 'var(--color-warning)';
  }
  return 'var(--color-error)';
};

export const getPriorityConfig = (
  priority: OptimizationSuggestion['priority']
): SuggestionPriorityMeta => {
  return PRIORITY_META_MAP[priority];
};

export const getPromptStatusMeta = (status: PromptStatus): PromptStatusMeta => {
  return PROMPT_STATUS_META_MAP[status];
};

export const normalizeVersion = (version: string): string => {
  if (version.toLowerCase().startsWith('v')) {
    return version;
  }
  return `v${version}`;
};

export const calculateTrend = (data: number[]): 'up' | 'down' | 'stable' => {
  if (data.length < 2) {
    return 'stable';
  }
  const first = data[0];
  const last = data[data.length - 1];
  const change = ((last - first) / first) * 100;
  if (change > 2) {
    return 'up';
  }
  if (change < -2) {
    return 'down';
  }
  return 'stable';
};

export const buildPromptOptions = (
  prompts: Array<{ id: string; name: string; version: string }>
) => {
  return prompts.map(prompt => ({
    label: `${prompt.name} (${normalizeVersion(prompt.version)})`,
    value: prompt.id,
  }));
};

export const getDateRangeLabel = (dateRange: [Dayjs, Dayjs] | null): string => {
  if (dateRange == null) {
    return '全部时间';
  }
  return `${dateRange[0].format('YYYY-MM-DD')} ~ ${dateRange[1].format('YYYY-MM-DD')}`;
};

export const countHighRiskFields = (fieldErrorRates: Array<{ error_rate: number }>): number => {
  return fieldErrorRates.filter(item => getErrorRateTone(item.error_rate) === 'error').length;
};

export const toTrendSeries = (performanceData: PerformanceMetrics[]) => {
  return {
    accuracyTrend: calculateTrend(performanceData.map(item => item.accuracy)),
    confidenceTrend: calculateTrend(performanceData.map(item => item.confidence)),
  };
};
