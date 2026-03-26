import { generatePath, matchPath } from 'react-router-dom';

import {
  ASSET_ROUTES,
  BASE_PATHS,
  CONTRACT_GROUP_ROUTES,
  MANAGER_ROUTES,
  OWNER_ROUTES,
  PROFILE_ROUTES,
  PROJECT_ROUTES,
  PROPERTY_CERTIFICATE_ROUTES,
  SYSTEM_ROUTES,
} from '@/constants/routes';
import type { CapabilityItem, ResourceType } from '@/types/capability';
import { getRoutePerspective, type RoutePerspective } from '@/routes/perspective';

type ConcretePerspective = Exclude<RoutePerspective, null>;

interface PerspectiveRouteTarget {
  listPath: string;
  detailPath?: string;
}

interface LegacyRouteConfig {
  listPaths: string[];
  detailPath?: string;
  createPaths?: string[];
  editPath?: string;
  importPaths?: string[];
}

interface ResourceRouteConfig {
  resource: ResourceType;
  owner?: PerspectiveRouteTarget;
  manager?: PerspectiveRouteTarget;
  legacy?: LegacyRouteConfig;
}

export interface PerspectiveMismatchResolution {
  resource: ResourceType;
  pathname: string;
  requestedPerspective: ConcretePerspective;
  availablePerspectives: ConcretePerspective[];
  targetPerspective: ConcretePerspective | null;
  targetPath: string | null;
}

const RESOURCE_ROUTE_CONFIGS: ResourceRouteConfig[] = [
  {
    resource: 'asset',
    owner: {
      listPath: OWNER_ROUTES.ASSETS,
      detailPath: OWNER_ROUTES.ASSET_DETAIL_PATH,
    },
    manager: {
      listPath: MANAGER_ROUTES.ASSETS,
      detailPath: MANAGER_ROUTES.ASSET_DETAIL_PATH,
    },
    legacy: {
      listPaths: [BASE_PATHS.ASSETS, ASSET_ROUTES.LIST],
      detailPath: ASSET_ROUTES.DETAIL_PATH,
      createPaths: [ASSET_ROUTES.NEW],
      editPath: ASSET_ROUTES.EDIT_PATH,
      importPaths: [ASSET_ROUTES.IMPORT],
    },
  },
  {
    resource: 'contract_group',
    owner: {
      listPath: OWNER_ROUTES.CONTRACT_GROUPS,
      detailPath: OWNER_ROUTES.CONTRACT_GROUP_DETAIL_PATH,
    },
    manager: {
      listPath: MANAGER_ROUTES.CONTRACT_GROUPS,
      detailPath: MANAGER_ROUTES.CONTRACT_GROUP_DETAIL_PATH,
    },
    legacy: {
      listPaths: [CONTRACT_GROUP_ROUTES.LIST],
      detailPath: CONTRACT_GROUP_ROUTES.DETAIL_PATH,
      createPaths: [CONTRACT_GROUP_ROUTES.NEW],
      editPath: CONTRACT_GROUP_ROUTES.EDIT_PATH,
      importPaths: [CONTRACT_GROUP_ROUTES.IMPORT],
    },
  },
  {
    resource: 'project',
    manager: {
      listPath: MANAGER_ROUTES.PROJECTS,
      detailPath: MANAGER_ROUTES.PROJECT_DETAIL_PATH,
    },
    legacy: {
      listPaths: [PROJECT_ROUTES.LIST],
      detailPath: PROJECT_ROUTES.DETAIL_PATH,
      editPath: PROJECT_ROUTES.EDIT_PATH,
    },
  },
  {
    resource: 'property_certificate',
    owner: {
      listPath: OWNER_ROUTES.PROPERTY_CERTIFICATES,
      detailPath: OWNER_ROUTES.PROPERTY_CERTIFICATE_DETAIL_PATH,
    },
    legacy: {
      listPaths: [PROPERTY_CERTIFICATE_ROUTES.LIST],
      detailPath: PROPERTY_CERTIFICATE_ROUTES.DETAIL_PATH,
      importPaths: [PROPERTY_CERTIFICATE_ROUTES.IMPORT],
    },
  },
];

