import { describe, expect, it } from 'vitest';
import * as routeConstants from '@/constants/routes';
import { ROUTE_CONFIG, ROUTES } from '@/constants/routes';

describe('rental route config contract resources', () => {
  it('removes legacy rental constant export names', () => {
    expect('RENTAL_ROUTES' in routeConstants).toBe(false);
    expect('LEGACY_RENTAL_ROUTES' in routeConstants).toBe(false);
    expect(ROUTES).not.toHaveProperty('LEGACY_RENTAL_ROUTES');
    expect(ROUTES.BASE_PATHS).not.toHaveProperty('LEGACY_RENTAL');
    expect(ROUTES.REDIRECTS).not.toHaveProperty('LEGACY_RENTAL_ROOT');
  });

  it('removes legacy rental route config entries', () => {
    const rentalSection = ROUTE_CONFIG.find(route => route.path === '/rental');

    expect(rentalSection).toBeUndefined();
    expect(ROUTE_CONFIG.some(route => route.path.startsWith('/rental'))).toBe(false);
    expect(
      ROUTE_CONFIG.some(route =>
        (route.children ?? []).some(child => child.path.startsWith('/rental'))
      )
    ).toBe(false);
  });

  it('exposes dedicated contract relation route constants and metadata', () => {
    expect('CONTRACT_GROUP_ROUTES' in routeConstants).toBe(true);
    expect(ROUTES).toHaveProperty('CONTRACT_GROUP_ROUTES');
    expect(ROUTES.CONTRACT_CENTER_ROUTES.LIST).toBe('/contract-center');
    expect(ROUTES.CONTRACT_CENTER_ROUTES.NEW).toBe('/contract-center/new');
    expect(ROUTES.CONTRACT_CENTER_ROUTES.IMPORT).toBe('/contract-center/import');
    expect(ROUTES.CONTRACT_CENTER_ROUTES.DETAIL_PATH).toBe('/contract-center/:id');
    expect(ROUTES.CONTRACT_CENTER_ROUTES.EDIT_PATH).toBe('/contract-center/:id/edit');
    expect(ROUTES.CONTRACT_CENTER_ROUTES.NEW_CONTRACT_PATH).toBe(
      '/contract-center/:id/contracts/new'
    );
    expect(ROUTES.CONTRACT_GROUP_ROUTES.LIST).toBe('/contract-groups');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.NEW).toBe('/contract-groups/new');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.IMPORT).toBe('/contract-groups/import');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.DETAIL_PATH).toBe('/contract-groups/:id');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.EDIT_PATH).toBe('/contract-groups/:id/edit');
    expect(ROUTES.CONTRACT_GROUP_ROUTES.NEW_CONTRACT_PATH).toBe(
      '/contract-groups/:id/contracts/new'
    );

    const contractGroupSection = ROUTE_CONFIG.find(route => route.path === '/contract-center');

    expect(contractGroupSection).toBeDefined();
    expect(contractGroupSection?.title).toBe('合同中心');
    expect(contractGroupSection?.breadcrumb).toEqual(['合同中心']);

    const routePermissions = (contractGroupSection?.children ?? []).map(
      child =>
        child.permissions?.map(permission => `${permission.resource}:${permission.action}`) ?? []
    );

    expect(routePermissions).toEqual([
      ['contract_group:read'],
      ['contract_group:create'],
      ['contract_group:create'],
      ['contract_group:read'],
      ['contract_group:update'],
      ['contract_group:create'],
    ]);
  });

  it('exposes global analytics route metadata outside asset management', () => {
    expect(ROUTES.ANALYTICS_ROUTES.OVERVIEW).toBe('/analytics');
    expect(ROUTES.FINANCE_ROUTES.LEDGER).toBe('/finance/ledger');

    const analyticsSection = ROUTE_CONFIG.find(route => route.path === '/analytics');
    const financeSection = ROUTE_CONFIG.find(route => route.path === '/finance/ledger');
    const assetsSection = ROUTE_CONFIG.find(route => route.path === '/assets');

    expect(analyticsSection).toMatchObject({
      path: '/analytics',
      title: '经营分析',
      permissions: [{ resource: 'analytics', action: 'read' }],
    });
    expect(financeSection).toMatchObject({
      path: '/finance/ledger',
      title: '财务台账',
      permissions: [{ resource: 'contract', action: 'read' }],
    });
    expect(assetsSection?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ path: '/analytics' })])
    );
  });
});
