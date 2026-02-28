import { useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import type {
  AuthzAction,
  Perspective,
  ResourceType,
  TemporaryAdminAction,
} from '@/types/capability';
import {
  evaluateCapability,
  getAvailablePerspectives as resolveAvailablePerspectives,
  hasPartyScopeAccess,
  mergeCapabilitiesByResource,
  type PartyRelationType,
} from '@/utils/authz/capabilityEvaluator';

export const useCapabilities = () => {
  const { capabilities: authCapabilities, capabilitiesLoading, isAdmin } = useAuth();

  const capabilities = useMemo(() => {
    return mergeCapabilitiesByResource(authCapabilities);
  }, [authCapabilities]);

  const canPerform = useCallback(
    (
      action: AuthzAction | TemporaryAdminAction,
      resourceType: ResourceType,
      perspective?: Perspective
    ) => {
      return evaluateCapability({
        capabilities,
        isAdmin,
        action,
        resourceType,
        perspective,
      });
    },
    [capabilities, isAdmin]
  );

  const hasPartyAccess = useCallback(
    (partyId: string, relationType: PartyRelationType, resourceType?: ResourceType): boolean => {
      return hasPartyScopeAccess({
        capabilities,
        isAdmin,
        partyId,
        relationType,
        resourceType,
      });
    },
    [capabilities, isAdmin]
  );

  const getAvailableActions = useCallback(
    (resourceType: ResourceType): AuthzAction[] => {
      const capability = capabilities.find(item => item.resource === resourceType);
      return capability?.actions ?? [];
    },
    [capabilities]
  );

  const getAvailablePerspectives = useCallback(
    (resourceType: ResourceType): Perspective[] => {
      const capability = capabilities.find(item => item.resource === resourceType);
      return resolveAvailablePerspectives(resourceType, capability);
    },
    [capabilities]
  );

  return {
    canPerform,
    hasPartyAccess,
    getAvailableActions,
    getAvailablePerspectives,
    capabilities,
    loading: capabilitiesLoading,
  };
};
