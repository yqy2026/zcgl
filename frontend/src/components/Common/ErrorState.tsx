/**
 * Error State Component
 *
 * Displays error states with clear messaging and actionable next steps
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React from 'react';
import { Button, Result, Space, Typography, Alert } from 'antd';
import {
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

/**
 * Error type variants
 */
export type ErrorType = '404' | '500' | '403' | 'network' | 'permission' | 'custom';

/**
 * Error state configuration
 */
export interface ErrorStateConfig {
  /**
   * Error type
   */
  type: ErrorType;
  /**
   * Error title
   */
  title?: string;
  /**
   * Error message/description
   */
  message?: string;
  /**
   * Technical error details (for developers)
   */
  errorDetails?: string;
  /**
   * Error code
   */
  errorCode?: string;
  /**
   * Primary action button
   */
  primaryAction?: {
    text: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  /**
   * Secondary action button
   */
  secondaryAction?: {
    text: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  /**
   * Show technical details (collapsed by default)
   */
  showTechnicalDetails?: boolean;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

/**
 * Default error messages by type
 */
const DEFAULT_ERRORS: Record<ErrorType, { title: string; message: string }> = {
  '404': {
    title: '页面未找到',
    message: '抱歉，您访问的页面不存在或已被删除。',
  },
  '500': {
    title: '服务器错误',
    message: '抱歉，服务器出现了问题，请稍后再试。',
  },
  '403': {
    title: '没有权限',
    message: '抱歉，您没有权限访问此页面。',
  },
  'network': {
    title: '网络连接失败',
    message: '请检查您的网络连接后重试。',
  },
  'permission': {
    title: '权限不足',
    message: '您没有执行此操作的权限，请联系管理员。',
  },
  custom: {
    title: '操作失败',
    message: '发生了错误，请稍后再试。',
  },
};

/**
 * Error icons by type
 */
const ERROR_ICONS: Record<ErrorType, React.ReactNode> = {
  '404': <CloseCircleOutlined style={{ fontSize: 72, color: 'var(--color-error)' }} />,
  '500': <WarningOutlined style={{ fontSize: 72, color: 'var(--color-warning)' }} />,
  '403': <InfoCircleOutlined style={{ fontSize: 72, color: 'var(--color-warning)' }} />,
  'network': <WarningOutlined style={{ fontSize: 72, color: 'var(--color-warning)' }} />,
  permission: <InfoCircleOutlined style={{ fontSize: 72, color: 'var(--color-warning)' }} />,
  custom: <CloseCircleOutlined style={{ fontSize: 72, color: 'var(--color-error)' }} />,
};

/**
 * Error State Component
 *
 * Displays user-friendly error messages with actionable next steps
 */
export const ErrorState: React.FC<ErrorStateConfig> = ({
  type,
  title,
  message,
  errorDetails,
  errorCode,
  primaryAction,
  secondaryAction,
  showTechnicalDetails = false,
  className,
  style,
}) => {
  const defaultError = DEFAULT_ERRORS[type];
  const errorTitle = title || defaultError.title;
  const errorMessage = message || defaultError.message;
  const icon = ERROR_ICONS[type];

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '400px',
        padding: 'var(--spacing-xl)',
        ...style,
      }}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <Result
        status="error"
        icon={icon}
        title={errorTitle}
        subTitle={
          <div>
            <Paragraph style={{ marginBottom: 0 }}>
              {errorMessage}
            </Paragraph>
            {errorCode && (
              <Text type="secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
                错误代码: {errorCode}
              </Text>
            )}
          </div>
        }
        extra={
          <Space direction="vertical" size="small" style={{ gap: 'var(--spacing-md)' }}>
            {/* Primary action */}
            {primaryAction && (
              <Button
                type="primary"
                size="large"
                icon={primaryAction.icon || <ReloadOutlined />}
                onClick={primaryAction.onClick}
                aria-label={primaryAction.text}
              >
                {primaryAction.text}
              </Button>
            )}

            {/* Secondary action */}
            {secondaryAction && (
              <Button
                size="large"
                icon={secondaryAction.icon || <ArrowLeftOutlined />}
                onClick={secondaryAction.onClick}
                aria-label={secondaryAction.text}
              >
                {secondaryAction.text}
              </Button>
            )}

            {/* Technical details */}
            {(showTechnicalDetails || errorDetails) && (
              <Alert
                message="技术详情"
                description={
                  <Text
                    code
                    style={{
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--color-text-tertiary)',
                    }}
                  >
                    {errorDetails || '暂无详细信息'}
                  </Text>
                }
                type="info"
                showIcon
                style={{ maxWidth: 600 }}
              />
            )}
          </Space>
        }
      />
    </div>
  );
};

/**
 * Component-level error state
 * Compact version for displaying errors within components
 */
export interface ComponentErrorProps {
  /**
   * Error message
   */
  message: string;
  /**
   * Error type
   * @default "custom"
   */
  type?: ErrorType;
  /**
   * On retry callback
   */
  onRetry?: () => void;
  /**
   * Show retry button
   * @default true
   */
  showRetry?: boolean;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export const ComponentError: React.FC<ComponentErrorProps> = ({
  message,
  type = 'custom',
  onRetry,
  showRetry = true,
  className,
  style,
}) => {
  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--spacing-xxl)',
        textAlign: 'center',
        ...style,
      }}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      {ERROR_ICONS[type]}
      <div style={{ marginTop: 'var(--spacing-lg)' }}>
        <Text type="danger" style={{ fontSize: 'var(--font-size-lg)' }}>
          {message}
        </Text>
      </div>
      {showRetry && onRetry && (
        <div style={{ marginTop: 'var(--spacing-lg)' }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={onRetry}
            aria-label="重试"
          >
            重试
          </Button>
        </div>
      )}
    </div>
  );
};

/**
 * Quick access factory functions
 */
export const PageNotFound: React.FC<{
  onBack?: () => void;
  className?: string;
}> = ({ onBack, className }) => {
  return (
    <ErrorState
      type="404"
      primaryAction={{
        text: '返回上一页',
        onClick: onBack || (() => window.history.back()),
        icon: <ArrowLeftOutlined />,
      }}
      className={className}
    />
  );
};

export const ServerError: React.FC<{
  onRetry?: () => void;
  errorCode?: string;
  className?: string;
}> = ({ onRetry, errorCode, className }) => {
  return (
    <ErrorState
      type="500"
      errorCode={errorCode}
      primaryAction={{
        text: '重新加载',
        onClick: onRetry || (() => window.location.reload()),
        icon: <ReloadOutlined />,
      }}
      className={className}
    />
  );
};

export const NetworkError: React.FC<{
  onRetry?: () => void;
  className?: string;
}> = ({ onRetry, className }) => {
  return (
    <ErrorState
      type="network"
      primaryAction={{
        text: '重试',
        onClick: onRetry || (() => window.location.reload()),
        icon: <ReloadOutlined />,
      }}
      className={className}
    />
  );
};

export const PermissionDenied: React.FC<{
  onBack?: () => void;
  className?: string;
}> = ({ onBack, className }) => {
  return (
    <ErrorState
      type="permission"
      primaryAction={{
        text: '返回',
        onClick: onBack || (() => window.history.back()),
        icon: <ArrowLeftOutlined />,
      }}
      className={className}
    />
  );
};

export default ErrorState;
