import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import { PropertyCertificateList } from '../PropertyCertificateList';
import { propertyCertificateService } from '@/services/propertyCertificateService';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/propertyCertificateService', () => ({
  propertyCertificateService: {
    listCertificates: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    loading: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    destroy: vi.fn(),
  },
}));

const certificates = [
  {
    id: 'cert-1',
    certificate_number: '粤(2026)0001号',
    certificate_type: 'real_estate',
    property_address: '广州市越秀区',
    building_area: '1200',
    created_at: '2026-03-01',
    updated_at: '2026-03-01',
    asset_ids: ['asset-1'],
  },
  {
    id: 'cert-2',
    certificate_number: '粤(2026)0002号',
    certificate_type: 'land_use',
    property_address: '广州市天河区',
    building_area: null,
    created_at: '2026-03-02',
    updated_at: '2026-03-02',
    asset_ids: ['asset-2'],
  },
];

describe('PropertyCertificateList（全中文化，#78）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(propertyCertificateService.listCertificates).mockResolvedValue(
      certificates as never
    );
  });

  it('渲染中文标题、列头与按钮', async () => {
    renderWithProviders(<PropertyCertificateList />);

    await waitFor(() => {
      expect(screen.getByText('产权证管理')).toBeInTheDocument();
    });
    expect(screen.getAllByText('证书编号').length).toBeGreaterThan(0);
    expect(screen.getAllByText('类型').length).toBeGreaterThan(0);
    expect(screen.getAllByText('坐落地址').length).toBeGreaterThan(0);
    expect(screen.getAllByText('建筑面积').length).toBeGreaterThan(0);
    expect(screen.getAllByText('创建时间').length).toBeGreaterThan(0);
    expect(screen.getAllByText('操作').length).toBeGreaterThan(0);
    expect(screen.getByText('新建产权证')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('搜索证书编号')).toBeInTheDocument();
  });

  it('证照类型显示中文标签', async () => {
    renderWithProviders(<PropertyCertificateList />);

    await waitFor(() => {
      expect(screen.getByText('粤(2026)0001号')).toBeInTheDocument();
    });
    expect(screen.getByText('不动产权证')).toBeInTheDocument();
    expect(screen.getByText('土地使用权证')).toBeInTheDocument();
  });

  it('页面无英文残留文案', async () => {
    renderWithProviders(<PropertyCertificateList />);

    await waitFor(() => {
      expect(screen.getByText('粤(2026)0001号')).toBeInTheDocument();
    });
    expect(screen.queryByText(/Certificate/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Property Certificates/)).not.toBeInTheDocument();
    expect(screen.queryByText('New Certificate')).not.toBeInTheDocument();
    expect(screen.queryByText('View')).not.toBeInTheDocument();
  });
});
