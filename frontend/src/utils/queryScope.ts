import { AuthStorage } from '@/utils/AuthStorage';
import type { Perspective } from '@/types/capability';

const ANONYMOUS_USER_SCOPE = 'user:anonymous';
const NO_PERSPECTIVE_SCOPE = 'perspective:none';

type ScopePerspective =
  | Extract<Perspective, 'owner' | 'manager'>
  | {
      perspective?: Perspective | null;
    }
  | null
  | undefined;

const normalizePerspective = (
  value: ScopePerspective
): Extract<Perspective, 'owner' | 'manager'> | null => {
  if (value == null) {
    return null;
  }

  if (typeof value === 'string') {
    return value === 'owner' || value === 'manager' ? (value as 'owner' | 'manager') : null;
  }

  const perspective = value.perspective;
  if (perspective === 'owner') {
    return 'owner';
  }

  if (perspective === 'manager') {
    return 'manager';
  }

  return null;
};

type ScopeViewLegacy =
  | {
      key: string;
    }
  | null
  | undefined;

const normalizeUserScope = (userId: string | null | undefined): string => {
  const normalizedUserId = userId?.trim() ?? '';
  return normalizedUserId !== '' ? `user:${normalizedUserId}` : ANONYMOUS_USER_SCOPE;
};

const normalizePerspectiveScope = (value: ScopePerspective): string => {
  const perspective = normalizePerspective(value);
  return perspective != null ? `perspective:${perspective}` : NO_PERSPECTIVE_SCOPE;
};

export const buildQueryScopeKey = (view: ScopePerspective | ScopeViewLegacy): string => {
  const currentUser = AuthStorage.getCurrentUser();
  return `${normalizeUserScope(currentUser?.id)}|${normalizePerspectiveScope(
    view as ScopePerspective
  )}`;
};

export const getCurrentRequestScopeKey = (perspective?: ScopePerspective): string => {
  const currentUser = AuthStorage.getCurrentUser();
  return `${normalizeUserScope(currentUser?.id)}|${normalizePerspectiveScope(perspective)}`;
};
