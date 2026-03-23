import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiHealthCheck from '../apiHealthCheck';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';

describe('apiHealthCheck contract-group monitoring', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiHealthCheck.clearResults();
    vi.spyOn(performance, 'now').mockReturnValueOnce(0).mockReturnValue(50);
    vi.mocked(apiClient.get).mockResolvedValue({ success: true });
  });

  it('checks the new contract-group endpoint instead of retired rental-contracts contracts', async () => {
    await apiHealthCheck.checkCriticalEndpoints();

    expect(vi.mocked(apiClient.get)).toHaveBeenCalledWith('/contract-groups', { timeout: 5000 });
    expect(vi.mocked(apiClient.get)).not.toHaveBeenCalledWith('/rental-contracts/contracts', {
      timeout: 5000,
    });
  });
});
