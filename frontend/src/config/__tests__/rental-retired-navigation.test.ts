import { describe, expect, it } from 'vitest';
import { MENU_ITEMS, getSelectedKeys } from '@/config/menuConfig';
import { dynamicBreadcrumbMap, staticBreadcrumbMap } from '@/config/breadcrumb';

describe('rental retired navigation config', () => {
  it('collapses rental menu to a single retired entry and keeps rental paths selected on that entry', () => {
    const rentalSection = (MENU_ITEMS ?? []).find(item => item?.key === 'rental');
    const rentalChildren =
      'children' in (rentalSection ?? {}) ? (rentalSection?.children ?? []) : [];

    expect(rentalSection?.label).toBe('旧租赁前端已退休');
    expect(rentalChildren).toHaveLength(1);
    expect(rentalChildren[0]?.key).toBe('/rental/contracts');
    expect(rentalChildren[0]?.label).toBe('旧租赁前端已退休');

    expect(getSelectedKeys('/rental/contracts')).toEqual(['/rental/contracts']);
    expect(getSelectedKeys('/rental/contracts/pdf-import')).toEqual([]);
    expect(getSelectedKeys('/rental/ledger')).toEqual(['/rental/contracts']);
    expect(getSelectedKeys('/rental/statistics')).toEqual(['/rental/contracts']);
  });

  it('uses retired breadcrumb labels for legacy rental paths', () => {
    expect(staticBreadcrumbMap['/rental']).toBe('旧租赁前端已退休');
    expect(staticBreadcrumbMap['/rental/contracts']).toBe('旧租赁前端已退休');
    expect(staticBreadcrumbMap['/rental/contracts/new']).toBe('旧租赁前端已退休');
    expect(staticBreadcrumbMap['/rental/contracts/pdf-import']).toBe('跳转至PDF导入');
    expect(staticBreadcrumbMap['/rental/ledger']).toBe('旧租赁台账已退休');
    expect(staticBreadcrumbMap['/rental/statistics']).toBe('旧租赁统计已退休');

    expect(dynamicBreadcrumbMap['/rental/contracts/:id']).toBe('旧合同详情入口已退休');
    expect(dynamicBreadcrumbMap['/rental/contracts/:id/edit']).toBe('旧合同编辑入口已退休');
    expect(dynamicBreadcrumbMap['/rental/contracts/:id/renew']).toBe('旧合同续签入口已退休');
  });

  it('keeps retired rental routing while contract groups stay under flat asset navigation', () => {
    const assetsSection = (MENU_ITEMS ?? []).find(item => item?.key === '/assets');
    const assetsChildren =
      'children' in (assetsSection ?? {}) ? (assetsSection?.children ?? []) : [];

    expect(assetsChildren).toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/contract-groups' })])
    );

    expect(getSelectedKeys('/contract-groups')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/contract-groups/import')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/contract-groups/new')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/contract-groups/group-1/edit')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/rental/contracts/pdf-import')).toEqual([]);

    expect(staticBreadcrumbMap['/contract-groups']).toBe('合同组管理');
    expect(staticBreadcrumbMap['/contract-groups/import']).toBe('PDF导入');
    expect(staticBreadcrumbMap['/contract-groups/new']).toBe('新建合同组');
    expect(staticBreadcrumbMap['/rental/contracts/pdf-import']).toBe('跳转至PDF导入');
    expect(dynamicBreadcrumbMap['/contract-groups/:id']).toBe('合同组详情');
    expect(dynamicBreadcrumbMap['/contract-groups/:id/edit']).toBe('编辑合同组');
  });

  it('keeps party detail routes highlighted under system party menu', () => {
    const systemSection = (MENU_ITEMS ?? []).find(item => item?.key === 'system');
    const systemChildren =
      'children' in (systemSection ?? {}) ? (systemSection?.children ?? []) : [];
    const partyEntry = systemChildren.find(item => item?.key === '/system/parties');

    expect(partyEntry?.label).toBe('主体管理');
    expect(getSelectedKeys('/system/parties')).toEqual(['/system/parties']);
    expect(getSelectedKeys('/system/parties/party-1')).toEqual(['/system/parties']);
  });
});
