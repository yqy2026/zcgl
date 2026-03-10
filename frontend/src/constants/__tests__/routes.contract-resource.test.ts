import { describe, expect, it } from 'vitest';
import * as routeConstants from '@/constants/routes';
import { ROUTE_CONFIG, ROUTES } from '@/constants/routes';

describe('rental route config contract resources', () => {
  it('retires legacy rental constant export names', () => {
    expect('RENTAL_ROUTES' in routeConstants).toBe(false);
    expect(ROUTES).toHaveProperty('LEGACY_RENTAL_ROUTES');
    expect(ROUTES.BASE_PATHS).not.toHaveProperty('LEGACY_RENTAL');
    expect(ROUTES.REDIRECTS).not.toHaveProperty('LEGACY_RENTAL_ROOT');
  });

  it('uses retired titles and read-only contract resource metadata for rental route entries', () => {
    const rentalSection = ROUTE_CONFIG.find(route => route.path === '/rental');

    expect(rentalSection).toBeDefined();
    expect(rentalSection?.title).toBe('旧租赁前端已退休');
    expect(rentalSection?.breadcrumb).toEqual(['旧租赁前端已退休']);

    const rentalChildren = rentalSection?.children ?? [];
    expect(rentalChildren.length).toBeGreaterThan(0);
    const legacyPdfImportRoute = rentalChildren.find(
      child => child.path === '/rental/contracts/pdf-import'
    );
    const retiredRentalChildren = rentalChildren.filter(
      child => child.path !== '/rental/contracts/pdf-import'
    );

    expect(legacyPdfImportRoute?.title).toBe('跳转至PDF导入');
    expect(retiredRentalChildren.every(child => child.title === '旧租赁前端已退休')).toBe(true);

    const resourceActions = rentalChildren.map(child => ({
      path: child.path,
      permissions:
        child.permissions?.map(permission => `${permission.resource}:${permission.action}`) ?? [],
    }));

    expect(resourceActions).toEqual([
      { path: '/rental/contracts', permissions: ['contract:read'] },
      { path: '/rental/contracts/new', permissions: ['contract:read'] },
      { path: '/rental/contracts/create', permissions: ['contract:read'] },
      { path: '/rental/contracts/pdf-import', permissions: ['contract_group:create'] },
      { path: '/rental/contracts/:id/renew', permissions: ['contract:read'] },
      { path: '/rental/contracts/:id', permissions: ['contract:read'] },
      { path: '/rental/contracts/:id/edit', permissions: ['contract:read'] },
      { path: '/rental/ledger', permissions: ['contract:read'] },
      { path: '/rental/statistics', permissions: ['contract:read'] },
    ]);
  });

  it('exposes dedicated contract group route constants and metadata', () => {
    expect('CONTRACT_GROUP_ROUTES' in routeConstants).toBe(true);
    expect(ROUTES).toHaveProperty('CONTRACT_GROUP_ROUTES');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.LIST).toBe('/contract-groups');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.NEW).toBe('/contract-groups/new');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.IMPORT).toBe('/contract-groups/import');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.DETAIL_PATH).toBe('/contract-groups/:id');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.EDIT_PATH).toBe('/contract-groups/:id/edit');

    const contractGroupSection = ROUTE_CONFIG.find(route => route.path === '/contract-groups');

    expect(contractGroupSection).toBeDefined();
    expect(contractGroupSection?.title).toBe('合同组管理');
    expect(contractGroupSection?.breadcrumb).toEqual(['合同组管理']);

    const routePermissions = (contractGroupSection?.children ?? []).map(
      child => child.permissions?.map(permission => `${permission.resource}:${permission.action}`) ?? []
    );

    expect(routePermissions).toEqual([
      ['contract_group:read'],
      ['contract_group:create'],
      ['contract_group:create'],
      ['contract_group:read'],
      ['contract_group:update'],
    ]);
  });
});
