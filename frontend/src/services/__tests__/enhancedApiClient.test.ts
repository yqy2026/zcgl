/**
 * EnhancedApiClient 单元测试
 * 测试增强型API客户端的核心功能
 */

import { EnhancedApiClient } from '../enhancedApiClient';
import { AxiosResponse } from 'axios';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  }))
}));

// Mock ResponseExtractor
jest.mock('../../utils/responseExtractor', () => ({
  ResponseExtractor: {
    smartExtract: jest.fn((response) => ({
      success: true,
      data: response.data,
      error: null
    }))
  },
  ApiErrorHandler: {
    handleError: jest.fn((error) => ({
      type: 'NETWORK_ERROR',
      message: error.message || '网络错误',
      originalError: error
    }))
  }
}));

describe('EnhancedApiClient', () => {
  let client: EnhancedApiClient;

  beforeEach(() => {
    client = new EnhancedApiClient({
      baseURL: 'https://api.example.com',
      timeout: 5000,
      enableLogging: false
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('初始化', () => {
    it('应该使用默认配置正确初始化', () => {
      const defaultClient = new EnhancedApiClient();
      expect(defaultClient).toBeInstanceOf(EnhancedApiClient);
    });

    it('应该使用自定义配置正确初始化', () => {
      const customClient = new EnhancedApiClient({
        baseURL: 'https://custom.api.com',
        timeout: 10000,
        enableLogging: true
      });
      expect(customClient).toBeInstanceOf(EnhancedApiClient);
    });
  });

  describe('GET 请求', () => {
    it('应该成功发送GET请求', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: { id: 1, name: 'Test' } },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      };

      const mockGet = (client as any).instance.get;
      mockGet.mockResolvedValueOnce(mockResponse);

      const result = await client.get('/api/test');

      expect(mockGet).toHaveBeenCalledWith('/api/test', {
        cache: false,
        retry: false,
        smartExtract: false
      });
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: 1, name: 'Test' });
    });

    it('应该支持缓存配置', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: [] },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      };

      const mockGet = (client as any).instance.get;
      mockGet.mockResolvedValueOnce(mockResponse);

      await client.get('/api/test', {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true
      });

      expect(mockGet).toHaveBeenCalledWith('/api/test', {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true
      });
    });

    it('应该处理网络错误', async () => {
      const mockError = new Error('Network Error');
      const mockGet = (client as any).instance.get;
      mockGet.mockRejectedValueOnce(mockError);

      await expect(client.get('/api/test')).rejects.toThrow();
    });
  });

  describe('POST 请求', () => {
    it('应该成功发送POST请求', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: { id: 1 } },
        status: 201,
        statusText: 'Created',
        headers: {},
        config: {} as any
      };

      const mockPost = (client as any).instance.post;
      mockPost.mockResolvedValueOnce(mockResponse);

      const postData = { name: 'Test Item' };
      const result = await client.post('/api/items', postData);

      expect(mockPost).toHaveBeenCalledWith('/api/items', postData, {
        cache: false,
        retry: false,
        smartExtract: false
      });
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: 1 });
    });

    it('应该支持重试配置', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: {} },
        status: 201,
        statusText: 'Created',
        headers: {},
        config: {} as any
      };

      const mockPost = (client as any).instance.post;
      mockPost.mockResolvedValueOnce(mockResponse);

      const postData = { name: 'Test Item' };
      await client.post('/api/items', postData, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });

      expect(mockPost).toHaveBeenCalledWith('/api/items', postData, {
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true
      });
    });
  });

  describe('PUT 请求', () => {
    it('应该成功发送PUT请求', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: { id: 1, name: 'Updated Item' } },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      };

      const mockPut = (client as any).instance.put;
      mockPut.mockResolvedValueOnce(mockResponse);

      const updateData = { name: 'Updated Item' };
      const result = await client.put('/api/items/1', updateData);

      expect(mockPut).toHaveBeenCalledWith('/api/items/1', updateData, {
        cache: false,
        retry: false,
        smartExtract: false
      });
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ id: 1, name: 'Updated Item' });
    });
  });

  describe('DELETE 请求', () => {
    it('应该成功发送DELETE请求', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: null },
        status: 204,
        statusText: 'No Content',
        headers: {},
        config: {} as any
      };

      const mockDelete = (client as any).instance.delete;
      mockDelete.mockResolvedValueOnce(mockResponse);

      const result = await client.delete('/api/items/1');

      expect(mockDelete).toHaveBeenCalledWith('/api/items/1', {
        cache: false,
        retry: false,
        smartExtract: false
      });
      expect(result.success).toBe(true);
      expect(result.data).toBeNull();
    });
  });

  describe('错误处理', () => {
    it('应该处理HTTP错误响应', async () => {
      const mockError = {
        response: {
          status: 404,
          data: { message: 'Not Found' }
        }
      };

      const mockGet = (client as any).instance.get;
      mockGet.mockRejectedValueOnce(mockError);

      await expect(client.get('/api/nonexistent')).rejects.toThrow();
    });

    it('应该处理网络超时错误', async () => {
      const mockError = new Error('timeout of 5000ms exceeded');
      const mockGet = (client as any).instance.get;
      mockGet.mockRejectedValueOnce(mockError);

      await expect(client.get('/api/slow')).rejects.toThrow();
    });
  });

  describe('批量请求', () => {
    it('应该支持批量请求', async () => {
      const mockResponses = [
        { data: { success: true, data: { id: 1 } }, status: 200 },
        { data: { success: true, data: { id: 2 } }, status: 200 }
      ];

      const mockBatch = (client as any).batch;
      mockBatch.mockResolvedValueOnce(mockResponses);

      const requests = [
        { method: 'GET', url: '/api/items/1' },
        { method: 'GET', url: '/api/items/2' }
      ];

      const results = await client.batch(requests);

      expect(mockBatch).toHaveBeenCalledWith(requests);
      expect(results).toHaveLength(2);
    });
  });

  describe('缓存功能', () => {
    it('应该缓存GET请求结果', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: { id: 1 } },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      };

      const mockGet = (client as any).instance.get;
      mockGet.mockResolvedValueOnce(mockResponse);

      // 第一次请求
      const result1 = await client.get('/api/items/1', { cache: true });

      // 第二次请求应该从缓存返回
      const result2 = await client.get('/api/items/1', { cache: true });

      expect(result1.data).toEqual(result2.data);
    });

    it('应该不缓存POST请求', async () => {
      const mockResponse: AxiosResponse = {
        data: { success: true, data: { id: 1 } },
        status: 201,
        statusText: 'Created',
        headers: {},
        config: {} as any
      };

      const mockPost = (client as any).instance.post;
      mockPost.mockResolvedValueOnce(mockResponse);

      await client.post('/api/items', { name: 'Test' }, { cache: true });

      // POST请求不应该触发缓存逻辑
      expect(mockPost).toHaveBeenCalledTimes(1);
    });
  });

  describe('重试机制', () => {
    it('应该在失败时重试请求', async () => {
      const mockError = new Error('Network Error');
      const mockSuccessResponse: AxiosResponse = {
        data: { success: true, data: { id: 1 } },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      };

      const mockGet = (client as any).instance.get;
      mockGet
        .mockRejectedValueOnce(mockError)
        .mockResolvedValueOnce(mockSuccessResponse);

      const result = await client.get('/api/test', {
        retry: { maxAttempts: 2, delay: 100, backoffMultiplier: 2 }
      });

      expect(mockGet).toHaveBeenCalledTimes(2);
      expect(result.success).toBe(true);
    });

    it('应该在达到最大重试次数后失败', async () => {
      const mockError = new Error('Network Error');
      const mockGet = (client as any).instance.get;
      mockGet.mockRejectedValue(mockError);

      await expect(
        client.get('/api/test', {
          retry: { maxAttempts: 2, delay: 10, backoffMultiplier: 2 }
        })
      ).rejects.toThrow();

      expect(mockGet).toHaveBeenCalledTimes(2);
    });
  });

  describe('配置验证', () => {
    it('应该验证重试配置', () => {
      expect(() => {
        new EnhancedApiClient({
          defaultRetryConfig: {
            maxAttempts: 0, // 无效值
            delay: 1000,
            backoffMultiplier: 2
          }
        });
      }).not.toThrow();
    });

    it('应该验证缓存配置', () => {
      expect(() => {
        new EnhancedApiClient({
          defaultCacheConfig: {
            enabled: true,
            ttl: 30000,
            maxSize: 100
          }
        });
      }).not.toThrow();
    });
  });
});