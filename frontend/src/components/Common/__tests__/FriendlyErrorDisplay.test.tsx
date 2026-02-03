/**
 * FriendlyErrorDisplay 组件测试
 * 测试友好错误显示组件
 *
 * 修复说明：
 * - 移除 antd Alert, Result, Button, Space, Typography 组件 mock
 * - 移除 @ant-design/icons mock
 * - 使用角色、文本内容和 className 进行断言
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';

describe('FriendlyErrorDisplay - 组件导入测试', () => {
  it('应该能够导入FriendlyErrorDisplay组件', async () => {
    const module = await import('../FriendlyErrorDisplay');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('FriendlyErrorDisplay - 基础渲染测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('error为undefined且showDetails为false时应返回空渲染', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const { container } = renderWithProviders(
      <FriendlyErrorDisplay error={undefined} showDetails={false} />
    );

    // 验证 Result 组件未被渲染
    expect(container.querySelector('.ant-result')).not.toBeInTheDocument();
  });

  it('默认type应该是network', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    renderWithProviders(<FriendlyErrorDisplay error={{ message: '测试错误' }} />);

    // antd Result 会渲染 title
    expect(screen.getByText('网络连接问题')).toBeInTheDocument();
  });
});

describe('FriendlyErrorDisplay - 错误类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ['network', '网络连接问题'],
    ['data', '数据加载失败'],
    ['server', '服务器错误'],
    ['permission', '权限不足'],
    ['not-found', '未找到数据'],
  ])('type=%s 应该显示对应标题', async (type, title) => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    renderWithProviders(<FriendlyErrorDisplay error={{ message: '测试' }} type={type as any} />);

    expect(screen.getByText(title)).toBeInTheDocument();
  });
});

describe('FriendlyErrorDisplay - 按钮与详情测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该触发onRetry与onGoHome回调', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const handleRetry = vi.fn();
    const handleGoHome = vi.fn();

    renderWithProviders(
      <FriendlyErrorDisplay
        error={{ message: '测试错误' }}
        onRetry={handleRetry}
        onGoHome={handleGoHome}
      />
    );

    fireEvent.click(screen.getByText('重试'));
    fireEvent.click(screen.getByText('返回首页'));
    expect(handleRetry).toHaveBeenCalledTimes(1);
    expect(handleGoHome).toHaveBeenCalledTimes(1);
  });

  it('showDetails为true时应该展示错误详情', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    renderWithProviders(
      <FriendlyErrorDisplay
        error={{ status: 500, code: 'TEST_ERROR', message: '测试错误' }}
        showDetails={true}
      />
    );

    // 验证 Alert 组件被渲染（通过 role）
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();

    // 验证详情文本
    expect(screen.getByText('状态码:')).toBeInTheDocument();
    expect(screen.getByText('错误代码:')).toBeInTheDocument();
    expect(screen.getByText('错误信息:')).toBeInTheDocument();
  });
});

describe('FriendlyErrorDisplay - 建议解决方案测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('network类型应包含网络建议', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    renderWithProviders(<FriendlyErrorDisplay error={{ message: '网络错误' }} type="network" />);

    expect(screen.getByText('检查网络连接是否正常')).toBeInTheDocument();
  });
});
