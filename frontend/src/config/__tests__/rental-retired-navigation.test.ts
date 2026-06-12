import { describe, expect, it } from 'vitest';
import {
  MENU_ACTION_KEYS,
  MENU_GROUP_KEYS,
  MENU_ITEMS,
  getSelectedKeys,
} from '@/config/menuConfig';
import { dynamicBreadcrumbMap, staticBreadcrumbMap } from '@/config/breadcrumb';

describe('legacy rental navigation removal', () => {
  it('does not expose a rental menu entry and does not select rental paths', () => {
    const rentalSection = (MENU_ITEMS ?? []).find(item => item?.key === 'rental');

    expect(rentalSection).toBeUndefined();
    expect(getSelectedKeys('/rental/contracts')).toEqual(['/rental/contracts']);
    expect(getSelectedKeys('/rental/contracts/pdf-import')).toEqual([
      '/rental/contracts/pdf-import',
    ]);
    expect(getSelectedKeys('/rental/ledger')).toEqual(['/rental/ledger']);
    expect(getSelectedKeys('/rental/statistics')).toEqual(['/rental/statistics']);
  });

  it('does not keep breadcrumb labels for legacy rental paths', () => {
    expect(staticBreadcrumbMap['/rental']).toBeUndefined();
    expect(staticBreadcrumbMap['/rental/contracts']).toBeUndefined();
    expect(staticBreadcrumbMap['/rental/contracts/new']).toBeUndefined();
    expect(staticBreadcrumbMap['/rental/contracts/pdf-import']).toBeUndefined();
    expect(staticBreadcrumbMap['/rental/ledger']).toBeUndefined();
    expect(staticBreadcrumbMap['/rental/statistics']).toBeUndefined();

    expect(dynamicBreadcrumbMap['/rental/contracts/:id']).toBeUndefined();
    expect(dynamicBreadcrumbMap['/rental/contracts/:id/edit']).toBeUndefined();
    expect(dynamicBreadcrumbMap['/rental/contracts/:id/renew']).toBeUndefined();
  });

  it('keeps contract groups as internal fallback routes without exposing a menu entry', () => {
    const assetsSection = (MENU_ITEMS ?? []).find(item => item?.key === '/asset-files');
    const assetsChildren =
      'children' in (assetsSection ?? {}) ? (assetsSection?.children ?? []) : [];

    expect(assetsChildren).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/contract-groups' })])
    );

    expect(getSelectedKeys('/contract-center')).toEqual([MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]);
    expect(getSelectedKeys('/contract-center/import')).toEqual(['/contract-center/import']);
    expect(getSelectedKeys('/contract-center/new')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-center/group-1')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-groups')).toEqual([MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]);
    expect(getSelectedKeys('/contract-groups/import')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-groups/new')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-groups/group-1/edit')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);

    expect(staticBreadcrumbMap['/contract-center']).toBe('合同中心');
    expect(staticBreadcrumbMap['/contract-center/import']).toBe('PDF导入');
    expect(staticBreadcrumbMap['/contract-center/new']).toBe('新建合同关系');
    expect(dynamicBreadcrumbMap['/contract-center/:id']).toBe('合同关系明细');
    expect(dynamicBreadcrumbMap['/contract-center/:id/edit']).toBe('编辑合同关系');
    expect(MENU_ITEMS).toEqual(
      expect.arrayContaining([expect.objectContaining({ key: MENU_GROUP_KEYS.CONTRACT_CENTER })])
    );
  });

  it('keeps party detail routes highlighted under system party menu', () => {
    const customerSection = (MENU_ITEMS ?? []).find(item => item?.key === '/customer-center');
    const customerChildren =
      'children' in (customerSection ?? {}) ? (customerSection?.children ?? []) : [];
    const partyEntry = customerChildren.find(item => item?.key === '/system/parties');

    expect(customerSection?.label).toBe('主体中心');
    expect(partyEntry?.label).toBe('主体管理');
    expect(getSelectedKeys('/system/parties')).toEqual(['/system/parties']);
    expect(getSelectedKeys('/system/parties/party-1')).toEqual(['/system/parties']);
  });

  it('does not expose out-of-scope ownership or property certificate navigation', () => {
    const assetSection = (MENU_ITEMS ?? []).find(item => item?.key === '/asset-files');
    const assetChildren = 'children' in (assetSection ?? {}) ? (assetSection?.children ?? []) : [];
    const customerSection = (MENU_ITEMS ?? []).find(item => item?.key === '/customer-center');
    const customerChildren =
      'children' in (customerSection ?? {}) ? (customerSection?.children ?? []) : [];

    expect(assetChildren).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/property-certificates' })])
    );
    expect(customerChildren).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/ownership' })])
    );
    expect(staticBreadcrumbMap['/property-certificates']).toBeUndefined();
    expect(staticBreadcrumbMap['/property-certificates/import']).toBeUndefined();
    expect(staticBreadcrumbMap['/ownership']).toBeUndefined();
    expect(dynamicBreadcrumbMap['/property-certificates/:id']).toBeUndefined();
    expect(dynamicBreadcrumbMap['/ownership/:id']).toBeUndefined();
  });
});
