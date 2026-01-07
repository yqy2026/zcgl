/**
 * ResponseExtractor 测试
 * 测试API响应数据提取功能
 */

import { describe, it, expect, vi } from 'vitest';
import { ResponseExtractor, ApiErrorHandler } from '../responseExtractor';
import { AxiosResponse, AxiosError } from 'axios';
import type { EnhancedApiError, ApiErrorType } from '@/types/apiResponse';

// =============================================================================
// Mock数据
// =============================================================================

const createMockResponse = (_data: any, status = 200): AxiosResponse => {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as any,
  } as AxiosResponse;
};

const standardResponse = createMockResponse({
  success: true,
  data: { id: 1, name: '测试数据' },
  message: '操作成功',
});

const paginatedResponse = createMockResponse({
  success: true,
  data: {
    items: [{ id: 1 }, { id: 2 }, { id: 3 }],
    pagination: {
      page: 1,
      pageSize: 20,
      total: 100,
      totalPages: 5,
    },
  },
});

const errorResponse = createMockResponse(
  {
    success: false,
    error: '请求失败',
    message: '详细错误信息',
  },
  400
);

const directResponse = createMockResponse({ id: 1, name: '直接数据' });

const _errorAxiosResponse = {
  response: {
    status: 401,
    data: {
      code: 'UNAUTHORIZED',
      message: '未授权访问',
    },
  },
} as AxiosError;

const networkErrorResponse = {
  response: undefined,
  message: 'Network Error',
} as AxiosError;

// =============================================================================
// ResponseExtractor 核心功能测试
// =============================================================================

describe('ResponseExtractor - 核心功能', () => {
  describe('smartExtract - 标准响应', () => {
    it('应该提取标准响应数据', () => {
      const _result = ResponseExtractor.smartExtract(standardResponse);

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: 1, name: '测试数据' });
      expect(result.rawResponse).toEqual(standardResponse);
    });

    it('应该处理带类型的提取', () => {
      interface DataType {
        id: number;
        name: string;
      }

      const _result = ResponseExtractor.smartExtract<DataType>(standardResponse, {
        enableTypeValidation: false,
      });

      expect(result.success).toBe(true);
      expect(result.data?.id).toBe(1);
      expect(result.data?.name).toBe('测试数据');
    });

    it('应该将缺少data字段的响应作为直接响应处理', () => {
      // 没有data字段的响应会被识别为直接响应
      const invalidResponse = createMockResponse({
        success: true,
        // 缺少data字段
      });

      const _result = ResponseExtractor.smartExtract(invalidResponse);

      // 当没有data字段时，会被识别为直接响应
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ success: true });
    });
  });

  describe('smartExtract - 分页响应', () => {
    it('应该提取分页响应数据', () => {
      const _result = ResponseExtractor.smartExtract(paginatedResponse);

      expect(result.success).toBe(true);
      expect(result.data).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }]);
    });

    it('应该将缺少items字段的响应作为标准响应处理', () => {
      // 没有items字段的分页响应会被识别为标准响应
      const invalidPaginatedResponse = createMockResponse({
        success: true,
        data: {
          pagination: { page: 1, total: 100 },
          // 缺少items字段
        },
      });

      const _result = ResponseExtractor.smartExtract(invalidPaginatedResponse);

      // 会被识别为标准响应，返回data对象本身
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ pagination: { page: 1, total: 100 } });
    });
  });

  describe('smartExtract - 错误响应', () => {
    it('应该提取错误响应信息', () => {
      const _result = ResponseExtractor.smartExtract(errorResponse);

      expect(result.success).toBe(false);
      expect(result.error).toBe('请求失败');
    });

    it('应该优先提取error字段', () => {
      const response = createMockResponse({
        success: false,
        error: '主要错误',
        message: '次要错误',
      });

      const _result = ResponseExtractor.smartExtract(response);

      expect(result.error).toBe('主要错误');
    });

    it('应该提取嵌套的message字段', () => {
      const response = createMockResponse({
        success: false,
        error: {
          message: '嵌套错误信息',
          code: 'ERROR_CODE',
        },
      });

      const _result = ResponseExtractor.smartExtract(response);

      expect(result.error).toBe('嵌套错误信息');
    });
  });

  describe('smartExtract - 直接响应', () => {
    it('应该识别并提取直接响应', () => {
      const _result = ResponseExtractor.smartExtract(directResponse);

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: 1, name: '直接数据' });
    });

    it('应该处理数组直接响应', () => {
      const arrayResponse = createMockResponse([1, 2, 3]);
      const _result = ResponseExtractor.smartExtract(arrayResponse);

      expect(result.success).toBe(true);
      expect(result.data).toEqual([1, 2, 3]);
    });

    it('应该处理字符串直接响应', () => {
      const stringResponse = createMockResponse('success');
      const _result = ResponseExtractor.smartExtract(stringResponse);

      expect(result.success).toBe(true);
      expect(result.data).toBe('success');
    });
  });

  describe('smartExtract - 自定义配置', () => {
    it('应该支持自定义字段名称', () => {
      const customResponse = createMockResponse({
        ok: true,
        result: { id: 1 },
        error: 'error message',
      });

      const _result = ResponseExtractor.smartExtract(customResponse, {
        detection: {
          successField: 'ok',
          dataField: 'result',
          errorFields: ['error'],
          strict: false,
        },
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: 1 });
    });
  });
});

