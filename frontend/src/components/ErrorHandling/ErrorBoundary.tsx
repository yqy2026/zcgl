/**
 * 统一错误边界组件
 * 合并了 ErrorBoundary 和 RouterErrorBoundary 的所有功能
 * 支持：重试机制、错误类型检测、路由导航、错误上报
 */

import React, { Component, ErrorInfo, ReactNode, useCallback } from 'react';
import { Result, Button, Typography, Alert, Space } from 'antd';
import { captureException } from '@/utils/errorMonitoring';
import { errorReportService, type FrontendErrorReportPayload } from '@/services/errorReportService';
import { isDevelopmentMode, isProductionMode } from '@/utils/runtimeEnv';
import styles from './ErrorBoundary.module.css';

const { Title, Paragraph, Text } = Typography;

// ===== 类型定义 =====

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  maxRetries?: number;
  showErrorDetails?: boolean;
}

type ErrorReport = FrontendErrorReportPayload;

interface RouterErrorHandlerProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onRetry: () => void;
  onGoHome: () => void;
  canRetry: boolean;
  retryCount: number;
  maxRetries: number;
  showErrorDetails?: boolean;
}

// ===== 错误边界组件 =====

class ErrorBoundaryComponent extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private maxRetries: number;

  constructor(props: ErrorBoundaryProps) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    };

    this.maxRetries =
      props.maxRetries !== undefined && props.maxRetries !== null ? props.maxRetries : 3;
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // 报告错误
    this.reportError(error, errorInfo);

    // 调用错误回调
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    console.error('错误边界捕获到错误:', error, errorInfo);
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    const errorReport: ErrorReport = {
      error: error.message,
      stack: error.stack ?? '',
      componentStack: errorInfo.componentStack ?? '',
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      retryCount: this.state.retryCount,
    };

    // 存储错误到 window 对象用于调试
    if (isDevelopmentMode()) {
      const debugWindow = window as Window & { __lastError?: ErrorReport };
      debugWindow.__lastError = errorReport;
    }

    // 发送错误报告到监控服务
    this.sendErrorReport(errorReport);
  };

  private sendErrorReport = async (errorReport: ErrorReport) => {
    try {
      if (isProductionMode()) {
        await errorReportService.report(errorReport);
      } else {
        // 开发环境打印到控制台
        console.group('错误报告');
        console.error('错误:', errorReport);
        console.groupEnd();
      }
    } catch (reportingError) {
      console.warn('错误报告发送失败:', reportingError);
    }
  };

  private handleRetry = () => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: prevState.retryCount + 1,
      }));
    }
  };

  private handleGoHome = () => {
    // 重置状态并导航到首页
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    });
    window.location.href = '/dashboard';
  };

  private canRetry = () => {
    return this.state.retryCount < this.maxRetries;
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback !== undefined && this.props.fallback !== null) {
        return this.props.fallback;
      }

      return (
        <ErrorHandler
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
          onGoHome={this.handleGoHome}
          canRetry={this.canRetry()}
          retryCount={this.state.retryCount}
          maxRetries={this.maxRetries}
          showErrorDetails={this.props.showErrorDetails}
        />
      );
    }

    return this.props.children;
  }
}

// ===== 错误处理UI组件 =====

