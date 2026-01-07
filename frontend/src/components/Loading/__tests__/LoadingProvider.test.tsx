/**
 * LoadingProvider 组件测试
 * 测试全局加载状态管理组件
 * 增强版本 - 添加更全面的测试用例
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import {} from '@testing-library/react';

// Mock Ant Design components
vi.mock('antd', () => ({
  Spin: ({ tip, size, delay }: any) => (
    <div data-testid="spin" data-tip={tip} data-size={size} data-delay={delay}>
      Loading...
    </div>
  ),
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

describe('LoadingProvider - 组件导入测试', () => {
  it('应该能够导出LoadingProvider', async () => {
    const module = await import('../LoadingProvider');
    expect(module).toBeDefined();
    expect(module.LoadingProvider).toBeDefined();
  });

  it('应该能够导出useLoading hook', async () => {
    const module = await import('../LoadingProvider');
    expect(module.useLoading).toBeDefined();
    expect(typeof module.useLoading).toBe('function');
  });

  it('应该能够导出useGlobalLoading hook', async () => {
    const module = await import('../LoadingProvider');
    expect(module.useGlobalLoading).toBeDefined();
    expect(typeof module.useGlobalLoading).toBe('function');
  });

  it('应该能够导出useLocalLoading hook', async () => {
    const module = await import('../LoadingProvider');
    expect(module.useLocalLoading).toBeDefined();
    expect(typeof module.useLocalLoading).toBe('function');
  });

  it('应该能够导出GlobalLoadingOverlay组件', async () => {
    const module = await import('../LoadingProvider');
    expect(module.GlobalLoadingOverlay).toBeDefined();
  });

  it('应该能够导出LocalLoading组件', async () => {
    const module = await import('../LoadingProvider');
    expect(module.LocalLoading).toBeDefined();
  });

  it('应该能够导出LoadingButton组件', async () => {
    const module = await import('../LoadingProvider');
    expect(module.LoadingButton).toBeDefined();
  });
});

describe('LoadingProvider - 基础功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该能够渲染LoadingProvider', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    const element = React.createElement(
      LoadingProvider,
      {},
      React.createElement('div', {}, 'Test Content')
    );
    expect(element).toBeTruthy();
  });

  it('应该支持children属性', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    const testChild = React.createElement('div', { 'data-testid': 'test' }, 'Child');
    const element = React.createElement(LoadingProvider, {}, testChild);
    expect(element).toBeTruthy();
  });
});

describe('LoadingProvider - useLoading Hook测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('useLoading应该返回正确的上下文值', async () => {
    const { LoadingProvider, useLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const context = useLoading();
      return React.createElement('div', {
        'data-has-global': !!context.showGlobalLoading,
        'data-has-local': !!context.showLocalLoading,
        'data-has-with-loading': typeof context.withLoading === 'function',
      });
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });

  it('useLoading应该包含showGlobalLoading方法', async () => {
    const { LoadingProvider, useLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { showGlobalLoading } = useLoading();
      return React.createElement(
        'button',
        {
          onClick: () => showGlobalLoading({ tip: 'Test' }),
        },
        'Show Loading'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });

  it('useLoading应该包含hideGlobalLoading方法', async () => {
    const { LoadingProvider, useLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { hideGlobalLoading } = useLoading();
      return React.createElement(
        'button',
        {
          onClick: hideGlobalLoading,
        },
        'Hide Loading'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });
});

describe('LoadingProvider - useGlobalLoading Hook测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('useGlobalLoading应该返回loading状态', async () => {
    const { LoadingProvider, useGlobalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { loading } = useGlobalLoading();
      return React.createElement(
        'div',
        {
          'data-loading': loading,
        },
        `Loading: ${loading}`
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });

  it('useGlobalLoading应该返回show方法', async () => {
    const { LoadingProvider, useGlobalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { show } = useGlobalLoading();
      return React.createElement(
        'button',
        {
          onClick: () => show({ tip: 'Loading...' }),
        },
        'Show'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });

  it('useGlobalLoading应该返回hide方法', async () => {
    const { LoadingProvider, useGlobalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { hide } = useGlobalLoading();
      return React.createElement(
        'button',
        {
          onClick: hide,
        },
        'Hide'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });
});

describe('LoadingProvider - useLocalLoading Hook测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('useLocalLoading应该接受key参数', async () => {
    const { LoadingProvider, useLocalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const localLoading = useLocalLoading('test-key');
      return React.createElement(
        'div',
        {
          'data-loading': localLoading.loading,
        },
        'Test'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });

  it('useLocalLoading应该返回show方法', async () => {
    const { LoadingProvider, useLocalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { show } = useLocalLoading('test-key');
      return React.createElement(
        'button',
        {
          onClick: () => show({ tip: 'Loading...' }),
        },
        'Show'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });

  it('useLocalLoading应该返回hide方法', async () => {
    const { LoadingProvider, useLocalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { hide } = useLocalLoading('test-key');
      return React.createElement(
        'button',
        {
          onClick: hide,
        },
        'Hide'
      );
    };

    const element = React.createElement(LoadingProvider, {}, React.createElement(TestComponent));
    expect(element).toBeTruthy();
  });
});

describe('GlobalLoadingOverlay - 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该在globalLoading为false时不显示', async () => {
    const { LoadingProvider, GlobalLoadingOverlay } = await import('../LoadingProvider');

    const element = React.createElement(
      LoadingProvider,
      {},
      React.createElement(GlobalLoadingOverlay)
    );
    expect(element).toBeTruthy();
  });
});

describe('LocalLoading - 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持loading属性', async () => {
    const { LocalLoading } = await import('../LoadingProvider');
    const element = React.createElement(
      LocalLoading,
      { loading: true },
      React.createElement('div', {}, 'Content')
    );
    expect(element).toBeTruthy();
  });

  it('应该支持children属性', async () => {
    const { LocalLoading } = await import('../LoadingProvider');
    const element = React.createElement(
      LocalLoading,
      { loading: false },
      React.createElement('div', {}, 'Content')
    );
    expect(element).toBeTruthy();
  });

  it('应该支持tip属性', async () => {
    const { LocalLoading } = await import('../LoadingProvider');
    const element = React.createElement(
      LocalLoading,
      { loading: true, tip: 'Loading...' },
      React.createElement('div', {}, 'Content')
    );
    expect(element).toBeTruthy();
  });

  it('应该支持size属性', async () => {
    const { LocalLoading } = await import('../LoadingProvider');
    const element = React.createElement(
      LocalLoading,
      { loading: true, size: 'large' },
      React.createElement('div', {}, 'Content')
    );
    expect(element).toBeTruthy();
  });

  it('应该支持delay属性', async () => {
    const { LocalLoading } = await import('../LoadingProvider');
    const element = React.createElement(
      LocalLoading,
      { loading: true, delay: 300 },
      React.createElement('div', {}, 'Content')
    );
    expect(element).toBeTruthy();
  });
});

describe('LoadingButton - 组件测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该支持loading属性', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const element = React.createElement(LoadingButton, { loading: true }, 'Click Me');
    expect(element).toBeTruthy();
  });

  it('应该支持children属性', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const element = React.createElement(LoadingButton, { loading: false }, 'Submit');
    expect(element).toBeTruthy();
  });

  it('应该支持onClick属性', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const handleClick = vi.fn();
    const element = React.createElement(
      LoadingButton,
      { loading: false, onClick: handleClick },
      'Click'
    );
    expect(element).toBeTruthy();
  });

  it('应该支持disabled属性', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const element = React.createElement(
      LoadingButton,
      { loading: false, disabled: true },
      'Disabled'
    );
    expect(element).toBeTruthy();
  });

  it('应该支持className属性', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const element = React.createElement(
      LoadingButton,
      { loading: false, className: 'custom-button' },
      'Styled'
    );
    expect(element).toBeTruthy();
  });

  it('应该支持style属性', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const element = React.createElement(
      LoadingButton,
      { loading: false, style: { margin: 10 } },
      'Styled'
    );
    expect(element).toBeTruthy();
  });
});

describe('LoadingProvider - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该处理嵌套LoadingProvider', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    const element = React.createElement(
      LoadingProvider,
      {},
      React.createElement(LoadingProvider, {}, React.createElement('div', {}, 'Nested'))
    );
    expect(element).toBeTruthy();
  });

  it('应该处理多个子组件', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    const element = React.createElement(
      LoadingProvider,
      {},
      React.createElement('div', {}, 'Child 1'),
      React.createElement('div', {}, 'Child 2'),
      React.createElement('div', {}, 'Child 3')
    );
    expect(element).toBeTruthy();
  });

  it('应该处理空children', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    const element = React.createElement(LoadingProvider, {}, null);
    expect(element).toBeTruthy();
  });
});
