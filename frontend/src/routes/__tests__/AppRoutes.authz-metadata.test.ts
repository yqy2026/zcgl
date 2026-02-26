import { describe, expect, it } from 'vitest';
import { protectedRoutes, type ProtectedRouteItem } from '@/routes/AppRoutes';
import { ROUTE_CONFIG, type RouteConfig } from '@/constants/routes';

type RoutePermission = { action: string; resource: string };

type ExpectedAuthzRoute = {
  path: string;
  permissions: RoutePermission[];
};

const normalizePermissions = (permissions: RoutePermission[]): string[] =>
  permissions.map(permission => `${permission.resource}:${permission.action}`).sort();

const collectExpectedAuthzRoutes = (routes: RouteConfig[]): ExpectedAuthzRoute[] => {
  const collected: ExpectedAuthzRoute[] = [];

  for (const route of routes) {
    if (route.permissions != null && route.permissions.length > 0) {
      collected.push({
        path: route.path,
        permissions: route.permissions,
      });
    }

    if (route.children != null && route.children.length > 0) {
      collected.push(...collectExpectedAuthzRoutes(route.children));
    }
  }

  return collected;
};

describe('AppRoutes authz metadata', () => {
  it('keeps protectedRoutes permissions aligned with ROUTE_CONFIG', () => {
    const expectedAuthzRoutes = collectExpectedAuthzRoutes(ROUTE_CONFIG);
    const protectedRouteMap = new Map(protectedRoutes.map(route => [route.path, route]));

    const overlappingExpectedRoutes = expectedAuthzRoutes.filter(({ path }) =>
      protectedRouteMap.has(path)
    );

    expect(overlappingExpectedRoutes.length).toBeGreaterThan(0);

    const mismatchedRoutes = overlappingExpectedRoutes.filter(({ path, permissions }) => {
      const route = protectedRouteMap.get(path);
      const actualPermissions = route?.permissions ?? [];
      return (
        JSON.stringify(normalizePermissions(actualPermissions)) !==
        JSON.stringify(normalizePermissions(permissions))
      );
    });

    expect(mismatchedRoutes).toEqual([]);
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

  it('keeps ownership and analytics resources aligned with backend vocabularies', () => {
    const expectedByPath = new Map<string, string>([
      ['/assets/analytics', 'analytics:read'],
      ['/assets/analytics-simple', 'analytics:read'],
      ['/ownership', 'ownership:read'],
      ['/ownership/:id', 'ownership:read'],
      ['/ownership/:id/edit', 'ownership:update'],
    ]);

    const permissionsByPath = new Map(
      collectExpectedAuthzRoutes(ROUTE_CONFIG).map(route => [
        route.path,
        normalizePermissions(route.permissions).join(','),
      ])
    );

    for (const [path, expectedPermission] of expectedByPath.entries()) {
      expect(permissionsByPath.get(path)).toBe(expectedPermission);
    }
  });
});
