import { create } from 'zustand';
import type { CapabilitiesResponse } from '@/types/capability';

export type BindingType = 'owner' | 'manager';

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
  initFromCapabilities: (response: CapabilitiesResponse | CapabilitiesResponse['capabilities'], isAdmin: boolean) => void;
  reset: () => void;
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

export const useDataScopeStore = create<DataScopeState>((set, get) => ({
  ...initialState,

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

    set(
      createState(
        bindingTypes,
        [...ownerPartyIds].sort(),
        [...managerPartyIds].sort(),
        isAdmin,
        true
      )
    );
  },

  reset: () => {
    set(initialState);
  },

  getEffectivePerspective: () => {
    const state = get();
    if (state.isAdmin || state.isDualBinding) {
      return null;
    }
    if (state.isSingleOwner) {
      return 'owner';
    }
    if (state.isSingleManager) {
      return 'manager';
    }
    return null;
  },
}));
