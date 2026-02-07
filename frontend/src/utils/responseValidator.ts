/**
 * API 响应验证工具
 *
 * @module utils/responseValidator
 * @description
 * 使用 Zod 提供运行时 API 响应验证功能。
 * 替代了之前的手动验证逻辑，提供更安全、简洁的类型校验。
 */

import { z } from 'zod';
import type { StandardApiResponse, PaginatedApiResponse, ErrorResponse } from '@/types/apiResponse';

// ==================== Zod Schemas ====================

// 基础响应 Schema
const StandardResponseBaseSchema = z.object({
  success: z.boolean(),
  data: z.unknown().optional(),
  message: z.string().optional(),
  code: z.string().optional(),
  timestamp: z.string().optional(),
});

// 确保 data 在 success=true 时存在
export const StandardResponseSchema = StandardResponseBaseSchema.refine(
  data => !data.success || data.data !== undefined,
  {
    message: 'Successful response must contain data field',
    path: ['data'],
  }
);

// 分页信息 Schema
export const PaginationSchema = z.object({
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
  total_pages: z.number(),
  has_next: z.boolean().optional(),
  has_prev: z.boolean().optional(),
});

// 分页数据 Schema
export const PaginatedDataSchema = z.object({
  items: z.array(z.unknown()),
  pagination: PaginationSchema,
});

// 分页响应 Schema
export const PaginatedResponseSchema = StandardResponseBaseSchema.extend({
  data: PaginatedDataSchema,
}).refine(data => !data.success || data.data !== undefined, {
  message: 'Successful response must contain data field',
  path: ['data'],
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

export interface DetailedValidationResult<T = unknown> {
  valid: boolean;
  data?: T;
  error?: string;
  zodError?: z.ZodError;
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
  data: unknown
): DetailedValidationResult<StandardApiResponse<T>> {
  const result = StandardResponseSchema.safeParse(data);

  if (result.success) {
    return {
      valid: true,
      data: result.data as StandardApiResponse<T>,
    };
  }
  return {
    valid: false,
    zodError: result.error,
    error: result.error.message,
  };
}

/**
 * 验证分页 API 响应格式
 */
export function isPaginatedApiResponse<T = unknown>(
  data: unknown
): data is PaginatedApiResponse<T> {
  return PaginatedResponseSchema.safeParse(data).success;
}

/**
 * 详细验证分页 API 响应
 */
export function validatePaginatedResponse<T = unknown>(
  data: unknown
): DetailedValidationResult<PaginatedApiResponse<T>> {
  const result = PaginatedResponseSchema.safeParse(data);

  if (result.success) {
    return {
      valid: true,
      data: result.data as PaginatedApiResponse<T>,
    };
  }
  return {
    valid: false,
    zodError: result.error,
    error: result.error.message,
  };
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
export function validateErrorResponse(data: unknown): DetailedValidationResult<ErrorResponse> {
  const result = ErrorResponseSchema.safeParse(data);

  if (result.success) {
    return {
      valid: true,
      data: result.data as ErrorResponse,
    };
  }
  return {
    valid: false,
    zodError: result.error,
    error: result.error.message,
  };
}

/**
 * 验证任意 API 响应格式
 */
export function validateApiResponse(data: unknown): {
  valid: boolean;
  type: 'standard' | 'paginated' | 'error' | 'unknown';
  result?: DetailedValidationResult;
} {
  if (isErrorResponse(data))
    return { valid: true, type: 'error', result: validateErrorResponse(data) };
  if (isPaginatedApiResponse(data))
    return { valid: true, type: 'paginated', result: validatePaginatedResponse(data) };
  if (isStandardApiResponse(data))
    return { valid: true, type: 'standard', result: validateStandardResponse(data) };

  return { valid: false, type: 'unknown' };
}

/**
 * 断言 API 响应格式
 */
export function assertApiResponse<T = unknown>(
  data: unknown,
  expectedType: 'standard' | 'paginated' | 'error'
): asserts data is T {
  let result;
  if (expectedType === 'standard') result = StandardResponseSchema.safeParse(data);
  else if (expectedType === 'paginated') result = PaginatedResponseSchema.safeParse(data);
  else if (expectedType === 'error') result = ErrorResponseSchema.safeParse(data);
  else throw new Error(`Unknown expected type: ${expectedType}`);

  if (!result.success) {
    throw new Error(`Invalid API response format for '${expectedType}': ${result.error.message}`);
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
