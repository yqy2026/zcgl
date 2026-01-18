/**
 * 类型守卫和运行时验证工具
 *
 * @module types/guards
 * @description
 * 提供类型安全的运行时检查工具，帮助在运行时验证数据类型。
 * 这些工具与 TypeScript 类型系统配合使用，提供完整的类型安全保障。
 *
 * @example
 * ```typescript
 * import { isString, isObject, hasProperty } from '@/types/guards';
 *
 * function processData(data: unknown) {
 *   if (!isObject(data)) return;
 *   if (!hasProperty(data, 'name')) return;
 *
 *   // TypeScript 现在知道 data.name 存在
 *   console.log(data.name);
 * }
 * ```
 */

// ==================== 基础类型守卫 ====================

/**
 * 检查值是否为字符串
 */
export function isString(value: unknown): value is string {
  return typeof value === 'string';
}

/**
 * 检查值是否为数字
 */
export function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value);
}

/**
 * 检查值是否为布尔值
 */
export function isBoolean(value: unknown): value is boolean {
  return typeof value === 'boolean';
}

/**
 * 检查值是否为函数
 */
export function isFunction(value: unknown): value is (...args: unknown[]) => unknown {
  return typeof value === 'function';
}

/**
 * 检查值是否为对象（非 null、非数组）
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * 检查值是否为数组
 */
export function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}

/**
 * 检查值是否为 null
 */
export function isNull(value: unknown): value is null {
  return value === null;
}

/**
 * 检查值是否为 undefined
 */
export function isUndefined(value: unknown): value is undefined {
  return value === undefined;
}

/**
 * 检查值是否为 null 或 undefined
 */
export function isNullish(value: unknown): value is null | undefined {
  return value === null || value === undefined;
}

/**
 * 检查值是否为日期对象
 */
export function isDate(value: unknown): value is Date {
  return value instanceof Date && !isNaN(value.getTime());
}

/**
 * 检查值是否为空（空字符串、空数组、空对象、null、undefined）
 */
export function isEmpty(value: unknown): boolean {
  if (isNullish(value)) return true;
  if (isString(value) || isArray(value)) return value.length === 0;
  if (isObject(value)) return Object.keys(value).length === 0;
  return false;
}

// ==================== 高级类型守卫 ====================

/**
 * 检查对象是否具有指定属性
 */
export function hasProperty<K extends string>(obj: unknown, key: K): obj is Record<K, unknown> {
  return isObject(obj) && key in obj;
}

/**
 * 检查对象是否具有多个指定属性
 */
export function hasProperties<K extends string>(
  obj: unknown,
  keys: K[]
): obj is Record<K, unknown> {
  return isObject(obj) && keys.every(key => key in obj);
}

/**
 * 检查属性是否为指定类型
 */
export function isPropertyOfType<T>(
  obj: unknown,
  key: string,
  typeCheck: (value: unknown) => value is T
): obj is Record<string, T> {
  return hasProperty(obj, key) && typeCheck(obj[key]);
}

/**
 * 检查是否为有效的 ID（字符串或数字）
 */
export function isValidId(value: unknown): value is string | number {
  return (isString(value) && value.length > 0) || (isNumber(value) && value > 0);
}

/**
 * 检查是否为有效的日期字符串
 */
export function isValidDateString(value: unknown): value is string {
  if (!isString(value)) return false;
  const date = new Date(value);
  return !isNaN(date.getTime());
}

/**
 * 检查是否为有效的 URL
 */
