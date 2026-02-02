/**
 * FriendlyErrorDisplay 组件测试
 * 测试友好错误显示组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';

interface AlertMockProps {
  message?: React.ReactNode;
  description?: React.ReactNode;
  type?: string;
  showIcon?: boolean;
}

interface ResultMockProps {
  icon?: React.ReactNode;
  title?: React.ReactNode;
  subTitle?: React.ReactNode;
  extra?: React.ReactNode;
}

interface ButtonMockProps {
  children?: React.ReactNode;
  icon?: React.ReactNode;
  type?: string;
  onClick?: () => void;
}

interface SpaceMockProps {
  children?: React.ReactNode;
  direction?: string;
  size?: number | string;
  wrap?: boolean;
}

interface TypographyTextMockProps {
  children?: React.ReactNode;
  strong?: boolean;
  type?: string;
}

interface TypographyTitleMockProps {
  children?: React.ReactNode;
  level?: number;
  style?: React.CSSProperties;
}

// Mock Ant Design components
vi.mock('antd', () => ({
  Alert: ({ message, description, type, showIcon }: AlertMockProps) => (
    <div data-testid="alert" data-message={message} data-type={type} data-show-icon={showIcon}>
      {description}
    </div>
  ),
  Result: ({ icon, title, subTitle, extra }: ResultMockProps) => (
    <div data-testid="result" data-title={title} data-subtitle={subTitle}>
      {icon}
      {extra}
    </div>
  ),
  Button: ({ children, icon, type, onClick }: ButtonMockProps) => (
    <button data-testid="button" data-type={type} onClick={onClick}>
      {icon}
      {children}
    </button>
  ),
  Space: ({ children, direction, size, wrap }: SpaceMockProps) => (
    <div data-testid="space" data-direction={direction} data-size={size} data-wrap={wrap}>
      {children}
    </div>
  ),
  Typography: {
    Text: ({ children, strong, type }: TypographyTextMockProps) => (
      <div data-testid="text" data-strong={strong} data-type={type}>
        {children}
      </div>
    ),
    Title: ({ children, level, style }: TypographyTitleMockProps) => (
      <div data-testid="title" data-level={level} style={style}>
        {children}
      </div>
    ),
  },
}));

// Mock icons
vi.mock('@ant-design/icons', () => ({
  ExclamationCircleOutlined: () => <div data-testid="icon-exclamation-circle" />,
  ReloadOutlined: () => <div data-testid="icon-reload" />,
  HomeOutlined: () => <div data-testid="icon-home" />,
  ApiOutlined: () => <div data-testid="icon-api" />,
  DatabaseOutlined: () => <div data-testid="icon-database" />,
  WifiOutlined: () => <div data-testid="icon-wifi" />,
  BulbOutlined: () => <div data-testid="icon-bulb" />,
}));

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
    renderWithProviders(<FriendlyErrorDisplay error={undefined} showDetails={false} />);

    expect(screen.queryByTestId('result')).not.toBeInTheDocument();
  });

  it('默认type应该是network', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    renderWithProviders(<FriendlyErrorDisplay error={{ message: '测试错误' }} />);

    expect(screen.getByTestId('result')).toHaveAttribute('data-title', '网络连接问题');
  });
});

describe('FriendlyErrorDisplay - 错误类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ['network', '网络连接问题', 'icon-wifi'],
    ['data', '数据加载失败', 'icon-database'],
    ['server', '服务器错误', 'icon-api'],
    ['permission', '权限不足', 'icon-exclamation-circle'],
    ['not-found', '未找到数据', 'icon-exclamation-circle'],
  ])('type=%s 应该显示对应标题与图标', async (type, title, iconTestId) => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    renderWithProviders(<FriendlyErrorDisplay error={{ message: '测试' }} type={type as any} />);

    expect(screen.getByTestId('result')).toHaveAttribute('data-title', title);
    expect(screen.getByTestId(iconTestId)).toBeInTheDocument();
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

    expect(screen.getByTestId('alert')).toBeInTheDocument();
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
    expect(screen.getByTestId('icon-bulb')).toBeInTheDocument();
  });
});
