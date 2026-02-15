import type { ReactNode } from 'react';
import type { Dayjs } from 'dayjs';
import type { OperationLog } from '@/services/systemService';

export type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
export type ResponseTimeTone = 'neutral' | 'success' | 'warning' | 'error';

export type LogJsonValue = string | Record<string, unknown> | unknown[] | null | undefined;

export interface ActionMeta {
  value: string;
  label: string;
  tone: Tone;
  icon: ReactNode;
}

export interface ModuleMeta {
  value: string;
  label: string;
  tone: Tone;
}

export interface StatusFilterOption {
  value: string;
  label: string;
}

export interface LogFilters {
  searchText: string;
  module: string;
  action: string;
  status: string;
  dateRange: [Dayjs, Dayjs] | null;
}

export interface LogListQueryResult {
  items: OperationLog[];
  total: number;
  pages?: number;
}

export interface OperationLogPaginationState {
  current: number;
  pageSize: number;
}
