/**
 * ActionFeedback 组件测试
 * 测试操作反馈组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock Ant Design components
vi.mock('antd', () => ({
  Button: ({
    children,
    onClick,
    'data-testid': testId,
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    'data-testid'?: string;
  }) => (
    <button data-testid={testId || 'button'} onClick={onClick}>
      {children}
    </button>
  ),
  Space: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="space">{children}</div>
  ),
  Typography: {
    Text: ({ children }: { children?: React.ReactNode }) => (
      <span data-testid="text">{children}</span>
    ),
    Paragraph: ({ children }: { children?: React.ReactNode }) => (
      <p data-testid="paragraph">{children}</p>
    ),
  },
  Alert: ({
    type,
    message,
    description,
    onClose,
  }: {
    type?: string;
    message?: React.ReactNode;
    description?: React.ReactNode;
    onClose?: () => void;
  }) => (
    <div data-testid="alert" data-type={type}>
      <div data-testid="alert-message">{message}</div>
      <div data-testid="alert-description">{description}</div>
      <button data-testid="alert-close" onClick={onClose}>
        Close
      </button>
    </div>
  ),
  Card: ({
    children,
    title,
  }: {
    children?: React.ReactNode;
    title?: React.ReactNode;
  }) => (
    <div data-testid="card">
      <div data-testid="card-title">{title}</div>
      {children}
    </div>
  ),
  Divider: () => <hr data-testid="divider" />,
}));

vi.mock('@ant-design/icons', () => ({
  CheckCircleOutlined: () => <span data-testid="icon-check" />,
  ExclamationCircleOutlined: () => <span data-testid="icon-exclamation" />,
  InfoCircleOutlined: () => <span data-testid="icon-info" />,
  CloseCircleOutlined: () => <span data-testid="icon-close" />,
  LoadingOutlined: () => <span data-testid="icon-loading" />,
  ReloadOutlined: () => <span data-testid="icon-reload" />,
  UndoOutlined: () => <span data-testid="icon-undo" />,
}));

describe('ActionFeedback - 组件导入测试', () => {
  it('应该能够导入ActionFeedback组件', async () => {
    const module = await import('../ActionFeedback');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });

  it('应该导出预设组件', async () => {
    const module = await import('../ActionFeedback');
    expect(module.LoadingFeedback).toBeDefined();
    expect(module.SuccessFeedback).toBeDefined();
    expect(module.ErrorFeedback).toBeDefined();
    expect(module.WarningFeedback).toBeDefined();
    expect(module.ActionFeedbackCard).toBeDefined();
  });
});

describe('ActionFeedback - 渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('没有result时应该返回null', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const { container } = render(<ActionFeedback result={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it('应该正确渲染success状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'success' as const, message: '操作成功' };
    render(<ActionFeedback result={result} />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
    expect(screen.getByTestId('alert')).toHaveAttribute('data-type', 'success');
  });

  it('应该正确渲染error状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'error' as const, message: '操作失败' };
    render(<ActionFeedback result={result} />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
    expect(screen.getByTestId('alert')).toHaveAttribute('data-type', 'error');
  });

  it('应该正确渲染loading状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'loading' as const };
    render(<ActionFeedback result={result} />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
    expect(screen.getByTestId('alert')).toHaveAttribute('data-type', 'info');
  });

  it('应该正确渲染warning状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'warning' as const };
    render(<ActionFeedback result={result} />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
    expect(screen.getByTestId('alert')).toHaveAttribute('data-type', 'warning');
  });

  it('应该显示自定义标题', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'success' as const };
    render(<ActionFeedback result={result} title="自定义标题" />);

    expect(screen.getByText('自定义标题')).toBeInTheDocument();
  });

  it('应该显示消息内容', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'success' as const, message: '测试消息' };
    render(<ActionFeedback result={result} />);

    expect(screen.getByText('测试消息')).toBeInTheDocument();
  });
});

describe('ActionFeedback - 回调函数测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该在关闭时调用onClose回调', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const handleClose = vi.fn();
    const result = { status: 'success' as const };
    render(<ActionFeedback result={result} onClose={handleClose} />);

    fireEvent.click(screen.getByTestId('alert-close'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});

describe('ActionFeedback - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('LoadingFeedback应该正确渲染', async () => {
    const { LoadingFeedback } = await import('../ActionFeedback');
    render(<LoadingFeedback />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
  });

  it('SuccessFeedback应该正确渲染', async () => {
    const { SuccessFeedback } = await import('../ActionFeedback');
    render(<SuccessFeedback />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
  });

  it('ErrorFeedback应该正确渲染', async () => {
    const { ErrorFeedback } = await import('../ActionFeedback');
    render(<ErrorFeedback />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
  });

  it('WarningFeedback应该正确渲染', async () => {
    const { WarningFeedback } = await import('../ActionFeedback');
    render(<WarningFeedback />);

    expect(screen.getByTestId('alert')).toBeInTheDocument();
  });

  it('ActionFeedbackCard应该正确渲染', async () => {
    const { ActionFeedbackCard } = await import('../ActionFeedback');
    const result = { status: 'success' as const };
    render(<ActionFeedbackCard result={result} />);

    expect(screen.getByTestId('card')).toBeInTheDocument();
  });

  it('ActionFeedbackCard应该显示标题', async () => {
    const { ActionFeedbackCard } = await import('../ActionFeedback');
    const result = { status: 'success' as const };
    render(<ActionFeedbackCard result={result} title="测试标题" />);

    expect(screen.getByText('测试标题')).toBeInTheDocument();
  });
});

describe('ActionFeedback - 详情和错误信息测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该显示details列表', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = {
      status: 'success' as const,
      details: ['详情1', '详情2'],
    };
    render(<ActionFeedback result={result} showDetails={true} />);

    expect(screen.getByText('详情1')).toBeInTheDocument();
    expect(screen.getByText('详情2')).toBeInTheDocument();
  });

  it('应该显示错误信息', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const error = new Error('测试错误');
    const result = { status: 'error' as const, error };
    render(<ActionFeedback result={result} />);

    expect(screen.getByText('测试错误')).toBeInTheDocument();
  });
});
