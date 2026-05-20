import { describe, expect, it } from 'vitest';
import { MENU_ITEMS, getOpenKeys, getSelectedKeys } from '@/config/menuConfig';

interface MenuEntry {
  key?: string;
  label?: string;
  children?: MenuEntry[];
}

const menuEntries = MENU_ITEMS as MenuEntry[];

describe('menuConfig perspective grouping', () => {
  it('uses project-centered navigation instead of owner and manager grouped navigation', () => {
    const projectGroup = menuEntries.find(item => item.key === '/project');

    expect(projectGroup).toMatchObject({
      key: '/project',
      label: '项目运营',
      children: expect.arrayContaining([
        expect.objectContaining({ key: '/project', label: '项目列表' }),
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
        expect.objectContaining({ key: '/contract-center', label: '合同中心' }),
        expect.objectContaining({ key: '/customer-center', label: '主体中心' }),
        expect.objectContaining({ key: '/asset-files', label: '资产资源' }),
        expect.objectContaining({ key: '/finance/ledger', label: '财务台账' }),
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
      '财务台账',
      '主体中心',
      '经营分析',
      '系统管理',
    ]);
  });

  it('selects flat entries by canonical paths', () => {
    expect(getSelectedKeys('/assets/list')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/contract-center')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/contract-center/import')).toEqual(['/contract-center/import']);
    expect(getSelectedKeys('/contract-groups')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/property-certificates')).toEqual(['/property-certificates']);
    expect(getSelectedKeys('/finance/ledger')).toEqual(['/finance/ledger']);
    expect(getSelectedKeys('/project')).toEqual(['/project']);
    expect(getSelectedKeys('/analytics')).toEqual(['/analytics']);

    expect(getOpenKeys('/assets/list')).toEqual(['/asset-files']);
    expect(getOpenKeys('/contract-center/import')).toEqual(['/contract-center']);
    expect(getOpenKeys('/contract-groups')).toEqual(['/contract-center']);
    expect(getOpenKeys('/property-certificates')).toEqual(['/asset-files']);
    expect(getOpenKeys('/finance/ledger')).toEqual([]);
    expect(getOpenKeys('/project')).toEqual(['/project']);
    expect(getOpenKeys('/analytics')).toEqual([]);
  });

  it('keeps flat parent entries selected for detail routes', () => {
    expect(getSelectedKeys('/assets/asset-1')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/assets/asset-1/edit')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/contract-center/group-1')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/property-certificates/cert-1')).toEqual(['/property-certificates']);
    expect(getSelectedKeys('/project/project-1')).toEqual(['/project']);
    expect(getSelectedKeys('/project/project-1/edit')).toEqual(['/project']);

    expect(getOpenKeys('/assets/asset-1')).toEqual(['/asset-files']);
    expect(getOpenKeys('/contract-center/group-1')).toEqual(['/contract-center']);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual(['/contract-center']);
    expect(getOpenKeys('/property-certificates/cert-1')).toEqual(['/asset-files']);
    expect(getOpenKeys('/project/project-1')).toEqual(['/project']);
  });

  it('keeps contract group fallback navigation under the auxiliary contract center', () => {
    expect(getSelectedKeys('/contract-center')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/contract-center/group-1')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/contract-groups')).toEqual(['/contract-center']);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual(['/contract-center']);
    expect(getOpenKeys('/contract-groups')).toEqual(['/contract-center']);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual(['/contract-center']);
  });
});
