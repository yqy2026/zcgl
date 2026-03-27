import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { Form } from 'antd';
import RelationInfoSection from '../RelationInfoSection';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

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

vi.mock('@/components/Common/PartySelector', () => ({
  default: ({ placeholder }: { placeholder?: string }) => (
    <input data-testid="mock-party-selector" placeholder={placeholder} />
  ),
}));

describe('RelationInfoSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应使用语义样式类承载卡片外边距', () => {
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      renderWithProviders(
        <Form>
          <RelationInfoSection />
        </Form>
      );

      expect(screen.getByText('关联信息').closest('[class*="relationCard"]')).toBeInTheDocument();
      expect(screen.getAllByTestId('mock-party-selector')).toHaveLength(3);
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('[MSW] Warning');
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });
});
