import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import PropertyCertificateDetailPage from '../PropertyCertificateDetailPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'cert-1' }),
  };
});

vi.mock('@/services/propertyCertificateService', () => ({
  propertyCertificateService: {
    getCertificate: vi.fn(),
    updateCertificate: vi.fn(),
    deleteCertificate: vi.fn(),
  },
}));

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssets: vi.fn(),
  },
}));

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

import { propertyCertificateService } from '@/services/propertyCertificateService';
import { assetService } from '@/services/assetService';

describe('PropertyCertificateDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(propertyCertificateService.getCertificate).mockResolvedValue({
      id: 'cert-1',
      certificate_number: 'CERT-001',
      certificate_type: 'real_estate',
      property_address: '测试地址 1 号',
      property_type: '商业',
      building_area: 1200,
      land_area: 800,
      floor_info: '1-3F',
      land_use_type: '商业',
      land_use_term_start: '2020-01-01',
      land_use_term_end: '2050-01-01',
      registration_date: '2020-02-01',
      co_ownership: null,
      restrictions: null,
      remarks: null,
      extraction_source: null,
      extraction_confidence: 0.92,
      is_verified: false,
      asset_ids: [],
      owners: [
        {
          id: 'owner-1',
          name: '测试主体',
          owner_type: 'organization',
          id_type: '统一社会信用代码',
          id_number: '1234567890',
          phone: '13800000000',
          address: '测试地址',
        },
      ],
      created_at: '2026-03-01',
      updated_at: '2026-03-02',
    });
    vi.mocked(assetService.getAssets).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 200,
      pages: 0,
    });
  });

  it('does not emit antd space deprecation warnings while rendering details', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(<PropertyCertificateDetailPage />, {
        route: '/owner/property-certificates/cert-1',
      });

      expect(await screen.findByText('产权证详情')).toBeInTheDocument();
      expect(await screen.findByText('CERT-001')).toBeInTheDocument();

      expect(formatConsoleMessages(consoleErrorSpy.mock.calls)).not.toContain('[antd: Space]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
