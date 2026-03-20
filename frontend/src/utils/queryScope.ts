import { AuthStorage } from '@/utils/AuthStorage';
import { viewSelectionStorage } from '@/utils/viewSelectionStorage';

const ANONYMOUS_USER_SCOPE = 'user:anonymous';
const NO_VIEW_SCOPE = 'view:none';

type ScopeView = {
  key: string;
} | null | undefined;

const normalizeUserScope = (userId: string | null | undefined): string => {
  const normalizedUserId = userId?.trim() ?? '';
  return normalizedUserId !== '' ? `user:${normalizedUserId}` : ANONYMOUS_USER_SCOPE;
};

const normalizeViewScope = (view: ScopeView): string => {
  const normalizedViewKey = view?.key?.trim() ?? '';
  return normalizedViewKey !== '' ? `view:${normalizedViewKey}` : NO_VIEW_SCOPE;
};

export const buildQueryScopeKey = (view: ScopeView): string => {
  const currentUser = AuthStorage.getCurrentUser();
  return `${normalizeUserScope(currentUser?.id)}|${normalizeViewScope(view)}`;
};

export const getCurrentRequestScopeKey = (): string => {
  const currentUser = AuthStorage.getCurrentUser();
  const currentUserId = currentUser?.id?.trim() ?? '';
  const currentView = currentUserId !== '' ? viewSelectionStorage.get(currentUserId) : null;

  return `${normalizeUserScope(currentUserId)}|${normalizeViewScope(currentView)}`;
};