const PERSPECTIVE_ORDER: ConcretePerspective[] = ['owner', 'manager'];

const getResourceRouteConfig = (resource: ResourceType): ResourceRouteConfig | undefined => {
  return RESOURCE_ROUTE_CONFIGS.find(item => item.resource === resource);
};

const getCapabilityForResource = (
  capabilities: CapabilityItem[],
  resource: ResourceType
): CapabilityItem | undefined => {
  return capabilities.find(item => item.resource === resource);
};

const dedupePerspectives = (items: ConcretePerspective[]): ConcretePerspective[] => {
  return Array.from(new Set(items));
};

const getAvailablePerspectivesForCapability = (
  capability: CapabilityItem | undefined
): ConcretePerspective[] => {
  const perspectives: ConcretePerspective[] = [];

  if (capability?.perspectives.includes('owner')) {
    perspectives.push('owner');
  }
  if (capability?.perspectives.includes('manager')) {
    perspectives.push('manager');
  }
  if ((capability?.data_scope.owner_party_ids.length ?? 0) > 0) {
    perspectives.push('owner');
  }
  if ((capability?.data_scope.manager_party_ids.length ?? 0) > 0) {
    perspectives.push('manager');
  }

  return dedupePerspectives(perspectives);
};

const choosePerspective = (
  config: ResourceRouteConfig,
  availablePerspectives: ConcretePerspective[]
): ConcretePerspective | null => {
  for (const perspective of PERSPECTIVE_ORDER) {
    if (config[perspective] != null && availablePerspectives.includes(perspective)) {
      return perspective;
    }
  }

  return null;
};

const chooseAlternativePerspective = (
  config: ResourceRouteConfig,
  requestedPerspective: ConcretePerspective,
  availablePerspectives: ConcretePerspective[]
): ConcretePerspective | null => {
  for (const perspective of PERSPECTIVE_ORDER) {
    if (perspective === requestedPerspective) {
      continue;
    }
    if (config[perspective] != null && availablePerspectives.includes(perspective)) {
      return perspective;
    }
  }

  return null;
};

const matchDetailParams = (
  pathname: string,
  config: ResourceRouteConfig
): Record<string, string> | null => {
  const detailPatterns = [
    config.owner?.detailPath,
    config.manager?.detailPath,
    config.legacy?.detailPath,
  ].filter((value): value is string => value != null);

  for (const pattern of detailPatterns) {
    const match = matchPath({ path: pattern, end: true }, pathname);
    if (match != null) {
      return match.params as Record<string, string>;
    }
  }

  return null;
};

const buildPerspectiveTargetPath = (
  config: ResourceRouteConfig,
  perspective: ConcretePerspective,
  pathname: string
): string | null => {
  const target = config[perspective];
  if (target == null) {
    return null;
  }

  const detailParams = matchDetailParams(pathname, config);
  if (detailParams != null && target.detailPath != null) {
    return generatePath(target.detailPath, detailParams);
  }

  return target.listPath;
};

const isListLegacyPath = (pathname: string, legacy: LegacyRouteConfig): boolean => {
  return legacy.listPaths.includes(pathname);
};

const isCreateLikeLegacyPath = (pathname: string, legacy: LegacyRouteConfig): boolean => {
  return (
    (legacy.createPaths?.includes(pathname) ?? false) ||
    (legacy.importPaths?.includes(pathname) ?? false) ||
    pathname === legacy.editPath
  );
};

const isLegacyDetailPath = (pathname: string, legacy: LegacyRouteConfig): boolean => {
  if (legacy.detailPath == null) {
    return false;
  }

  return matchPath({ path: legacy.detailPath, end: true }, pathname) != null;
};

