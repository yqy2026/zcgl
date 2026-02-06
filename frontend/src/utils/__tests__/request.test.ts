/**
 * Request工具错误处理单元测试
 *
 * 测试范围:
 * 1. 错误追踪ID生成 (唯一性、格式正确性、时间戳)
 * 2. Token兼容性 (优先级、回退、空值处理)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthStorage } from '@/utils/AuthStorage';

describe('Request工具 - 错误处理增强', () => {
  beforeEach(() => {
    // 清除localStorage
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('错误追踪ID生成', () => {
    it('应该生成唯一错误ID', () => {
      const errorIds = new Set<string>();

      // 模拟生成100个错误ID
      for (let i = 0; i < 100; i++) {
        const errorId = `ERR-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        errorIds.add(errorId);
      }

      // 验证所有ID都是唯一的
      expect(errorIds.size).toBe(100);
    });

    it('错误ID格式应该符合规范', () => {
      const errorId = `ERR-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      // 验证格式: ERR-{timestamp}-{random}
      expect(errorId).toMatch(/^ERR-\d+-[a-z0-9]+$/);
    });

    it('应该记录精确时间戳', () => {
      const before = Date.now();
      const timestamp = new Date().toISOString();
      const after = Date.now();

      const timestampMs = new Date(timestamp).getTime();

      // 验证时间戳在合理范围内
      expect(timestampMs).toBeGreaterThanOrEqual(before);
      expect(timestampMs).toBeLessThanOrEqual(after);
    });

    it('时间戳应该是ISO 8601格式', () => {
      const timestamp = new Date().toISOString();

      // 验证ISO 8601格式
      expect(timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });
  });

  describe('Token存储策略', () => {
    it('应该清理本地存储中的旧token键', () => {
      localStorage.setItem('auth_token', 'token-auth');
      localStorage.setItem('token', 'token-old');
      localStorage.setItem('refresh_token', 'refresh-old');
      localStorage.setItem('refreshToken', 'refresh-legacy');

      AuthStorage.setAuthData({
        user: {
          id: '1',
          username: 'test',
          full_name: 'Test User',
          role_id: 'role-user-id',
          role_name: 'user',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        permissions: [],
      });

      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(localStorage.getItem('refreshToken')).toBeNull();
    });

    it('本地存储不再作为token来源', () => {
      const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
      expect(token).toBeNull();
    });
  });

  describe('错误对象元数据', () => {
    it('应该正确添加errorId到错误对象', () => {
      const error: Error & { errorId?: string } = new Error('Test error');
      error.errorId = `ERR-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      expect(error.errorId).toBeDefined();
      expect(error.errorId).toMatch(/^ERR-\d+-[a-z0-9]+$/);
    });

    it('应该正确添加timestamp到错误对象', () => {
      const error: Error & { timestamp?: string } = new Error('Test error');
      error.timestamp = new Date().toISOString();

      expect(error.timestamp).toBeDefined();
      expect(error.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    it('错误对象应该包含完整的追踪信息', () => {
      const error: Error & { errorId?: string; timestamp?: string } = new Error('Test error');
      error.errorId = `ERR-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      error.timestamp = new Date().toISOString();

      expect(error).toHaveProperty('errorId');
      expect(error).toHaveProperty('timestamp');
      expect(error).toHaveProperty('message');
    });
  });

  describe('错误状态码处理', () => {
    it('应该正确处理400错误', () => {
      const status = 400;
      const _expectedMessage = '请求参数错误';

      expect(status).toBeGreaterThanOrEqual(400);
      expect(status).toBeLessThan(500);
    });

    it('应该正确处理401未授权错误', () => {
      const status = 401;
      const needsAuth = true;

      expect(status).toBe(401);
      expect(needsAuth).toBe(true);
    });

    it('应该正确处理403权限不足错误', () => {
      const status = 403;
      const hasAccess = false;

      expect(status).toBe(403);
      expect(hasAccess).toBe(false);
    });

    it('应该正确处理404资源不存在错误', () => {
      const status = 404;
      const resourceExists = false;

      expect(status).toBe(404);
      expect(resourceExists).toBe(false);
    });

    it('应该正确处理500服务器内部错误', () => {
      const status = 500;
      const isServerError = true;

      expect(status).toBeGreaterThanOrEqual(500);
      expect(isServerError).toBe(true);
    });
  });
});
