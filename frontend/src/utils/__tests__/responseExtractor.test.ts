/**
 * ResponseExtractor 单元测试
 * 测试智能响应数据提取功能
 */

import { ResponseExtractor } from '../responseExtractor';
import { AxiosResponse } from 'axios';
import type { StandardApiResponse, PaginatedApiResponse } from '../../types/api-response';

describe('ResponseExtractor', () => {
  // 模拟标准响应
  const createMockStandardResponse = <T>(data: T, success = true, message?: string): AxiosResponse<StandardApiResponse<T>> => ({
    data: {
      success,
      data,
      message: message || (success ? '操作成功' : '操作失败')
    },
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {} as any
  });

  // 模拟分页响应
  const createMockPaginatedResponse = <T>(
    items: T[],
    pagination: any,
    success = true
  ): AxiosResponse<PaginatedApiResponse<T>> => ({
    data: {
      success,
      data: {
        items,
        pagination
      }
    },
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {} as any
  });

  // 模拟直接数据响应
  const createMockDirectResponse = <T>(data: T): AxiosResponse<T> => ({
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {} as any
  });

  describe('smartExtract', () => {
    it('应该正确提取标准响应格式', () => {
      const userData = { id: 1, name: 'Test User' };
      const response = createMockStandardResponse(userData);

      const result = ResponseExtractor.smartExtract(response);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(userData);
      expect(result.error).toBeUndefined();
    });

    it('应该正确处理失败的标准响应', () => {
      const response = createMockStandardResponse(null, false, '用户不存在');

      const result = ResponseExtractor.smartExtract(response);

      expect(result.success).toBe(false);
      expect(result.data).toBeNull();
      expect(result.error).toBe('用户不存在');
    });

    it('应该正确提取分页响应格式', () => {
      const items = [{ id: 1 }, { id: 2 }];
      const pagination = { page: 1, pageSize: 10, total: 2, totalPages: 1 };
      const response = createMockPaginatedResponse(items, pagination);

      const result = ResponseExtractor.smartExtract(response);

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ items, pagination });
      expect(result.error).toBeUndefined();
    });

    it('应该正确提取直接数据响应', () => {
      const users = [{ id: 1 }, { id: 2 }];
      const response = createMockDirectResponse(users);

      const result = ResponseExtractor.smartExtract(response);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(users);
      expect(result.error).toBeUndefined();
    });

    it('应该使用类型验证功能', () => {
      interface User {
        id: number;
        name: string;
      }

      const validUser = { id: 1, name: 'Valid User' };
      const response = createMockStandardResponse(validUser);

      const result = ResponseExtractor.smartExtract<User>(response, {
        enableTypeValidation: true,
        expectedType: 'object'
      });

      expect(result.success).toBe(true);
      expect(result.data).toEqual(validUser);
    });

    it('应该处理类型验证失败的情况', () => {
      interface User {
        id: number;
        name: string;
      }

      const invalidData = { id: 'not-a-number' };
      const response = createMockStandardResponse(invalidData);

      const result = ResponseExtractor.smartExtract<User>(response, {
        enableTypeValidation: true,
        expectedType: 'object'
      });

      expect(result.success).toBe(true); // 仍然提取数据，但会有类型警告
    });
  });

  describe('extractData', () => {
    it('应该快速提取数据，失败时返回默认值', () => {
      const userData = { id: 1, name: 'Test User' };
      const response = createMockStandardResponse(userData);

      const data = ResponseExtractor.extractData(response, null);

      expect(data).toEqual(userData);
    });

    it('应该在失败时返回默认值', () => {
      const response = createMockStandardResponse(null, false, '用户不存在');

      const data = ResponseExtractor.extractData(response, null);

      expect(data).toBeNull();
    });
  });

  describe('batchExtract', () => {
    it('应该批量处理多个响应', () => {
      const userResponse = createMockStandardResponse({ id: 1, name: 'User 1' });
      const userListResponse = createMockStandardResponse([{ id: 2 }, { id: 3 }]);
      const errorResponse = createMockStandardResponse(null, false, '请求失败');

      const responses = [userResponse, userListResponse, errorResponse];
      const results = ResponseExtractor.batchExtract(responses);

      expect(results).toHaveLength(3);
      expect(results[0].success).toBe(true);
      expect(results[1].success).toBe(true);
      expect(results[2].success).toBe(false);

      expect(results[0].data).toEqual({ id: 1, name: 'User 1' });
      expect(results[1].data).toEqual([{ id: 2 }, { id: 3 }]);
      expect(results[2].error).toBe('请求失败');
    });
  });

  describe('extractAndTransform', () => {
    it('应该提取数据并应用转换函数', () => {
      const userData = { id: 1, firstName: 'John', lastName: 'Doe' };
      const response = createMockStandardResponse(userData);

      const result = ResponseExtractor.extractAndTransform(response, (data) => ({
        id: data.id,
        fullName: `${data.firstName} ${data.lastName}`
      }));

      expect(result.success).toBe(true);
      expect(result.data).toEqual({
        id: 1,
        fullName: 'John Doe'
      });
    });

    it('应该在转换失败时返回错误', () => {
      const invalidData = { id: 1 };
      const response = createMockStandardResponse(invalidData);

      const result = ResponseExtractor.extractAndTransform(response, (data) => {
        if (!data.firstName || !data.lastName) {
          throw new Error('缺少必需的名称字段');
        }
        return { fullName: `${data.firstName} ${data.lastName}` };
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('缺少必需的名称字段');
    });
  });

  describe('错误处理', () => {
    it('应该处理空的响应', () => {
      const response = { data: null } as AxiosResponse;

      const result = ResponseExtractor.smartExtract(response);

      expect(result.success).toBe(false);
      expect(result.error).toContain('响应数据为空');
    });

    it('应该处理无效的响应结构', () => {
      const response = { data: { someField: 'value' } } as AxiosResponse;

      const result = ResponseExtractor.smartExtract(response);

      expect(result.success).toBe(true); // 作为直接数据处理
      expect(result.data).toEqual({ someField: 'value' });
    });
  });

  describe('性能测试', () => {
    it('应该能够高效处理大量响应', () => {
      const start = Date.now();

      // 创建1000个响应进行批量处理
      const responses = Array.from({ length: 1000 }, (_, i) =>
        createMockStandardResponse({ id: i, name: `User ${i}` })
      );

      const results = ResponseExtractor.batchExtract(responses);

      const end = Date.now();
      const duration = end - start;

      expect(results).toHaveLength(1000);
      expect(results.every(r => r.success)).toBe(true);
      expect(duration).toBeLessThan(1000); // 应该在1秒内完成
    });
  });
});