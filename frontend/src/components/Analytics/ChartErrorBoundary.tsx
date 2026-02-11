import { Component, ErrorInfo, ReactNode } from 'react';
import { Alert, Button } from 'antd';
import { createLogger } from '@/utils/logger';
import styles from './ChartErrorBoundary.module.css';

const componentLogger = createLogger('ChartErrorBoundary');

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ChartErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    componentLogger.error('Chart Error Boundary caught an error:', error);
    this.setState({
      error,
      errorInfo,
    });

    if (this.props.onError !== undefined && this.props.onError !== null) {
      this.props.onError(error, errorInfo);
    }
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined && this.props.fallback !== null) {
        return this.props.fallback;
      }

      return (
        <div className={styles.errorContainer} role="alert" aria-live="polite">
          <Alert
            title="图表加载失败"
            description={
              <div className={styles.errorDescription}>
                <p className={styles.errorMessage}>无法渲染图表，可能是数据格式有问题。</p>
                {this.state.error && (
                  <p className={styles.errorDetail}>
                    错误详情: {this.state.error.message}
                  </p>
                )}
              </div>
            }
            type="error"
            showIcon
            className={styles.errorAlert}
          />
          <Button size="small" className={styles.retryButton} onClick={this.handleRetry}>
            重试
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChartErrorBoundary;
