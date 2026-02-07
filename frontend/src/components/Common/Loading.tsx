/**
 * Loading Component
 *
 * A flexible loading component with multiple variants:
 * - Page-level full-screen loading
 * - Component-level inline loading
 * - Skeleton screens for lists/tables
 * - Button loading (disabled + spinner)
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React from 'react';
import { Spin, Skeleton, Button as AntButton, Space, Typography } from 'antd';
import type { ButtonProps } from 'antd/es/button';

const { Text } = Typography;

/**
 * Page-level loading component
 * Displays a centered spinner with optional message
 */
export interface PageLoadingProps {
  /**
   * Loading message to display
   * @default "加载中..."
   */
  message?: string;
  /**
   * Size of the spinner
   * @default "large"
   */
  size?: 'small' | 'default' | 'large';
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export const PageLoading: React.FC<PageLoadingProps> = ({
  message = '加载中...',
  size = 'large',
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
        minHeight: '400px',
        ...style,
      }}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={message}
    >
      <Spin size={size} />
      {message && (
        <Text
          style={{
            marginTop: 'var(--spacing-md)',
            color: 'var(--color-text-secondary)',
          }}
        >
          {message}
        </Text>
      )}
    </div>
  );
};

/**
 * Component-level inline loading
 * Displays a small spinner inline with content
 */
export interface InlineLoadingProps {
  /**
   * Loading message
   */
  message?: string;
  /**
   * Size of the spinner
   * @default "small"
   */
  size?: 'small' | 'default' | 'large';
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export const InlineLoading: React.FC<InlineLoadingProps> = ({
  message,
  size = 'small',
  className,
  style,
}) => {
  return (
    <div
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--spacing-sm)',
        ...style,
      }}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={message || '加载中'}
    >
      <Spin size={size} />
      {message && (
        <Text
          type="secondary"
          style={{
            color: 'var(--color-text-secondary)',
          }}
        >
          {message}
        </Text>
      )}
    </div>
  );
};

/**
 * Skeleton loading props
 */
export interface SkeletonLoadingProps {
  /**
   * Type of skeleton
   */
  type?: 'list' | 'table' | 'card';
  /**
   * Number of skeleton items to display
   * @default 6
   */
  count?: number;
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
 * Skeleton loading component
 * Displays placeholder content while data is loading
 */
export const SkeletonLoading: React.FC<SkeletonLoadingProps> = ({
  type = 'list',
  count = 6,
  className,
  style,
}) => {
  const renderListSkeleton = () => (
    <Space direction="vertical" style={{ width: '100%', gap: 'var(--spacing-md)' }} size="small">
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton.Input
          key={index}
          active
          size="large"
          style={{ width: '100%' }}
        />
      ))}
    </Space>
  );

  const renderTableSkeleton = () => (
    <div style={{ width: '100%' }}>
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton
          key={index}
          active
          paragraph={{ rows: 1 }}
          style={{ marginBottom: 'var(--spacing-md)' }}
        />
      ))}
    </div>
  );

  const renderCardSkeleton = () => (
    <Space direction="vertical" style={{ width: '100%', gap: 'var(--spacing-lg)' }} size="small">
      <Skeleton.Input active size="large" style={{ width: '40%' }} />
      <Skeleton.Input active size="small" style={{ width: '100%' }} />
      <Skeleton.Input active size="small" style={{ width: '100%' }} />
      <Skeleton.Button active size="large" style={{ width: '30%' }} />
    </Space>
  );

  const renderContent = () => {
    switch (type) {
      case 'list':
        return renderListSkeleton();
      case 'table':
        return renderTableSkeleton();
      case 'card':
        return renderCardSkeleton();
      default:
        return renderListSkeleton();
    }
  };

  return (
    <div
      className={className}
      style={style}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={`加载${type === 'list' ? '列表' : type === 'table' ? '表格' : '卡片'}数据中`}
    >
      {renderContent()}
    </div>
  );
};

/**
 * Loading button props
 */
export interface LoadingButtonProps extends Omit<ButtonProps, 'loading' | 'children'> {
  /**
   * Loading state
   */
  loading: boolean;
  /**
   * Button text when not loading
   */
  children: React.ReactNode;
  /**
   * Loading text to display
   * @default "加载中..."
   */
  loadingText?: string;
  /**
   * Icon to display when loading
   */
  loadingIcon?: React.ReactNode;
}

/**
 * Loading button component
 * A button with built-in loading state
 */
export const LoadingButton: React.FC<LoadingButtonProps> = ({
  loading,
  children,
  loadingText = '加载中...',
  loadingIcon,
  disabled,
  ...restProps
}) => {
  return (
    <AntButton
      {...restProps}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading ? (
        <Space size="small" style={{ gap: 'var(--spacing-sm)' }}>
          {loadingIcon || <Spin size="small" />}
          <span>{loadingText}</span>
        </Space>
      ) : (
        children
      )}
    </AntButton>
  );
};

/**
 * Default export with all loading variants
 */
const Loading: React.FC = () => {
  return null;
};

export default Object.assign(Loading, {
  Page: PageLoading,
  Inline: InlineLoading,
  Skeleton: SkeletonLoading,
  Button: LoadingButton,
});
