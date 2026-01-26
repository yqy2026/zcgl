/**
 * API 响应验证工具
 *
 * @module utils/responseValidator
 * @description
 * 使用 Zod 提供运行时 API 响应验证功能。
 * 替代了之前的手动验证逻辑，提供更安全、简洁的类型校验。
 */

import { z } from 'zod';
import type {
  StandardApiResponse,
  PaginatedApiResponse,
  ErrorResponse,
} from '../types/apiResponse';

// ==================== Zod Schemas ====================

// 基础响应 Schema
export const StandardResponseSchema = z.object({
  success: z.boolean(),
  data: z.unknown().optional(),
  message: z.string().optional(),
  code: z.string().optional(),
  timestamp: z.string().optional(),
}).refine((data) => {
  // 成功响应必须包含 data 字段
  if (data.success && data.data === undefined) return false;
  return true;
}, {
  message: "Successful response must contain data field",
  path: ["data"]
});

// 分页信息 Schema
export const PaginationSchema = z.object({
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
  totalPages: z.number(),
  hasNext: z.boolean().optional(),
  hasPrev: z.boolean().optional(),
});

// 分页数据 Schema
export const PaginatedDataSchema = z.object({
  items: z.array(z.unknown()),
  pagination: PaginationSchema,
});

// 分页响应 Schema
export const PaginatedResponseSchema = StandardResponseSchema.extend({
  data: PaginatedDataSchema,
});

// 错误详情 Schema
export const ErrorDetailSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
  timestamp: z.string().optional(),
  requestId: z.string().optional(),
});

// 错误响应 Schema
export const ErrorResponseSchema = z.object({
  success: z.literal(false),
  error: ErrorDetailSchema,
});

// ==================== Validation Results ====================

export interface ValidationResult<T = unknown> {
  valid: boolean;
  data?: T;
  error?: string;
  path?: string;
}

export interface DetailedValidationResult<T = unknown> extends ValidationResult<T> {
  warnings: string[];
  missingFields: string[];
  extraFields: string[];
  typeErrors: Array<{ field: string; expected: string; actual: string }>;
  zodError?: z.ZodError;
}

/**
 * 将 Zod 错误转换为详细验证结果
 */
function mapZodErrorToDetailedResult<T>(zodError: z.ZodError, data: unknown): DetailedValidationResult<T> {
  const result: DetailedValidationResult<T> = {
    valid: false,
    warnings: [],
    missingFields: [],
    extraFields: [],
    typeErrors: [],
    zodError,
  };

  zodError.issues.forEach((issue) => {
    const path = issue.path.join('.');

    if (issue.code === 'invalid_type') {
      if (issue.received === 'undefined') {
        result.missingFields.push(path);
      } else {
        result.typeErrors.push({
          field: path,
          expected: issue.expected,
          actual: issue.received,
        });
      }
    } else if (issue.code === 'unrecognized_keys') {
      result.extraFields.push(...issue.keys.map(k => path ? `${path}.${k}` : k));
      result.warnings.push(`Found extra fields: ${issue.keys.join(', ')}`);
    } else {
      result.typeErrors.push({
        field: path,
        expected: 'valid',
        actual: issue.message,
      });
    }
  });

  return result;
}

// ==================== Validation Functions ====================

/**
 * 验证标准 API 响应格式
 */
export function isStandardApiResponse<T = unknown>(data: unknown): data is StandardApiResponse<T> {
  return StandardResponseSchema.safeParse(data).success;
}

/**
 * 详细验证标准 API 响应
 */
export function validateStandardResponse<T = unknown>(
  data: unknown,
  strict: boolean = false
): DetailedValidationResult<StandardApiResponse<T>> {
  const schema = strict ? StandardResponseSchema.strict() : StandardResponseSchema;
  const result = schema.safeParse(data);

  if (result.success) {
    return {
      valid: true,
      data: result.data as StandardApiResponse<T>,
      warnings: [],
      missingFields: [],
      extraFields: [],
      typeErrors: []
    };
  }
  return mapZodErrorToDetailedResult(result.error, data);
}

/**
 * 验证分页 API 响应格式
 */
export function isPaginatedApiResponse<T = unknown>(data: unknown): data is PaginatedApiResponse<T> {
  return PaginatedResponseSchema.safeParse(data).success;
}

/**
 * 详细验证分页 API 响应
 */
export function validatePaginatedResponse<T = unknown>(
  data: unknown,
  strict: boolean = false
): DetailedValidationResult<PaginatedApiResponse<T>> {
  const schema = strict ? PaginatedResponseSchema.strict() : PaginatedResponseSchema;
  const result = schema.safeParse(data);

  if (result.success) {
    return {
      valid: true,
      data: result.data as PaginatedApiResponse<T>,
      warnings: [],
      missingFields: [],
      extraFields: [],
      typeErrors: []
    };
  }
  return mapZodErrorToDetailedResult(result.error, data);
}

/**
 * 验证错误响应格式
 */
export function isErrorResponse(data: unknown): data is ErrorResponse {
  return ErrorResponseSchema.safeParse(data).success;
}

/**
 * 详细验证错误响应
 */
export function validateErrorResponse(
  data: unknown,
  strict: boolean = false
): DetailedValidationResult<ErrorResponse> {
  const schema = strict ? ErrorResponseSchema.strict() : ErrorResponseSchema;
  const result = schema.safeParse(data);

  if (result.success) {
    return {
      valid: true,
      data: result.data as ErrorResponse,
      warnings: [],
      missingFields: [],
      extraFields: [],
      typeErrors: []
    };
  }
  return mapZodErrorToDetailedResult(result.error, data);
}

/**
 * 验证任意 API 响应格式
 */
export function validateApiResponse(data: unknown): {
  valid: boolean;
  type: 'standard' | 'paginated' | 'error' | 'unknown';
  result?: DetailedValidationResult;
} {
  if (isErrorResponse(data)) return { valid: true, type: 'error', result: validateErrorResponse(data) };
  if (isPaginatedApiResponse(data)) return { valid: true, type: 'paginated', result: validatePaginatedResponse(data) };
  if (isStandardApiResponse(data)) return { valid: true, type: 'standard', result: validateStandardResponse(data) };

  return { valid: false, type: 'unknown' };
}

/**
 * 断言 API 响应格式
 */
export function assertApiResponse<T = unknown>(
  data: unknown,
  expectedType: 'standard' | 'paginated' | 'error'
): asserts data is T {
  let isValid = false;

  if (expectedType === 'standard') isValid = isStandardApiResponse(data);
  else if (expectedType === 'paginated') isValid = isPaginatedApiResponse(data);
  else if (expectedType === 'error') isValid = isErrorResponse(data);

  if (!isValid) {
    throw new Error(`无效的 API 响应格式或类型不匹配。期望 '${expectedType}'。`);
  }
}

export const ResponseValidator = {
  isStandardApiResponse,
  isPaginatedApiResponse,
  isErrorResponse,
  validateStandardResponse,
  validatePaginatedResponse,
  validateErrorResponse,
  validateApiResponse,
  assertApiResponse,
} as const;
