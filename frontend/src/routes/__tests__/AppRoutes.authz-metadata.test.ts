import { describe, expect, it } from 'vitest';
import { protectedRoutes, type ProtectedRouteItem } from '@/routes/AppRoutes';
import {
  CONTRACT_CENTER_ROUTES,
  CONTRACT_GROUP_ROUTES,
  ANALYTICS_ROUTES,
  OPERATIONS_ROUTES,
  PROJECT_ROUTES,
  SYSTEM_ROUTES,
} from '@/constants/routes';

type RoutePermission = { action: string; resource: string };

const normalizePermissions = (permissions: RoutePermission[]): string[] =>
  permissions.map(permission => `${permission.resource}:${permission.action}`).sort();

describe('AppRoutes authz metadata', () => {
  it('keeps Phase 3d critical route resource mappings aligned', () => {
    const expectedByPath = new Map<string, string>([
      [PROJECT_ROUTES.LIST, 'project:read'],
      [PROJECT_ROUTES.DETAIL_PATH, 'project:read'],
      [PROJECT_ROUTES.EDIT_PATH, 'project:read'],
      [CONTRACT_CENTER_ROUTES.LIST, 'contract_group:read'],
      [CONTRACT_CENTER_ROUTES.NEW, 'contract_group:create'],
      [CONTRACT_CENTER_ROUTES.IMPORT, 'contract_group:create'],
      [CONTRACT_CENTER_ROUTES.DETAIL_PATH, 'contract_group:read'],
      [CONTRACT_CENTER_ROUTES.EDIT_PATH, 'contract_group:update'],
      [CONTRACT_CENTER_ROUTES.NEW_CONTRACT_PATH, 'contract_group:create'],
      [CONTRACT_GROUP_ROUTES.LIST, 'contract_group:read'],
      [CONTRACT_GROUP_ROUTES.NEW, 'contract_group:create'],
      [CONTRACT_GROUP_ROUTES.DETAIL_PATH, 'contract_group:read'],
      [CONTRACT_GROUP_ROUTES.EDIT_PATH, 'contract_group:update'],
      [CONTRACT_GROUP_ROUTES.NEW_CONTRACT_PATH, 'contract_group:create'],
      [ANALYTICS_ROUTES.OVERVIEW, 'analytics:read'],
      [OPERATIONS_ROUTES.LEDGER, 'contract:read'],
    ]);

    const protectedRouteMap = new Map(protectedRoutes.map(route => [route.path, route]));

    for (const [path, expectedPermission] of expectedByPath.entries()) {
      const route = protectedRouteMap.get(path);
      expect(route).toBeDefined();
      const actualPermissions = route?.permissions ?? [];
      expect(normalizePermissions(actualPermissions)).toEqual([expectedPermission]);
    }
  });

  it('does not expose out-of-scope ownership or property certificate page routes', () => {
    const protectedRoutePaths = protectedRoutes.map(route => route.path);

    expect(protectedRoutePaths).not.toEqual(
      expect.arrayContaining([
        '/ownership',
        '/ownership/:id',
        '/ownership/:id/edit',
        '/property-certificates',
        '/property-certificates/:id',
        '/property-certificates/import',
      ])
    );
  });

  it('requires explicit capability metadata for each protected route', () => {
    const unguardedRoutes = protectedRoutes.filter(route => {
      const hasPermissions = (route.permissions?.length ?? 0) > 0;
      const bypassCapabilityGuard =
        (route as ProtectedRouteItem & { capabilityGuardBypass?: boolean })
          .capabilityGuardBypass === true;
      return (
        route.adminOnly !== true && hasPermissions === false && bypassCapabilityGuard === false
      );
    });

    expect(unguardedRoutes).toEqual([]);
  });

  it('marks system management routes as adminOnly', () => {
    const systemPaths = [
      SYSTEM_ROUTES.PARTIES,
      SYSTEM_ROUTES.USERS,
      SYSTEM_ROUTES.ROLES,
      SYSTEM_ROUTES.ORGANIZATIONS,
      SYSTEM_ROUTES.DICTIONARIES,
      SYSTEM_ROUTES.LOGS,
      SYSTEM_ROUTES.SETTINGS,
      SYSTEM_ROUTES.DATA_POLICIES,
    ];

    const protectedRouteMap = new Map(protectedRoutes.map(route => [route.path, route]));

    for (const path of systemPaths) {
      const route = protectedRouteMap.get(path);
      expect(route).toBeDefined();
      expect(route?.adminOnly).toBe(true);
      expect((route?.permissions?.length ?? 0) > 0).toBe(false);
    }
  });
});
