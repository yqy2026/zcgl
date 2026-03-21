import React, {
  createContext,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { partyService } from '@/services/partyService';
import type { Perspective } from '@/types/capability';
import type { StoredViewSelection, ViewSelectionOption } from '@/types/viewSelection';
import { mergeCapabilitiesByResource } from '@/utils/authz/capabilityEvaluator';
import { viewSelectionStorage } from '@/utils/viewSelectionStorage';
import { useAuth } from './AuthContext';

interface ViewContextValue {
  currentView: ViewSelectionOption | null;
  availableViews: ViewSelectionOption[];
  selectionRequired: boolean;
  selectorOpen: boolean;
  isViewReady: boolean;
  openSelector: () => void;
  closeSelector: () => void;
  selectView: (key: string) => void;
}

interface ViewProviderProps {
  children: React.ReactNode;
}

const ViewContext = createContext<ViewContextValue | undefined>(undefined);

const AUTHZ_STALE_EVENT_NAME = 'authz-stale';

interface RawViewOption {
  key: string;
  perspective: Perspective;
  partyId: string;
}

const PERSPECTIVE_LABELS: Record<string, string> = {
  owner: '产权方',
  manager: '运营方',
};

const toPerspectiveLabel = (perspective: Perspective): string =>
  PERSPECTIVE_LABELS[perspective] ?? String(perspective);

const buildRawViewOptions = (
  capabilities: ReturnType<typeof mergeCapabilitiesByResource>
): RawViewOption[] => {
  const options = new Map<string, RawViewOption>();

  for (const capability of capabilities) {
    for (const partyId of capability.data_scope.owner_party_ids) {
      const key = `owner:${partyId}`;
      options.set(key, {
        key,
        perspective: 'owner',
        partyId,
      });
    }

    for (const partyId of capability.data_scope.manager_party_ids) {
      const key = `manager:${partyId}`;
      options.set(key, {
        key,
        perspective: 'manager',
        partyId,
      });
    }
  }

  return Array.from(options.values());
};

const normalizeStoredSelection = (
  selection: StoredViewSelection | null
): StoredViewSelection | null => {
  if (selection == null) {
    return null;
  }
  if (selection.key.trim() === '' || selection.partyId.trim() === '') {
    return null;
  }
  return selection;
};

const resolvePartyName = async (partyId: string): Promise<string> => {
  try {
    const party = await partyService.getPartyById(partyId);
    return party.name;
  } catch {
    return `主体 ${partyId.slice(0, 8)}`;
  }
};

export const ViewProvider: React.FC<ViewProviderProps> = ({ children }) => {
  const { user, capabilities, capabilitiesLoading, isAuthenticated } = useAuth();
  const [currentView, setCurrentView] = useState<ViewSelectionOption | null>(null);
  const [availableViews, setAvailableViews] = useState<ViewSelectionOption[]>([]);
  const [selectionRequired, setSelectionRequired] = useState(false);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const staleSelectionRef = useRef(false);

  const mergedCapabilities = useMemo(() => {
    return mergeCapabilitiesByResource(capabilities);
  }, [capabilities]);

  const currentUserId = user?.id ?? '';

  const persistSelection = useCallback(
    (selection: ViewSelectionOption | null) => {
      if (currentUserId.trim() === '') {
        return;
      }
      if (selection == null) {
        viewSelectionStorage.clear(currentUserId);
        return;
      }
      viewSelectionStorage.set(currentUserId, {
        key: selection.key,
        perspective: selection.perspective,
        partyId: selection.partyId,
      });
    },
    [currentUserId]
  );

  const selectView = useCallback(
    (key: string) => {
      const selection = availableViews.find(item => item.key === key) ?? null;
      if (selection == null) {
        return;
      }
      staleSelectionRef.current = false;
      persistSelection(selection);
      startTransition(() => {
        setCurrentView(selection);
        setSelectionRequired(false);
        setSelectorOpen(false);
      });
    },
    [availableViews, persistSelection]
  );

  const openSelector = useCallback(() => {
    if (availableViews.length === 0) {
      return;
    }
    setSelectorOpen(true);
  }, [availableViews.length]);

  const closeSelector = useCallback(() => {
    if (selectionRequired) {
      return;
    }
    setSelectorOpen(false);
  }, [selectionRequired]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleAuthzStale = () => {
      if (currentUserId.trim() === '') {
        return;
      }
      staleSelectionRef.current = true;
      viewSelectionStorage.clear(currentUserId);
      startTransition(() => {
        setCurrentView(null);
        setSelectionRequired(true);
        setSelectorOpen(true);
      });
    };

    window.addEventListener(AUTHZ_STALE_EVENT_NAME, handleAuthzStale);
    return () => {
      window.removeEventListener(AUTHZ_STALE_EVENT_NAME, handleAuthzStale);
    };
  }, [currentUserId]);

  useEffect(() => {
    let cancelled = false;

    const syncViews = async () => {
      if (isAuthenticated !== true || currentUserId.trim() === '') {
        staleSelectionRef.current = false;
        startTransition(() => {
          setCurrentView(null);
          setAvailableViews([]);
          setSelectionRequired(false);
          setSelectorOpen(false);
        });
        return;
      }

      if (capabilitiesLoading) {
        return;
      }

      const rawOptions = buildRawViewOptions(mergedCapabilities);
      if (rawOptions.length === 0) {
        staleSelectionRef.current = false;
        persistSelection(null);
        startTransition(() => {
          setCurrentView(null);
          setAvailableViews([]);
          setSelectionRequired(false);
          setSelectorOpen(false);
        });
        return;
      }

      const uniquePartyIds = Array.from(new Set(rawOptions.map(item => item.partyId)));
      const partyNames = new Map<string, string>();
      await Promise.all(
        uniquePartyIds.map(async partyId => {
          partyNames.set(partyId, await resolvePartyName(partyId));
        })
      );

      if (cancelled) {
        return;
      }

      const resolvedOptions = rawOptions.map(option => {
        const partyName = partyNames.get(option.partyId) ?? `主体 ${option.partyId.slice(0, 8)}`;
        return {
          ...option,
          partyName,
          label: `${toPerspectiveLabel(option.perspective)} · ${partyName}`,
        };
      });

      const storedSelection =
        staleSelectionRef.current === true
          ? null
          : normalizeStoredSelection(viewSelectionStorage.get(currentUserId));
      const restoredSelection =
        storedSelection == null
          ? null
          : (resolvedOptions.find(item => item.key === storedSelection.key) ?? null);

      if (restoredSelection != null) {
        startTransition(() => {
          setAvailableViews(resolvedOptions);
          setCurrentView(restoredSelection);
          setSelectionRequired(false);
          setSelectorOpen(false);
        });
        return;
      }

      if (resolvedOptions.length === 1) {
        const [onlyOption] = resolvedOptions;
        staleSelectionRef.current = false;
        persistSelection(onlyOption);
        startTransition(() => {
          setAvailableViews(resolvedOptions);
          setCurrentView(onlyOption);
          setSelectionRequired(false);
          setSelectorOpen(false);
        });
        return;
      }

      persistSelection(null);
      startTransition(() => {
        setAvailableViews(resolvedOptions);
        setCurrentView(null);
        setSelectionRequired(true);
        setSelectorOpen(true);
      });
    };

    void syncViews();

    return () => {
      cancelled = true;
    };
  }, [capabilitiesLoading, currentUserId, isAuthenticated, mergedCapabilities, persistSelection]);

  const value = useMemo<ViewContextValue>(
    () => ({
      currentView,
      availableViews,
      selectionRequired,
      selectorOpen,
      isViewReady: selectionRequired !== true && currentView != null,
      openSelector,
      closeSelector,
      selectView,
    }),
    [
      availableViews,
      closeSelector,
      currentView,
      openSelector,
      selectView,
      selectionRequired,
      selectorOpen,
    ]
  );

  return <ViewContext.Provider value={value}>{children}</ViewContext.Provider>;
};

export const useView = (): ViewContextValue => {
  const context = useContext(ViewContext);
  if (context == null) {
    throw new Error('useView must be used within a ViewProvider');
  }
  return context;
};
