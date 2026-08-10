import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AssetMultiSelect from '../AssetMultiSelect';
import { assetService } from '@/services/assetService';

vi.mock('@/services/assetService', () => ({
  assetService: {
    searchAssets: vi.fn(),
  },
}));

const assets = [
  { id: 'asset-1', asset_name: '松柏东街 1 号', address: '广州市越秀区' },
  { id: 'asset-2', asset_name: '湖滨产业园 A 座', address: '广州市天河区' },
];

const searchAssetsMock = vi.mocked(assetService.searchAssets);

describe('AssetMultiSelect (PDF 导入确认页资产多选)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchAssetsMock.mockResolvedValue({
      items: assets as never,
      total: 2,
      page: 1,
      page_size: 20,
      success: true,
      message: '',
      data: undefined,
    } as never);
  });

  it('初始加载时按项目过滤远程搜索资产', async () => {
    render(<AssetMultiSelect projectId="project-1" />);

    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenCalledWith('', {
        limit: 20,
        project_id: 'project-1',
      });
    });
  });

  it('选择资产后以 ID 数组回调 onChange', async () => {
    const onChange = vi.fn();
    render(<AssetMultiSelect onChange={onChange} />);

    fireEvent.mouseDown(screen.getByRole('combobox'));
    const option = await screen.findByText(/松柏东街 1 号/);
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledWith(['asset-1']);
  });

  it('项目变化时按新项目重新加载', async () => {
    const { rerender } = render(<AssetMultiSelect projectId="project-1" />);
    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenCalledWith('', {
        limit: 20,
        project_id: 'project-1',
      });
    });

    rerender(<AssetMultiSelect projectId="project-2" />);

    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenLastCalledWith('', {
        limit: 20,
        project_id: 'project-2',
      });
    });
  });
});
