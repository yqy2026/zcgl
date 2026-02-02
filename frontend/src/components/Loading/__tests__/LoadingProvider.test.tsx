/**
 * LoadingProvider 组件测试
 * 测试全局加载状态管理组件
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { screen, fireEvent } from '@/test/utils/test-helpers';

interface SpinMockProps {
  children?: React.ReactNode;
  tip?: React.ReactNode;
  size?: 'small' | 'default' | 'large' | number;
  delay?: number;
  spinning?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

// Mock Ant Design components
vi.mock('antd', () => ({
  Spin: ({ children, tip, size, delay, spinning, className, style }: SpinMockProps) => (
    <div
      data-testid="spin"
      data-tip={tip}
      data-size={size}
      data-delay={delay}
      data-spinning={spinning}
      className={className}
      style={style}
    >
      Loading...
      {children}
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

  it('应该能够渲染LoadingProvider并展示children', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    renderWithProviders(
      <LoadingProvider>
        <div>Test Content</div>
      </LoadingProvider>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('useLoading应该可以控制全局Loading显示', async () => {
    const { LoadingProvider, GlobalLoadingOverlay, useLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { showGlobalLoading, hideGlobalLoading } = useLoading();
      return (
        <div>
          <button onClick={() => showGlobalLoading({ tip: 'Test Tip' })}>Show</button>
          <button onClick={hideGlobalLoading}>Hide</button>
        </div>
      );
    };

    renderWithProviders(
      <LoadingProvider>
        <TestComponent />
        <GlobalLoadingOverlay />
      </LoadingProvider>
    );

    expect(screen.queryByTestId('spin')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Show'));
    expect(screen.getByTestId('spin')).toHaveAttribute('data-tip', 'Test Tip');

    fireEvent.click(screen.getByText('Hide'));
    expect(screen.queryByTestId('spin')).not.toBeInTheDocument();
  });

  it('useLocalLoading应该可以切换局部Loading状态', async () => {
    const { LoadingProvider, useLocalLoading } = await import('../LoadingProvider');

    const TestComponent = () => {
      const { loading, show, hide } = useLocalLoading('test-key');
      return (
        <div>
          <span data-testid="local-loading-state">{String(loading)}</span>
          <button onClick={() => show({ tip: 'Local Tip' })}>Show</button>
          <button onClick={hide}>Hide</button>
        </div>
      );
    };

    renderWithProviders(
      <LoadingProvider>
        <TestComponent />
      </LoadingProvider>
    );

    expect(screen.getByTestId('local-loading-state')).toHaveTextContent('false');

    fireEvent.click(screen.getByText('Show'));
    expect(screen.getByTestId('local-loading-state')).toHaveTextContent('true');

    fireEvent.click(screen.getByText('Hide'));
    expect(screen.getByTestId('local-loading-state')).toHaveTextContent('false');
  });

  it('GlobalLoadingOverlay在未加载时不显示', async () => {
    const { LoadingProvider, GlobalLoadingOverlay } = await import('../LoadingProvider');

    renderWithProviders(
      <LoadingProvider>
        <GlobalLoadingOverlay />
      </LoadingProvider>
    );

    expect(screen.queryByTestId('spin')).not.toBeInTheDocument();
  });

  it('LocalLoading应该透传Spin属性并渲染内容', async () => {
    const { LocalLoading } = await import('../LoadingProvider');

    renderWithProviders(
      <LocalLoading loading={true} tip="Loading..." size="large" delay={300}>
        <div>Content</div>
      </LocalLoading>
    );

    const spin = screen.getByTestId('spin');
    expect(spin).toHaveAttribute('data-tip', 'Loading...');
    expect(spin).toHaveAttribute('data-size', 'large');
    expect(spin).toHaveAttribute('data-delay', '300');
    expect(spin).toHaveAttribute('data-spinning', 'true');
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('LoadingButton在非loading时触发onClick', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const handleClick = vi.fn();

    renderWithProviders(
      <LoadingButton loading={false} onClick={handleClick}>
        Click
      </LoadingButton>
    );

    fireEvent.click(screen.getByRole('button', { name: /Click/ }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('LoadingButton在loading时禁止点击', async () => {
    const { LoadingButton } = await import('../LoadingProvider');
    const handleClick = vi.fn();

    renderWithProviders(
      <LoadingButton loading={true} onClick={handleClick}>
        Click
      </LoadingButton>
    );

    fireEvent.click(screen.getByRole('button', { name: /Click/ }));
    expect(handleClick).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /Click/ })).toBeDisabled();
  });

  it('应该支持嵌套LoadingProvider', async () => {
    const { LoadingProvider } = await import('../LoadingProvider');
    renderWithProviders(
      <LoadingProvider>
        <LoadingProvider>
          <div>Nested</div>
        </LoadingProvider>
      </LoadingProvider>
    );

    expect(screen.getByText('Nested')).toBeInTheDocument();
  });
});
