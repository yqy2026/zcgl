import { describe, expect, it } from 'vitest';
import { protectedRoutes } from '@/routes/AppRoutes';
import { ASSET_OPERATIONS_V5_ROUTES } from '@/constants/routes';

type RoutePermission = { action: string; resource: string };

const normalizePermissions = (permissions: RoutePermission[]): string[] =>
  permissions.map(permission => `${permission.resource}:${permission.action}`).sort();

describe('AppRoutes authz metadata', () => {
  it('keeps v5 route resource mappings aligned', () => {
    const expectedByPath = new Map<string, string>([
      [ASSET_OPERATIONS_V5_ROUTES.UNITS, 'asset_ops:read'],
      [ASSET_OPERATIONS_V5_ROUTES.UPSTREAM_CONTRACTS, 'asset_ops:read'],
      [ASSET_OPERATIONS_V5_ROUTES.TERMINAL_CONTRACTS, 'asset_ops:read'],
      [ASSET_OPERATIONS_V5_ROUTES.INTAKE, 'asset_ops:write'],
      [ASSET_OPERATIONS_V5_ROUTES.TERMINAL_ACTIONS, 'asset_ops:write'],
      [ASSET_OPERATIONS_V5_ROUTES.UPSTREAM_ACTIONS, 'asset_ops:write'],
    ]);

    const protectedRouteMap = new Map(protectedRoutes.map(route => [route.path, route]));

    for (const [path, expectedPermission] of expectedByPath.entries()) {
      const route = protectedRouteMap.get(path);
      expect(route, path).toBeDefined();
      expect(normalizePermissions(route?.permissions ?? [])).toEqual([expectedPermission]);
    }
  });

  it('does not expose legacy business routes', () => {
    const protectedRoutePaths = protectedRoutes.map(route => route.path);

    expect(protectedRoutePaths).not.toEqual(
      expect.arrayContaining([
        '/dashboard',
        '/assets/list',
        '/contract-center',
        '/operations/ledger',
        '/analytics',
        '/ownership',
      ])
    );
  });
});
