/**
 * useDictionary Hook 测试
 * 测试字典数据获取和管理功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook, waitFor } from '@/test/utils/test-helpers';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

const formatStderrWrites = (calls: unknown[][]) =>
  calls.map(call => String(call[0] ?? '')).join(' ');

// =============================================================================
// Mock dictionaryService
// =============================================================================

const mockGetOptions = vi.fn();
const mockGetAvailableTypes = vi.fn();
const mockQuickCreate = vi.fn();
const mockDeleteType = vi.fn();

vi.mock('../../services/dictionary', () => ({
  dictionaryService: {
    getOptions: (...args: unknown[]) => mockGetOptions(...args),
    getAvailableTypes: () => mockGetAvailableTypes(),
    quickCreate: (...args: unknown[]) => mockQuickCreate(...args),
    deleteType: (...args: unknown[]) => mockDeleteType(...args),
  },
}));

// =============================================================================
// Mock logger
// =============================================================================

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

// =============================================================================
// Test utilities
// =============================================================================

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  Wrapper.displayName = 'QueryClientWrapper';
  return Wrapper;
};

// =============================================================================
// useDictionary 测试
// =============================================================================

describe('useDictionary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load dictionary options successfully', async () => {
    const mockOptions = [
      { label: '选项1', value: 'option1' },
      { label: '选项2', value: 'option2' },
    ];

    mockGetOptions.mockResolvedValue({
      success: true,
      data: mockOptions,
    });

    const { useDictionary } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionary('asset_type'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.options).toEqual(mockOptions);
    expect(result.current.error).toBeNull();
    expect(mockGetOptions).toHaveBeenCalledWith('asset_type', {
      useCache: true,
      useFallback: true,
      isActive: true,
    });
  });

  it('should handle empty dictType', async () => {
    const { useDictionary } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionary(''), {
      wrapper: createWrapper(),
    });

    // 空字典类型不应触发请求
    expect(result.current.options).toEqual([]);
    expect(mockGetOptions).not.toHaveBeenCalled();
  });

  it('should handle API error', async () => {
    mockGetOptions.mockResolvedValue({
      success: false,
      error: '获取字典失败',
    });

    const { useDictionary } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionary('invalid_type'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.options).toEqual([]);
    expect(result.current.error).toBe('获取字典失败');
  });

  it('should respect isActive parameter', async () => {
    mockGetOptions.mockResolvedValue({
      success: true,
      data: [],
    });

    const { useDictionary } = await import('../useDictionary');
    renderHook(() => useDictionary('asset_type', false), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockGetOptions).toHaveBeenCalled();
    });

    expect(mockGetOptions).toHaveBeenCalledWith('asset_type', {
      useCache: true,
      useFallback: true,
      isActive: false,
    });
  });

  it('should provide refresh function', async () => {
    mockGetOptions.mockResolvedValue({
      success: true,
      data: [{ label: '初始', value: 'initial' }],
    });

    const { useDictionary } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionary('asset_type'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(typeof result.current.refresh).toBe('function');

    // 模拟刷新后返回新数据
    mockGetOptions.mockResolvedValue({
      success: true,
      data: [{ label: '更新后', value: 'updated' }],
    });

    await result.current.refresh();

    await waitFor(() => {
      expect(result.current.options).toEqual([{ label: '更新后', value: 'updated' }]);
    });
  });

  it('should handle null data gracefully', async () => {
    mockGetOptions.mockResolvedValue({
      success: true,
      data: null,
    });

    const { useDictionary } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionary('asset_type'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.options).toEqual([]);
  });
});

// =============================================================================
// useDictionaries 测试
// =============================================================================

describe('useDictionaries', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load multiple dictionaries', async () => {
    mockGetOptions
      .mockResolvedValueOnce({
        success: true,
        data: [{ label: '类型1', value: 'type1' }],
      })
      .mockResolvedValueOnce({
        success: true,
        data: [{ label: '状态1', value: 'status1' }],
      });

    const { useDictionaries } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaries(['asset_type', 'asset_status']), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current['asset_type'].isLoading).toBe(false);
      expect(result.current['asset_status'].isLoading).toBe(false);
    });

    expect(result.current['asset_type'].options).toEqual([{ label: '类型1', value: 'type1' }]);
    expect(result.current['asset_status'].options).toEqual([{ label: '状态1', value: 'status1' }]);
  });

  it('should handle partial failures', async () => {
    mockGetOptions
      .mockResolvedValueOnce({
        success: true,
        data: [{ label: '成功', value: 'success' }],
      })
      .mockResolvedValueOnce({
        success: false,
        error: '加载失败',
      });

    const { useDictionaries } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaries(['dict1', 'dict2']), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current['dict1'].isLoading).toBe(false);
      expect(result.current['dict2'].isLoading).toBe(false);
    });

    expect(result.current['dict1'].options).toHaveLength(1);
    expect(result.current['dict1'].error).toBeNull();
    expect(result.current['dict2'].options).toEqual([]);
    expect(result.current['dict2'].error).toBe('加载失败');
  });

  it('should handle empty array', async () => {
    const { useDictionaries } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaries([]), {
      wrapper: createWrapper(),
    });

    expect(Object.keys(result.current)).toHaveLength(0);
    expect(mockGetOptions).not.toHaveBeenCalled();
  });
});

// =============================================================================
// useDictionaryManager 测试
// =============================================================================

describe('useDictionaryManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load available dictionary types on mount', async () => {
    mockGetAvailableTypes.mockReturnValue([
      { code: 'asset_type', name: '资产类型' },
      { code: 'asset_status', name: '资产状态' },
    ]);

    const { useDictionaryManager } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaryManager(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.types).toEqual(['asset_type', 'asset_status']);
    expect(mockGetAvailableTypes).toHaveBeenCalled();
  });

  it('should create dictionary successfully', async () => {
    mockGetAvailableTypes.mockReturnValue([]);
    mockQuickCreate.mockResolvedValue({ success: true });
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      const { useDictionaryManager } = await import('../useDictionary');
      const { result } = renderHook(() => useDictionaryManager(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let success = false;
      await act(async () => {
        success = await result.current.createDictionary('new_type', [
          { label: '新选项', value: 'new_option' },
        ]);
      });

      expect(success).toBe(true);
      expect(mockQuickCreate).toHaveBeenCalledWith('new_type', {
        options: [{ label: '新选项', value: 'new_option' }],
      });
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('not wrapped in act');
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('should handle create dictionary failure', async () => {
    mockGetAvailableTypes.mockReturnValue([]);
    mockQuickCreate.mockResolvedValue({ success: false, error: '创建失败' });

    const { useDictionaryManager } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaryManager(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const success = await result.current.createDictionary('new_type', []);

    expect(success).toBe(false);
  });

  it('should delete dictionary successfully', async () => {
    mockGetAvailableTypes.mockReturnValue([{ code: 'to_delete', name: '待删除' }]);
    mockDeleteType.mockResolvedValue({ success: true });
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      const { useDictionaryManager } = await import('../useDictionary');
      const { result } = renderHook(() => useDictionaryManager(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let success = false;
      await act(async () => {
        success = await result.current.deleteDictionary('to_delete');
      });

      expect(success).toBe(true);
      expect(mockDeleteType).toHaveBeenCalledWith('to_delete');
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('not wrapped in act');
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('should handle delete dictionary failure', async () => {
    mockGetAvailableTypes.mockReturnValue([]);
    mockDeleteType.mockResolvedValue({ success: false, error: '删除失败' });

    const { useDictionaryManager } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaryManager(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const success = await result.current.deleteDictionary('some_type');

    expect(success).toBe(false);
  });

  it('should provide refresh function', async () => {
    mockGetAvailableTypes
      .mockReturnValueOnce([{ code: 'initial', name: '初始' }])
      .mockReturnValueOnce([
        { code: 'initial', name: '初始' },
        { code: 'new', name: '新增' },
      ]);
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      const { useDictionaryManager } = await import('../useDictionary');
      const { result } = renderHook(() => useDictionaryManager(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.types).toEqual(['initial']);

      await act(async () => {
        await result.current.refresh();
      });

      await waitFor(() => {
        expect(result.current.types).toEqual(['initial', 'new']);
      });
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain('not wrapped in act');
    } finally {
      stderrWriteSpy.mockRestore();
    }
  });

  it('should handle getAvailableTypes exception', async () => {
    mockGetAvailableTypes.mockImplementation(() => {
      throw new Error('Service error');
    });

    const { useDictionaryManager } = await import('../useDictionary');
    const { result } = renderHook(() => useDictionaryManager(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.types).toEqual([]);
  });
});
