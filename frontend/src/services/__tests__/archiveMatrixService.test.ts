import { describe, expect, it, vi } from 'vitest';
import { apiClient } from '@/api/client';
import { archiveMatrixService } from '@/services/archiveMatrixService';
vi.mock('@/api/client', () => ({ apiClient: { get: vi.fn() } }));
describe('archive matrix service', () => {
  it('queries scoped current facts without cache and keeps pagination', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: { as_of: '2026-11-03', items: [], total: 23 },
    });
    expect((await archiveMatrixService.matrix({ q: '园区', offset: 20, limit: 20 })).total).toBe(
      23
    );
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/archive/matrix', {
      params: { q: '园区', offset: 20, limit: 20 },
      cache: false,
    });
  });
  it('rejects an empty response instead of inventing completion', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ success: false });
    await expect(archiveMatrixService.completion({})).rejects.toThrow();
  });
});
