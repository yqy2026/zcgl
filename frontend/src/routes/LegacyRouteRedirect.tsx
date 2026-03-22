import React, { useMemo } from 'react';
import { Navigate } from 'react-router-dom';
import { Spin } from 'antd';

import { useAuth } from '@/contexts/AuthContext';
import type { CapabilityItem, ResourceType } from '@/types/capability';
import {
  ASSET_ROUTES,
  BASE_PATHS,
  CONTRACT_GROUP_ROUTES,
  MANAGER_ROUTES,
  OWNER_ROUTES,
  PROJECT_ROUTES,
  PROPERTY_CERTIFICATE_ROUTES,
} from '@/constants/routes';

type LegacyListPath =
  | typeof BASE_PATHS.ASSETS
  | typeof ASSET_ROUTES.LIST
  | typeof CONTRACT_GROUP_ROUTES.LIST
  | typeof PROJECT_ROUTES.LIST
  | typeof PROPERTY_CERTIFICATE_ROUTES.LIST;

interface RedirectConfig {
  resource: ResourceType;
  ownerTarget?: string;
  managerTarget?: string;
}

const REDIRECT_CONFIG: Record<LegacyListPath, RedirectConfig> = {
  [BASE_PATHS.ASSETS]: {
    resource: 'asset',
    ownerTarget: OWNER_ROUTES.ASSETS,
    managerTarget: MANAGER_ROUTES.ASSETS,
  },
  [ASSET_ROUTES.LIST]: {
    resource: 'asset',
    ownerTarget: OWNER_ROUTES.ASSETS,
    managerTarget: MANAGER_ROUTES.ASSETS,
  },
  [CONTRACT_GROUP_ROUTES.LIST]: {
    resource: 'contract_group',
    ownerTarget: OWNER_ROUTES.CONTRACT_GROUPS,
    managerTarget: MANAGER_ROUTES.CONTRACT_GROUPS,
  },
  [PROJECT_ROUTES.LIST]: {
    resource: 'project',
    managerTarget: MANAGER_ROUTES.PROJECTS,
  },
  [PROPERTY_CERTIFICATE_ROUTES.LIST]: {
    resource: 'property_certificate',
    ownerTarget: OWNER_ROUTES.PROPERTY_CERTIFICATES,
  },
};

const hasOwnerBinding = (capability: CapabilityItem | undefined): boolean =>
  (capability?.data_scope.owner_party_ids.length ?? 0) > 0;

const hasManagerBinding = (capability: CapabilityItem | undefined): boolean =>
  (capability?.data_scope.manager_party_ids.length ?? 0) > 0;

interface LegacyRouteRedirectProps {
  legacyPath: LegacyListPath;
}

const LegacyRouteRedirect: React.FC<LegacyRouteRedirectProps> = ({ legacyPath }) => {
  const { capabilities, capabilitiesLoading, error } = useAuth();

  const target = useMemo(() => {
    const config = REDIRECT_CONFIG[legacyPath];
    const capability = capabilities.find(item => item.resource === config.resource);

    if (config.ownerTarget != null && hasOwnerBinding(capability)) {
      return config.ownerTarget;
    }

    if (config.managerTarget != null && hasManagerBinding(capability)) {
      return config.managerTarget;
    }

    return BASE_PATHS.DASHBOARD;
  }, [capabilities, legacyPath]);

  if (capabilitiesLoading) {
    return (
      <div>
        <Spin size="small" /> 路由跳转计算中...
      </div>
    );
  }

  if (error != null) {
    return <Navigate to={BASE_PATHS.DASHBOARD} replace />;
  }

  return <Navigate to={target} replace />;
};

export default LegacyRouteRedirect;
