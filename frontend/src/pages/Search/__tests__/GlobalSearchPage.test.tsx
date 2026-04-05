import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { Route, Routes } from 'react-router-dom';

vi.mock('@/services/searchService', () => ({
  searchService: {
    searchGlobal: vi.fn(),
  },
}));

import GlobalSearchPage from '../GlobalSearchPage';
import { searchService } from '@/services/searchService';

describe('GlobalSearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(searchService.searchGlobal).mockResolvedValue({
      query: '测试',
      total: 2,
      items: [
        {
          object_type: 'asset',
          object_id: 'asset-1',
          title: '测试资产',
          subtitle: 'AST-001',
          summary: '资产结果',
          keywords: ['asset_name'],
          route_path: '/assets/asset-1',
          score: 90,
          business_rank: 50,
          group_label: '资产',
        },
        {
          object_type: 'customer',
          object_id: 'party-1',
          title: '终端租户甲',
          subtitle: 'external',
          summary: '客户结果',
          keywords: ['customer_name'],
          route_path: '/customers/party-1',
          score: 80,
          business_rank: 40,
          group_label: '客户',
        },
      ],
      groups: [
        { object_type: 'asset', label: '资产', count: 1 },
        { object_type: 'customer', label: '客户', count: 1 },
      ],
    });
  });

  it('renders all-view results and supports grouped view switch', async () => {
    renderWithProviders(
        <Routes>
          <Route path="/search" element={<GlobalSearchPage />} />
        </Routes>,
        { route: '/search?q=测试' }
    );

    expect(await screen.findByText('测试资产')).toBeInTheDocument();
    expect(screen.getByText('终端租户甲')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('radio', { name: '按对象分组' }));

    await waitFor(() => {
      expect(screen.getByText('资产')).toBeInTheDocument();
      expect(screen.getByText('客户')).toBeInTheDocument();
    });
  });

  it('navigates to result route when clicking a result item', async () => {
      renderWithProviders(
        <Routes>
          <Route path="/search" element={<GlobalSearchPage />} />
          <Route path="/assets/:id" element={<div>Asset Detail</div>} />
        </Routes>,
        { route: '/search?q=测试' }
      );

    fireEvent.click(await screen.findByRole('button', { name: '查看资产测试资产详情' }));

    await waitFor(() => {
      expect(screen.getByText('Asset Detail')).toBeInTheDocument();
    });
  });
});