const ErrorHandler: React.FC<RouterErrorHandlerProps> = ({
  error,
  errorInfo,
  onRetry,
  onGoHome,
  canRetry,
  retryCount,
  maxRetries,
  showErrorDetails = isDevelopmentMode(),
}) => {
  const handleGoBack = () => {
    // React 19 兼容性：ErrorBoundary 可能在 Router 上下文外渲染
    // 使用 window.history API 作为回退方案
    if (window.history.length > 1) {
      window.history.back();
    } else {
      // 没有历史记录时，导航到首页
      window.location.href = '/dashboard';
    }
  };

  const getErrorType = (error: Error | null) => {
    if (!error) return 'unknown';

    if (error.name === 'ChunkLoadError') return 'chunk_load';
    if (error.name === 'TypeError') return 'type_error';
    if (error.name === 'NetworkError') return 'network';
    if (error.message.includes('Loading chunk')) return 'chunk_load';

    return 'runtime';
  };

  const errorType = getErrorType(error);
  const isChunkLoadError = errorType === 'chunk_load';

  const getErrorTitle = () => {
    if (isChunkLoadError) return '页面加载失败';
    if (errorType === 'network') return '网络连接错误';
    if (errorType === 'type_error') return '页面渲染错误';
    return '页面访问出错';
  };

  const getErrorDescription = () => {
    if (isChunkLoadError === true) {
      return '页面资源加载失败，可能是网络问题或应用版本更新。请尝试刷新页面。';
    }
    if (errorType === 'network') {
      return '网络连接异常，请检查网络连接后重试。';
    }
    if (errorType === 'type_error') {
      return '页面渲染时发生错误，这可能是临时的技术问题。';
    }
    return '访问页面时遇到了意外错误，我们正在努力修复。';
  };

  return (
    <div className={styles.errorPageContainer}>
      <Result
        status="error"
        title={getErrorTitle()}
        subTitle={getErrorDescription()}
        extra={[
          <Space key="actions" orientation="vertical" size="middle">
            <Space>
              {canRetry && (
                <Button type="primary" onClick={onRetry}>
                  重试 ({retryCount}/{maxRetries})
                </Button>
              )}
              <Button onClick={handleGoBack}>返回上一页</Button>
              <Button onClick={onGoHome}>返回首页</Button>
              {isChunkLoadError && (
                <Button onClick={() => window.location.reload()}>刷新页面</Button>
              )}
            </Space>

            {isChunkLoadError && (
              <Alert
                title="提示"
                description="如果您经常遇到此错误，请尝试清除浏览器缓存或联系技术支持。"
                type="info"
                showIcon
              />
            )}
          </Space>,
        ]}
      />

      {showErrorDetails && error && (
        <div className={styles.errorDetailsPanel}>
          <Title level={5}>错误详情 (开发模式)</Title>
          <Paragraph>
            <Text strong>错误类型:</Text> {errorType}
            <br />
            <Text strong>错误消息:</Text> {error.message}
            <br />
            <Text strong>重试次数:</Text> {retryCount}/{maxRetries}
          </Paragraph>

          {error.stack !== undefined && error.stack !== null && error.stack !== '' && (
            <details className={styles.detailsBlock}>
              <summary>错误堆栈</summary>
              <pre className={styles.stackTrace}>{error.stack}</pre>
            </details>
          )}

          {errorInfo !== null &&
            errorInfo.componentStack !== undefined &&
            errorInfo.componentStack !== null &&
            errorInfo.componentStack !== '' && (
              <details className={styles.detailsBlock}>
                <summary>组件堆栈</summary>
                <pre className={styles.stackTrace}>{errorInfo.componentStack}</pre>
              </details>
            )}
        </div>
      )}
    </div>
  );
};

// ===== Hooks =====

/**
 * 错误处理 Hook - 用于在组件内部处理错误
 */
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const captureError = React.useCallback((error: Error) => {
    console.error('Error captured by useErrorHandler:', error);
    setError(error);

    // 存储错误到 window 对象用于调试
    if (isDevelopmentMode()) {
      const debugWindow = window as Window & {
        __lastError?: { message: string; stack?: string; timestamp: string };
      };
      debugWindow.__lastError = {
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString(),
      };
    }

    // 生产环境下上报错误
    if (isProductionMode()) {
      captureException(error, {
        component: 'ErrorBoundary',
        action: 'captureError',
        route: window.location.pathname,
      });
    }
  }, []);

  return {
    error,
    captureError,
    resetError,
    hasError: !!error,
  };
};

/**
 * 路由错误处理 Hook - 用于路由级别的错误处理
 * 注意：此 Hook 需要在 Router 上下文中使用
 */
export const useRouterErrorBoundary = () => {
  const handleError = useCallback((error: Error, fallbackPath: string = '/dashboard') => {
    console.error('路由错误:', error);

    // 根据错误类型决定处理方式
    if (error.name === 'ChunkLoadError') {
      // 资源加载错误，刷新页面
      window.location.reload();
    } else {
      // 其他错误，使用 window.location 导航到安全页面
      // 这样即使在 Router 上下文之外也能工作
      window.location.href = fallbackPath;
    }
  }, []);

  return { handleError };
};

// ===== 导出 =====

export const ErrorBoundary = ErrorBoundaryComponent;

// 预定义的专用错误边界
export const AssetErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary
      maxRetries={2}
      onError={error => {
        console.error('资产管理模块错误:', error);
      }}
    >
      {children}
    </ErrorBoundary>
  );
};

export const SystemErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary
      maxRetries={1}
      onError={error => {
        console.error('系统管理模块错误:', error);
      }}
    >
      {children}
    </ErrorBoundary>
  );
};

export default ErrorBoundary;
