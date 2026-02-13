/**
 * 统一类型定义导出
 * 为整个前端应用提供一致的类型定义基础
 *
 * @module types
 * @description
 * 此文件整合了所有类型定义，提供统一的导出接口。
 * 使用此文件导入类型可避免循环依赖和路径混乱。
 *
 * @example
 * ```typescript
 * // 推荐方式：从统一入口导入
 * import type { ApiResponse, PaginatedResponse, Asset } from '@/types';
 *
 * // 不推荐：从具体文件导入
 * import type { ApiResponse } from '@/types/api';
 * ```
 */

// ==================== API 响应类型 ====================

export type {
  // 标准响应格式（统一使用 common.ts 中的定义）
  ApiResponse,
  ErrorResponse,

  // 分页响应格式
  PaginatedResponse,

  // Excel 导入导出
  ExcelImportResponse,
  ExcelExportRequest,
  ExcelExportResponse,

  // 备份相关
  BackupInfo,
  BackupListResponse,
} from './api';

export type {
  // 高级 API 响应类型
  StandardApiResponse,
  PaginatedApiResponse,
  DirectResponse,
  ErrorResponse as ApiErrorResponse,

  // 响应提取器
  ExtractResult,
  ResponseDetectionConfig,
  SmartExtractOptions,

  // 错误处理
  ApiErrorType,
  ApiClientError,

  // 重试和缓存
  RetryConfig,
  CacheConfig,

  // 客户端配置
  ApiClientConfig,
} from './apiResponse';

// ==================== 通用类型 ====================

export type {
  // 分页和查询
  PaginationConfig,
  SorterConfig,
  FilterConfig,
  TableConfig,
  QueryParams,

  // 工具类型
  KeyValue,
  Optional,
  DeepPartial,
  RequireAtLeastOne,

  // 函数类型
  EventHandler,
  AsyncEventHandler,

  // 状态和结果
  LoadingState,
  OperationResult,
  ValidationResult,
  AsyncState,

  // 其他工具类型
  SortDirection,
  Filters,
  CrudOperation,
  Permission,
  Theme,
  Language,
  Unit,
  Size,
  Position,
  Color,
  IconType,
  CustomEventDetail,
  Callback,
  CallbackWithParam,
  Options,

  // 常用联合类型
  StringOrNumber,
  StringOrNumberOrUndefined,
  StringOrUndefined,
  NumberOrUndefined,
  BooleanOrUndefined,
  Nullish,
  NonNullish,
  ID,
  Timestamp,
  Percentage,
  Dictionary,

  // 任务和历史
  TaskStatus,
  ImportExportHistory,
  TaskStatusResponse,

  // HTTP 和错误
  HttpStatusCode,
  AppError,
  FileInfo,
} from './common';

// ==================== 业务实体类型 ====================

export type {
  // 认证和用户
  LoginFormData,
  LoginCredentials,
  User,
  Role,
  // Permission, // Duplicate - exported from common
  // Organization, // Duplicate - exported from organization
  AuthState,
  AuthResponse,
  CookieAuthResponse,
  UserActivity,
} from './auth';

export type {
  // 资产相关
  Asset,
  // AssetListItem, // Does not exist
  AssetFormData,
  // AssetAreaSummary, // Does not exist (use AssetSummary)
  // AssetFilters, // Does not exist
} from './asset';

export type {
  // 权属方相关
  Ownership,
  // OwnershipListItem, // Does not exist
  OwnershipFormData,
} from './ownership';

export type {
  // 项目相关
  Project,
  // ProjectListItem, // Does not exist
  // ProjectFormData, // Does not exist
} from './project';

// 组织相关类型已从 auth 模块导出，避免重复导出

export type {
  // 租赁合同相关
  RentContract,
  // RentContractListItem, // Does not exist
  RentContractFormData,
  // ContractStatus, // Does not exist
  // ContractTerm, // Does not exist (use ContractType)
} from './rentContract';

export type {
  // 通知相关
  Notification,
  // NotificationListItem, // Does not exist
  // NotificationPreferences, // Does not exist
} from './notification';

export type {
  // 字典相关
  EnumFieldValue,
  EnumFieldType,
  EnumFieldWithType,
  DictionaryType,
  DictionaryField,
  DictionaryOption,
  DictionaryTypeInfo,
  SystemDictionary,
  DictionaryServiceResult,
  DictionaryQueryParams,
} from './dictionary';

// 枚举字段相关类型暂无导出（类型不存在）

export type {
  // 分析相关
  AnalyticsData,
  ChartDataPoint,
  // MetricValue, // Does not exist
  // TrendData, // Does not exist
} from './analytics';

// PDF 导入相关类型暂无导出（类型不存在）

// ==================== 类型守卫 ====================

// 类型守卫从 apiResponse.ts 和 guards.ts 导出

// 重新导出类型守卫函数
export {
  isStandardApiResponse,
  isPaginatedResponse,
  isErrorResponse,
  isDirectResponse,
} from './apiResponse';

