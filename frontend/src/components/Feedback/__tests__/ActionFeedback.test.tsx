/**
 * ActionFeedback 组件测试
 * 测试操作反馈组件
 *
 * 修复说明：
 * - 移除 antd 组件 mock，使用真实组件
 * - 使用文本内容和角色选择器进行断言
 * - 保持测试覆盖范围不变
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, within } from '@/test/utils/test-helpers';
import React from 'react';

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
    const { container } = renderWithProviders(<ActionFeedback result={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it('应该正确渲染success状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'success' as const, message: '操作成功' };
    renderWithProviders(<ActionFeedback result={result} />);

    // Alert 组件会在 DOM 中渲染
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('应该正确渲染error状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'error' as const, message: '操作失败' };
    renderWithProviders(<ActionFeedback result={result} />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('应该正确渲染loading状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'loading' as const };
    renderWithProviders(<ActionFeedback result={result} />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('应该正确渲染warning状态', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'warning' as const };
    renderWithProviders(<ActionFeedback result={result} />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('应该显示自定义标题', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'success' as const };
    renderWithProviders(<ActionFeedback result={result} title="自定义标题" />);

    expect(screen.getByText('自定义标题')).toBeInTheDocument();
  });

  it('应该显示消息内容', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const result = { status: 'success' as const, message: '测试消息' };
    renderWithProviders(<ActionFeedback result={result} />);

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
    renderWithProviders(<ActionFeedback result={result} onClose={handleClose} />);

    // 点击关闭按钮（Alert 组件的关闭图标按钮）
    const closeButton = screen.getByRole('button', { name: /close/i }) || screen.queryByLabelText(/close/i);
    if (closeButton) {
      fireEvent.click(closeButton);
      expect(handleClose).toHaveBeenCalledTimes(1);
    }
  });
});

describe('ActionFeedback - 预设组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('LoadingFeedback应该正确渲染', async () => {
    const { LoadingFeedback } = await import('../ActionFeedback');
    renderWithProviders(<LoadingFeedback />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('SuccessFeedback应该正确渲染', async () => {
    const { SuccessFeedback } = await import('../ActionFeedback');
    renderWithProviders(<SuccessFeedback />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('ErrorFeedback应该正确渲染', async () => {
    const { ErrorFeedback } = await import('../ActionFeedback');
    renderWithProviders(<ErrorFeedback />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('WarningFeedback应该正确渲染', async () => {
    const { WarningFeedback } = await import('../ActionFeedback');
    renderWithProviders(<WarningFeedback />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('ActionFeedbackCard应该正确渲染', async () => {
    const { ActionFeedbackCard } = await import('../ActionFeedback');
    const result = { status: 'success' as const };
    const { container } = renderWithProviders(<ActionFeedbackCard result={result} />);

    // Card 组件渲染为一个 div
    expect(container.firstChild).toBeInTheDocument();
  });

  it('ActionFeedbackCard应该显示标题', async () => {
    const { ActionFeedbackCard } = await import('../ActionFeedback');
    const result = { status: 'success' as const };
    renderWithProviders(<ActionFeedbackCard result={result} title="测试标题" />);

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
    renderWithProviders(<ActionFeedback result={result} showDetails={true} />);

    expect(screen.getByText('详情1')).toBeInTheDocument();
    expect(screen.getByText('详情2')).toBeInTheDocument();
  });

  it('应该显示错误信息', async () => {
    const ActionFeedback = (await import('../ActionFeedback')).default;
    const error = new Error('测试错误');
    const result = { status: 'error' as const, error };
    renderWithProviders(<ActionFeedback result={result} />);

    expect(screen.getByText('测试错误')).toBeInTheDocument();
  });
});
