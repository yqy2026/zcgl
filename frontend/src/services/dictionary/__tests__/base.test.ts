import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { DICTIONARY_CONFIGS } from '@/services/dictionary/config';
import { baseDictionaryService } from '@/services/dictionary/base';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

describe('baseDictionaryService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseDictionaryService.clearCache();
  });

  it('getOptions 在无效类型时应返回失败结果', async () => {
    const result = await baseDictionaryService.getOptions('not-exists', {
      includeMetadata: true,
    });

    expect(result.success).toBe(false);
    expect(result.source).toBe('fallback');
    expect(result.data).toEqual([]);
    expect(result.error).toContain('字典类型不存在');
  });

  it('getOptions 应优先返回 API 数据并命中缓存', async () => {
    const payload = [
      { label: 'A', value: 'a', isActive: true },
      { label: 'B', value: 'b', isActive: false },
    ];
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: payload,
    } as never);

    const first = await baseDictionaryService.getOptions('usage_status', {
      useCache: true,
      includeMetadata: true,
    });
    const second = await baseDictionaryService.getOptions('usage_status', {
      useCache: true,
      includeMetadata: true,
    });

    expect(first.success).toBe(true);
    expect(first.source).toBe('api');
    expect(first.data).toEqual(payload);
    expect(first.metadata?.activeItems).toBe(1);
    expect(second.success).toBe(true);
    expect(second.source).toBe('cache');
    expect(vi.mocked(apiClient.get)).toHaveBeenCalledTimes(1);
  });

  it('getOptions 在 API 异常时应回退 fallback 数据', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('network'));

    const result = await baseDictionaryService.getOptions('ownership_category', {
      useFallback: true,
      includeMetadata: true,
    });

    expect(result.success).toBe(true);
    expect(result.source).toBe('fallback');
    expect(result.data.length).toBeGreaterThan(0);
    expect(result.error).toContain('network');
  });

  it('getBatchOptions 应返回缓存与实时查询混合结果', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [{ label: '缓存项', value: 'cached' }],
    } as never);
    await baseDictionaryService.getOptions('tenant_type', { useCache: true });

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      success: true,
      data: [{ label: '实时项', value: 'fresh' }],
    } as never);

    const result = await baseDictionaryService.getBatchOptions(
      ['tenant_type', 'contract_status'],
      {
        useCache: true,
        includeMetadata: true,
      }
    );

    expect(result.tenant_type.source).toBe('cache');
    expect(result.contract_status.source).toBe('api');
    expect(result.contract_status.data[0]?.value).toBe('fresh');
  });

  it('getParallelOptions 在内部异常时应返回 fallback 失败结果', async () => {
    const spy = vi
      .spyOn(baseDictionaryService, 'getOptions')
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce({
        success: true,
        data: [{ label: 'ok', value: 'ok' }],
        source: 'api',
      });

    const result = await baseDictionaryService.getParallelOptions(['a', 'b']);
    expect(result.a.success).toBe(false);
    expect(result.a.source).toBe('fallback');
    expect(result.b.success).toBe(true);

    spy.mockRestore();
  });

  it('类型检索方法应按配置返回结果', () => {
    const available = baseDictionaryService.getAvailableTypes();
    const searched = baseDictionaryService.searchTypes('状态');
    const config = baseDictionaryService.getTypeConfig('usage_status');

    expect(available.length).toBeGreaterThan(0);
    expect(searched.length).toBeGreaterThan(0);
    expect(baseDictionaryService.isTypeAvailable('usage_status')).toBe(true);
    expect(baseDictionaryService.isTypeAvailable('not-exists')).toBe(false);
    expect(config?.code).toBe('usage_status');
  });

  it('preload 与 smartPreload 应执行进度与智能预加载逻辑', async () => {
    const progress = vi.fn();
    const types = ['usage_status', 'contract_status'];
    const getOptionsSpy = vi.spyOn(baseDictionaryService, 'getOptions').mockResolvedValue({
      success: true,
      data: [{ label: 'x', value: 'x' }],
      source: 'api',
    });

    const preload = await baseDictionaryService.preload(types, {
      batchSize: 1,
      onProgress: progress,
    });

    expect(preload.success).toBe(true);
    expect(preload.loadedTypes).toEqual(types);
    expect(progress).toHaveBeenCalledTimes(2);
    getOptionsSpy.mockRestore();

    // 让缓存产生命中记录，触发 smartPreload 分支
    baseDictionaryService.clearCache();
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [{ label: '命中', value: 'hit' }],
    } as never);
    await baseDictionaryService.getOptions('usage_status', { useCache: true });
    await baseDictionaryService.getOptions('usage_status', { useCache: true });

    const preloadSpy = vi.spyOn(baseDictionaryService, 'preload').mockResolvedValue({
      success: true,
      loadedTypes: ['usage_status'],
      failedTypes: [],
      totalItems: 1,
      loadTime: 1,
    });
    await baseDictionaryService.smartPreload();
    expect(preloadSpy).toHaveBeenCalled();

    preloadSpy.mockRestore();
  });

  it('统计与缓存报告应返回推荐信息', async () => {
    // 人为制造低命中缓存
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [{ label: 'x', value: 'x', isActive: true }],
    } as never);
    await baseDictionaryService.getOptions('usage_status', { useCache: true, forceRefresh: true });

    const stats = baseDictionaryService.getStats();
    const report = baseDictionaryService.getCacheReport();

    expect(stats.totalTypes).toBe(Object.keys(DICTIONARY_CONFIGS).length);
    expect(report.summary.totalTypes).toBe(stats.totalTypes);
    expect(Array.isArray(report.recommendations)).toBe(true);
  });

  it('refreshTypes 与 validateDictionaryData 应覆盖成功和失败分支', async () => {
    const refreshSpy = vi
      .spyOn(baseDictionaryService, 'getOptions')
      .mockResolvedValueOnce({
        success: true,
        data: [{ label: 'ok', value: 'ok' }],
        source: 'api',
      })
      .mockResolvedValueOnce({
        success: false,
        data: [],
        source: 'fallback',
        error: 'failed',
      });

    const refreshed = await baseDictionaryService.refreshTypes(['usage_status', 'contract_status']);
    expect(refreshed.success).toEqual(['usage_status']);
    expect(refreshed.failed[0]?.type).toBe('contract_status');
    refreshSpy.mockRestore();

    const invalidType = baseDictionaryService.validateDictionaryData('not-exists');
    expect(invalidType.isValid).toBe(false);

    // 写入包含重复值的缓存数据，触发校验建议
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: [
        { label: '一', value: 'dup' },
        { label: '二', value: 'dup' },
        { label: '', value: '' },
      ],
    } as never);
    await baseDictionaryService.getOptions('usage_status', { useCache: true, forceRefresh: true });
    const validation = baseDictionaryService.validateDictionaryData('usage_status');
    expect(validation.isValid).toBe(false);
    expect(validation.issues.length).toBeGreaterThan(0);
    expect(validation.suggestions.length).toBeGreaterThan(0);
  });
});
