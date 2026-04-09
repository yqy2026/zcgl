import dayjs from 'dayjs';
import type { LogStatistics, OperationLog } from '@/services/systemService';
import type {
  LogFilters,
  LogJsonValue,
  OperationLogPaginationState,
  ResponseTimeTone,
  Tone,
} from './types';

interface OperationLogRequestParams {
  page: number;
  page_size: number;
  module?: string;
  action?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  response_status?: string;
}

const normalizeActionFilter = (action: string): string => {
  if (action === 'view') {
    return 'read';
  }
  return action;
};

interface StatusMeta {
  label: string;
  tone: Tone;
}

export const parseJsonValue = (value: LogJsonValue): LogJsonValue => {
  if (typeof value !== 'string') {
    return value;
  }
  const trimmed = value.trim();
  if (trimmed === '') {
    return value;
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (parsed == null) {
      return value;
    }
    if (Array.isArray(parsed) || typeof parsed === 'object') {
      return parsed as Record<string, unknown> | unknown[];
    }
    return value;
  } catch {
    return value;
  }
};

export const formatJsonValue = (value: unknown): string => {
  if (value == null) {
    return '-';
  }
  if (typeof value === 'string') {
    const parsed = parseJsonValue(value);
    if (parsed !== value) {
      return JSON.stringify(parsed, null, 2);
    }
    return value;
  }
  return JSON.stringify(value, null, 2);
};

export const normalizeOperationLogs = (items: OperationLog[]): OperationLog[] => {
  return items.map(item => ({
    ...item,
    request_params: parseJsonValue(item.request_params),
    request_body: parseJsonValue(item.request_body),
    details: parseJsonValue(item.details),
    user_name: item.user_name ?? item.username ?? '-',
    module_name: item.module_name ?? item.module,
    action_name: item.action_name ?? item.action,
  }));
};

export const buildOperationLogRequestParams = (
  filters: LogFilters,
  pagination: OperationLogPaginationState
): OperationLogRequestParams => {
  const trimmedSearch = filters.searchText.trim();

  return {
    page: pagination.current,
    page_size: pagination.pageSize,
    module: filters.module === '' ? undefined : filters.module,
    action: filters.action === '' ? undefined : normalizeActionFilter(filters.action),
    start_date:
      filters.dateRange != null && filters.dateRange[0] != null
        ? filters.dateRange[0].format('YYYY-MM-DD')
        : undefined,
    end_date:
      filters.dateRange != null && filters.dateRange[1] != null
        ? filters.dateRange[1].format('YYYY-MM-DD')
        : undefined,
    search: trimmedSearch === '' ? undefined : trimmedSearch,
    response_status: filters.status === '' ? undefined : filters.status,
  };
};

export const countActiveLogFilters = (filters: LogFilters): number => {
  let count = 0;
  if (filters.module !== '') {
    count += 1;
  }
  if (filters.action !== '') {
    count += 1;
  }
  if (filters.status !== '') {
    count += 1;
  }
  if (filters.dateRange != null) {
    count += 1;
  }
  if (filters.searchText.trim() !== '') {
    count += 1;
  }
  return count;
};

export const getResponseTimeTone = (time?: number | null): ResponseTimeTone => {
  if (typeof time !== 'number') {
    return 'neutral';
  }
  if (time > 1000) {
    return 'error';
  }
  if (time > 500) {
    return 'warning';
  }
  return 'success';
};

export const getResponseTimeLabel = (time?: number | null): string => {
  if (typeof time !== 'number') {
    return '';
  }
  if (time > 1000) {
    return '慢';
  }
  if (time > 500) {
    return '中';
  }
  return '快';
};

export const getStatusMeta = (status?: number | null): StatusMeta => {
  if (status == null) {
    return { label: '未知', tone: 'neutral' };
  }
  if (status >= 200 && status < 300) {
    return { label: '成功', tone: 'success' };
  }
  if (status >= 400 && status < 500) {
    return { label: '客户端错误', tone: 'warning' };
  }
  if (status >= 500) {
    return { label: '服务器错误', tone: 'error' };
  }
  return { label: '未知', tone: 'neutral' };
};

export const deriveOperationLogStatistics = (
  logs: OperationLog[],
  total: number
): LogStatistics => {
  const responseTimes = logs
    .map(log => log.response_time)
    .filter((time): time is number => typeof time === 'number');
  const avgResponseTime =
    responseTimes.length > 0
      ? Math.round(responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length)
      : 0;

  return {
    total,
    today: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'day')).length,
    this_week: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'week')).length,
    this_month: logs.filter(log => dayjs(log.created_at).isSame(dayjs(), 'month')).length,
    by_action: {},
    by_module: {},
    error_count: logs.filter(log => (log.response_status ?? 0) >= 400).length,
    avg_response_time: avgResponseTime,
  };
};
