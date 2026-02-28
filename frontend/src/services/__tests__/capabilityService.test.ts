import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CapabilityService } from '../capabilityService';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : String(error),
    })),
  },
}));

import { apiClient } from '@/api/client';

describe('CapabilityService', () => {
  let service: CapabilityService;

  beforeEach(() => {
    service = new CapabilityService();
    vi.clearAllMocks();
  });

  it('fetches capabilities from /auth/me/capabilities', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [
          {
            resource: 'asset',
            actions: ['read'],
            perspectives: ['owner'],
            data_scope: {
              owner_party_ids: ['p-1'],
              manager_party_ids: [],
            },
          },
        ],
      },
    });

    const result = await service.fetchCapabilities();

    expect(result.capabilities).toHaveLength(1);
    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/me/capabilities',
      expect.objectContaining({ cache: false })
    );
  });

  it('uses cache for repeated getCapabilities call', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [],
      },
    });

    await service.getCapabilities();
    await service.getCapabilities();

    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  it('bypasses cache when forceRefresh=true', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [],
      },
    });

    await service.getCapabilities();
    await service.getCapabilities({ forceRefresh: true });

    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });

  it('shares in-flight request to avoid duplicate concurrent calls', async () => {
    let resolveRequest: ((value: unknown) => void) | null = null;

    vi.mocked(apiClient.get).mockImplementation(
      () =>
        new Promise(resolve => {
          resolveRequest = resolve;
        }) as ReturnType<typeof apiClient.get>
    );

    const requestA = service.fetchCapabilities();
    const requestB = service.fetchCapabilities();

    resolveRequest?.({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [],
      },
    });

    await Promise.all([requestA, requestB]);

    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  it('clears cache and in-flight state', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [],
      },
    });

    await service.getCapabilities();
    service.clearCache();
    await service.getCapabilities();

    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });

  it('does not let stale in-flight request repopulate cache after clearCache', async () => {
    let resolveFirst: ((value: unknown) => void) | null = null;
    let resolveSecond: ((value: unknown) => void) | null = null;

    vi.mocked(apiClient.get)
      .mockImplementationOnce(
        () =>
          new Promise(resolve => {
            resolveFirst = resolve;
          }) as ReturnType<typeof apiClient.get>
      )
      .mockImplementationOnce(
        () =>
          new Promise(resolve => {
            resolveSecond = resolve;
          }) as ReturnType<typeof apiClient.get>
      );

    const firstRequest = service.fetchCapabilities();
    service.clearCache();
    const secondRequest = service.fetchCapabilities({ forceRefresh: true });

    resolveSecond?.({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-27T00:00:00Z',
        capabilities: [
          {
            resource: 'asset',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: [], manager_party_ids: [] },
          },
        ],
      },
    });
    resolveFirst?.({
      success: true,
      data: {
        version: 'v1',
        generated_at: '2026-02-26T00:00:00Z',
        capabilities: [
          {
            resource: 'project',
            actions: ['read'],
            perspectives: [],
            data_scope: { owner_party_ids: [], manager_party_ids: [] },
          },
        ],
      },
    });

    await Promise.all([firstRequest, secondRequest]);

    const cached = service.getCachedCapabilities();
    expect(cached?.capabilities).toEqual([
      {
        resource: 'asset',
        actions: ['read'],
        perspectives: [],
        data_scope: { owner_party_ids: [], manager_party_ids: [] },
      },
    ]);
  });
});
