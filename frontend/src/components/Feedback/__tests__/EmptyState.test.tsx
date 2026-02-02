/**
 * EmptyState 组件测试
 * 覆盖预设状态、按钮行为与自定义内容
 */

import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@/test/utils/test-helpers';
import type { CSSProperties, ReactNode } from 'react';

import EmptyState, {
  NoDataState,
  NetworkErrorState,
  NoFilterResultsState,
} from '../EmptyState';

interface EmptyMockProps {
  image?: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
}

interface ButtonMockProps {
  children?: ReactNode;
  icon?: ReactNode;
  type?: string;
  onClick?: () => void;
  danger?: boolean;
}

interface TypographyTextMockProps {
  children?: ReactNode;
  type?: string;
  strong?: boolean;
  style?: CSSProperties;
}

interface SpaceMockProps {
  children?: ReactNode;
  wrap?: boolean;
}

interface IconMockProps {
  style?: CSSProperties;
}

vi.mock('antd', () => ({
  Empty: ({ image, description, children }: EmptyMockProps) => (
    <div data-testid="empty">
      {image && <div data-testid="empty-image">{image}</div>}
      {description && <div data-testid="empty-description">{description}</div>}
      {children && <div data-testid="empty-children">{children}</div>}
    </div>
  ),
  Button: ({ children, icon, type, onClick, danger }: ButtonMockProps) => (
    <button data-testid="button" data-type={type} data-danger={danger} onClick={onClick}>
      {icon && <span data-testid="button-icon">{icon}</span>}
      {children}
    </button>
  ),
  Typography: {
    Text: ({ children, type, strong, style }: TypographyTextMockProps) => (
      <span data-testid="text" data-type={type} data-strong={strong} style={style}>
        {children}
      </span>
    ),
  },
  Space: ({ children, wrap }: SpaceMockProps) => (
    <div data-testid="space" data-wrap={wrap}>
      {children}
    </div>
  ),
}));

vi.mock('@ant-design/icons', () => ({
  FileTextOutlined: ({ style }: IconMockProps) => <div data-testid="icon-file-text" style={style} />,
  SearchOutlined: ({ style }: IconMockProps) => <div data-testid="icon-search" style={style} />,
  PlusOutlined: () => <div data-testid="icon-plus" />,
  ReloadOutlined: () => <div data-testid="icon-reload" />,
  InboxOutlined: ({ style }: IconMockProps) => <div data-testid="icon-inbox" style={style} />,
  DisconnectOutlined: ({ style }: IconMockProps) => <div data-testid="icon-disconnect" style={style} />,
  FilterOutlined: ({ style }: IconMockProps) => <div data-testid="icon-filter" style={style} />,
}));

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
      <EmptyState
        actions={<button type="button">自定义操作</button>}
        onCreateClick={vi.fn()}
      />
    );

    expect(screen.getByText('自定义操作')).toBeInTheDocument();
    expect(screen.queryByText('新增数据')).toBeNull();
  });

  it('does not render action container when no actions and no handlers', () => {
    renderWithProviders(<EmptyState />);

    expect(screen.queryByTestId('space')).toBeNull();
  });

  it('preset wrapper renders default title', () => {
    renderWithProviders(<NoDataState onCreateClick={vi.fn()} />);

    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
