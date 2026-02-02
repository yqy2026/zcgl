/**
 * SkeletonLoader 组件测试
 * 覆盖主要类型和加载逻辑
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { screen } from '@/test/utils/test-helpers';

import SkeletonLoader from '../SkeletonLoader';

interface SkeletonItemMockProps {
  style?: React.CSSProperties;
  active?: boolean;
}

interface SkeletonAvatarMockProps {
  size?: number | string;
  active?: boolean;
}

interface SkeletonNodeMockProps {
  children?: React.ReactNode;
  style?: React.CSSProperties;
  active?: boolean;
}

interface SkeletonDefaultMockProps {
  avatar?: boolean;
  paragraph?: boolean;
  title?: boolean;
  rows?: number;
  active?: boolean;
}

interface CardMockProps {
  children?: React.ReactNode;
  title?: React.ReactNode;
  size?: string;
  style?: React.CSSProperties;
}

interface RowMockProps {
  children?: React.ReactNode;
  gutter?: unknown;
  style?: React.CSSProperties;
}

interface ColMockProps {
  children?: React.ReactNode;
  span?: number;
  xs?: unknown;
  sm?: unknown;
  md?: unknown;
  lg?: unknown;
}

// Mock Ant Design components
vi.mock('antd', () => {
  const Skeleton = (({
    avatar,
    paragraph,
    title,
    rows,
    active,
  }: SkeletonDefaultMockProps) => (
    <div
      data-testid="skeleton"
      data-avatar={avatar}
      data-rows={rows}
      data-active={active}
      data-has-title={!!title}
      data-has-paragraph={!!paragraph}
    >
      {paragraph && <span data-testid="skeleton-paragraph" />}
    </div>
  )) as React.FC<SkeletonDefaultMockProps> & {
    Input?: React.FC<SkeletonItemMockProps>;
    Button?: React.FC<SkeletonItemMockProps>;
    Avatar?: React.FC<SkeletonAvatarMockProps>;
    Node?: React.FC<SkeletonNodeMockProps>;
  };
  Skeleton.displayName = 'MockSkeleton';

  const SkeletonInput = ({ style, active }: SkeletonItemMockProps) => (
    <div data-testid="skeleton-input" data-active={active} style={style} />
  );
  SkeletonInput.displayName = 'MockSkeletonInput';
  Skeleton.Input = SkeletonInput;

  const SkeletonButton = ({ style, active }: SkeletonItemMockProps) => (
    <div data-testid="skeleton-button" data-active={active} style={style} />
  );
  SkeletonButton.displayName = 'MockSkeletonButton';
  Skeleton.Button = SkeletonButton;

  const SkeletonAvatar = ({ size, active }: SkeletonAvatarMockProps) => (
    <div data-testid="skeleton-avatar" data-size={size} data-active={active} />
  );
  SkeletonAvatar.displayName = 'MockSkeletonAvatar';
  Skeleton.Avatar = SkeletonAvatar;

  const SkeletonNode = ({ children, style, active }: SkeletonNodeMockProps) => (
    <div data-testid="skeleton-node" data-active={active} style={style}>
      {children}
    </div>
  );
  SkeletonNode.displayName = 'MockSkeletonNode';
  Skeleton.Node = SkeletonNode;

  const Card = ({ children, title, size, style }: CardMockProps) => (
    <div data-testid="card" data-size={size} data-has-title={!!title} style={style}>
      {children}
    </div>
  );
  Card.displayName = 'MockCard';

  const Row = ({ children, gutter, style }: RowMockProps) => (
    <div data-testid="row" data-gutter={gutter} style={style}>
      {children}
    </div>
  );
  Row.displayName = 'MockRow';

  const Col = ({ children, span, xs, sm, md, lg }: ColMockProps) => (
    <div
      data-testid="col"
      data-span={span}
      data-xs={xs}
      data-sm={sm}
      data-md={md}
      data-lg={lg}
    >
      {children}
    </div>
  );
  Col.displayName = 'MockCol';

  return {
    Skeleton,
    Card,
    Row,
    Col,
  };
});

describe('SkeletonLoader', () => {
  it('renders list skeleton with default rows', () => {
    renderWithProviders(<SkeletonLoader type="list" />);

    const cards = screen.getAllByTestId('card');
    expect(cards).toHaveLength(3);
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  it('supports custom rows for list type', () => {
    renderWithProviders(<SkeletonLoader type="list" rows={5} />);

    const cards = screen.getAllByTestId('card');
    expect(cards).toHaveLength(5);
  });

  it('renders card type layout', () => {
    renderWithProviders(<SkeletonLoader type="card" rows={2} />);

    expect(screen.getByTestId('row')).toBeInTheDocument();
    expect(screen.getAllByTestId('col').length).toBeGreaterThan(0);
  });

  it('renders form type skeleton fields', () => {
    renderWithProviders(<SkeletonLoader type="form" rows={2} />);

    expect(screen.getAllByTestId('skeleton-input').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('skeleton-button').length).toBeGreaterThan(0);
  });

  it('renders table type skeleton', () => {
    renderWithProviders(<SkeletonLoader type="table" rows={4} />);

    expect(screen.getAllByTestId('skeleton-input').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('row').length).toBeGreaterThan(0);
  });

  it('renders chart type skeleton', () => {
    renderWithProviders(<SkeletonLoader type="chart" />);

    expect(screen.getByTestId('skeleton-node')).toBeInTheDocument();
  });

  it('renders detail type skeleton', () => {
    renderWithProviders(<SkeletonLoader type="detail" rows={2} />);

    expect(screen.getByTestId('skeleton-avatar')).toBeInTheDocument();
    expect(screen.getAllByTestId('card').length).toBeGreaterThan(0);
  });

  it('renders children when loading is false and children provided', () => {
    renderWithProviders(
      <SkeletonLoader loading={false}>
        <div data-testid="content">Actual Content</div>
      </SkeletonLoader>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
  });

  it('renders skeleton when loading is false but children missing', () => {
    renderWithProviders(<SkeletonLoader loading={false} />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  it('falls back to default skeleton for unknown type', () => {
    renderWithProviders(<SkeletonLoader type={'unknown' as 'list'} />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });
});
