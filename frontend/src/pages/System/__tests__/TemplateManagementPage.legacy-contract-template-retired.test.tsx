import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import TemplateManagementPage from '../TemplateManagementPage';
import { assetService } from '@/services/assetService';
import { MessageManager } from '@/utils/messageManager';

vi.mock('@/services/assetService', () => ({
  assetService: {
    downloadImportTemplate: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  }),
}));

describe('TemplateManagementPage mock 收敛（#79）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetService.downloadImportTemplate).mockResolvedValue(undefined);
  });

  it('keeps asset template download working', async () => {
    renderWithProviders(<TemplateManagementPage />);

    expect(await screen.findByText('资产导入模板')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '下载模板 资产导入模板' }));

    await waitFor(() => {
      expect(assetService.downloadImportTemplate).toHaveBeenCalledTimes(1);
      expect(MessageManager.success).toHaveBeenCalledWith('资产导入模板下载成功');
    });
  });

  it('does not render the retired rent-contract template entry', async () => {
    renderWithProviders(<TemplateManagementPage />);

    expect(await screen.findByText('资产导入模板')).toBeInTheDocument();
    expect(screen.queryByText('租赁合同导入模板')).not.toBeInTheDocument();
    expect(screen.queryByText('租赁合同')).not.toBeInTheDocument();
  });

  it('does not render fake statistics cards or fake version/size columns', async () => {
    renderWithProviders(<TemplateManagementPage />);

    expect(await screen.findByText('资产导入模板')).toBeInTheDocument();
    expect(screen.getByText('共 1 个模板')).toBeInTheDocument();
    expect(screen.queryByText('可用模板')).not.toBeInTheDocument();
    expect(screen.queryByText('资产模板')).not.toBeInTheDocument();
    expect(screen.queryByText('合同模板')).not.toBeInTheDocument();
    expect(screen.queryByText('总下载量')).not.toBeInTheDocument();
    expect(screen.queryByText('文件大小')).not.toBeInTheDocument();
    expect(screen.queryByText('更新时间')).not.toBeInTheDocument();
  });
});
