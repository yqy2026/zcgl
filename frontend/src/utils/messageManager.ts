/**
 * 全局消息管理器
 * 用于在非React组件（如工具函数）中显示消息提示
 *
 * 使用方式：
 * 1. 在App组件中初始化: MessageManager.init(App.useApp().message)
 * 2. 在任何地方使用: MessageManager.error('错误信息')
 */

import type { MessageInstance } from 'antd/es/message/interface';
import { message as antdMessage } from 'antd';

class MessageManagerClass {
  private messageInstance: MessageInstance | null = null;
  private isInitialized = false;

  /**
   * 初始化消息管理器（必须在App组件中调用）
   */
  init(messageApi: MessageInstance) {
    this.messageInstance = messageApi;
    this.isInitialized = true;
  }

  /**
   * 确保已初始化，如果未初始化则记录错误
   */
  private ensureInitialized(methodName: string) {
    if (!this.isInitialized || !this.messageInstance) {
      // 在开发环境下记录详细错误
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.error(
          `[MessageManager] 未初始化 - 调用了 ${methodName}()。` +
            '请在 App 组件中使用 MessageManager.init(App.useApp().message) 初始化。' +
            '当前使用静态 API 作为后备。'
        );
      }
      return false;
    }
    return true;
  }

  success(content: string, duration?: number) {
    if (this.ensureInitialized('success') && this.messageInstance) {
      return this.messageInstance.success({
        content,
        duration: duration ?? 3,
        key: `success-${Date.now()}`,
      });
    }
    // 后备方案：使用 Ant Design 静态 API
    return antdMessage.success(content, duration ?? 3);
  }

  error(content: string, duration?: number) {
    if (this.ensureInitialized('error') && this.messageInstance) {
      return this.messageInstance.error({
        content,
        duration: duration ?? 4,
        key: `error-${Date.now()}`,
      });
    }
    // 后备方案：使用 Ant Design 静态 API
    return antdMessage.error(content, duration ?? 4);
  }

  warning(content: string, duration?: number) {
    if (this.ensureInitialized('warning') && this.messageInstance) {
      return this.messageInstance.warning({
        content,
        duration: duration ?? 3,
        key: `warning-${Date.now()}`,
      });
    }
    // 后备方案：使用 Ant Design 静态 API
    return antdMessage.warning(content, duration ?? 3);
  }

  info(content: string, duration?: number) {
    if (this.ensureInitialized('info') && this.messageInstance) {
      return this.messageInstance.info({
        content,
        duration: duration ?? 3,
        key: `info-${Date.now()}`,
      });
    }
    // 后备方案：使用 Ant Design 静态 API
    return antdMessage.info(content, duration ?? 3);
  }

  loading(content: string, duration?: number) {
    if (this.ensureInitialized('loading') && this.messageInstance) {
      return this.messageInstance.loading({
        content,
        duration: duration ?? 0,
        key: `loading-${Date.now()}`,
      });
    }
    // 后备方案：使用 Ant Design 静态 API
    return antdMessage.loading(content, duration ?? 0);
  }

  destroy(key?: string) {
    if (this.ensureInitialized('destroy') && this.messageInstance) {
      if (key !== null && key !== undefined && key !== '') {
        void this.messageInstance.destroy(key);
      } else {
        void this.messageInstance.destroy();
      }
    } else {
      // 后备方案：使用 Ant Design 静态 API
      if (key !== null && key !== undefined && key !== '') {
        antdMessage.destroy(key);
      } else {
        antdMessage.destroy();
      }
    }
  }
}

// 导出单例
export const MessageManager = new MessageManagerClass();
