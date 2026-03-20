import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { Form } from 'antd';
import RelationInfoSection from '../RelationInfoSection';

vi.mock('@/components/Common/PartySelector', () => ({
  default: () => <div data-testid="party-selector" />,
}));

vi.mock('../RentContractFormContext', () => ({
  useRentContractFormContext: vi.fn(() => ({
    assets: [
      {
        id: 'asset-1',
        asset_name: '测试资产A',
        address: '测试地址A',
      },
    ],
    loadingAssets: false,
  })),
}));

describe('RelationInfoSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应使用语义样式类承载卡片外边距', () => {
    renderWithProviders(
      <Form>
        <RelationInfoSection />
      </Form>
    );

    expect(screen.getByText('关联信息').closest('[class*="relationCard"]')).toBeInTheDocument();
  });
});
