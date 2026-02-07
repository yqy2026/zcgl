/**
 * EmptyState 组件测试
 * 覆盖预设状态、按钮行为与自定义内容
 *
 * 修复说明：
 * - 移除 antd 组件 mock，使用真实组件
 * - 使用文本内容而非 data-testid 进行断言
 * - 保持测试覆盖范围不变
 */

import { describe, it, expect, vi } from 'vitest';
import { fireEvent, screen } from '@/test/utils/test-helpers';

import EmptyState, { NoDataState, NetworkErrorState, NoFilterResultsState } from '../EmptyState';

describe('EmptyState', () => {
  it('renders default no-data state and create button when handler provided', () => {
    const handleCreate = vi.fn();
    renderWithProviders(<EmptyState onCreateClick={handleCreate} />);

    expect(screen.getByText('暂无数据')).toBeInTheDocument();
    const createButton = screen.getByText('新增数据');
    fireEvent.click(createButton);
    expect(handleCreate).toHaveBeenCalled();
  });

  it('renders network error with refresh button', () => {
    const handleRefresh = vi.fn();
    renderWithProviders(<NetworkErrorState onRefreshClick={handleRefresh} />);

    expect(screen.getByText('网络连接失败')).toBeInTheDocument();
    const refreshButton = screen.getByText('刷新');
    fireEvent.click(refreshButton);
    expect(handleRefresh).toHaveBeenCalled();
  });

  it('renders filter result state with clear filter action', () => {
    const handleClear = vi.fn();
    renderWithProviders(<NoFilterResultsState onClearFilterClick={handleClear} />);

    const clearButton = screen.getByText('清除筛选');
    fireEvent.click(clearButton);
    expect(handleClear).toHaveBeenCalled();
  });

  it('uses custom title, description, and image overrides', () => {
    renderWithProviders(
      <EmptyState
        title="自定义标题"
        description="自定义描述"
        image={<div data-testid="custom-image" />}
      />
    );

    expect(screen.getByText('自定义标题')).toBeInTheDocument();
    expect(screen.getByText('自定义描述')).toBeInTheDocument();
    expect(screen.getByTestId('custom-image')).toBeInTheDocument();
  });

  it('uses actions prop instead of default buttons', () => {
    renderWithProviders(
      <EmptyState actions={<button type="button">自定义操作</button>} onCreateClick={vi.fn()} />
    );

    expect(screen.getByText('自定义操作')).toBeInTheDocument();
    expect(screen.queryByText('新增数据')).toBeNull();
  });

  it('does not render action container when no actions and no handlers', () => {
    renderWithProviders(<EmptyState />);

    // 验证没有操作按钮
    expect(screen.queryByText('新增数据')).toBeNull();
  });

  it('preset wrapper renders default title', () => {
    renderWithProviders(<NoDataState onCreateClick={vi.fn()} />);

    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
