import { Component, ErrorInfo, ReactNode } from 'react';
import { Alert, Button } from 'antd';
import { createLogger } from '@/utils/logger';

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

    if (this.props.onError) {
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
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <Alert
            message="图表加载失败"
            description={
              <div>
                <p>无法渲染图表，可能是数据格式有问题。</p>
                {this.state.error && (
                  <p style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
                    错误详情: {this.state.error.message}
                  </p>
                )}
              </div>
            }
            type="error"
            showIcon
            action={
              <Button size="small" onClick={this.handleRetry}>
                重试
              </Button>
            }
            style={{ marginBottom: '16px' }}
          />
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChartErrorBoundary;
