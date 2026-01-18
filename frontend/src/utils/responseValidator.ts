/**
 * API 响应验证工具
 *
 * @module utils/responseValidator
 * @description
 * 提供运行时 API 响应验证功能，确保后端返回的数据符合预期的格式。
 * 与 TypeScript 类型系统配合使用，提供完整的类型安全保障。
 *
 * @example
 * ```typescript
 * import { validateStandardResponse } from '@/utils/responseValidator';
 *
 * const response = await fetch('/api/users');
 * const data = await response.json();
 *
 * if (validateStandardResponse(data)) {
 *   // TypeScript 现在知道 data.success 是 true，data.data 存在
 *   console.log(data.data);
 * }
 * ```
 */

import type {
  StandardApiResponse,
  PaginatedApiResponse,
  ErrorResponse,
} from '../types/apiResponse';

// ==================== 验证结果类型 ====================

/**
 * 验证结果
 */
export interface ValidationResult<T = unknown> {
  valid: boolean;
  data?: T;
  error?: string;
  path?: string;
}

/**
 * 详细验证结果
 */
export interface DetailedValidationResult<T = unknown> extends ValidationResult<T> {
  warnings: string[];
  missingFields: string[];
  extraFields: string[];
  typeErrors: Array<{ field: string; expected: string; actual: string }>;
}

// ==================== 标准响应验证 ====================

/**
 * 验证标准 API 响应格式
 *
 * @param data - 待验证的数据
 * @returns 类型守卫，如果验证通过则返回 true
 */
