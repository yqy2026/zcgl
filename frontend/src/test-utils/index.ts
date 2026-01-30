/**
 * 测试工具库统一导出
 *
 * 使用示例:
 * ```typescript
 * import { createMockAsset, createAntdMock } from '@/test-utils';
 *
 * // 创建 Mock 数据
 * const asset = createMockAsset({ property_name: '自定义名称' });
 *
 * // Mock Ant Design
 * vi.mock('antd', () => createAntdMock());
 * ```
 */

// 工厂函数
export * from './factories';

// Mock 模块
export * from './mocks';
