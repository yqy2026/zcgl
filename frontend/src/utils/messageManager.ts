/**
 * 全局消息管理器
 * 用于在非React组件（如工具函数）中显示消息提示
 *
 * 使用方式：
 * 1. 在App组件中初始化: MessageManager.init(App.useApp().message)
 * 2. 在任何地方使用: MessageManager.error('错误信息')
 */

import type { MessageInstance } from 'antd/es/message/interface';

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
   * 确保已初始化
   */
  private ensureInitialized() {
    if (!this.isInitialized || !this.messageInstance) {
      // 如果未初始化，使用静态方法作为后备
      // 这会产生警告，但至少功能可用
      if (process.env.NODE_ENV === 'development') {
        console.warn(
          'MessageManager 未初始化。请在 App 组件中使用 MessageManager.init(App.useApp().message) 初始化。' +
          '当前使用静态方法作为后备，可能无法使用动态主题。'
        );
      }
    }
  }

  success(content: string, duration?: number) {
    this.ensureInitialized();
    if (this.messageInstance) {
      return this.messageInstance.success({
        content,
        duration: duration ?? 3,
        key: `success-${Date.now()}`,
      });
    }
  }

  error(content: string, duration?: number) {
    this.ensureInitialized();
    if (this.messageInstance) {
      return this.messageInstance.error({
        content,
        duration: duration ?? 4,
        key: `error-${Date.now()}`,
      });
    }
  }

  warning(content: string, duration?: number) {
    this.ensureInitialized();
    if (this.messageInstance) {
      return this.messageInstance.warning({
        content,
        duration: duration ?? 3,
        key: `warning-${Date.now()}`,
      });
    }
  }

  info(content: string, duration?: number) {
    this.ensureInitialized();
    if (this.messageInstance) {
      return this.messageInstance.info({
        content,
        duration: duration ?? 3,
        key: `info-${Date.now()}`,
      });
    }
  }

  loading(content: string, duration?: number) {
    this.ensureInitialized();
    if (this.messageInstance) {
      return this.messageInstance.loading({
        content,
        duration: duration ?? 0,
        key: `loading-${Date.now()}`,
      });
    }
  }

  destroy(key?: string) {
    this.ensureInitialized();
    if (this.messageInstance) {
      if (key !== null && key !== undefined && key !== '') {
        void this.messageInstance.destroy(key);
      } else {
        void this.messageInstance.destroy();
      }
    }
  }
}

// 导出单例
export const MessageManager = new MessageManagerClass();
