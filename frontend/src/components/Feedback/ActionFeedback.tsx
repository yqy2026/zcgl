import React, { useState, useEffect } from 'react';
import { Button, Space, Typography, Alert, Card, Divider } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ReloadOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import styles from './ActionFeedback.module.css';

const { Text, Paragraph } = Typography;

export type ActionStatus = 'idle' | 'loading' | 'success' | 'error' | 'warning';

interface ActionResult {
  status: ActionStatus;
  message?: string;
  details?: string[];
  data?: unknown;
  error?: Error;
}

interface ActionFeedbackProps {
  result?: ActionResult;
  title?: string;
  showRetry?: boolean;
  showUndo?: boolean;
  showDetails?: boolean;
  autoHide?: boolean;
  autoHideDelay?: number;
  onRetry?: () => void;
  onUndo?: () => void;
  onClose?: () => void;
  style?: React.CSSProperties;
  className?: string;
}

const ActionFeedback: React.FC<ActionFeedbackProps> = ({
  result,
  title,
  showRetry = true,
  showUndo = false,
  showDetails = true,
  autoHide = false,
  autoHideDelay = 5000,
  onRetry,
  onUndo,
  onClose,
  style,
  className,
}) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (autoHide !== undefined && autoHide !== null && result?.status === 'success') {
      const timer = setTimeout(() => {
        setVisible(false);
        if (onClose !== undefined && onClose !== null) {
          onClose();
        }
      }, autoHideDelay);

      return () => clearTimeout(timer);
    }
  }, [result?.status, autoHide, autoHideDelay, onClose]);

  if (result === null || result === undefined || !visible) {
    return null;
  }

  // 获取状态配置
  const getStatusConfig = () => {
    switch (result.status) {
      case 'loading':
        return {
          type: 'info' as const,
          icon: <LoadingOutlined className={styles.feedbackIconLoading} />,
          title: '处理中...',
          showActions: false,
        };
      case 'success':
        return {
          type: 'success' as const,
          icon: <CheckCircleOutlined className={styles.feedbackIconSuccess} />,
          title: '操作成功',
          showActions: showUndo,
        };
      case 'error':
        return {
          type: 'error' as const,
          icon: <CloseCircleOutlined className={styles.feedbackIconError} />,
          title: '操作失败',
          showActions: showRetry,
        };
      case 'warning':
        return {
          type: 'warning' as const,
          icon: <ExclamationCircleOutlined className={styles.feedbackIconWarning} />,
          title: '操作警告',
          showActions: showRetry,
        };
      default:
        return {
          type: 'info' as const,
          icon: <InfoCircleOutlined className={styles.feedbackIconInfo} />,
          title: '信息',
          showActions: false,
        };
    }
  };

  const config = getStatusConfig();

  // 渲染操作按钮
  const renderActions = () => {
    if (!config.showActions) {
      return null;
    }

    const actions = [];

    if (result.status === 'error' && showRetry && onRetry) {
      actions.push(
        <Button key="retry" type="primary" size="small" icon={<ReloadOutlined />} onClick={onRetry}>
          重试
        </Button>
      );
    }

    if (result.status === 'success' && showUndo && onUndo) {
      actions.push(
        <Button key="undo" size="small" icon={<UndoOutlined />} onClick={onUndo}>
          撤销
        </Button>
      );
    }

    if (actions.length === 0) {
      return null;
    }

    return (
      <div className={styles.actionsContainer}>
        <Space size="small">{actions}</Space>
      </div>
    );
  };

  // 渲染详细信息
  const renderDetails = () => {
    if (
      showDetails === false ||
      result.details === null ||
      result.details === undefined ||
      result.details.length === 0
    ) {
      return null;
    }

    return (
      <div className={styles.detailsContainer}>
        <Divider className={styles.sectionDivider} />
        <Text type="secondary" className={styles.sectionLabel}>
          详细信息：
        </Text>
        <ul className={styles.detailsList}>
          {result.details.map(detail => (
            <li key={detail}>
              <Text type="secondary">{detail}</Text>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  // 渲染错误信息
  const renderErrorInfo = () => {
    if (result.status !== 'error' || !result.error) {
      return null;
    }

    return (
      <div className={styles.errorInfoContainer}>
        <Divider className={styles.sectionDivider} />
        <Text type="secondary" className={styles.sectionLabel}>
          错误信息：
        </Text>
        <Paragraph code className={styles.errorCodeBlock}>
          {result.error.message}
        </Paragraph>
      </div>
    );
  };

  return (
    <div style={style} className={className}>
      <Alert
        type={config.type}
        showIcon
        icon={config.icon}
        title={
          <Space>
            <Text strong>{title ?? config.title}</Text>
            {result.status === 'loading' && <Text type="secondary">(请稍候...)</Text>}
          </Space>
        }
        description={
          <div>
            {result.message !== null && result.message !== undefined && (
              <Text>{result.message}</Text>
            )}
            {renderDetails()}
            {renderErrorInfo()}
            {renderActions()}
          </div>
        }
        closable={result.status !== 'loading'}
        onClose={() => {
          setVisible(false);
          if (onClose !== undefined && onClose !== null) {
            onClose();
          }
        }}
      />
    </div>
  );
};

// 预设的操作反馈组件
export const LoadingFeedback: React.FC<{
  message?: string;
  title?: string;
}> = ({ message = '正在处理，请稍候...', title }) => (
  <ActionFeedback
    result={{
      status: 'loading',
      message,
    }}
    title={title}
  />
);

export const SuccessFeedback: React.FC<{
  message?: string;
  title?: string;
  showUndo?: boolean;
  onUndo?: () => void;
}> = ({ message = '操作已成功完成', title, showUndo, onUndo }) => (
  <ActionFeedback
    result={{
      status: 'success',
      message,
    }}
    title={title}
    showUndo={showUndo}
    onUndo={onUndo}
    autoHide
  />
);

export const ErrorFeedback: React.FC<{
  message?: string;
  title?: string;
  error?: Error;
  details?: string[];
  onRetry?: () => void;
}> = ({ message = '操作失败，请重试', title, error, details, onRetry }) => (
  <ActionFeedback
    result={{
      status: 'error',
      message,
      error,
      details,
    }}
    title={title}
    onRetry={onRetry}
  />
);

export const WarningFeedback: React.FC<{
  message?: string;
  title?: string;
  details?: string[];
  onRetry?: () => void;
}> = ({ message, title, details, onRetry }) => (
  <ActionFeedback
    result={{
      status: 'warning',
      message,
      details,
    }}
    title={title}
    onRetry={onRetry}
  />
);

// 操作反馈卡片
export const ActionFeedbackCard: React.FC<{
  result: ActionResult;
  title?: string;
  extra?: React.ReactNode;
  onRetry?: () => void;
  onUndo?: () => void;
}> = ({ result, title, extra, onRetry, onUndo }) => {
  const config = {
    loading: { icon: LoadingOutlined, iconClassName: styles.feedbackIconLoading },
    success: { icon: CheckCircleOutlined, iconClassName: styles.feedbackIconSuccess },
    error: { icon: CloseCircleOutlined, iconClassName: styles.feedbackIconError },
    warning: { icon: ExclamationCircleOutlined, iconClassName: styles.feedbackIconWarning },
    idle: { icon: InfoCircleOutlined, iconClassName: styles.feedbackIconIdle },
  };

  const statusConfig = config[result.status];
  const IconComponent = statusConfig.icon;

  return (
    <Card
      title={
        <Space>
          <IconComponent className={statusConfig.iconClassName} />
          <span>{title !== null && title !== undefined && title !== '' ? title : '操作状态'}</span>
        </Space>
      }
      extra={extra}
      size="small"
    >
      {result.message !== null && result.message !== undefined && result.message !== '' && (
        <Paragraph>{result.message}</Paragraph>
      )}

      {result.details !== null && result.details !== undefined && result.details.length > 0 && (
        <div>
          <Text type="secondary">详细信息：</Text>
          <ul className={styles.cardDetailsList}>
            {result.details.map(detail => (
              <li key={detail}>
                <Text type="secondary">{detail}</Text>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(result.status === 'error' && onRetry) || (result.status === 'success' && onUndo) ? (
        <div className={styles.cardActionsContainer}>
          <Space>
            {result.status === 'error' && onRetry && (
              <Button type="primary" size="small" icon={<ReloadOutlined />} onClick={onRetry}>
                重试
              </Button>
            )}
            {result.status === 'success' && onUndo && (
              <Button size="small" icon={<UndoOutlined />} onClick={onUndo}>
                撤销
              </Button>
            )}
          </Space>
        </div>
      ) : null}
    </Card>
  );
};

export default ActionFeedback;
