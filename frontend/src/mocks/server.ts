/**
 * MSW Server 配置
 * 配置Mock Service Worker服务器用于测试
 */

import { setupServer } from 'msw/node';
import { handlers as oldHandlers } from './handlers';
import { handlers as newHandlers } from '@/test/utils/handlers';
import { allHandlers as statisticsHandlers } from '@/test/utils/handlers-statistics';

// 合并所有 handlers
export const handlers = [
  ...statisticsHandlers,  // 新增：统计 API handlers (优先级高)
  ...oldHandlers,
  ...newHandlers,
];

/**
 * 创建MSW服务器实例
 *
 * 使用说明:
 * 1. 在测试文件中导入: import { mswServer } from '@/mocks/server'
 * 2. 在beforeAll中启动: mswServer.listen()
 * 3. 在afterAll中关闭: mswServer.close()
 * 4. 在afterEach中重置: mswServer.resetHandlers()
 */
export const mswServer = setupServer(...handlers);

// 默认导出
export default mswServer;
