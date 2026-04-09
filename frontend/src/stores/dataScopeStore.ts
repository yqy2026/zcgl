import { create } from 'zustand';
import type { CapabilitiesResponse } from '@/types/capability';

export type BindingType = 'owner' | 'manager';
const VIEW_MODE_STORAGE_KEY = 'data-scope:view-mode';

interface DataScopeState {
  bindingTypes: BindingType[];
  ownerPartyIds: string[];
  managerPartyIds: string[];
  isAdmin: boolean;
  initialized: boolean;
  isOwner: boolean;
  isManager: boolean;
  isDualBinding: boolean;
  isSingleOwner: boolean;
  isSingleManager: boolean;
  currentViewMode: BindingType | null;
  initFromCapabilities: (response: CapabilitiesResponse | CapabilitiesResponse['capabilities'], isAdmin: boolean) => void;
  setCurrentViewMode: (viewMode: BindingType | null) => void;
  reset: () => void;
  getEffectiveViewMode: () => BindingType | null;
  getEffectivePerspective: () => BindingType | null;
}

interface ComputedFlags {
  isOwner: boolean;
  isManager: boolean;
  isDualBinding: boolean;
  isSingleOwner: boolean;
  isSingleManager: boolean;
}

const computeFlags = (bindingTypes: BindingType[]): ComputedFlags => {
  const isOwner = bindingTypes.includes('owner');
  const isManager = bindingTypes.includes('manager');
  return {
    isOwner,
    isManager,
    isDualBinding: isOwner && isManager,
    isSingleOwner: isOwner && !isManager,
    isSingleManager: !isOwner && isManager,
  };
};

const createState = (
  bindingTypes: BindingType[],
  ownerPartyIds: string[],
  managerPartyIds: string[],
  isAdmin: boolean,
  initialized: boolean
) => ({
  bindingTypes,
  ownerPartyIds,
  managerPartyIds,
  isAdmin,
  initialized,
  ...computeFlags(bindingTypes),
});

const initialState = createState([], [], [], false, false);

const resolveDefaultViewMode = (
  bindingTypes: BindingType[],
  isAdmin: boolean,
  persistedViewMode: string | null
): BindingType | null => {
  if (isAdmin) {
    return null;
  }

  const flags = computeFlags(bindingTypes);
  const allowedModes: BindingType[] = [];
  if (flags.isOwner) {
    allowedModes.push('owner');
  }
  if (flags.isManager) {
    allowedModes.push('manager');
  }

  if (allowedModes.length === 0) {
    return null;
  }

  if (
    (persistedViewMode === 'owner' || persistedViewMode === 'manager') &&
    allowedModes.includes(persistedViewMode)
  ) {
    return persistedViewMode;
  }

  if (flags.isSingleOwner) {
    return 'owner';
  }
  if (flags.isSingleManager) {
    return 'manager';
  }

  return 'owner';
};

export const useDataScopeStore = create<DataScopeState>((set, get) => ({
  ...initialState,
  currentViewMode: null,

  initFromCapabilities: (response, isAdmin) => {
    const capabilities = Array.isArray(response) ? response : response.capabilities;
    const ownerPartyIds = new Set<string>();
    const managerPartyIds = new Set<string>();

    for (const capability of capabilities) {
      capability.data_scope.owner_party_ids.forEach(id => {
        const normalizedId = id.trim();
        if (normalizedId !== '') {
          ownerPartyIds.add(normalizedId);
        }
      });
      capability.data_scope.manager_party_ids.forEach(id => {
        const normalizedId = id.trim();
        if (normalizedId !== '') {
          managerPartyIds.add(normalizedId);
        }
      });
    }

    const bindingTypes: BindingType[] = [];
    if (ownerPartyIds.size > 0) {
      bindingTypes.push('owner');
    }
    if (managerPartyIds.size > 0) {
      bindingTypes.push('manager');
    }

    const currentViewMode = resolveDefaultViewMode(
      bindingTypes,
      isAdmin,
      typeof window === 'undefined' ? null : window.localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    );

    if (typeof window !== 'undefined') {
      if (currentViewMode == null) {
        window.localStorage.removeItem(VIEW_MODE_STORAGE_KEY);
      } else {
        window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, currentViewMode);
      }
    }

    set(
      {
        ...createState(
          bindingTypes,
          [...ownerPartyIds].sort(),
          [...managerPartyIds].sort(),
          isAdmin,
          true
        ),
        currentViewMode,
      }
    );
  },

  setCurrentViewMode: viewMode => {
    const state = get();
    const nextViewMode =
      viewMode != null &&
      ((viewMode === 'owner' && state.isOwner) || (viewMode === 'manager' && state.isManager))
        ? viewMode
        : resolveDefaultViewMode(state.bindingTypes, state.isAdmin, null);

    if (typeof window !== 'undefined') {
      if (nextViewMode == null) {
        window.localStorage.removeItem(VIEW_MODE_STORAGE_KEY);
      } else {
        window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, nextViewMode);
      }
    }

    set({ currentViewMode: nextViewMode });
  },

  reset: () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(VIEW_MODE_STORAGE_KEY);
    }
    set({ ...initialState, currentViewMode: null });
  },

  getEffectiveViewMode: () => {
    const state = get();
    if (state.isAdmin) {
      return null;
    }
    return state.currentViewMode;
  },

  getEffectivePerspective: () => {
    return get().getEffectiveViewMode();
  },
}));