export const isNeutralRoute = (pathname: string): boolean => {
  return (
    pathname === BASE_PATHS.DASHBOARD ||
    pathname === PROFILE_ROUTES.PROFILE ||
    pathname.startsWith('/auth/') ||
    pathname === '/auth' ||
    pathname === BASE_PATHS.SYSTEM ||
    pathname.startsWith(`${BASE_PATHS.SYSTEM}/`) ||
    pathname === SYSTEM_ROUTES.PARTIES ||
    pathname === SYSTEM_ROUTES.USERS ||
    pathname === SYSTEM_ROUTES.ROLES ||
    pathname === SYSTEM_ROUTES.ORGANIZATIONS ||
    pathname === SYSTEM_ROUTES.DICTIONARIES ||
    pathname === SYSTEM_ROUTES.LOGS ||
    pathname === SYSTEM_ROUTES.SETTINGS ||
    pathname === SYSTEM_ROUTES.TEMPLATES ||
    pathname === SYSTEM_ROUTES.DATA_POLICIES
  );
};

export const resolveLegacyPerspectiveTarget = (
  pathname: string,
  capabilities: CapabilityItem[]
): string | null => {
  for (const config of RESOURCE_ROUTE_CONFIGS) {
    const legacy = config.legacy;
    if (legacy == null) {
      continue;
    }

    const matchesLegacyPath =
      isListLegacyPath(pathname, legacy) ||
      isCreateLikeLegacyPath(pathname, legacy) ||
      isLegacyDetailPath(pathname, legacy);
    if (!matchesLegacyPath) {
      continue;
    }

    const availablePerspectives = getAvailablePerspectivesForCapability(
      getCapabilityForResource(capabilities, config.resource)
    );
    const targetPerspective = choosePerspective(config, availablePerspectives);
    if (targetPerspective == null) {
      return null;
    }

    return buildPerspectiveTargetPath(config, targetPerspective, pathname);
  }

  return null;
};

export const resolveLegacyPerspectiveFailure = (
  pathname: string,
  capabilities: CapabilityItem[]
): PerspectiveMismatchResolution | null => {
  for (const config of RESOURCE_ROUTE_CONFIGS) {
    const legacy = config.legacy;
    if (legacy == null) {
      continue;
    }

    const matchesLegacyPath =
      isListLegacyPath(pathname, legacy) ||
      isCreateLikeLegacyPath(pathname, legacy) ||
      isLegacyDetailPath(pathname, legacy);
    if (!matchesLegacyPath) {
      continue;
    }

    const availablePerspectives = getAvailablePerspectivesForCapability(
      getCapabilityForResource(capabilities, config.resource)
    );
    const targetPerspective = choosePerspective(config, availablePerspectives);
    if (targetPerspective != null) {
      return null;
    }

    return {
      resource: config.resource,
      pathname,
      requestedPerspective: 'owner',
      availablePerspectives,
      targetPerspective: null,
      targetPath: null,
    };
  }

  return null;
};

export const resolvePerspectiveMismatch = ({
  pathname,
  resource,
  capabilities,
}: {
  pathname: string;
  resource: ResourceType;
  capabilities: CapabilityItem[];
}): PerspectiveMismatchResolution | null => {
  const requestedPerspective = getRoutePerspective(pathname);
  if (requestedPerspective == null) {
    return null;
  }

  const config = getResourceRouteConfig(resource);
  if (config == null || config[requestedPerspective] == null) {
    return null;
  }

  const capability = getCapabilityForResource(capabilities, resource);
  const availablePerspectives = getAvailablePerspectivesForCapability(capability);
  if (availablePerspectives.includes(requestedPerspective)) {
    return null;
  }

  const targetPerspective = chooseAlternativePerspective(
    config,
    requestedPerspective,
    availablePerspectives
  );

  return {
    resource,
    pathname,
    requestedPerspective,
    availablePerspectives,
    targetPerspective,
    targetPath:
      targetPerspective == null ? null : buildPerspectiveTargetPath(config, targetPerspective, pathname),
  };
};
