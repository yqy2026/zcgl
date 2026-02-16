import { describe, expect, it } from 'vitest';

import {
  ResponseValidator,
  assertApiResponse,
  isErrorResponse,
  isPaginatedApiResponse,
  isStandardApiResponse,
  validateApiResponse,
  validateErrorResponse,
  validatePaginatedResponse,
  validateStandardResponse,
} from '../responseValidator';

describe('responseValidator', () => {
  const standardResponse = {
    success: true,
    data: { id: 1, name: '资产A' },
    message: 'ok',
  };

  const paginatedResponse = {
    success: true,
    data: {
      items: [{ id: 1 }, { id: 2 }],
      pagination: {
        page: 1,
        page_size: 20,
        total: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    },
  };

  const errorResponse = {
    success: false,
    error: {
      code: 'BAD_REQUEST',
      message: '参数错误',
      details: { field: 'name' },
    },
  };

  it('validates standard responses', () => {
    expect(isStandardApiResponse(standardResponse)).toBe(true);
    expect(isStandardApiResponse({ success: true })).toBe(false);

    const result = validateStandardResponse(standardResponse);
    expect(result.valid).toBe(true);
    expect(result.data?.data).toEqual({ id: 1, name: '资产A' });

    const invalid = validateStandardResponse({ success: true });
    expect(invalid.valid).toBe(false);
    expect(invalid.error).toContain('Successful response must contain data field');
    expect(invalid.zodError).toBeDefined();
  });

  it('validates paginated responses', () => {
    expect(isPaginatedApiResponse(paginatedResponse)).toBe(true);
    expect(
      isPaginatedApiResponse({
        success: true,
        data: { pagination: { page: 1 } },
      })
    ).toBe(false);

    const result = validatePaginatedResponse(paginatedResponse);
    expect(result.valid).toBe(true);
    expect(result.data?.data.items).toHaveLength(2);

    const invalid = validatePaginatedResponse({
      success: true,
      data: { items: [] },
    });
    expect(invalid.valid).toBe(false);
    expect(invalid.zodError).toBeDefined();
  });

  it('validates error responses', () => {
    expect(isErrorResponse(errorResponse)).toBe(true);
    expect(isErrorResponse({ success: false, error: { code: 'x' } })).toBe(false);

    const result = validateErrorResponse(errorResponse);
    expect(result.valid).toBe(true);
    expect(result.data?.error.code).toBe('BAD_REQUEST');

    const invalid = validateErrorResponse({
      success: false,
      error: { message: '缺少 code' },
    });
    expect(invalid.valid).toBe(false);
    expect(invalid.error).toContain('code');
  });

  it('detects response type with validateApiResponse', () => {
    expect(validateApiResponse(errorResponse)).toMatchObject({
      valid: true,
      type: 'error',
    });
    expect(validateApiResponse(paginatedResponse)).toMatchObject({
      valid: true,
      type: 'paginated',
    });
    expect(validateApiResponse(standardResponse)).toMatchObject({
      valid: true,
      type: 'standard',
    });
    expect(validateApiResponse({ ok: true })).toEqual({
      valid: false,
      type: 'unknown',
    });
  });

  it('asserts expected response type and throws on mismatch', () => {
    expect(() => assertApiResponse(standardResponse, 'standard')).not.toThrow();
    expect(() => assertApiResponse(paginatedResponse, 'paginated')).not.toThrow();
    expect(() => assertApiResponse(errorResponse, 'error')).not.toThrow();

    expect(() => assertApiResponse({ success: true }, 'standard')).toThrow(
      "Invalid API response format for 'standard'"
    );

    expect(() => assertApiResponse({}, 'unknown' as never)).toThrow('Unknown expected type');
  });

  it('exports a stable validator object facade', () => {
    expect(ResponseValidator.isStandardApiResponse).toBe(isStandardApiResponse);
    expect(ResponseValidator.isPaginatedApiResponse).toBe(isPaginatedApiResponse);
    expect(ResponseValidator.isErrorResponse).toBe(isErrorResponse);
    expect(ResponseValidator.validateStandardResponse).toBe(validateStandardResponse);
    expect(ResponseValidator.validatePaginatedResponse).toBe(validatePaginatedResponse);
    expect(ResponseValidator.validateErrorResponse).toBe(validateErrorResponse);
    expect(ResponseValidator.validateApiResponse).toBe(validateApiResponse);
    expect(ResponseValidator.assertApiResponse).toBe(assertApiResponse);
  });
});
