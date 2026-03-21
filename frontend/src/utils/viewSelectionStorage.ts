import type { StoredViewSelection } from '@/types/viewSelection';

const STORAGE_PREFIX = 'view-selection:';

const buildStorageKey = (userId: string): string => `${STORAGE_PREFIX}${userId}`;

export const viewSelectionStorage = {
  get(userId: string): StoredViewSelection | null {
    if (userId.trim() === '') {
      return null;
    }

    try {
      const raw = localStorage.getItem(buildStorageKey(userId));
      if (raw == null) {
        return null;
      }
      return JSON.parse(raw) as StoredViewSelection;
    } catch {
      return null;
    }
  },

  set(userId: string, selection: StoredViewSelection): void {
    if (userId.trim() === '') {
      return;
    }
    localStorage.setItem(buildStorageKey(userId), JSON.stringify(selection));
  },

  clear(userId: string): void {
    if (userId.trim() === '') {
      return;
    }
    localStorage.removeItem(buildStorageKey(userId));
  },
};
