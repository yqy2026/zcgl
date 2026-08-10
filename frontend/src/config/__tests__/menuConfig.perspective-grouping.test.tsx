import { describe, expect, it } from 'vitest';
import {
  MENU_ACTION_KEYS,
  MENU_GROUP_KEYS,
  MENU_ITEMS,
  getMenuNavigationPath,
  getOpenKeys,
  getSelectedKeys,
} from '@/config/menuConfig';
import { CONTRACT_CENTER_ROUTES, PROJECT_ROUTES } from '@/constants/routes';

interface MenuEntry {
  key?: string;
  label?: string;
  children?: MenuEntry[];
}

const menuEntries = MENU_ITEMS as MenuEntry[];

describe('menuConfig perspective grouping', () => {
  it('uses project-centered navigation instead of owner and manager grouped navigation', () => {
    const projectGroup = menuEntries.find(item => item.key === MENU_GROUP_KEYS.PROJECT);

    expect(projectGroup).toMatchObject({
      key: MENU_GROUP_KEYS.PROJECT,
      label: '项目运营',
      children: expect.arrayContaining([
        expect.objectContaining({ key: MENU_ACTION_KEYS.PROJECT_LIST, label: '项目列表' }),
      ]),
    });
    expect(projectGroup?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/contract-groups' })])
    );
    expect(projectGroup?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/assets/list' })])
    );

    const assetGroup = menuEntries.find(item => item.key === '/asset-files');
    expect(assetGroup).toMatchObject({
      key: '/asset-files',
      label: '资产资源',
      children: expect.arrayContaining([
        expect.objectContaining({ key: '/assets/list', label: '资产台账' }),
        expect.objectContaining({ key: '/property-certificates', label: '产权证管理' }),
      ]),
    });

    expect(menuEntries).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: MENU_GROUP_KEYS.CONTRACT_CENTER, label: '合同中心' }),
        expect.objectContaining({ key: '/customer-center', label: '主体中心' }),
        expect.objectContaining({ key: '/asset-files', label: '资产资源' }),
        expect.objectContaining({ key: '/operations/ledger', label: '经营台账' }),
        expect.objectContaining({ key: '/analytics', label: '经营分析' }),
      ])
    );
    expect(menuEntries.map(item => item.key)).not.toEqual(
      expect.arrayContaining(['/owner', '/manager'])
    );
    expect(menuEntries.map(item => item.label)).toEqual([
      '工作台',
      '项目运营',
      '资产资源',
      '合同中心',
      '经营台账',
      '主体中心',
      '经营分析',
      '系统管理',
    ]);
  });

  it('selects flat entries by canonical paths', () => {
    expect(getSelectedKeys('/assets/list')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/contract-center')).toEqual([MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]);
    expect(getSelectedKeys('/contract-center/import')).toEqual(['/contract-center/import']);
    expect(getSelectedKeys('/contract-groups')).toEqual([MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]);
    expect(getSelectedKeys('/property-certificates')).toEqual(['/property-certificates']);
    expect(getSelectedKeys('/operations/ledger')).toEqual(['/operations/ledger']);
    expect(getSelectedKeys('/project')).toEqual([MENU_ACTION_KEYS.PROJECT_LIST]);
    expect(getSelectedKeys('/analytics')).toEqual(['/analytics']);

    expect(getOpenKeys('/assets/list')).toEqual(['/asset-files']);
    expect(getOpenKeys('/contract-center/import')).toEqual([MENU_GROUP_KEYS.CONTRACT_CENTER]);
    expect(getOpenKeys('/contract-groups')).toEqual([MENU_GROUP_KEYS.CONTRACT_CENTER]);
    expect(getOpenKeys('/property-certificates')).toEqual(['/asset-files']);
    expect(getOpenKeys('/operations/ledger')).toEqual([]);
    expect(getOpenKeys('/project')).toEqual([MENU_GROUP_KEYS.PROJECT]);
    expect(getOpenKeys('/analytics')).toEqual([]);
  });

  it('keeps flat parent entries selected for detail routes', () => {
    expect(getSelectedKeys('/assets/asset-1')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/assets/asset-1/edit')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/contract-center/group-1')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/property-certificates/cert-1')).toEqual([
      '/property-certificates',
    ]);
    expect(getSelectedKeys('/project/project-1')).toEqual([MENU_ACTION_KEYS.PROJECT_LIST]);
    expect(getSelectedKeys('/project/project-1/edit')).toEqual([MENU_ACTION_KEYS.PROJECT_LIST]);

    expect(getOpenKeys('/assets/asset-1')).toEqual(['/asset-files']);
    expect(getOpenKeys('/contract-center/group-1')).toEqual([MENU_GROUP_KEYS.CONTRACT_CENTER]);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual([MENU_GROUP_KEYS.CONTRACT_CENTER]);
    expect(getOpenKeys('/property-certificates/cert-1')).toEqual(['/asset-files']);
    expect(getOpenKeys('/project/project-1')).toEqual([MENU_GROUP_KEYS.PROJECT]);
  });

  it('keeps contract group fallback navigation under the auxiliary contract center', () => {
    expect(getSelectedKeys('/contract-center')).toEqual([MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]);
    expect(getSelectedKeys('/contract-center/group-1')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getSelectedKeys('/contract-groups')).toEqual([MENU_ACTION_KEYS.CONTRACT_CENTER_LIST]);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual([
      MENU_ACTION_KEYS.CONTRACT_CENTER_LIST,
    ]);
    expect(getOpenKeys('/contract-groups')).toEqual([MENU_GROUP_KEYS.CONTRACT_CENTER]);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual([MENU_GROUP_KEYS.CONTRACT_CENTER]);
  });

  it('uses registered list route keys for menu entries that have dynamic detail siblings', () => {
    const projectGroup = menuEntries.find(item => item.key === MENU_GROUP_KEYS.PROJECT);
    const contractCenter = menuEntries.find(item => item.key === MENU_GROUP_KEYS.CONTRACT_CENTER);

    expect(projectGroup?.children).toEqual(
      expect.arrayContaining([expect.objectContaining({ key: MENU_ACTION_KEYS.PROJECT_LIST })])
    );
    expect(contractCenter?.children).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: MENU_ACTION_KEYS.CONTRACT_CENTER_LIST }),
      ])
    );
    expect(getMenuNavigationPath(MENU_ACTION_KEYS.PROJECT_LIST)).toBe(PROJECT_ROUTES.LIST);
    expect(getMenuNavigationPath(MENU_ACTION_KEYS.CONTRACT_CENTER_LIST)).toBe(
      CONTRACT_CENTER_ROUTES.LIST
    );
    expect(projectGroup?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: PROJECT_ROUTES.LIST })])
    );
    expect(contractCenter?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: CONTRACT_CENTER_ROUTES.LIST })])
    );
    expect(projectGroup?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/project/list' })])
    );
    expect(contractCenter?.children).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: '/contract-center/list' })])
    );
  });

  it('keeps every menu key unique while mapping action keys to routes', () => {
    const collectKeys = (items: MenuEntry[]): string[] =>
      items.flatMap(item => [
        ...(item.key != null ? [item.key] : []),
        ...collectKeys(item.children ?? []),
      ]);

    const keys = collectKeys(menuEntries);

    expect(new Set(keys).size).toBe(keys.length);
    expect(getMenuNavigationPath(MENU_GROUP_KEYS.PROJECT)).toBeUndefined();
    expect(getMenuNavigationPath(MENU_GROUP_KEYS.CONTRACT_CENTER)).toBeUndefined();
    expect(getMenuNavigationPath('/dashboard')).toBe('/dashboard');
  });
});
