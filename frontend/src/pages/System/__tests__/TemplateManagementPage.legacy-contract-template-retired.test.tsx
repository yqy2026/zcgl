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

describe('TemplateManagementPage legacy contract template retirement', () => {
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

  it('shows a retirement notice instead of calling legacy rent contract template download', async () => {
    renderWithProviders(<TemplateManagementPage />);

    expect(await screen.findByText('租赁合同导入模板')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '下载模板 租赁合同导入模板' }));

    await waitFor(() => {
      expect(MessageManager.info).toHaveBeenCalledWith(
        '租赁合同导入模板已退休，请等待新 contract/contract-group 模板入口'
      );
    });
  });
});