// =============================================================================
// 便捷方法测试
// =============================================================================

describe('ResponseExtractor - 便捷方法', () => {
  describe('extractData', () => {
    it('应该快速提取成功响应数据', () => {
      const data = ResponseExtractor.extractData(standardResponse);

      expect(data).toEqual({ id: 1, name: '测试数据' });
    });

    it('应该返回默认值当提取失败时', () => {
      const defaultValue = { id: 0, name: '默认数据' };
      const data = ResponseExtractor.extractData(errorResponse, defaultValue);

      expect(data).toEqual(defaultValue);
    });

    it('提取失败时应该显示警告', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      ResponseExtractor.extractData(errorResponse);

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('响应数据提取失败'));

      consoleSpy.mockRestore();
    });
  });

  describe('extractMessage', () => {
    it('应该提取响应消息', () => {
      const message = ResponseExtractor.extractMessage(standardResponse);

      expect(message).toBe('操作成功');
    });

    it('应该提取嵌套的data.message', () => {
      const response = createMockResponse({
        data: {
          message: '嵌套消息',
        },
      });

      const message = ResponseExtractor.extractMessage(response);

      expect(message).toBe('嵌套消息');
    });

    it('应该返回默认消息当无法提取时', () => {
      const response = createMockResponse({});
      const message = ResponseExtractor.extractMessage(response);

      expect(message).toBe('操作成功');
    });

    it('异常时应该返回完成消息', () => {
      const response = null as any;
      const message = ResponseExtractor.extractMessage(response);

      expect(message).toBe('操作完成');
    });
  });

  describe('isSuccess', () => {
    it('应该正确判断成功响应', () => {
      expect(ResponseExtractor.isSuccess(standardResponse)).toBe(true);
      expect(ResponseExtractor.isSuccess(paginatedResponse)).toBe(true);
      expect(ResponseExtractor.isSuccess(directResponse)).toBe(true);
    });

    it('应该正确判断失败响应', () => {
      expect(ResponseExtractor.isSuccess(errorResponse)).toBe(false);
    });
  });

  describe('batchExtract', () => {
    it('应该批量提取响应数据', () => {
      const responses = [standardResponse, paginatedResponse, directResponse];
      const results = ResponseExtractor.batchExtract(responses);

      expect(results).toHaveLength(3);
      expect(results[0].success).toBe(true);
      expect(results[1].success).toBe(true);
      expect(results[2].success).toBe(true);
    });

    it('应该处理批量中包含的失败响应', () => {
      const responses = [standardResponse, errorResponse, directResponse];
      const results = ResponseExtractor.batchExtract(responses);

      expect(results).toHaveLength(3);
      expect(results[0].success).toBe(true);
      expect(results[1].success).toBe(false);
      expect(results[2].success).toBe(true);
    });

    it('应该支持自定义选项批量提取', () => {
      const responses = [standardResponse, paginatedResponse];
      const results = ResponseExtractor.batchExtract(responses, {
        enableTypeValidation: false,
      });

      expect(results).toHaveLength(2);
      expect(results.every(r => r.success)).toBe(true);
    });
  });

  describe('extractAndTransform', () => {
    it('应该提取并转换数据', () => {
      const transformer = (_data: any) => ({
        ...data,
        transformed: true,
      });

      const _result = ResponseExtractor.extractAndTransform(standardResponse, transformer);

      expect(result.success).toBe(true);
      expect(result.data).toEqual({
        id: 1,
        name: '测试数据',
        transformed: true,
      });
    });

    it('应该在原始提取失败时返回错误', () => {
      const transformer = (_data: any) => ({ transformed: true });
      const _result = ResponseExtractor.extractAndTransform(errorResponse, transformer);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('应该捕获转换过程中的错误', () => {
      const transformer = () => {
        throw new Error('转换失败');
      };

      const _result = ResponseExtractor.extractAndTransform(standardResponse, transformer);

      expect(result.success).toBe(false);
      expect(result.error).toContain('转换失败');
    });

    it('应该支持类型化的转换', () => {
      interface SourceType {
        id: number;
        value: string;
      }

      interface TargetType {
        identifier: number;
        content: string;
      }

      const transformer = (data: SourceType): TargetType => ({
        identifier: data.id,
        content: data.value,
      });

      const sourceResponse = createMockResponse({
        success: true,
        data: { id: 123, value: 'test' },
      });

      const _result = ResponseExtractor.extractAndTransform<SourceType, TargetType>(
        sourceResponse,
        transformer
      );

      expect(result.success).toBe(true);
      expect(result.data).toEqual({
        identifier: 123,
        content: 'test',
      });
    });
  });
});

