/**
 * Null Safety Utilities
 * Comprehensive helper functions for handling nullable values safely
 */

/**
 * Safely checks if a value is present (not null/undefined/empty)
 * Works for strings, numbers, booleans, objects, and arrays
 */
export function isPresent<T>(value: T | null | undefined): value is T {
  if (value === null || value === undefined) {
    return false;
  }

  // For strings, also check for empty
  if (typeof value === 'string' && value === '') {
    return false;
  }

  // For numbers, also check for NaN
  if (typeof value === 'number' && Number.isNaN(value)) {
    return false;
  }

  // For objects/arrays, check if empty
  if (typeof value === 'object') {
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return Object.keys(value).length > 0;
  }

  return true;
}

/**
 * Safely get a nested property from an object
 * Returns undefined if any part of the path is null/undefined
 */
export function safeGet<T, K extends keyof T>(obj: T | null | undefined, key: K): T[K] | undefined {
  if (obj === null || obj === undefined) {
    return undefined;
  }
  return obj[key];
}

/**
 * Safely access a deeply nested property using a path
 * Example: safeNestedGet(obj, 'a.b.c')
 */
export function safeNestedGet(obj: unknown, path: string): unknown {
  return path.split('.').reduce((current: unknown, key: string) => {
    if (current === null || current === undefined) {
      return undefined;
    }
    return (current as Record<string, unknown>)[key];
  }, obj);
}

/**
 * Coalesce multiple values, returning the first non-null/non-undefined value
 */
export function coalesce<T>(...values: (T | null | undefined)[]): T | undefined {
  for (const value of values) {
    if (value !== null && value !== undefined) {
      return value;
    }
  }
  return undefined;
}

/**
 * Safely execute a function that might throw
 * Returns a fallback value on error
 */
export function safeExecute<T>(
  fn: () => T,
  fallback: T,
  onError?: (error: Error) => void
): T {
  try {
    return fn();
  } catch (error) {
    if (isPresent(onError)) {
      onError(error as Error);
    }
    return fallback;
  }
}

/**
 * Type guard for Axios errors
 */
export function isAxiosError(error: unknown): error is {
  response?: { data?: { detail?: string }; statusText?: string };
  request?: unknown;
  message: string;
  code?: string;
  name?: string;
} {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error
  );
}

/**
 * Type guard for standard Error objects
 */
export function isError(error: unknown): error is Error {
  return (
    error instanceof Error ||
    (typeof error === 'object' &&
      error !== null &&
      'message' in error)
  );
}

/**
 * Safely extract error message from various error types
 */
export function getErrorMessage(error: unknown): string {
  if (isError(error)) {
    return error.message;
  }
  if (isAxiosError(error)) {
    const detail = safeGet(safeGet(error.response, 'data'), 'detail');
    if (isPresent(detail)) {
      return detail as string;
    }
    return error.message;
  }
  return 'Unknown error';
}

/**
 * Conditional check helper for nullable strings
 */
export function ifString(value: string | null | undefined, callback: (val: string) => void): void {
  if (value !== null && value !== undefined && value !== '') {
    callback(value);
  }
}

/**
 * Conditional check helper for nullable numbers
 */
export function ifNumber(value: number | null | undefined, callback: (val: number) => void): void {
  if (value !== null && value !== undefined && !Number.isNaN(value)) {
    callback(value);
  }
}

/**
 * Conditional check helper for nullable booleans
 */
export function ifBoolean(value: boolean | null | undefined, callback: (val: boolean) => void): void {
  if (value !== null && value !== undefined) {
    callback(value);
  }
}

/**
 * Conditional check helper for nullable objects
 */
export function ifObject<T extends object>(value: T | null | undefined, callback: (val: T) => void): void {
  if (value !== null && value !== undefined) {
    callback(value);
  }
}
