/**
 * SkeletonLoader 组件测试
 * 覆盖主要类型和加载逻辑
 *
 * 修复说明：
 * - 移除 antd Skeleton, Card, Row, Col 组件 mock
 * - 使用 className 验证组件渲染
 * - 保持测试覆盖范围不变
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { screen } from '@/test/utils/test-helpers';

import SkeletonLoader from '../SkeletonLoader';

describe('SkeletonLoader', () => {
  it('renders list skeleton with default rows', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="list" />);

    // 验证 Card 组件被渲染
    const cards = container.querySelectorAll('.ant-card');
    expect(cards.length).toBeGreaterThan(0);
    // 验证 Skeleton 组件被渲染
    const skeletons = container.querySelectorAll('.ant-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('supports custom rows for list type', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="list" rows={5} />);

    const cards = container.querySelectorAll('.ant-card');
    expect(cards.length).toBe(5);
  });

  it('renders card type layout', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="card" rows={2} />);

    // 验证 Row 和 Col 被渲染
    const rows = container.querySelectorAll('.ant-row');
    expect(rows.length).toBeGreaterThan(0);
    const cols = container.querySelectorAll('.ant-col');
    expect(cols.length).toBeGreaterThan(0);
  });

  it('renders form type skeleton fields', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="form" rows={2} />);

    // 验证 Skeleton.Input 被渲染（会有特定的类）
    const inputs = container.querySelectorAll('.ant-skeleton-input');
    expect(inputs.length).toBeGreaterThan(0);
    const buttons = container.querySelectorAll('.ant-skeleton-button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('renders table type skeleton', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="table" rows={4} />);

    const inputs = container.querySelectorAll('.ant-skeleton-input');
    expect(inputs.length).toBeGreaterThan(0);
    const rows = container.querySelectorAll('.ant-row');
    expect(rows.length).toBeGreaterThan(0);
  });

  it('renders chart type skeleton', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="chart" />);

    // Skeleton.Node 会有特定的类
    const skeletonNodes = container.querySelectorAll('.ant-skeleton-node');
    expect(skeletonNodes.length).toBeGreaterThan(0);
  });

  it('renders detail type skeleton', () => {
    const { container } = renderWithProviders(<SkeletonLoader type="detail" rows={2} />);

    const avatars = container.querySelectorAll('.ant-skeleton-avatar');
    expect(avatars.length).toBeGreaterThan(0);
    const cards = container.querySelectorAll('.ant-card');
    expect(cards.length).toBeGreaterThan(0);
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
    const { container } = renderWithProviders(<SkeletonLoader loading={false} />);

    const skeletons = container.querySelectorAll('.ant-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('falls back to default skeleton for unknown type', () => {
    const { container } = renderWithProviders(<SkeletonLoader type={'unknown' as 'list'} />);

    const skeletons = container.querySelectorAll('.ant-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
