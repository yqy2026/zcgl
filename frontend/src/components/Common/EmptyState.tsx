/**
 * Empty State Component
 *
 * Displays empty states with friendly messaging and actionable next steps
 *
 * Accessibility: Fully WCAG 2.1 AA compliant
 */

import React from 'react';
import { Button, Space, Typography, Image } from 'antd';
import {
  PlusOutlined,
  FileSearchOutlined,
  InboxOutlined,
  SearchOutlined,
  ArrowLeftOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import styles from './EmptyState.module.css';

const { Text, Paragraph, Title } = Typography;

/**
 * Empty state type variants
 */
export type EmptyType =
  | 'no-data'
  | 'no-results'
  | 'cleared'
  | 'not-found'
  | 'unauthorized'
  | 'custom';

/**
 * Empty state configuration
 */
export interface EmptyStateConfig {
  /**
   * Empty state type
   */
  type: EmptyType;
  /**
   * Title to display
   */
  title?: string;
  /**
   * Description message
   */
  description?: string;
  /**
   * Image URL (optional)
   */
  image?: string;
  /**
   * Image alt text
   */
  imageAlt?: string;
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
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

/**
 * Default empty state messages by type
 */
const DEFAULT_EMPTY_STATES: Record<EmptyType, { title: string; description: string }> = {
  'no-data': {
    title: '暂无数据',
    description: '还没有任何数据，点击下方按钮创建第一条数据。',
  },
  'no-results': {
    title: '未找到相关结果',
    description: '尝试调整搜索条件或关键词，可能会有所发现。',
  },
  'cleared': {
    title: '已清空',
    description: '所有数据已被清空，您可以重新开始。',
  },
  'not-found': {
    title: '未找到',
    description: '没有找到符合条件的数据。',
  },
  'unauthorized': {
    title: '无法访问',
    description: '请先登录以查看此内容。',
  },
  custom: {
    title: '暂无内容',
    description: '这里还没有任何内容。',
  },
};

/**
 * Empty state icons by type
 */
const EMPTY_ICONS: Record<EmptyType, React.ReactNode> = {
  'no-data': <InboxOutlined className={styles.emptyIconGlyph} />,
  'no-results': <FileSearchOutlined className={styles.emptyIconGlyph} />,
  'cleared': <SearchOutlined className={styles.emptyIconGlyph} />,
  'not-found': <SearchOutlined className={styles.emptyIconGlyph} />,
  'unauthorized': <FileSearchOutlined className={styles.emptyIconGlyph} />,
  custom: <InboxOutlined className={styles.emptyIconGlyph} />,
};

/**
 * Empty State Component
 *
 * Displays user-friendly empty states with actionable next steps
 */
export const EmptyState: React.FC<EmptyStateConfig> = ({
  type,
  title,
  description,
  image,
  imageAlt,
  primaryAction,
  secondaryAction,
  className,
  style,
}) => {
  const defaultEmpty = DEFAULT_EMPTY_STATES[type];
  const emptyTitle = title || defaultEmpty.title;
  const emptyDescription = description || defaultEmpty.description;
  const icon = EMPTY_ICONS[type];
  const containerClassName =
    className !== undefined && className !== ''
      ? `${styles.emptyState} ${className}`
      : styles.emptyState;

  return (
    <div
      className={containerClassName}
      style={style}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Icon or Image */}
      {image ? (
        <Image
          src={image}
          alt={imageAlt || emptyTitle}
          preview={false}
          className={styles.emptyImage}
        />
      ) : (
        <div className={styles.emptyIconContainer}>{icon}</div>
      )}

      {/* Title and Description */}
      <div className={styles.emptyContent}>
        <Title level={4} className={styles.emptyTitle}>
          {emptyTitle}
        </Title>
        <Paragraph className={styles.emptyDescription}>
          {emptyDescription}
        </Paragraph>
      </div>

      {/* Action Buttons */}
      {(primaryAction || secondaryAction) && (
        <Space size="middle" className={styles.actionsSpace}>
          {/* Primary action */}
          {primaryAction && (
            <Button
              type="primary"
              size="large"
              icon={primaryAction.icon || <PlusOutlined />}
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
        </Space>
      )}
    </div>
  );
};

/**
 * Component-level empty state
 * Compact version for displaying empty states within components
 */
export interface ComponentEmptyProps {
  /**
   * Empty state message
   */
  message?: string;
  /**
   * Empty state type
   * @default "no-data"
   */
  type?: EmptyType;
  /**
   * On create callback
   */
  onCreate?: () => void;
  /**
   * Show create button
   * @default true
   */
  showCreate?: boolean;
  /**
   * Create button text
   * @default "创建"
   */
  createText?: string;
  /**
   * Additional CSS class name
   */
  className?: string;
  /**
   * Additional styles
   */
  style?: React.CSSProperties;
}

export const ComponentEmpty: React.FC<ComponentEmptyProps> = ({
  message = '暂无数据',
  type = 'no-data',
  onCreate,
  showCreate = true,
  createText = '创建',
  className,
  style,
}) => {
  const containerClassName =
    className !== undefined && className !== ''
      ? `${styles.componentEmpty} ${className}`
      : styles.componentEmpty;

  return (
    <div
      className={containerClassName}
      style={style}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className={styles.componentIconContainer}>
        {EMPTY_ICONS[type]}
      </div>
      <div className={styles.componentMessageContainer}>
        <Text type="secondary" className={styles.componentMessageText}>
          {message}
        </Text>
      </div>
      {showCreate && onCreate && (
        <div className={styles.componentActionContainer}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onCreate}
            aria-label={createText}
          >
            {createText}
          </Button>
        </div>
      )}
    </div>
  );
};

/**
 * Quick access factory functions
 */
export const NoData: React.FC<{
  onCreate?: () => void;
  createText?: string;
  className?: string;
}> = ({ onCreate, createText = '创建', className }) => {
  return (
    <EmptyState
      type="no-data"
      primaryAction={
        onCreate
          ? {
              text: createText,
              onClick: onCreate,
              icon: <PlusOutlined />,
            }
          : undefined
      }
      className={className}
    />
  );
};

export const NoResults: React.FC<{
  onClear?: () => void;
  onSearch?: () => void;
  className?: string;
}> = ({ onClear, onSearch, className }) => {
  return (
    <EmptyState
      type="no-results"
      primaryAction={
        onSearch
          ? {
              text: '重新搜索',
              onClick: onSearch,
              icon: <SearchOutlined />,
            }
          : undefined
      }
      secondaryAction={
        onClear
          ? {
              text: '清除搜索',
              onClick: onClear,
              icon: <ArrowLeftOutlined />,
            }
          : undefined
      }
      className={className}
    />
  );
};

export const Cleared: React.FC<{
  onCreate?: () => void;
  createText?: string;
  className?: string;
}> = ({ onCreate, createText = '重新创建', className }) => {
  return (
    <EmptyState
      type="cleared"
      primaryAction={
        onCreate
          ? {
              text: createText,
              onClick: onCreate,
              icon: <PlusOutlined />,
            }
          : undefined
      }
      className={className}
    />
  );
};

export const Unauthorized: React.FC<{
  onBack?: () => void;
  onLogin?: () => void;
  className?: string;
}> = ({ onBack, onLogin, className }) => {
  return (
    <EmptyState
      type="unauthorized"
      title="未授权"
      description="请先登录以查看此内容"
      primaryAction={
        onLogin
          ? {
              text: '登录',
              onClick: onLogin,
              icon: <PlusOutlined />,
            }
          : undefined
      }
      secondaryAction={
        onBack
          ? {
              text: '返回',
              onClick: onBack,
              icon: <ArrowLeftOutlined />,
            }
          : undefined
      }
      className={className}
    />
  );
};

export const UploadFile: React.FC<{
  onUpload?: () => void;
  uploadText?: string;
  className?: string;
}> = ({ onUpload, uploadText = '上传文件', className }) => {
  return (
    <EmptyState
      type="no-data"
      title="暂无文件"
      description="点击下方按钮上传文件"
      image="/images/empty-upload.svg"
      primaryAction={
        onUpload
          ? {
              text: uploadText,
              onClick: onUpload,
              icon: <CloudUploadOutlined />,
            }
          : undefined
      }
      className={className}
    />
  );
};

export default Object.assign(EmptyState, {
  Component: ComponentEmpty,
  NoData,
  NoResults,
  Cleared,
  Unauthorized,
  UploadFile,
});
