import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/utils/AuthStorage', () => ({
  AuthStorage: {
    getCurrentUser: vi.fn(),
  },
}));

import { AuthStorage } from '@/utils/AuthStorage';
import { buildQueryScopeKey, getCurrentRequestScopeKey } from '../queryScope';

describe('queryScope', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('builds a scoped key from user id and route perspective', () => {
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue({
      id: 'user-1',
    } as never);

    expect(buildQueryScopeKey('owner')).toBe('user:user-1|perspective:owner');
    expect(buildQueryScopeKey('manager')).toBe('user:user-1|perspective:manager');
    expect(buildQueryScopeKey(null)).toBe('user:user-1|perspective:none');
  });

  it('falls back to anonymous scope when no user is available', () => {
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue(null);

    expect(buildQueryScopeKey('owner')).toBe('user:anonymous|perspective:owner');
  });

  it('derives the current request scope without consulting stored view selection', () => {
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue({
      id: 'user-2',
    } as never);

    expect(getCurrentRequestScopeKey('manager')).toBe('user:user-2|perspective:manager');
    expect(getCurrentRequestScopeKey()).toBe('user:user-2|perspective:none');
  });
});
