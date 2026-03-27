import React from 'react';
import { Progress, Typography, Space, Card, Steps, Timeline } from 'antd';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import styles from './ProgressIndicator.module.css';

const { Text, Title } = Typography;

export type ProgressType = 'line' | 'circle' | 'dashboard' | 'steps' | 'timeline';
export type ProgressStatus = 'normal' | 'success' | 'exception' | 'active';

interface ProgressStep {
  title: string;
  description?: string;
  status?: 'wait' | 'process' | 'finish' | 'error';
  icon?: React.ReactNode;
}

interface ProgressIndicatorProps {
  type?: ProgressType;
  percent?: number;
  status?: ProgressStatus;
  title?: string;
  description?: string;
  showInfo?: boolean;
  strokeWidth?: number;
  size?: 'small' | 'default' | 'large';
  steps?: ProgressStep[];
  current?: number;
  direction?: 'horizontal' | 'vertical';
  style?: React.CSSProperties;
  className?: string;
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  type = 'line',
  percent = 0,
  status = 'normal',
  title,
  description,
  showInfo = true,
  strokeWidth,
  size = 'default',
  steps = [],
  current = 0,
  direction = 'horizontal',
  style,
  className,
}) => {
  // 获取状态颜色
  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'var(--color-success)';
      case 'exception':
        return 'var(--color-error)';
      case 'active':
        return 'var(--color-primary)';
      default:
        return 'var(--color-primary)';
    }
  };

  // 获取状态图标
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined className={styles.successIcon} />;
      case 'exception':
        return <ExclamationCircleOutlined className={styles.exceptionIcon} />;
      case 'active':
        return <LoadingOutlined className={styles.activeIcon} />;
      default:
        return <ClockCircleOutlined className={styles.defaultIcon} />;
    }
  };

  // 渲染进度条
  const renderProgress = () => {
    const commonProps = {
      percent,
      status,
      showInfo,
      strokeColor: getStatusColor(),
    };
    const lineSize = strokeWidth != null ? { height: strokeWidth } : undefined;
    const circularSize = size === 'small' ? 80 : size === 'large' ? 120 : 100;

    switch (type) {
      case 'line':
        return <Progress {...commonProps} size={lineSize} />;

      case 'circle':
        return <Progress {...commonProps} type="circle" size={circularSize} />;

      case 'dashboard':
        return <Progress {...commonProps} type="dashboard" size={circularSize} />;

      case 'steps':
        return (
          <Steps
            current={current}
            status={status === 'exception' ? 'error' : undefined}
            orientation={direction}
            size={size === 'large' ? 'default' : size}
            items={steps.map(step => ({
              key: step.title,
              title: step.title,
              description: step.description,
              status: step.status,
              icon: step.icon,
            }))}
          />
        );

      case 'timeline':
        return (
          <Timeline
            items={steps.map(step => ({
              key: step.title,
              color:
                step.status === 'finish'
                  ? 'green'
                  : step.status === 'error'
                    ? 'red'
                    : step.status === 'process'
                      ? 'blue'
                      : 'gray',
              icon: step.icon,
              content: (
                <div>
                  <Text strong>{step.title}</Text>
                  {step.description != null && (
                    <div>
                      <Text type="secondary">{step.description}</Text>
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        );

      default:
        return <Progress {...commonProps} />;
    }
  };

  return (
    <div style={style} className={className}>
      {(title != null || description != null) && (
        <div className={styles.headerSection}>
          {title != null && (
            <div className={styles.titleRow}>
              {getStatusIcon()}
              <Title level={5} className={styles.titleText}>
                {title}
              </Title>
            </div>
          )}
          {description != null && <Text type="secondary">{description}</Text>}
        </div>
      )}

      {renderProgress()}
    </div>
  );
};

// 预设的进度指示器组件
export const LoadingProgress: React.FC<{
  title?: string;
  description?: string;
  percent?: number;
}> = ({ title = '加载中', description = '请稍候...', percent = 0 }) => (
  <ProgressIndicator
    type="line"
    percent={percent}
    status="active"
    title={title}
    description={description}
  />
);

export const UploadProgress: React.FC<{
  percent: number;
  fileName?: string;
}> = ({ percent, fileName }) => (
  <ProgressIndicator
    type="line"
    percent={percent}
    status={percent === 100 ? 'success' : 'active'}
    title="文件上传"
    description={fileName != null ? `正在上传: ${fileName}` : '正在上传文件...'}
  />
);

export const ProcessSteps: React.FC<{
  steps: ProgressStep[];
  current: number;
  title?: string;
}> = ({ steps, current, title }) => (
  <ProgressIndicator type="steps" steps={steps} current={current} title={title} />
);

export const ProcessTimeline: React.FC<{
  steps: ProgressStep[];
  title?: string;
}> = ({ steps, title }) => <ProgressIndicator type="timeline" steps={steps} title={title} />;

// 进度卡片组件
export const ProgressCard: React.FC<{
  title: string;
  description?: string;
  percent: number;
  status?: ProgressStatus;
  extra?: React.ReactNode;
  actions?: React.ReactNode[];
}> = ({ title, description, percent, status = 'normal', extra, actions }) => (
  <Card
    title={
      <Space>
        {status === 'active' && <LoadingOutlined />}
        {status === 'success' && <CheckCircleOutlined className={styles.successIcon} />}
        {status === 'exception' && <ExclamationCircleOutlined className={styles.exceptionIcon} />}
        <span>{title}</span>
      </Space>
    }
    extra={extra}
    actions={actions}
  >
    {description != null && (
      <Text type="secondary" className={styles.cardDescription}>
        {description}
      </Text>
    )}
    <Progress
      percent={percent}
      status={status}
      strokeColor={
        status === 'success'
          ? 'var(--color-success)'
          : status === 'exception'
            ? 'var(--color-error)'
            : 'var(--color-primary)'
      }
    />
  </Card>
);

export default ProgressIndicator;
