/**
 * 类型安全的辅助工具
 * 用于处理nullable值，避免strict-boolean-expressions警告
 */

/**
 * 检查字符串是否有值（非null且非空）
 */
export function isStringPresent(value: string | null | undefined): value is string {
  return value !== null && value !== undefined && value !== '';
}

/**
 * 检查数字是否有值（非null且非NaN）
 */
export function isNumberPresent(value: number | null | undefined): value is number {
  return value !== null && value !== undefined && !Number.isNaN(value);
}

/**
 * 检查布尔值是否有值（非null）
 */
export function isBooleanPresent(value: boolean | null | undefined): value is boolean {
  return value !== null && value !== undefined;
}

/**
 * 检查对象是否有值（非null）
 */
export function isObjectPresent<T extends object>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

/**
 * 获取字符串值或默认值
 */
export function getStringValue(value: string | null | undefined, defaultValue: string = ''): string {
  return value ?? defaultValue;
}

/**
 * 获取数字值或默认值
 */
export function getNumberValue(value: number | null | undefined, defaultValue: number = 0): number {
  return value ?? defaultValue;
}

/**
 * 获取布尔值或默认值
 */
export function getBooleanValue(value: boolean | null | undefined, defaultValue: boolean = false): boolean {
  return value ?? defaultValue;
}
