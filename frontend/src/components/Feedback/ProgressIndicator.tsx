import React from 'react';
import { Progress, Typography, Space, Card, Steps, Timeline } from 'antd';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;
const { Step } = Steps;

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
        return '#52c41a';
      case 'exception':
        return '#ff4d4f';
      case 'active':
        return '#1890ff';
      default:
        return '#1890ff';
    }
  };

  // 获取状态图标
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'exception':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'active':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 渲染进度条
  const renderProgress = () => {
    const commonProps = {
      percent,
      status,
      showInfo,
      strokeWidth,
      strokeColor: getStatusColor(),
    };

    switch (type) {
      case 'line':
        return <Progress {...commonProps} />;

      case 'circle':
        return (
          <Progress
            {...commonProps}
            type="circle"
            width={size === 'small' ? 80 : size === 'large' ? 120 : 100}
          />
        );

      case 'dashboard':
        return (
          <Progress
            {...commonProps}
            type="dashboard"
            width={size === 'small' ? 80 : size === 'large' ? 120 : 100}
          />
        );

      case 'steps':
        return (
          <Steps
            current={current}
            status={status === 'exception' ? 'error' : undefined}
            direction={direction}
            size={size === 'large' ? 'default' : size}
          >
            {steps.map((step, index) => (
              <Step
                key={index}
                title={step.title}
                description={step.description}
                status={step.status}
                icon={step.icon}
              />
            ))}
          </Steps>
        );

      case 'timeline':
        return (
          <Timeline>
            {steps.map((step, index) => (
              <Timeline.Item
                key={index}
                color={
                  step.status === 'finish'
                    ? 'green'
                    : step.status === 'error'
                      ? 'red'
                      : step.status === 'process'
                        ? 'blue'
                        : 'gray'
                }
                dot={step.icon}
              >
                <div>
                  <Text strong>{step.title}</Text>
                  {step.description != null && (
                    <div>
                      <Text type="secondary">{step.description}</Text>
                    </div>
                  )}
                </div>
              </Timeline.Item>
            ))}
          </Timeline>
        );

      default:
        return <Progress {...commonProps} />;
    }
  };

  return (
    <div style={style} className={className}>
      {(title != null || description != null) && (
        <div style={{ marginBottom: 16 }}>
          {title != null && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
              {getStatusIcon()}
              <Title level={5} style={{ margin: '0 0 0 8px' }}>
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
        {status === 'success' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
        {status === 'exception' && <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
        <span>{title}</span>
      </Space>
    }
    extra={extra}
    actions={actions}
  >
    {description != null && (
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        {description}
      </Text>
    )}
    <Progress
      percent={percent}
      status={status}
      strokeColor={
        status === 'success' ? '#52c41a' : status === 'exception' ? '#ff4d4f' : '#1890ff'
      }
    />
  </Card>
);

export default ProgressIndicator;
