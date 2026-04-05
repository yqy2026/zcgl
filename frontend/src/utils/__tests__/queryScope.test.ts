import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDataScopeStore } from '@/stores/dataScopeStore';

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
    useDataScopeStore.getState().reset();
  });

  it('builds a scoped key from user id and binding types', () => {
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue({
      id: 'user-1',
    } as never);
    useDataScopeStore.setState({ bindingTypes: ['owner'], isAdmin: false });

    expect(buildQueryScopeKey()).toBe('user:user-1|scope:owner');
  });

  it('falls back to anonymous scope when no user is available', () => {
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue(null);

    expect(buildQueryScopeKey()).toBe('user:anonymous|scope:none');
  });

  it('derives admin request scope from store state', () => {
    vi.mocked(AuthStorage.getCurrentUser).mockReturnValue({
      id: 'user-2',
    } as never);
    useDataScopeStore.setState({ bindingTypes: ['owner', 'manager'], isAdmin: true });

    expect(getCurrentRequestScopeKey()).toBe('user:user-2|scope:admin');
  });
});