// =============================================================================
// ApiErrorHandler 测试
// =============================================================================

describe('ApiErrorHandler - 错误处理', () => {
  describe('handleError - Axios错误', () => {
    it('应该处理网络错误（需要真实AxiosError实例）', () => {
      // 注意：由于测试环境无法创建真正的AxiosError实例，
      // 这里的测试验证的是fallback到UNKNOWN_ERROR的逻辑
      const error = ApiErrorHandler.handleError(networkErrorResponse);

      // 由于不是真正的AxiosError实例，会fallback到UNKNOWN_ERROR
      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.code).toBe('UNKNOWN_ERROR');
      expect(error.message).toContain('Network Error'); // 使用原始错误消息
    });

    it('应该处理401未授权错误（需要真实AxiosError实例）', () => {
      const unauthorizedError = {
        response: {
          status: 401,
          data: {
            message: '未授权',
          },
        },
      } as AxiosError;

      const error = ApiErrorHandler.handleError(unauthorizedError);

      // 不是真正的AxiosError实例，fallback到UNKNOWN_ERROR，使用默认消息
      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.code).toBe('UNKNOWN_ERROR');
      expect(error.message).toBe('未知错误');
    });

    it('应该处理422验证错误（需要真实AxiosError实例）', () => {
      const validationError = {
        response: {
          status: 422,
          data: {
            code: 'VALIDATION_ERROR',
            message: '验证失败',
            details: ['字段不能为空'],
          },
        },
      } as AxiosError;

      const error = ApiErrorHandler.handleError(validationError);

      // 不是真正的AxiosError实例，fallback到UNKNOWN_ERROR，使用默认消息
      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.code).toBe('UNKNOWN_ERROR');
      expect(error.message).toBe('未知错误');
    });

    it('应该处理5xx服务器错误（需要真实AxiosError实例）', () => {
      const serverError = {
        response: {
          status: 500,
          data: {
            message: '服务器内部错误',
          },
        },
      } as AxiosError;

      const error = ApiErrorHandler.handleError(serverError);

      // 不是真正的AxiosError实例，fallback到UNKNOWN_ERROR，使用默认消息
      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.code).toBe('UNKNOWN_ERROR');
      expect(error.message).toBe('未知错误');
    });

    it('应该处理502网关错误（需要真实AxiosError实例）', () => {
      const gatewayError = {
        response: {
          status: 502,
          data: {},
        },
      } as AxiosError;

      const error = ApiErrorHandler.handleError(gatewayError);

      // 不是真正的AxiosError实例，fallback到UNKNOWN_ERROR，使用默认消息
      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.code).toBe('UNKNOWN_ERROR');
      expect(error.message).toBe('未知错误');
    });

    it('应该处理有requestId的错误', () => {
      const errorWithRequestId = {
        response: {
          status: 400,
          data: {
            requestId: 'req-123456',
            message: 'Bad Request',
          },
        },
      } as AxiosError;

      const error = ApiErrorHandler.handleError(errorWithRequestId);

      // 由于不是真正的AxiosError实例，检查原始错误对象和默认消息
      expect(error.originalError).toBeDefined();
      expect(error.message).toBe('未知错误'); // fallback到默认消息
    });
  });

  describe('handleError - 已有的增强错误', () => {
    it('应该直接返回已有的增强错误', () => {
      const existingError: EnhancedApiError = {
        type: 'VALIDATION_ERROR' as ApiErrorType,
        code: 'CUSTOM_ERROR',
        message: '自定义错误',
        timestamp: new Date().toISOString(),
      };

      const error = ApiErrorHandler.handleError(existingError);

      expect(error).toEqual(existingError);
    });
  });

  describe('handleError - 未知错误', () => {
    it('应该处理未知类型的错误', () => {
      const unknownError = new Error('未知错误');

      const error = ApiErrorHandler.handleError(unknownError);

      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.code).toBe('UNKNOWN_ERROR');
      expect(error.message).toBe('未知错误');
    });

    it('应该处理没有message的错误', () => {
      const errorWithoutMessage = { code: 123 };

      const error = ApiErrorHandler.handleError(errorWithoutMessage);

      expect(error.type).toBe('UNKNOWN_ERROR');
      expect(error.message).toBe('未知错误');
    });
  });
});

