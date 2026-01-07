// API错误处理工具

import { message, notification } from 'antd';
import type { ErrorResponse } from '@/types/api';
import { HTTP_STATUS, ERROR_CODES } from '../api/config';
import { createLogger } from '../utils/logger';

const errorLogger = createLogger('ErrorHandler');

// 扩展错误接口以支持更多属性
interface ExtendedError extends Partial<ErrorResponse> {
  code?: string;
  status?: number;
  stack?: string;
  name?: string;
  data?: unknown;
  message?: string;
}

// 日志数据接口
export interface LogData {
  timestamp: string;
  level: 'error' | 'warning' | 'info';
  message: string;
  error?: {
    message?: string;
    stack?: string;
    name?: string;
  };
  context?: Record<string, unknown>;
  userAgent?: string;
  url?: string;
}

export interface ErrorHandlerOptions {
  showMessage?: boolean;
  showNotification?: boolean;
  logError?: boolean;
  customHandler?: (error: ErrorResponse) => void;
}

export class ApiErrorHandler {
  private static instance: ApiErrorHandler;

  private constructor() {}

  static getInstance(): ApiErrorHandler {
    if (ApiErrorHandler.instance === null || ApiErrorHandler.instance === undefined) {
      ApiErrorHandler.instance = new ApiErrorHandler();
    }
    return ApiErrorHandler.instance;
  }

  // 处理API错误
  handle(error: ErrorResponse | ExtendedError, options: ErrorHandlerOptions = {}): void {
    const {
      showMessage = true,
      showNotification = false,
      logError = true,
      customHandler,
    } = options;

    const extendedError = error as ExtendedError;

    // 记录错误日志
    if (logError) {
      this.logError(extendedError);
    }

    // 自定义错误处理
    if (customHandler) {
      customHandler(error as ErrorResponse);
      return;
    }

    // 根据错误类型显示不同的提示
    if (showMessage) {
      this.showErrorMessage(extendedError);
    }

    if (showNotification) {
      this.showErrorNotification(extendedError);
    }

    // 特殊错误处理
    this.handleSpecialErrors(extendedError);
  }

  // 显示错误消息
  private showErrorMessage(error: ExtendedError): void {
    const errorMessage = this.getErrorMessage(error);

    // 避免显示重复的错误消息
    message.destroy();
    message.error(errorMessage);
  }

  // 显示错误通知
  private showErrorNotification(error: ExtendedError): void {
    const errorMessage = this.getErrorMessage(error);

    notification.error({
      message: '请求出错',
      description: errorMessage,
      duration: 4.5,
    });
  }

  // 获取错误消息
  private getErrorMessage(error: ExtendedError): string {
    if (error.message !== null && error.message !== undefined && error.message !== '') {
      return error.message;
    }

    if (error.code !== undefined && error.code in ERROR_CODES) {
      return ERROR_CODES[error.code as keyof typeof ERROR_CODES];
    }

    if (error.status !== undefined) {
      const entries = Object.entries(HTTP_STATUS) as [string, number][];
      const found = entries.find(([_, val]) => val === error.status);
      if (found) {
        return found[0];
      }
      return `HTTP Error ${error.status}`;
    }

    return '未知错误，请稍后重试';
  }

  // 记录错误日志
  private logError(error: ExtendedError): void {
    const logData: LogData = {
      timestamp: new Date().toISOString(),
      level: 'error',
      message: this.getErrorMessage(error),
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name,
      },
      context: error.data as Record<string, unknown>,
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    // 使用logger
    errorLogger.error('API Error', logData as unknown as Error);

    // 在开发环境下打印详细错误
    if (process.env.NODE_ENV === 'development') {
      // console.error('API Error Details:', error)
    }
  }

  // 处理特殊错误
  private handleSpecialErrors(error: ExtendedError): void {
    // 处理401未授权错误
    if (error.status === 401) {
      this.handleUnauthorized();
    }

    // 处理403禁止访问错误
    if (error.status === 403) {
      // 可以在这里跳转到403页面或者清除部分权限状态
    }
  }

  // 处理未授权
  private handleUnauthorized(): void {
    // 清除本地存储的token
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    // 跳转到登录页
    if (window.location.pathname !== '/login') {
      message.warning('登录已过期，请重新登录');
      // 使用window.location跳转，因为这里是非React组件环境
      setTimeout(() => {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
      }, 1000);
    }
  }
}

// 导出单例实例
export const errorHandler = ApiErrorHandler.getInstance();

// 辅助函数：创建错误处理器
export const createErrorHandler = (options: ErrorHandlerOptions = {}) => {
  return (error: ErrorResponse) => {
    errorHandler.handle(error, options);
  };
};

// 辅助函数：包装Promise处理错误
export const withErrorHandling = async <T>(
  promise: Promise<T>,
  options: ErrorHandlerOptions = {}
): Promise<[T | null, ErrorResponse | null]> => {
  try {
    const data = await promise;
    return [data, null];
  } catch (error) {
    const errorResponse = error as ErrorResponse;
    errorHandler.handle(errorResponse, options);
    return [null, errorResponse];
  }
};

// Legacy alias for backward compatibility
export const handleApiError = (error: unknown, options: ErrorHandlerOptions = {}): void => {
  errorHandler.handle(error as ErrorResponse, options);
};
