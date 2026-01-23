/**
 * @deprecated API 响应类型已迁移至 @/types/apiResponse
 * 请使用 StandardApiResponse、PaginatedApiResponse 等标准类型
 *
 * @module types/common
 * @description
 * 通用类型定义，用于替换 any 类型，提高类型安全性。
 * API 响应类型已迁移至 @/types/apiResponse，此处保留以向后兼容。
 */

// ==================== API 响应类型（已废弃，保留向后兼容）====================

/**
 * @deprecated 使用 @/types/apiResponse 中的 StandardApiResponse 代替
 */
export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  message?: string;
  timestamp?: string;
}

/**
 * @deprecated 使用 @/types/apiResponse 中的 ErrorResponse 代替
 */
export interface ApiErrorResponse {
  success: false;
  error: string;
  details?: string;
  code?: string;
  timestamp?: string;
}

/**
 * @deprecated 使用 @/types/apiResponse 中的 StandardApiResponse 代替
 */
export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

// 分页相关类型
export interface PaginationConfig {
  current: number;
  page_size: number;
  total: number;
  showSizeChanger?: boolean;
  showQuickJumper?: boolean;
  showTotal?: (total: number, range: [number, number]) => string;
}

export interface SorterConfig {
  field: string;
  order: 'ascend' | 'descend';
}

export interface FilterConfig {
  [key: string]: string | number | boolean | undefined;
}

// 表格配置类型
export interface TableConfig {
  pagination: PaginationConfig;
  filters: FilterConfig;
  sorter: SorterConfig;
}

// 键值对类型
export type KeyValue<T> = Record<string, T>;

// 可选类型
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

// 深度可选类型
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// 选择性必需类型
export type RequireAtLeastOne<T, Keys extends keyof T = keyof T> = Pick<
  T,
  Exclude<keyof T, Keys>
> & { [K in Keys]: T[K] } & Partial<T>;

// 函数类型
export type EventHandler<T = Event> = (event: T) => void;
export type AsyncEventHandler<T = void> = () => Promise<T>;

// 错误类型
export interface AppError {
  code: string;
  message: string;
  details?: unknown;
  stack?: string;
  timestamp?: string;
}

// HTTP状态码类型
export type HttpStatusCode =
  | 200
  | 201
  | 204
  | 301
  | 302
  | 304
  | 400
  | 401
  | 403
  | 404
  | 405
  | 409
  | 422
  | 429
  | 500
  | 502
  | 503
  | 504;

// 文件类型
export interface FileInfo {
  name: string;
  size: number;
  type: string;
  lastModified: number;
  content?: ArrayBuffer | string;
}

// 加载状态类型
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// 操作结果类型
export interface OperationResult<T = void> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp?: string;
}

// 验证结果类型
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings?: string[];
}

// 排序类型
export type SortDirection = 'asc' | 'desc' | 'ascend' | 'descend';

// 查询参数类型
export interface QueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  sortBy?: string;
  sortOrder?: SortDirection;
  [key: string]: unknown;
}

// 通用过滤器类型（替代Record<string, any>）
export type Filters = Record<string, string | number | boolean | undefined | null>;

/**
 * @deprecated 使用 @/types/apiResponse 中的 PaginatedApiResponse 代替
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  totalPages: number;
}

// 任务状态类型
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

// 导入/导出历史记录类型
export interface ImportExportHistory {
  id: string;
  filename: string;
  status: TaskStatus;
  progress: number;
  totalRecords: number;
  processedRecords: number;
  successRecords: number;
  errorRecords: number;
  createdAt: string;
  completedAt?: string;
  errorMessage?: string;
  createdBy?: string;
}

// 导入/导出状态响应类型
export interface TaskStatusResponse {
  taskId: string;
  status: TaskStatus;
  progress: number;
  totalRecords?: number;
  processedRecords?: number;
  successRecords?: number;
  errorRecords?: number;
  result?: unknown;
  error?: string;
}

// CRUD操作类型
export type CrudOperation = 'create' | 'read' | 'update' | 'delete';

// 权限类型
export type Permission = string | string[];

// 主题类型
export type Theme = 'light' | 'dark' | 'auto';

// 语言类型
export type Language = 'zh-CN' | 'en-US';

// 单位类型
export type Unit = 'px' | '%' | 'em' | 'rem' | 'vh' | 'vw';

// 尺寸类型
export interface Size {
  width?: number | string;
  height?: number | string;
}

// 位置类型
export interface Position {
  x?: number;
  y?: number;
}

// 颜色类型
export type Color = string;

// 图标类型
export type IconType = string | React.ComponentType<Record<string, unknown>>;

// Express类型已在前端中不使用，注释掉以避免导入错误
// export type { Response } from "express";
// export type { Request } from "express";

// 事件相关类型
export interface CustomEventDetail<T = Record<string, unknown>> {
  detail: T;
}

// 通用回调类型
export type Callback<T = void> = () => T;
export type CallbackWithParam<T, P> = (param: P) => T;

// 异步操作状态
export interface AsyncState<T, E = string> {
  data?: T;
  loading: boolean;
  error?: E;
}

// 选项类型
export type Options<T> = {
  [K in keyof T]: T[K];
};

// 常用联合类型
export type StringOrNumber = string | number;
export type StringOrNumberOrUndefined = string | number | undefined;
export type StringOrUndefined = string | undefined;
export type NumberOrUndefined = number | undefined;
export type BooleanOrUndefined = boolean | undefined;

// 空值检查类型
export type Nullish = null | undefined;

// 严格非空类型
export type NonNullish<T> = T extends null | undefined ? never : T;

// ID类型
export type ID = string | number;

// 时间戳类型
export type Timestamp = number | string | Date;

// 百分比类型
export type Percentage = number; // 0-100之间的数字

// 通用字典类型
export type Dictionary<T> = Record<string, T>;

// 日志级别类型
export enum LogLevel {
  TRACE = 'trace',
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
  FATAL = 'fatal',
}
