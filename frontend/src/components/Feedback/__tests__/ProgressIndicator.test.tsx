/**
 * ProgressIndicator 组件测试
 * 覆盖进度类型、状态图标与预设组件
 */

import { describe, it, expect } from 'vitest';
import { screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import ProgressIndicator, {
  LoadingProgress,
  UploadProgress,
  ProcessSteps,
  ProcessTimeline,
  ProgressCard,
} from '../ProgressIndicator';

interface ProgressMockProps {
  percent?: number;
  status?: string;
  showInfo?: boolean;
  strokeColor?: string;
  type?: string;
  width?: number;
  strokeWidth?: number;
}

interface TypographyTextMockProps {
  children?: ReactNode;
  type?: string;
  strong?: boolean;
  style?: CSSProperties;
}

interface TypographyTitleMockProps {
  children?: ReactNode;
  level?: number;
  style?: CSSProperties;
}

interface SpaceMockProps {
  children?: ReactNode;
}

interface CardMockProps {
  children?: ReactNode;
  title?: ReactNode;
  extra?: ReactNode;
  actions?: ReactNode[];
}

interface StepsItemMock {
  title?: ReactNode;
  description?: ReactNode;
  status?: string;
  icon?: ReactNode;
}

interface StepsMockProps {
  items?: StepsItemMock[];
  current?: number;
  status?: string;
  direction?: string;
  size?: string;
}

interface TimelineMockProps {
  children?: ReactNode;
}

interface TimelineItemMockProps {
  children?: ReactNode;
  color?: string;
  dot?: ReactNode;
}

interface IconMockProps {
  style?: CSSProperties;
}

vi.mock('antd', () => {
  const Timeline = ({ children }: TimelineMockProps) => <div data-testid="timeline">{children}</div>;
  Timeline.displayName = 'MockTimeline';

  const TimelineItem = ({ children, color, dot }: TimelineItemMockProps) => (
    <div data-testid="timeline-item" data-color={color}>
      {dot && <div data-testid="timeline-dot">{dot}</div>}
      {children}
    </div>
  );
  TimelineItem.displayName = 'MockTimelineItem';
  Timeline.Item = TimelineItem;

  const Progress = ({ percent, status, showInfo, strokeColor, type, width }: ProgressMockProps) => (
    <div
      data-testid="progress"
      data-percent={percent}
      data-status={status}
      data-show-info={showInfo}
      data-type={type || 'line'}
      data-width={width}
      data-stroke-color={strokeColor}
    />
  );
  Progress.displayName = 'MockProgress';

  const TypographyText = ({ children, type, strong, style }: TypographyTextMockProps) => (
    <span data-testid="text" data-type={type} data-strong={strong} style={style}>
      {children}
    </span>
  );
  TypographyText.displayName = 'MockTypographyText';

  const TypographyTitle = ({ children, level, style }: TypographyTitleMockProps) => (
    <div data-testid="title" data-level={level} style={style}>
      {children}
    </div>
  );
  TypographyTitle.displayName = 'MockTypographyTitle';

  const Space = ({ children }: SpaceMockProps) => <div data-testid="space">{children}</div>;
  Space.displayName = 'MockSpace';

  const Card = ({ children, title, extra, actions }: CardMockProps) => (
    <div data-testid="card">
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      {children}
      {actions && <div data-testid="card-actions">{actions}</div>}
    </div>
  );
  Card.displayName = 'MockCard';

  const Steps = ({ items = [], current, status, direction, size }: StepsMockProps) => (
    <div
      data-testid="steps"
      data-current={current}
      data-status={status}
      data-direction={direction}
      data-size={size}
    >
      {items.map((item, index) => (
        <div key={index} data-testid="step-item" data-status={item.status}>
          <div data-testid="step-title">{item.title}</div>
          {item.description && <div data-testid="step-description">{item.description}</div>}
          {item.icon && <div data-testid="step-icon">{item.icon}</div>}
        </div>
      ))}
    </div>
  );
  Steps.displayName = 'MockSteps';

  return {
    Progress,
    Typography: {
      Text: TypographyText,
      Title: TypographyTitle,
    },
    Space,
    Card,
    Steps,
    Timeline,
  };
});

vi.mock('@ant-design/icons', () => {
  const CheckCircleOutlined = ({ style }: IconMockProps) => (
    <div data-testid="icon-check" style={style} />
  );
  const LoadingOutlined = ({ style }: IconMockProps) => (
    <div data-testid="icon-loading" style={style} />
  );
  const ClockCircleOutlined = ({ style }: IconMockProps) => (
    <div data-testid="icon-clock" style={style} />
  );
  const ExclamationCircleOutlined = ({ style }: IconMockProps) => (
    <div data-testid="icon-exclamation" style={style} />
  );

  CheckCircleOutlined.displayName = 'CheckCircleOutlined';
  LoadingOutlined.displayName = 'LoadingOutlined';
  ClockCircleOutlined.displayName = 'ClockCircleOutlined';
  ExclamationCircleOutlined.displayName = 'ExclamationCircleOutlined';

  return {
    CheckCircleOutlined,
    LoadingOutlined,
    ClockCircleOutlined,
    ExclamationCircleOutlined,
  };
});

describe('ProgressIndicator', () => {
  it('renders line progress with defaults', () => {
    renderWithProviders(<ProgressIndicator />);

    const progress = screen.getByTestId('progress');
    expect(progress).toHaveAttribute('data-type', 'line');
    expect(progress).toHaveAttribute('data-percent', '0');
  });

  it('renders circle progress with small size', () => {
    renderWithProviders(<ProgressIndicator type="circle" size="small" percent={50} />);

    const progress = screen.getByTestId('progress');
    expect(progress).toHaveAttribute('data-type', 'circle');
    expect(progress).toHaveAttribute('data-width', '80');
  });

  it('renders title and success icon', () => {
    renderWithProviders(<ProgressIndicator title="完成" status="success" percent={100} />);

    expect(screen.getByTestId('title')).toHaveTextContent('完成');
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
  });

  it('renders steps with items and current index', () => {
    renderWithProviders(
      <ProcessSteps
        title="流程"
        current={1}
        steps={[
          { title: '步骤1', status: 'finish' },
          { title: '步骤2', status: 'process' },
        ]}
      />
    );

    const steps = screen.getByTestId('steps');
    expect(steps).toHaveAttribute('data-current', '1');
    expect(screen.getAllByTestId('step-item')).toHaveLength(2);
  });

  it('renders timeline with status-based colors', () => {
    renderWithProviders(
      <ProcessTimeline
        steps={[
          { title: '事件1', status: 'finish' },
          { title: '事件2', status: 'error' },
          { title: '事件3', status: 'process' },
          { title: '事件4', status: 'wait' },
        ]}
      />
    );

    const items = screen.getAllByTestId('timeline-item');
    expect(items[0]).toHaveAttribute('data-color', 'green');
    expect(items[1]).toHaveAttribute('data-color', 'red');
    expect(items[2]).toHaveAttribute('data-color', 'blue');
    expect(items[3]).toHaveAttribute('data-color', 'gray');
  });

  it('renders LoadingProgress defaults', () => {
    renderWithProviders(<LoadingProgress />);

    expect(screen.getByTestId('title')).toHaveTextContent('加载中');
    expect(screen.getByTestId('icon-loading')).toBeInTheDocument();
  });

  it('renders UploadProgress description and success status', () => {
    renderWithProviders(<UploadProgress percent={100} fileName="demo.xlsx" />);

    expect(screen.getByTestId('text')).toHaveTextContent('正在上传: demo.xlsx');
    expect(screen.getByTestId('progress')).toHaveAttribute('data-status', 'success');
  });

  it('renders ProgressCard content and actions', () => {
    renderWithProviders(
      <ProgressCard
        title="导入进度"
        description="处理中"
        percent={60}
        status="active"
        extra={<button type="button">额外</button>}
        actions={[<button key="pause" type="button">暂停</button>]}
      />
    );

    expect(screen.getByTestId('card-title')).toHaveTextContent('导入进度');
    expect(screen.getByTestId('card-extra')).toHaveTextContent('额外');
    expect(screen.getByTestId('card-actions')).toHaveTextContent('暂停');
  });
});
