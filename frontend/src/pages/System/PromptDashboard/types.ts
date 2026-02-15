import type { ReactNode } from 'react';
import type { Dayjs } from 'dayjs';

export interface PerformanceMetrics {
  date: string;
  accuracy: number;
  confidence: number;
  extraction_count: number;
  corrected_count: number;
}

export interface FieldErrorRate {
  field_name: string;
  error_count: number;
  total_count: number;
  error_rate: number;
}

export interface OptimizationSuggestion {
  priority: 'high' | 'medium' | 'low';
  field_name: string;
  issue: string;
  suggestion: string;
}

export type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
export type MetricTone = Extract<Tone, 'success' | 'warning' | 'error'>;

export interface PromptStatusMeta {
  label: string;
  hint: string;
  tone: Tone;
  icon: ReactNode;
}

export interface SuggestionPriorityMeta {
  label: string;
  hint: string;
  tone: Tone;
  icon: ReactNode;
  alertType: 'error' | 'warning' | 'info';
}

export type PromptDashboardDateRange = [Dayjs, Dayjs] | null;
