import { describe, expect, it } from 'vitest';

import {
  TypeGuards,
  assert,
  assertNotNullish,
  assertTrue,
  filterDuplicates,
  filterNullish,
  getErrorMessage,
  hasProperties,
  hasProperty,
  hasValidationErrors,
  isArray,
  isBoolean,
  isDate,
  isEmpty,
  isErrorResponse,
  isFile,
  isFileList,
  isFunction,
  isInRange,
  isLengthInRange,
  isNegative,
  isNonNegative,
  isNotEmptyArray,
  isNull,
  isNullish,
  isNumber,
  isNumberArray,
  isObject,
  isObjectArray,
  isPaginatedResponse,
  isPositive,
  isPropertyOfType,
  isString,
  isStringArray,
  isSuccessResponse,
  isUndefined,
  isUniqueArray,
  isValidDateString,
  isValidEmail,
  isValidFormData,
  isValidId,
  isValidPhoneNumber,
  isValidUrl,
  partition,
} from '@/types/guards';

describe('guards', () => {
  it('基础类型守卫应正确识别类型', () => {
    expect(isString('abc')).toBe(true);
    expect(isString(1)).toBe(false);
    expect(isNumber(12.3)).toBe(true);
    expect(isNumber(Number.NaN)).toBe(false);
    expect(isBoolean(false)).toBe(true);
    expect(isFunction(() => true)).toBe(true);
    expect(isObject({ a: 1 })).toBe(true);
    expect(isObject([])).toBe(false);
    expect(isArray([1, 2])).toBe(true);
    expect(isNull(null)).toBe(true);
    expect(isUndefined(undefined)).toBe(true);
    expect(isNullish(null)).toBe(true);
    expect(isNullish(undefined)).toBe(true);
    expect(isDate(new Date('2026-01-01'))).toBe(true);
    expect(isDate(new Date('bad'))).toBe(false);
  });

  it('isEmpty 应处理多种空值', () => {
    expect(isEmpty(null)).toBe(true);
    expect(isEmpty(undefined)).toBe(true);
    expect(isEmpty('')).toBe(true);
    expect(isEmpty([])).toBe(true);
    expect(isEmpty({})).toBe(true);
    expect(isEmpty('x')).toBe(false);
    expect(isEmpty([1])).toBe(false);
    expect(isEmpty({ a: 1 })).toBe(false);
    expect(isEmpty(0)).toBe(false);
  });

  it('对象属性守卫应工作正常', () => {
    const obj: unknown = { name: 'zcgl', count: 1 };
    expect(hasProperty(obj, 'name')).toBe(true);
    expect(hasProperties(obj, ['name', 'count'])).toBe(true);
    expect(hasProperties(obj, ['name', 'missing'])).toBe(false);
    expect(isPropertyOfType(obj, 'name', isString)).toBe(true);
    expect(isPropertyOfType(obj, 'count', isString)).toBe(false);
  });

  it('格式与标识校验应正确工作', () => {
    expect(isValidId('id-1')).toBe(true);
    expect(isValidId(10)).toBe(true);
    expect(isValidId('')).toBe(false);
    expect(isValidId(0)).toBe(false);

    expect(isValidDateString('2026-01-01')).toBe(true);
    expect(isValidDateString('not-a-date')).toBe(false);

    expect(isValidUrl('https://example.com')).toBe(true);
    expect(isValidUrl('ht@tp://x')).toBe(false);

    expect(isValidEmail('a@b.com')).toBe(true);
    expect(isValidEmail('bad-email')).toBe(false);

    expect(isValidPhoneNumber('13812345678')).toBe(true);
    expect(isValidPhoneNumber('123456')).toBe(false);
  });

  it('API 响应守卫应识别成功/失败/分页结构', () => {
    const success = { success: true, data: { id: 1 } };
    const error = { success: false, error: { message: 'failed' } };
    const paginated = {
      success: true,
      data: {
        items: [{ id: 1 }],
        pagination: { page: 1, pageSize: 10, total: 1 },
      },
    };

    expect(isSuccessResponse(success)).toBe(true);
    expect(isSuccessResponse(error)).toBe(false);
    expect(isErrorResponse(error)).toBe(true);
    expect(isErrorResponse(success)).toBe(false);
    expect(isPaginatedResponse(paginated)).toBe(true);
    expect(isPaginatedResponse(success)).toBe(false);
  });

  it('getErrorMessage 应按优先级提取错误消息', () => {
    expect(getErrorMessage(null)).toBe('未知错误');
    expect(getErrorMessage({ message: 'msg' })).toBe('msg');
    expect(getErrorMessage({ error: 'bad' })).toBe('bad');
    expect(getErrorMessage({ error: { message: 'nested' } })).toBe('nested');
    expect(getErrorMessage({ error: { code: 500 } })).toBe('操作失败，请重试');
  });

  it('数组与表单守卫应正常工作', () => {
    expect(isNotEmptyArray<number>([1])).toBe(true);
    expect(isNotEmptyArray<number>([])).toBe(false);
    expect(isNumberArray([1, 2, 3])).toBe(true);
    expect(isNumberArray([1, '2'])).toBe(false);
    expect(isStringArray(['a', 'b'])).toBe(true);
    expect(isStringArray(['a', 2])).toBe(false);
    expect(isObjectArray([{ a: 1 }, { b: 2 }])).toBe(true);
    expect(isObjectArray([{ a: 1 }, []])).toBe(false);
    expect(isUniqueArray([1, 2, 3])).toBe(true);
    expect(isUniqueArray([1, 1, 2])).toBe(false);

    expect(isValidFormData({ a: 1 })).toBe(true);
    expect(isValidFormData({})).toBe(false);
    expect(hasValidationErrors({ name: ['required'] })).toBe(true);
    expect(hasValidationErrors({ name: 'required' })).toBe(false);
  });

  it('文件与范围守卫应正常工作', () => {
    const file = new File(['content'], 'demo.txt', { type: 'text/plain' });
    const input = document.createElement('input');
    input.type = 'file';

    expect(isFile(file)).toBe(true);
    expect(isFile({})).toBe(false);
    expect(isFileList(input.files)).toBe(true);
    expect(isFileList([])).toBe(false);

    expect(isInRange(5, 1, 10)).toBe(true);
    expect(isInRange(11, 1, 10)).toBe(false);
    expect(isLengthInRange('abc', 1, 3)).toBe(true);
    expect(isLengthInRange('abcd', 1, 3)).toBe(false);
    expect(isPositive(1)).toBe(true);
    expect(isPositive(0)).toBe(false);
    expect(isNegative(-1)).toBe(true);
    expect(isNegative(1)).toBe(false);
    expect(isNonNegative(0)).toBe(true);
    expect(isNonNegative(-1)).toBe(false);
  });

  it('断言函数应在失败时抛错', () => {
    expect(() => assert('ok', isString)).not.toThrow();
    expect(() => assert(1, isString, 'must string')).toThrow('must string');
    expect(() => assertNotNullish('v')).not.toThrow();
    expect(() => assertNotNullish(null, 'nullish')).toThrow('nullish');
    expect(() => assertTrue(true)).not.toThrow();
    expect(() => assertTrue(false, 'bad')).toThrow('bad');
  });

  it('集合工具函数应正确处理数据', () => {
    expect(filterNullish([1, null, 2, undefined, 3])).toEqual([1, 2, 3]);
    expect(filterDuplicates([1, 1, 2, 3, 3])).toEqual([1, 2, 3]);
    expect(partition([1, 2, 3, 4], v => v % 2 === 0)).toEqual([
      [2, 4],
      [1, 3],
    ]);
  });

  it('TypeGuards 默认导出应包含核心能力', () => {
    expect(TypeGuards.isString('a')).toBe(true);
    expect(TypeGuards.isNumber(1)).toBe(true);
    expect(TypeGuards.isValidEmail('x@y.com')).toBe(true);
    expect(TypeGuards.isUniqueArray([1, 2, 2])).toBe(false);
    expect(TypeGuards.partition([1, 2], v => v > 1)).toEqual([[2], [1]]);
  });
});