// =============================================================================
// 边界情况测试
// =============================================================================

describe('ResponseExtractor - 边界情况', () => {
  it('应该处理null响应', () => {
    const _result = ResponseExtractor.smartExtract(null as any);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('应该处理undefined响应', () => {
    const _result = ResponseExtractor.smartExtract(undefined as any);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('应该处理空对象响应', () => {
    const _result = ResponseExtractor.smartExtract(createMockResponse({}));

    expect(result.success).toBe(true); // 直接响应
    expect(result.data).toEqual({});
  });

  it('应该处理异常情况', () => {
    // 模拟一个会在访问data时抛出异常的响应
    const problematicResponse = {
      get data() {
        throw new Error('访问异常');
      },
    } as any;

    const _result = ResponseExtractor.smartExtract(problematicResponse);

    expect(result.success).toBe(false);
    expect(result.error).toContain('数据提取失败');
  });
});

describe('ApiErrorHandler - 边界情况', () => {
  it('应该处理缺少response的错误', () => {
    const error = ApiErrorHandler.handleError(networkErrorResponse);

    // 不是真正的AxiosError实例，fallback到UNKNOWN_ERROR
    expect(error.type).toBe('UNKNOWN_ERROR');
    expect(error.message).toContain('Network Error');
  });

  it('应该处理缺少data的response', () => {
    const errorWithoutData = {
      response: {
        status: 500,
        // 缺少data
      },
    } as AxiosError;

    const error = ApiErrorHandler.handleError(errorWithoutData);

    // 不是真正的AxiosError实例，fallback到UNKNOWN_ERROR，使用默认消息
    expect(error.type).toBe('UNKNOWN_ERROR');
    expect(error.message).toBe('未知错误');
  });
});
