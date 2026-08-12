import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor, within } from '@/test/utils/test-helpers';
import { QueryClient } from '@tanstack/react-query';
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
vi.mock('@/services/propertyCertificateAttachmentService', () => ({
  propertyCertificateAttachmentService: {
    list: vi.fn().mockResolvedValue([]),
    append: vi.fn(),
    replace: vi.fn(),
    remove: vi.fn(),
    previewUrl: vi.fn(),
    downloadUrl: vi.fn(),
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
      property_address: 'Test address 1',
      property_type: 'Commercial',
      building_area: '1200',
      land_area: '800',
      floor_info: '1-3F',
      land_use_type: 'Commercial',
      land_use_term_start: '2020-01-01',
      land_use_term_end: '2050-01-01',
      registration_date: '2020-02-01',
      co_ownership: null,
      restrictions: null,
      remarks: null,
      asset_ids: [],
      holder_party_ids: ['party-holder'],
      data_quality_warnings: [
        {
          risk_id: 'warning-1',
          risk_type: 'holder_owner_mismatch',
          severity: 'warning',
          message: '资产一主产权主体不一致',
          certificate_id: 'cert-1',
          asset_id: 'asset-1',
        },
        {
          risk_id: 'warning-2',
          risk_type: 'holder_owner_mismatch',
          severity: 'warning',
          message: '资产二主产权主体不一致',
          certificate_id: 'cert-1',
          asset_id: 'asset-2',
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
        route: '/property-certificates/cert-1',
      });

      expect(await screen.findAllByText('产权证详情')).not.toHaveLength(0);
      expect(await screen.findByText('CERT-001')).toBeInTheDocument();

      expect(formatConsoleMessages(consoleErrorSpy.mock.calls)).not.toContain('[antd: Space]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it('shows every certificate warning on the detail page and edit modal', async () => {
    renderWithProviders(<PropertyCertificateDetailPage />, {
      route: '/property-certificates/cert-1',
    });

    expect(await screen.findByText('资产一主产权主体不一致')).toBeInTheDocument();
    expect(screen.getByText('资产二主产权主体不一致')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /编辑/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('资产一主产权主体不一致')).toBeInTheDocument();
    expect(within(dialog).getByText('资产二主产权主体不一致')).toBeInTheDocument();
  });

  it('invalidates certificate, asset and project risk cache families after update', async () => {
    vi.mocked(propertyCertificateService.updateCertificate).mockResolvedValue(
      await propertyCertificateService.getCertificate('cert-1')
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    renderWithProviders(<PropertyCertificateDetailPage />, {
      route: '/property-certificates/cert-1',
      queryClient,
    });

    fireEvent.click(await screen.findByRole('button', { name: /编辑/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() => {
      expect(propertyCertificateService.updateCertificate).toHaveBeenCalled();
    });
    for (const queryKey of [
      ['property-certificate'],
      ['property-certificates'],
      ['asset-certificates'],
      ['asset'],
      ['project-risks'],
      ['project-analytics'],
    ]) {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey });
    }
  });

  it('invalidates dependent caches before navigating after deletion', async () => {
    vi.mocked(propertyCertificateService.deleteCertificate).mockResolvedValue(undefined);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    renderWithProviders(<PropertyCertificateDetailPage />, {
      route: '/property-certificates/cert-1',
      queryClient,
    });

    fireEvent.click(await screen.findByRole('button', { name: /删\s*除/ }));
    const confirm = await screen.findByRole('tooltip');
    fireEvent.click(within(confirm).getByRole('button', { name: /删\s*除/ }));

    await waitFor(() => {
      expect(propertyCertificateService.deleteCertificate).toHaveBeenCalledWith('cert-1');
    });
    for (const queryKey of [
      ['property-certificate'],
      ['property-certificates'],
      ['asset-certificates'],
      ['asset'],
      ['project-risks'],
      ['project-analytics'],
    ]) {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey });
    }
    expect(mockNavigate).toHaveBeenCalledWith('/property-certificates');
  });
});
