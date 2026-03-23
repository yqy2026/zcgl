import { describe, expect, it } from 'vitest';
import { ROUTE_CONFIG, ROUTES } from '@/constants/routes';

describe('perspective-prefixed routes', () => {
  it('exports owner and manager read route groups', () => {
    expect(ROUTES.OWNER_ROUTES).toMatchObject({
      ASSETS: '/owner/assets',
      ASSET_DETAIL_PATH: '/owner/assets/:id',
      DETAIL: expect.any(Function),
      CONTRACT_GROUPS: '/owner/contract-groups',
      CONTRACT_GROUP_DETAIL_PATH: '/owner/contract-groups/:id',
      PROPERTY_CERTIFICATES: '/owner/property-certificates',
      PROPERTY_CERTIFICATE_DETAIL_PATH: '/owner/property-certificates/:id',
    });
    expect(ROUTES.OWNER_ROUTES.DETAIL('asset-1')).toBe('/owner/assets/asset-1');

    expect(ROUTES.MANAGER_ROUTES).toMatchObject({
      ASSETS: '/manager/assets',
      ASSET_DETAIL_PATH: '/manager/assets/:id',
      DETAIL: expect.any(Function),
      CONTRACT_GROUPS: '/manager/contract-groups',
      CONTRACT_GROUP_DETAIL_PATH: '/manager/contract-groups/:id',
      PROJECTS: '/manager/projects',
      PROJECT_DETAIL_PATH: '/manager/projects/:id',
    });
    expect(ROUTES.MANAGER_ROUTES.DETAIL('asset-2')).toBe('/manager/assets/asset-2');

    expect(Object.values(ROUTES.MANAGER_ROUTES)).not.toContain('/manager/ledger');
  });

  it('adds owner and manager metadata-only route sections', () => {
    const ownerSection = ROUTE_CONFIG.find(route => route.path === '/owner');
    const managerSection = ROUTE_CONFIG.find(route => route.path === '/manager');

    expect(ownerSection).toBeDefined();
    expect(managerSection).toBeDefined();

    expect(ownerSection?.children).toEqual(
      expect.arrayContaining([
        {
          path: '/owner/assets',
          title: '资产列表',
          permissions: [{ resource: 'asset', action: 'read' }],
        },
        {
          path: '/owner/contract-groups',
          title: '合同组列表',
          permissions: [{ resource: 'contract_group', action: 'read' }],
        },
        {
          path: '/owner/property-certificates',
          title: '产权证列表',
          permissions: [{ resource: 'property_certificate', action: 'read' }],
        },
      ])
    );

    expect(managerSection?.children).toEqual(
      expect.arrayContaining([
        {
          path: '/manager/assets',
          title: '资产列表',
          permissions: [{ resource: 'asset', action: 'read' }],
        },
        {
          path: '/manager/contract-groups',
          title: '合同组列表',
          permissions: [{ resource: 'contract_group', action: 'read' }],
        },
        {
          path: '/manager/projects',
          title: '项目列表',
          permissions: [{ resource: 'project', action: 'read' }],
        },
      ])
    );

    const managerPaths = (managerSection?.children ?? []).map(child => child.path);
    expect(managerPaths).not.toContain('/manager/ledger');
  });
});
