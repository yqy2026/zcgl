import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import AssetMultiSelect from '../AssetMultiSelect';
import { assetService } from '@/services/assetService';
import { createTestQueryClient, renderWithProviders } from '@/test/test-utils';

vi.mock('@/utils/queryScope', () => ({
  buildQueryScopeKey: () => 'user:user-1|scope:owner',
}));

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

  afterEach(() => {
    vi.useRealTimers();
  });

  it('初始加载时按项目过滤远程搜索资产', async () => {
    renderWithProviders(<AssetMultiSelect projectId="project-1" />);

    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenCalledWith('', {
        page_size: 20,
        project_id: 'project-1',
      });
    });
  });

  it('查询 key 包含 scope、项目和 trim 后关键词', async () => {
    vi.useFakeTimers();
    const queryClient = createTestQueryClient();
    renderWithProviders(<AssetMultiSelect projectId="project-1" />, { queryClient });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '  松柏  ' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(
      queryClient.getQueryState(['asset-options', 'user:user-1|scope:owner', 'project-1', '松柏'])
    ).toBeDefined();
  });

  it('远程搜索按 300ms 去抖并发送 trim 后关键词', async () => {
    vi.useFakeTimers();
    renderWithProviders(<AssetMultiSelect projectId="project-1" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    searchAssetsMock.mockClear();

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '  松' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '  松柏  ' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(299);
    });
    expect(searchAssetsMock).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(searchAssetsMock).toHaveBeenCalledTimes(1);
    expect(searchAssetsMock).toHaveBeenCalledWith('松柏', {
      page_size: 20,
      project_id: 'project-1',
    });
  });

  it('没有项目时不请求资产', async () => {
    renderWithProviders(<AssetMultiSelect />);

    await waitFor(() => {
      expect(searchAssetsMock).not.toHaveBeenCalled();
    });
  });

  it('选择资产后以 ID 数组回调 onChange', async () => {
    const onChange = vi.fn();
    renderWithProviders(<AssetMultiSelect projectId="project-1" onChange={onChange} />);

    fireEvent.mouseDown(screen.getByRole('combobox'));
    const option = await screen.findByText(/松柏东街 1 号/);
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledWith(['asset-1']);
  });

  it('项目变化时按新项目重新加载', async () => {
    const { rerender } = renderWithProviders(<AssetMultiSelect projectId="project-1" />);
    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenCalledWith('', {
        page_size: 20,
        project_id: 'project-1',
      });
    });

    rerender(<AssetMultiSelect projectId="project-2" />);

    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenLastCalledWith('', {
        page_size: 20,
        project_id: 'project-2',
      });
    });
  });

  it('项目变化时取消旧项目的待执行搜索并清空关键词', async () => {
    vi.useFakeTimers();
    const { rerender } = renderWithProviders(<AssetMultiSelect projectId="project-1" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    searchAssetsMock.mockClear();

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '旧项目关键词' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });

    rerender(<AssetMultiSelect projectId="project-2" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(searchAssetsMock).toHaveBeenCalledWith('', {
      page_size: 20,
      project_id: 'project-2',
    });
    expect(searchAssetsMock).not.toHaveBeenCalledWith('旧项目关键词', {
      page_size: 20,
      project_id: 'project-2',
    });
  });

  it('项目变化时不会把已生效的旧项目关键词用于新项目', async () => {
    vi.useFakeTimers();
    const { rerender } = renderWithProviders(<AssetMultiSelect projectId="project-1" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    searchAssetsMock.mockClear();

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '旧项目关键词' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(searchAssetsMock).toHaveBeenCalledWith('旧项目关键词', {
      page_size: 20,
      project_id: 'project-1',
    });
    searchAssetsMock.mockClear();

    rerender(<AssetMultiSelect projectId="project-2" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(screen.getByRole('combobox')).toHaveValue('');
    expect(searchAssetsMock).toHaveBeenCalledWith('', {
      page_size: 20,
      project_id: 'project-2',
    });
    expect(searchAssetsMock).not.toHaveBeenCalledWith('旧项目关键词', {
      page_size: 20,
      project_id: 'project-2',
    });
  });

  it('远程搜索失败时显示可观察的错误状态', async () => {
    searchAssetsMock.mockRejectedValueOnce(new Error('network failed'));
    renderWithProviders(<AssetMultiSelect projectId="project-1" />);

    fireEvent.mouseDown(screen.getByRole('combobox'));

    expect(await screen.findByText('资产加载失败，请重试')).toBeInTheDocument();
  });

  it('项目变化时不展示旧项目选项', async () => {
    let resolveProject2:
      | ((value: Awaited<ReturnType<typeof assetService.searchAssets>>) => void)
      | undefined;
    searchAssetsMock.mockImplementation(async (_query, filters) => {
      if (filters?.project_id === 'project-2') {
        return await new Promise(resolve => {
          resolveProject2 = resolve;
        });
      }
      return {
        items: assets as never,
        total: 2,
        page: 1,
        page_size: 20,
        pages: 1,
      };
    });

    const { rerender } = renderWithProviders(<AssetMultiSelect projectId="project-1" />);
    fireEvent.mouseDown(screen.getByRole('combobox'));
    expect(await screen.findByText(/松柏东街 1 号/)).toBeInTheDocument();

    rerender(<AssetMultiSelect projectId="project-2" />);

    await waitFor(() => {
      expect(searchAssetsMock).toHaveBeenLastCalledWith('', {
        page_size: 20,
        project_id: 'project-2',
      });
    });
    expect(screen.queryByText(/松柏东街 1 号/)).not.toBeInTheDocument();

    resolveProject2?.({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      pages: 0,
    });
  });
});