export function isStandardApiResponse<T = unknown>(data: unknown): data is StandardApiResponse<T> {
  if (data == null || typeof data !== 'object') {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // 检查必需字段
  if (typeof obj.success !== 'boolean') {
    return false;
  }

  // 成功响应必须有 data 字段
  if (obj.success === true && !('data' in obj)) {
    return false;
  }

  // 失败响应建议有错误信息（但不强制）
  if (obj.success === false && !('message' in obj) && !('code' in obj)) {
    // 可以有警告，但不阻止验证
  }

  return true;
}

/**
 * 详细验证标准 API 响应
 *
 * @param data - 待验证的数据
 * @param strict - 是否启用严格模式（额外字段会报警告）
 * @returns 详细验证结果
 */
export function validateStandardResponse<T = unknown>(
  data: unknown,
  strict: boolean = false
): DetailedValidationResult<StandardApiResponse<T>> {
  const result: DetailedValidationResult<StandardApiResponse<T>> = {
    valid: false,
    warnings: [],
    missingFields: [],
    extraFields: [],
    typeErrors: [],
  };

  // 基础类型检查
  if (data == null || typeof data !== 'object') {
    result.error = '响应必须是对象类型';
    return result;
  }

  const obj = data as Record<string, unknown>;

  // 检查 success 字段
  if (typeof obj.success !== 'boolean') {
    result.typeErrors.push({
      field: 'success',
      expected: 'boolean',
      actual: typeof obj.success,
    });
    result.missingFields.push('success');
  }

  // 检查 data 字段（成功响应）
  if (obj.success === true) {
    if (!('data' in obj)) {
      result.missingFields.push('data');
    }
  }

  // 检查 message 和 code 字段（可选）
  if ('message' in obj && typeof obj.message !== 'string' && typeof obj.message !== 'undefined') {
    result.typeErrors.push({
      field: 'message',
      expected: 'string | undefined',
      actual: typeof obj.message,
    });
  }

  if ('code' in obj && typeof obj.code !== 'string' && typeof obj.code !== 'undefined') {
    result.typeErrors.push({
      field: 'code',
      expected: 'string | undefined',
      actual: typeof obj.code,
    });
  }

  // 检查 timestamp 字段（可选）
  if (
    'timestamp' in obj &&
    typeof obj.timestamp !== 'string' &&
    typeof obj.timestamp !== 'undefined'
  ) {
    result.typeErrors.push({
      field: 'timestamp',
      expected: 'string | undefined',
      actual: typeof obj.timestamp,
    });
  }

  // 严格模式：检查额外字段
  if (strict) {
    const allowedFields = ['success', 'data', 'message', 'code', 'timestamp'];
    const extraFields = Object.keys(obj).filter(key => !allowedFields.includes(key));
    if (extraFields.length > 0) {
      result.extraFields.push(...extraFields);
      result.warnings.push(`发现额外字段: ${extraFields.join(', ')}`);
    }
  }

  // 判断是否验证通过
  result.valid = result.typeErrors.length === 0 && result.missingFields.length === 0;

  if (result.valid) {
    result.data = data as StandardApiResponse<T>;
  }

  return result;
}

// ==================== 分页响应验证 ====================

/**
 * 验证分页 API 响应格式
 *
 * @param data - 待验证的数据
 * @returns 类型守卫，如果验证通过则返回 true
 */
export function isPaginatedApiResponse<T = unknown>(
  data: unknown
): data is PaginatedApiResponse<T> {
  // 首先必须是标准响应
  if (!isStandardApiResponse(data)) {
    return false;
  }

  const obj = data as StandardApiResponse<unknown>;

  // 成功响应必须有嵌套的 data 对象
  if (obj.data == null || typeof obj.data !== 'object') {
    return false;
  }

  const nestedData = obj.data as Record<string, unknown>;

  // 必须有 items 和 pagination 字段
  if (!('items' in nestedData) || !Array.isArray(nestedData.items)) {
    return false;
  }

  if (!('pagination' in nestedData) || typeof nestedData.pagination !== 'object') {
    return false;
  }

  const pagination = nestedData.pagination as Record<string, unknown>;

  // pagination 必须有特定字段
  const requiredPaginationFields = ['page', 'pageSize', 'total', 'totalPages'];
  for (const field of requiredPaginationFields) {
    if (!(field in pagination)) {
      return false;
    }
  }

  return true;
}

/**
 * 详细验证分页 API 响应
 */
export function validatePaginatedResponse<T = unknown>(
  data: unknown,
  strict: boolean = false
): DetailedValidationResult<PaginatedApiResponse<T>> {
  const result: DetailedValidationResult<PaginatedApiResponse<T>> = {
    valid: false,
    warnings: [],
    missingFields: [],
    extraFields: [],
    typeErrors: [],
  };

  // 首先验证标准响应格式
  const standardResult = validateStandardResponse(data, strict);
  if (!standardResult.valid) {
    return result as DetailedValidationResult<PaginatedApiResponse<T>>;
  }

  const obj = data as StandardApiResponse<unknown>;

  // 检查 data 是否为对象
  if (obj.data == null || typeof obj.data !== 'object') {
    result.missingFields.push('data (object)');
    return result;
  }

  const nestedData = obj.data as Record<string, unknown>;

  // 检查 items 字段
  if (!('items' in nestedData)) {
    result.missingFields.push('data.items');
  } else if (!Array.isArray(nestedData.items)) {
    result.typeErrors.push({
      field: 'data.items',
      expected: 'array',
      actual: typeof nestedData.items,
    });
  }

  // 检查 pagination 字段
  if (!('pagination' in nestedData)) {
    result.missingFields.push('data.pagination');
  } else if (typeof nestedData.pagination !== 'object') {
    result.typeErrors.push({
      field: 'data.pagination',
      expected: 'object',
      actual: typeof nestedData.pagination,
    });
  } else {
    // 验证 pagination 子字段
    const pagination = nestedData.pagination as Record<string, unknown>;
    const requiredFields = ['page', 'pageSize', 'total', 'totalPages'];

    for (const field of requiredFields) {
      if (!(field in pagination)) {
        result.missingFields.push(`data.pagination.${field}`);
      } else if (
        field === 'page' ||
        field === 'pageSize' ||
        field === 'total' ||
        field === 'totalPages'
      ) {
        if (typeof pagination[field] !== 'number') {
          result.typeErrors.push({
            field: `data.pagination.${field}`,
            expected: 'number',
            actual: typeof pagination[field],
          });
        }
      }
    }

    // 严格模式：检查额外字段
    if (strict) {
      const allowedPaginationFields = [
        'page',
        'pageSize',
        'total',
        'totalPages',
        'hasNext',
        'hasPrev',
      ];
      const extraFields = Object.keys(pagination).filter(
        key => !allowedPaginationFields.includes(key)
      );
      if (extraFields.length > 0) {
        result.extraFields.push(...extraFields.map(f => `data.pagination.${f}`));
        result.warnings.push(`data.pagination 发现额外字段: ${extraFields.join(', ')}`);
      }
    }
  }

  // 判断是否验证通过
  result.valid = result.typeErrors.length === 0 && result.missingFields.length === 0;

  if (result.valid) {
    result.data = data as PaginatedApiResponse<T>;
  }

  return result;
}

// ==================== 错误响应验证 ====================

/**
 * 验证错误响应格式
 *
 * @param data - 待验证的数据
 * @returns 类型守卫，如果验证通过则返回 true
 */
export function isErrorResponse(data: unknown): data is ErrorResponse {
  if (data == null || typeof data !== 'object') {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // 必须有 success: false
  if (obj.success !== false) {
    return false;
  }

  // 必须有 error 对象
  if (!('error' in obj) || typeof obj.error !== 'object' || obj.error === null) {
    return false;
  }

  const error = obj.error as Record<string, unknown>;

  // error 对象必须有 code 和 message
  if (typeof error.code !== 'string') {
    return false;
  }

  if (typeof error.message !== 'string') {
    return false;
  }

  return true;
}

/**
 * 详细验证错误响应
 */
export function validateErrorResponse(
  data: unknown,
  strict: boolean = false
): DetailedValidationResult<ErrorResponse> {
  const result: DetailedValidationResult<ErrorResponse> = {
    valid: false,
    warnings: [],
    missingFields: [],
    extraFields: [],
    typeErrors: [],
  };

  if (data == null || typeof data !== 'object') {
    result.error = '响应必须是对象类型';
    return result;
  }

  const obj = data as Record<string, unknown>;

  // 检查 success 字段
  if (obj.success !== false) {
    result.typeErrors.push({
      field: 'success',
      expected: 'false',
      actual: String(obj.success),
    });
  }

  // 检查 error 字段
  if (!('error' in obj)) {
    result.missingFields.push('error');
  } else if (typeof obj.error !== 'object' || obj.error === null) {
    result.typeErrors.push({
      field: 'error',
      expected: 'object',
      actual: obj.error === null ? 'null' : typeof obj.error,
    });
  } else {
    const error = obj.error as Record<string, unknown>;

    // 检查 error.code
    if (typeof error.code !== 'string') {
      result.missingFields.push('error.code');
      result.typeErrors.push({
        field: 'error.code',
        expected: 'string',
        actual: typeof error.code,
      });
    }

    // 检查 error.message
    if (typeof error.message !== 'string') {
      result.missingFields.push('error.message');
      result.typeErrors.push({
        field: 'error.message',
        expected: 'string',
        actual: typeof error.message,
      });
    }

    // 检查可选字段
    if ('details' in error && typeof error.details !== 'object') {
      result.typeErrors.push({
        field: 'error.details',
        expected: 'object | undefined',
        actual: typeof error.details,
      });
    }

    if (
      'timestamp' in error &&
      typeof error.timestamp !== 'string' &&
      typeof error.timestamp !== 'undefined'
    ) {
      result.typeErrors.push({
        field: 'error.timestamp',
        expected: 'string | undefined',
        actual: typeof error.timestamp,
      });
    }

    // 严格模式：检查额外字段
    if (strict) {
      const allowedErrorFields = ['code', 'message', 'details', 'timestamp', 'requestId'];
      const extraFields = Object.keys(error).filter(key => !allowedErrorFields.includes(key));
      if (extraFields.length > 0) {
        result.extraFields.push(...extraFields.map(f => `error.${f}`));
        result.warnings.push(`error 发现额外字段: ${extraFields.join(', ')}`);
      }
    }
  }

  // 判断是否验证通过
  result.valid = result.typeErrors.length === 0 && result.missingFields.length === 0;

  if (result.valid) {
    result.data = data as ErrorResponse;
  }

  return result;
}

// ==================== 通用验证工具 ====================

/**
 * 验证任意 API 响应格式
 *
 * @param data - 待验证的数据
 * @returns 验证结果，包含响应类型信息
 */
export function validateApiResponse(data: unknown): {
  valid: boolean;
  type: 'standard' | 'paginated' | 'error' | 'unknown';
  result?: DetailedValidationResult;
} {
  // 尝试验证为错误响应
  const errorResult = validateErrorResponse(data, false);
  if (errorResult.valid) {
    return {
      valid: true,
      type: 'error',
      result: errorResult,
    };
  }

  // 尝试验证为分页响应
  const paginatedResult = validatePaginatedResponse(data, false);
  if (paginatedResult.valid) {
    return {
      valid: true,
      type: 'paginated',
      result: paginatedResult,
    };
  }

  // 尝试验证为标准响应
  const standardResult = validateStandardResponse(data, false);
  if (standardResult.valid) {
    return {
      valid: true,
      type: 'standard',
      result: standardResult,
    };
  }

  // 无法识别的格式
  return {
    valid: false,
    type: 'unknown',
  };
}

/**
 * 断言 API 响应格式
 *
 * @param data - 待验证的数据
 * @param expectedType - 期望的响应类型
 * @throws Error 如果验证失败
 */
export function assertApiResponse<T = unknown>(
  data: unknown,
  expectedType: 'standard' | 'paginated' | 'error'
): asserts data is T {
  const validation = validateApiResponse(data);

  if (!validation.valid) {
    throw new Error(`无效的 API 响应格式: 无法识别响应结构`);
  }

  if (validation.type !== expectedType) {
    throw new Error(`API 响应类型不匹配: 期望 '${expectedType}'，实际 '${validation.type}'`);
  }
}

// ==================== 默认导出 ====================

/**
 * 响应验证器工具集
 */
export const ResponseValidator = {
  // 类型守卫
  isStandardApiResponse,
  isPaginatedApiResponse,
  isErrorResponse,

  // 详细验证
  validateStandardResponse,
  validatePaginatedResponse,
  validateErrorResponse,

  // 通用工具
  validateApiResponse,
  assertApiResponse,
} as const;
