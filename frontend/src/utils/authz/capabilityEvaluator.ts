import type {
  AuthzAction,
  CapabilityItem,
  Perspective,
  ResourceType,
  TemporaryAdminAction,
} from '@/types/capability';

export type PartyRelationType = 'owner' | 'manager' | 'tenant';

export interface EvaluateCapabilityInput {
  capabilities: CapabilityItem[];
  isAdmin: boolean;
  action: AuthzAction | TemporaryAdminAction;
  resourceType: ResourceType;
  perspective?: Perspective;
}

export interface HasPartyScopeAccessInput {
  capabilities: CapabilityItem[];
  isAdmin: boolean;
  partyId: string;
  relationType: PartyRelationType;
  resourceType?: ResourceType;
}

const TEMP_ADMIN_ONLY_ACTION: TemporaryAdminAction = 'backup';
const TEMP_ADMIN_ONLY_RESOURCE: ResourceType = 'system';

const dedupe = <T extends string>(items: readonly T[] | undefined): T[] => {
  if (!Array.isArray(items)) {
    return [];
  }
  const next = items.filter(item => typeof item === 'string' && item.trim() !== '');
  return Array.from(new Set(next));
};

const normalizeCapability = (capability: CapabilityItem): CapabilityItem => {
  return {
    resource: capability.resource,
    actions: dedupe(capability.actions),
    perspectives: dedupe(capability.perspectives),
    data_scope: {
      owner_party_ids: dedupe(capability.data_scope?.owner_party_ids),
      manager_party_ids: dedupe(capability.data_scope?.manager_party_ids),
    },
  };
};

export const mergeCapabilitiesByResource = (capabilities: CapabilityItem[]): CapabilityItem[] => {
  const merged = new Map<ResourceType, CapabilityItem>();

  for (const rawCapability of capabilities) {
    const capability = normalizeCapability(rawCapability);
    const existing = merged.get(capability.resource);

    if (existing == null) {
      merged.set(capability.resource, capability);
      continue;
    }

    merged.set(capability.resource, {
      resource: capability.resource,
      actions: dedupe([...existing.actions, ...capability.actions]),
      perspectives: dedupe([...existing.perspectives, ...capability.perspectives]),
      data_scope: {
        owner_party_ids: dedupe([
          ...existing.data_scope.owner_party_ids,
          ...capability.data_scope.owner_party_ids,
        ]),
        manager_party_ids: dedupe([
          ...existing.data_scope.manager_party_ids,
          ...capability.data_scope.manager_party_ids,
        ]),
      },
    });
  }

  return Array.from(merged.values());
};

export const getAvailablePerspectives = (
  resourceType: ResourceType,
  capability: CapabilityItem | undefined
): Perspective[] => {
  void resourceType;
  return capability?.perspectives ?? [];
};

const hasPartyScopeMatch = (
  capability: CapabilityItem,
  relationType: PartyRelationType,
  partyId: string
): boolean => {
  const ownerPartyIds = capability.data_scope.owner_party_ids;
  const managerPartyIds = capability.data_scope.manager_party_ids;

  if (relationType === 'owner') {
    return ownerPartyIds.includes(partyId);
  }

  if (relationType === 'manager') {
    return managerPartyIds.includes(partyId);
  }

  return ownerPartyIds.includes(partyId) || managerPartyIds.includes(partyId);
};

export const evaluateCapability = ({
  capabilities,
  isAdmin,
  action,
  resourceType,
  perspective,
}: EvaluateCapabilityInput): boolean => {
  if (action === TEMP_ADMIN_ONLY_ACTION && resourceType === TEMP_ADMIN_ONLY_RESOURCE) {
    return isAdmin === true;
  }

  if (isAdmin) {
    return true;
  }

  const mergedCapabilities = mergeCapabilitiesByResource(capabilities);
  const capability = mergedCapabilities.find(item => item.resource === resourceType);
  if (capability == null) {
    return false;
  }

  if (!capability.actions.includes(action as AuthzAction)) {
    return false;
  }

  if (perspective == null) {
    return true;
  }

  const perspectives = getAvailablePerspectives(resourceType, capability);
  if (perspectives.length === 0) {
    return true;
  }

  return perspectives.includes(perspective);
};

export const hasPartyScopeAccess = ({
  capabilities,
  isAdmin,
  partyId,
  relationType,
  resourceType,
}: HasPartyScopeAccessInput): boolean => {
  if (isAdmin) {
    return true;
  }

  if (partyId.trim() === '') {
    return false;
  }

  const mergedCapabilities = mergeCapabilitiesByResource(capabilities);
  if (resourceType != null) {
    const capability = mergedCapabilities.find(item => item.resource === resourceType);
    if (capability == null) {
      return false;
    }
    return hasPartyScopeMatch(capability, relationType, partyId);
  }

  return mergedCapabilities.some(capability =>
    hasPartyScopeMatch(capability, relationType, partyId)
  );
};
