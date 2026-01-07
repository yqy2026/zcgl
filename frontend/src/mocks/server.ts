/**
 * MSW Server 配置
 * 配置Mock Service Worker服务器用于测试
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

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
