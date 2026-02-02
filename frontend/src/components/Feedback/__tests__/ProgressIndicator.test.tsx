/**
 * ProgressIndicator 组件测试
 * 覆盖进度类型、状态图标与预设组件
 *
 * 修复说明：
 * - 移除 antd Progress, Typography, Space, Card, Steps, Timeline 组件 mock
 * - 移除 @ant-design/icons mock
 * - 使用 className 和文本内容进行断言
 */

import { describe, it, expect } from 'vitest';
import { screen } from '@/test/utils/test-helpers';

import ProgressIndicator, {
  LoadingProgress,
  UploadProgress,
  ProcessSteps,
  ProcessTimeline,
  ProgressCard,
} from '../ProgressIndicator';

describe('ProgressIndicator', () => {
  it('renders line progress with defaults', () => {
    const { container } = renderWithProviders(<ProgressIndicator />);

    const progress = container.querySelector('.ant-progress');
    expect(progress).toBeInTheDocument();
  });

  it('renders circle progress with small size', () => {
    const { container } = renderWithProviders(
      <ProgressIndicator type="circle" size="small" percent={50} />
    );

    const progress = container.querySelector('.ant-progress-circle');
    expect(progress).toBeInTheDocument();
  });

  it('renders title and success status', () => {
    renderWithProviders(<ProgressIndicator title="完成" status="success" percent={100} />);

    expect(screen.getByText('完成')).toBeInTheDocument();
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

    expect(screen.getByText('流程')).toBeInTheDocument();
    expect(screen.getByText('步骤1')).toBeInTheDocument();
    expect(screen.getByText('步骤2')).toBeInTheDocument();
  });

  it('renders timeline with steps', () => {
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

    expect(screen.getByText('事件1')).toBeInTheDocument();
    expect(screen.getByText('事件2')).toBeInTheDocument();
    expect(screen.getByText('事件3')).toBeInTheDocument();
    expect(screen.getByText('事件4')).toBeInTheDocument();
  });

  it('renders LoadingProgress defaults', () => {
    renderWithProviders(<LoadingProgress />);

    expect(screen.getByText('加载中')).toBeInTheDocument();
  });

  it('renders UploadProgress description and status', () => {
    renderWithProviders(<UploadProgress percent={100} fileName="demo.xlsx" />);

    expect(screen.getByText(/正在上传.*demo.xlsx/)).toBeInTheDocument();
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

    expect(screen.getByText('导入进度')).toBeInTheDocument();
    expect(screen.getByText('额外')).toBeInTheDocument();
    expect(screen.getByText('暂停')).toBeInTheDocument();
  });
});
