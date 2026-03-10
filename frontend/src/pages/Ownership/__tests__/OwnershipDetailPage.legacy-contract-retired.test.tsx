import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import OwnershipDetailPage from '../OwnershipDetailPage';
import { renderWithProviders } from '@/test/utils/test-helpers';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'owner-1' }),
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnership: vi.fn(),
  },
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssets: vi.fn(),
  },
}));

import { ownershipService } from '@/services/ownershipService';
import { assetService } from '@/services/assetService';

const readOwnershipDetailSource = (): string => {
  return readFileSync(resolve(process.cwd(), 'src/pages/Ownership/OwnershipDetailPage.tsx'), 'utf8');
};

describe('OwnershipDetailPage legacy contract retirement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ownershipService.getOwnership).mockResolvedValue({
      id: 'owner-1',
      name: '测试权属方',
      short_name: '测试简称',
      is_active: true,
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-02T00:00:00Z',
    });
    vi.mocked(assetService.getAssets).mockResolvedValue({
      items: [
        {
          id: 'asset-1',
          asset_name: '测试物业',
          usage_status: '已出租',
          rentable_area: 100,
          project_name: '测试项目',
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
  });

  it('stops importing legacy rentContractService', () => {
    const source = readOwnershipDetailSource();

    expect(source).not.toContain("from '@/services/rentContractService'");
    expect(source).toContain('旧租赁合同与财务汇总入口已退休');
  });

  it('renders explicit migration alerts for legacy contract and finance sections', async () => {
    renderWithProviders(<OwnershipDetailPage />, { route: '/ownership/owner-1' });

    expect(await screen.findByText('旧租赁合同与财务汇总入口已退休')).toBeInTheDocument();
    expect(screen.getByText('关联合同（迁移中）')).toBeInTheDocument();
    expect(screen.getByText('财务汇总迁移中')).toBeInTheDocument();
    expect(screen.getByText('关联资产 (1)')).toBeInTheDocument();
  });
});
