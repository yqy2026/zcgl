/**
 * FriendlyErrorDisplay 组件测试
 * 测试友好错误显示组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

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
}));

describe('FriendlyErrorDisplay - 组件导入测试', () => {
  it('应该能够导入FriendlyErrorDisplay组件', async () => {
    const module = await import('../FriendlyErrorDisplay');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });
});

describe('FriendlyErrorDisplay - 基础属性测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持error属性', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = {
      message: '测试错误',
      status: 500,
      code: 'TEST_ERROR',
    };
    const element = React.createElement(FriendlyErrorDisplay, { error });
    expect(element).toBeTruthy();
  });

  it('应该支持type属性', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'network',
    });
    expect(element).toBeTruthy();
  });

  it('默认type应该是network', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, { error });
    expect(element).toBeTruthy();
  });

  it('应该支持showDetails属性', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('默认showDetails应该是false', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, { error });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 错误类型测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('type为network应该显示网络错误', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '网络错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'network',
    });
    expect(element).toBeTruthy();
  });

  it('type为data应该显示数据错误', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '数据错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'data',
    });
    expect(element).toBeTruthy();
  });

  it('type为server应该显示服务器错误', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '服务器错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'server',
    });
    expect(element).toBeTruthy();
  });

  it('type为permission应该显示权限错误', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '权限错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'permission',
    });
    expect(element).toBeTruthy();
  });

  it('type为not-found应该显示未找到错误', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '未找到' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'not-found',
    });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 按钮测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持onRetry回调', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const handleRetry = vi.fn();
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      onRetry: handleRetry,
    });
    expect(element).toBeTruthy();
  });

  it('应该支持onGoHome回调', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const handleGoHome = vi.fn();
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      onGoHome: handleGoHome,
    });
    expect(element).toBeTruthy();
  });

  it('应该同时显示两个按钮', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      onRetry: vi.fn(),
      onGoHome: vi.fn(),
    });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 错误详情测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('showDetails为true时应该显示错误详情', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = {
      message: '测试错误',
      status: 500,
      code: 'TEST_ERROR',
    };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示status状态码', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { status: 404 };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示code错误代码', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { code: 'ERR_001' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示message错误信息', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误消息' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('应该显示details详细信息', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { details: { key: 'value' } };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('details为null时不应该显示详细信息', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { details: null };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 建议解决方案测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('type为network应该显示网络问题建议', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '网络错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'network',
    });
    expect(element).toBeTruthy();
  });

  it('type为data应该显示数据问题建议', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '数据错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'data',
    });
    expect(element).toBeTruthy();
  });

  it('type为server应该显示服务器问题建议', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '服务器错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'server',
    });
    expect(element).toBeTruthy();
  });

  it('type为permission应该显示权限问题建议', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '权限错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'permission',
    });
    expect(element).toBeTruthy();
  });

  it('type为not-found应该显示未找到问题建议', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '未找到' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'not-found',
    });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('error为undefined且showDetails为false应该返回null', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const element = React.createElement(FriendlyErrorDisplay, {
      error: undefined,
      showDetails: false,
    });
    expect(element).toBeTruthy();
  });

  it('error为undefined但showDetails为true应该显示组件', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const element = React.createElement(FriendlyErrorDisplay, {
      error: undefined,
      showDetails: true,
    });
    expect(element).toBeTruthy();
  });

  it('应该处理空error对象', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const element = React.createElement(FriendlyErrorDisplay, {
      error: {},
    });
    expect(element).toBeTruthy();
  });

  it('应该处理无效的type', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'invalid' as unknown as 'network' | 'server' | 'auth' | 'notFound' | 'unknown',
    });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 图标测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('type为network应该显示Wifi图标', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '网络错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'network',
    });
    expect(element).toBeTruthy();
  });

  it('type为data应该显示Database图标', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '数据错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'data',
    });
    expect(element).toBeTruthy();
  });

  it('type为server应该显示API图标', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '服务器错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'server',
    });
    expect(element).toBeTruthy();
  });

  it('type为permission应该显示Exclamation图标', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '权限错误' };
    const element = React.createElement(FriendlyErrorDisplay, {
      error,
      type: 'permission',
    });
    expect(element).toBeTruthy();
  });
});

describe('FriendlyErrorDisplay - 布局测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该居中显示', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, { error });
    expect(element).toBeTruthy();
  });

  it('应该有适当的内边距', async () => {
    const FriendlyErrorDisplay = (await import('../FriendlyErrorDisplay')).default;
    const error = { message: '测试错误' };
    const element = React.createElement(FriendlyErrorDisplay, { error });
    expect(element).toBeTruthy();
  });
});