export function isValidUrl(value: unknown): value is string {
  if (!isString(value)) return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

/**
 * 检查是否为有效的邮箱地址
 */
export function isValidEmail(value: unknown): value is string {
  if (!isString(value)) return false;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(value);
}

/**
 * 检查是否为有效的手机号（中国大陆）
 */
export function isValidPhoneNumber(value: unknown): value is string {
  if (!isString(value)) return false;
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(value);
}

// ==================== API 响应类型守卫 ====================

import { StandardApiResponse, PaginatedApiResponse, ErrorResponse } from './apiResponse';

/**
 * 检查是否为标准 API 成功响应
 */
export function isSuccessResponse<T = unknown>(
  response: unknown
): response is StandardApiResponse<T> & { success: true; data: T } {
  return isObject(response) && response.success === true && 'data' in response;
}

/**
 * 检查是否为标准 API 错误响应
 */
export function isErrorResponse(response: unknown): response is ErrorResponse {
  return (
    isObject(response) &&
    response.success === false &&
    'error' in response &&
    isObject(response.error)
  );
}

/**
 * 检查是否为分页响应
 */
export function isPaginatedResponse<T = unknown>(
  response: unknown
): response is PaginatedApiResponse<T> {
  if (!isSuccessResponse(response)) return false;
  const data = response.data;
  return (
    isObject(data) &&
    'items' in data &&
    'pagination' in data &&
    isArray(data.items) &&
    isObject(data.pagination)
  );
}

/**
 * 从响应中提取错误消息
 */
export function getErrorMessage(error: unknown): string {
  if (!isObject(error)) return '未知错误';

  if (hasProperty(error, 'message') && isString(error.message)) {
    return error.message;
  }

  if (hasProperty(error, 'error')) {
    if (isString(error.error)) return error.error;
    if (
      isObject(error.error) &&
      hasProperty(error.error, 'message') &&
      isString(error.error.message)
    ) {
      return error.error.message;
    }
  }

  return '操作失败，请重试';
}

// ==================== 数组和集合类型守卫 ====================

/**
 * 检查数组是否为空
 */
export function isNotEmptyArray<T>(value: unknown): value is [T, ...T[]] {
  return isArray(value) && value.length > 0;
}

/**
 * 检查是否为数字数组
 */
export function isNumberArray(value: unknown): value is number[] {
  return isArray(value) && value.every(isNumber);
}

/**
 * 检查是否为字符串数组
 */
export function isStringArray(value: unknown): value is string[] {
  return isArray(value) && value.every(isString);
}

/**
 * 检查是否为对象数组
 */
export function isObjectArray(value: unknown): value is Record<string, unknown>[] {
  return isArray(value) && value.every(isObject);
}

/**
 * 检查数组中的所有元素是否唯一
 */
export function isUniqueArray<T>(value: T[]): boolean {
  return new Set(value).size === value.length;
}

// ==================== 表单和验证类型守卫 ====================

/**
 * 检查是否为有效的表单数据
 */
export function isValidFormData(data: unknown): data is Record<string, unknown> {
  return isObject(data) && Object.keys(data).length > 0;
}

/**
 * 检查是否有验证错误
 */
export function hasValidationErrors(errors: unknown): errors is Record<string, string[]> {
  return (
    isObject(errors) && Object.values(errors).some(value => isArray(value) && value.every(isString))
  );
}

/**
 * 检查是否为有效的文件对象
 */
export function isFile(value: unknown): value is File {
  return value instanceof File;
}

/**
 * 检查是否为文件列表
 */
export function isFileList(value: unknown): value is FileList {
  return value instanceof FileList;
}

// ==================== 范围和边界类型守卫 ====================

/**
 * 检查数字是否在指定范围内
 */
export function isInRange(value: unknown, min: number, max: number): value is number {
  return isNumber(value) && value >= min && value <= max;
}

/**
 * 检查字符串长度是否在指定范围内
 */
export function isLengthInRange(value: unknown, min: number, max: number): value is string {
  return isString(value) && value.length >= min && value.length <= max;
}

/**
 * 检查是否为正数
 */
export function isPositive(value: unknown): value is number {
  return isNumber(value) && value > 0;
}

/**
 * 检查是否为负数
 */
export function isNegative(value: unknown): value is number {
  return isNumber(value) && value < 0;
}

/**
 * 检查是否为非负数
 */
export function isNonNegative(value: unknown): value is number {
  return isNumber(value) && value >= 0;
}

// ==================== 断言函数 ====================

/**
 * 断言值为指定类型，否则抛出错误
 */
export function assert<T>(
  value: unknown,
  guard: (value: unknown) => value is T,
  message?: string
): asserts value is T {
  if (!guard(value)) {
    throw new TypeError(message ?? `Type assertion failed: ${typeof value}`);
  }
}

/**
 * 断言值不为 nullish
 */
export function assertNotNullish<T>(
  value: T | null | undefined,
  message?: string
): asserts value is T {
  if (isNullish(value)) {
    throw new TypeError(message ?? 'Value should not be null or undefined');
  }
}

/**
 * 断言条件为真
 */
export function assertTrue(condition: boolean, message?: string): asserts condition is true {
  if (!condition) {
    throw new Error(message ?? 'Assertion failed: condition is not true');
  }
}

// ==================== 类型窄化工具 ====================

/**
 * 过滤掉 nullish 值
 */
export function filterNullish<T>(values: (T | null | undefined)[]): T[] {
  return values.filter((value): value is T => !isNullish(value));
}

/**
 * 过滤掉重复值
 */
export function filterDuplicates<T>(values: T[]): T[] {
  return Array.from(new Set(values));
}

/**
 * 分离有效和无效值
 */
export function partition<T>(
  values: T[],
  predicate: (value: T) => boolean
): [valid: T[], invalid: T[]] {
  const valid: T[] = [];
  const invalid: T[] = [];

  for (const value of values) {
    if (predicate(value)) {
      valid.push(value);
    } else {
      invalid.push(value);
    }
  }

  return [valid, invalid];
}

// ==================== 默认导出 ====================

/**
 * 类型守卫工具集
 */
export const TypeGuards = {
  // 基础类型
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

  // 高级类型
  hasProperty,
  hasProperties,
  isPropertyOfType,
  isValidId,
  isValidDateString,
  isValidUrl,
  isValidEmail,
  isValidPhoneNumber,

  // API 响应
  isSuccessResponse,
  isErrorResponse,
  isPaginatedResponse,
  getErrorMessage,

  // 数组
  isNotEmptyArray,
  isNumberArray,
  isStringArray,
  isObjectArray,
  isUniqueArray,

  // 表单
  isValidFormData,
  hasValidationErrors,
  isFile,
  isFileList,

  // 范围
  isInRange,
  isLengthInRange,
  isPositive,
  isNegative,
  isNonNegative,

  // 断言
  assert,
  assertNotNullish,
  assertTrue,

  // 工具
  filterNullish,
  filterDuplicates,
  partition,
} as const;
