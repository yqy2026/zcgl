import { AuthStorage } from '@/utils/AuthStorage';
import { useDataScopeStore } from '@/stores/dataScopeStore';

const ANONYMOUS_USER_SCOPE = 'user:anonymous';

const normalizeUserScope = (userId: string | null | undefined): string => {
  const normalizedUserId = userId?.trim() ?? '';
  return normalizedUserId !== '' ? `user:${normalizedUserId}` : ANONYMOUS_USER_SCOPE;
};

export const buildScopeKey = (_legacyScope?: unknown): string => {
  const currentUser = AuthStorage.getCurrentUser();
  const { bindingTypes, isAdmin } = useDataScopeStore.getState();

  let scopeToken: string;
  if (isAdmin) {
    scopeToken = 'scope:admin';
  } else if (bindingTypes.length > 0) {
    scopeToken = `scope:${[...bindingTypes].sort().join(',')}`;
  } else {
    scopeToken = 'scope:none';
  }

  return `${normalizeUserScope(currentUser?.id)}|${scopeToken}`;
};

export const buildQueryScopeKey = (_legacyScope?: unknown): string => buildScopeKey();
export const getCurrentRequestScopeKey = (_legacyScope?: unknown): string => buildScopeKey();
