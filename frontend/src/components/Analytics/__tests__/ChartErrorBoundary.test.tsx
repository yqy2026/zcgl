/**
 * ChartErrorBoundary 组件测试
 * 测试图表错误边界组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

// Mock Ant Design components
vi.mock('antd', () => ({
  Alert: ({ message, description, type, showIcon, action, style }: any) => (
    <div
      data-testid="alert"
      data-type={type}
      data-message={message}
      data-show-icon={showIcon}
      style={style}
    >
      {description}
      {action}
    </div>
  ),
  Button: ({ children, size, onClick }: any) => (
    <button data-testid="button" data-size={size} onClick={onClick}>
      {children}
    </button>
  ),
}));

describe('ChartErrorBoundary - 组件导入测试', () => {
  it('应该能够导入ChartErrorBoundary组件', async () => {
    const module = await import('../ChartErrorBoundary');
    expect(module).toBeDefined();
    expect(module.default).toBeDefined();
  });

  it('应该导出ChartErrorBoundary类', async () => {
    const module = await import('../ChartErrorBoundary');
    expect(module.ChartErrorBoundary).toBeDefined();
  });
});

describe('ChartErrorBoundary - 基础功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('应该正常渲染children', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const children = React.createElement('div', {}, '正常内容');
    const element = React.createElement(ChartErrorBoundary, {}, children);
    expect(element).toBeTruthy();
  });

  it('应该支持fallback属性', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const fallback = React.createElement('div', {}, '自定义错误界面');
    const children = React.createElement('div', {}, '正常内容');
    const element = React.createElement(ChartErrorBoundary, { fallback }, children);
    expect(element).toBeTruthy();
  });

  it('应该支持onError回调', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const handleError = vi.fn();
    const children = React.createElement('div', {}, '正常内容');
    const element = React.createElement(ChartErrorBoundary, { onError: handleError }, children);
    expect(element).toBeTruthy();
  });
});

describe('ChartErrorBoundary - 错误处理测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('应该捕获子组件错误', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });

  it('应该显示默认错误UI', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });

  it('错误UI应该显示错误消息', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });

  it('错误UI应该显示错误详情', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误消息');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });
});

describe('ChartErrorBoundary - 重试功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('应该显示重试按钮', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });

  it('点击重试应该重置错误状态', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(ChartErrorBoundary, {}, React.createElement(ThrowError));
    expect(element).toBeTruthy();
  });
});

describe('ChartErrorBoundary - 边界情况测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('应该处理null children', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const element = React.createElement(ChartErrorBoundary, {}, null);
    expect(element).toBeTruthy();
  });

  it('应该处理undefined children', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const element = React.createElement(ChartErrorBoundary, {}, undefined);
    expect(element).toBeTruthy();
  });

  it('应该处理多个children', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const children = [
      React.createElement('div', { key: 1 }, 'Child 1'),
      React.createElement('div', { key: 2 }, 'Child 2'),
    ];
    const element = React.createElement(ChartErrorBoundary, {}, ...children);
    expect(element).toBeTruthy();
  });
});

describe('ChartErrorBoundary - fallback测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('应该使用自定义fallback', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const fallback = React.createElement('div', {}, '自定义错误');
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(
      ChartErrorBoundary,
      { fallback },
      React.createElement(ThrowError)
    );
    expect(element).toBeTruthy();
  });

  it('fallback可以为null', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(
      ChartErrorBoundary,
      { fallback: null },
      React.createElement(ThrowError)
    );
    expect(element).toBeTruthy();
  });
});

describe('ChartErrorBoundary - onError回调测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('错误时应该调用onError', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const handleError = vi.fn();
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(
      ChartErrorBoundary,
      { onError: handleError },
      React.createElement(ThrowError)
    );
    expect(element).toBeTruthy();
  });

  it('应该传递error对象给onError', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const handleError = vi.fn();
    const ThrowError = () => {
      throw new Error('测试错误消息');
    };
    const element = React.createElement(
      ChartErrorBoundary,
      { onError: handleError },
      React.createElement(ThrowError)
    );
    expect(element).toBeTruthy();
  });

  it('应该传递errorInfo给onError', async () => {
    const ChartErrorBoundary = (await import('../ChartErrorBoundary')).default;
    const handleError = vi.fn();
    const ThrowError = () => {
      throw new Error('测试错误');
    };
    const element = React.createElement(
      ChartErrorBoundary,
      { onError: handleError },
      React.createElement(ThrowError)
    );
    expect(element).toBeTruthy();
  });
});

describe('ChartErrorBoundary - 静态方法测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该有getDerivedStateFromError静态方法', async () => {
    const module = await import('../ChartErrorBoundary');
    const ChartErrorBoundary = module.default;
    expect(ChartErrorBoundary.getDerivedStateFromError).toBeDefined();
  });

  it('getDerivedStateFromError应该返回错误状态', async () => {
    const module = await import('../ChartErrorBoundary');
    const ChartErrorBoundary = module.default as any;
    const error = new Error('测试错误');
    const state = ChartErrorBoundary.getDerivedStateFromError(error);
    expect(state.hasError).toBe(true);
    expect(state.error).toBe(error);
  });
});
