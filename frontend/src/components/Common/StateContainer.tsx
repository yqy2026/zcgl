/**
 * Reusable State Containers
 * Provides consistent styling for loading, empty, and error states
 */

import React from 'react';
import { Spin, Empty, Result, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

interface LoadingContainerProps {
  loading?: boolean;
  text?: string;
  children?: React.ReactNode;
}

export const LoadingContainer: React.FC<LoadingContainerProps> = ({
  loading = true,
  text = '加载中...',
  children,
}) => {
  if (!loading) {
    return <>{children}</>;
  }

  return (
    <div className="loadingContainer">
      <Spin size="large" />
      {text && <div className="marginTopMd">{text}</div>}
    </div>
  );
};

interface EmptyStateContainerProps {
  description?: string;
  action?: React.ReactNode;
}

export const EmptyStateContainer: React.FC<EmptyStateContainerProps> = ({
  description = '暂无数据',
  action,
}) => {
  return (
    <div className="emptyState">
      <Empty description={description} />
      {action && <div className="marginTopMd">{action}</div>}
    </div>
  );
};

interface ErrorStateContainerProps {
  title?: string;
  error?: Error | string;
  onRetry?: () => void;
  action?: React.ReactNode;
}

export const ErrorStateContainer: React.FC<ErrorStateContainerProps> = ({
  title = '加载失败',
  error,
  onRetry,
  action,
}) => {
  const errorMessage = error instanceof Error ? error.message : error;

  return (
    <div className="errorContainer">
      <Result
        status="error"
        title={title}
        subTitle={errorMessage}
        extra={
          <>
            {onRetry && (
              <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
                重试
              </Button>
            )}
            {action}
          </>
        }
      />
    </div>
  );
};

interface ContentSectionProps {
  children: React.ReactNode;
  spacing?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const ContentSection: React.FC<ContentSectionProps> = ({
  children,
  spacing = 'lg',
  className,
}) => {
  const spacingClass = `marginBottom${spacing.charAt(0).toUpperCase() + spacing.slice(1)}`;

  return <div className={`${spacingClass} ${className ?? ''}`}>{children}</div>;
};