// 重新导出增强类型守卫和验证工具
export {
  // 基础类型守卫
  isString,
  isNumber,
  isBoolean,
  isFunction,
  isObject,
  isArray,
  isNull,
  isUndefined,
  isNullish,
  isDate,
  isEmpty,

  // 高级类型守卫
  hasProperty,
  hasProperties,
  isPropertyOfType,
  isValidId,
  isValidDateString,
  isValidUrl,
  isValidEmail,
  isValidPhoneNumber,

  // API 响应类型守卫
  isSuccessResponse,
  isErrorResponse as isApiErrorResponse,
  isPaginatedResponse as isPaginatedApiResponse,
  getErrorMessage,

  // 数组和集合
  isNotEmptyArray,
  isNumberArray,
  isStringArray,
  isObjectArray,
  isUniqueArray,

  // 表单和验证
  isValidFormData,
  hasValidationErrors,
  isFile,
  isFileList,

  // 范围和边界
  isInRange,
  isLengthInRange,
  isPositive,
  isNegative,
  isNonNegative,

  // 断言函数
  assert,
  assertNotNullish,
  assertTrue,

  // 工具函数
  filterNullish,
  filterDuplicates,
  partition,

  // 工具集
  TypeGuards,
} from './guards';

// ==================== API 响应验证器 ====================

// 重新导出 API 响应验证器
export {
  // 类型守卫
  // isStandardApiResponse, // Duplicate - exported from apiResponse
  isPaginatedApiResponse as isPaginatedApiValidationResponse,
  isErrorResponse as isApiValidationErrorResponse,

  // 详细验证
  validateStandardResponse,
  validatePaginatedResponse,
  validateErrorResponse,

  // 通用工具
  validateApiResponse,
  assertApiResponse,

  // 验证器工具集
  ResponseValidator,
} from '@/utils/responseValidator';

// ==================== 全局类型增强 ====================

/// <reference path="./global.d.ts" />

// ==================== 常用类型别名 ====================

/**
 * 实体 ID 类型
 */
export type EntityId = string;

/**
 * 可选的实体 ID
 */
export type OptionalEntityId = EntityId | null | undefined;

/**
 * 时间范围类型
 */
export interface DateRange {
  start: Date | string;
  end: Date | string;
}

/**
 * 树形节点类型（用于层级数据）
 */
export interface TreeNode<T = unknown> {
  id: string | number;
  title: string;
  children?: TreeNode<T>[];
  data?: T;
  key?: string | number;
  isLeaf?: boolean;
}

/**
 * 选择项类型（用于下拉框等）
 */
export interface SelectOption<T = unknown> {
  label: string;
  value: string | number;
  disabled?: boolean;
  data?: T;
}

/**
 * 表格列类型
 */
export interface TableColumn<T = unknown> {
  key: string;
  title: string;
  dataIndex?: keyof T | string;
  width?: number | string;
  align?: 'left' | 'center' | 'right';
  fixed?: 'left' | 'right';
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: unknown, record: T, index: number) => React.ReactNode;
}

/**
 * 表单字段类型
 */
export interface FormField {
  name: string | string[];
  label?: string;
  required?: boolean;
  rules?: unknown[];
  initialValue?: unknown;
}

/**
 * 模态框属性类型
 */
export interface ModalProps {
  visible: boolean;
  title: string;
  width?: number | string;
  onOk: () => void;
  onCancel: () => void;
  okText?: string;
  cancelText?: string;
  confirmLoading?: boolean;
}

/**
 * Toast 消息类型
 */
export interface ToastMessage {
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
  description?: string;
  duration?: number;
}

// ==================== 常量类型 ====================

/**
 * HTTP 方法类型
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

/**
 * 内容类型
 */
export type ContentType =
  | 'application/json'
  | 'application/x-www-form-urlencoded'
  | 'multipart/form-data'
  | 'text/plain'
  | 'text/html';

/**
 * 环境类型
 */
export type Environment = 'development' | 'staging' | 'production';

/**
 * 日志级别
 */
export enum LogLevel {
  TRACE = 'trace',
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
  FATAL = 'fatal',
}

// ==================== 工具类型（高级） ====================

/**
 * 使指定键变为只读
 */
export type ReadonlyKeys<T, K extends keyof T> = Omit<T, K> & {
  readonly [P in K]: T[P];
};

/**
 * 使指定键变为必需
 */
export type RequireKeys<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;

/**
 * 深度只读
 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

/**
 * 提取函数的返回类型
 */
export type ReturnType<T extends (...args: unknown[]) => unknown> = T extends (
  ...args: unknown[]
) => infer R
  ? R
  : unknown;

/**
 * 提取 Promise 的值类型
 */
export type Awaited<T> = T extends Promise<infer U> ? U : T;

/**
 * 排除 null 和 undefined
 */
export type NonNullable<T> = T extends null | undefined ? never : T;

/**
 * 数组或单个值
 */
export type OneOrMany<T> = T | T[];

/**
 * 元组转联合
 */
export type TupleToUnion<T extends unknown[]> = T[number];

/**
 * 获取对象的所有键
 */
export type Keys<T> = keyof T;

/**
 * 获取对象的所有值类型
 */
export type Values<T> = T[keyof T];

// ==================== 默认导出 ====================

/**
 * 类型模块默认导出
 * 提供类型信息的元数据
 */
export const TypeInfo = {
  version: '1.0.0',
  description: '统一类型定义模块',
} as const;
