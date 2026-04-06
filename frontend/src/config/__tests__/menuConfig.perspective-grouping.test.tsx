import { describe, expect, it } from 'vitest';
import { MENU_ITEMS, getOpenKeys, getSelectedKeys } from '@/config/menuConfig';

interface MenuEntry {
  key?: string;
  label?: string;
  children?: MenuEntry[];
}

const menuEntries = MENU_ITEMS as MenuEntry[];

describe('menuConfig perspective grouping', () => {
  it('uses flat asset navigation instead of owner and manager grouped navigation', () => {
    const assetsGroup = menuEntries.find(item => item.key === '/assets');

    expect(assetsGroup).toMatchObject({
      key: '/assets',
      label: '资产管理',
      children: expect.arrayContaining([
        expect.objectContaining({ key: '/assets/list', label: '资产列表' }),
        expect.objectContaining({ key: '/contract-groups', label: '合同组管理' }),
        expect.objectContaining({ key: '/property-certificates', label: '产权证管理' }),
        expect.objectContaining({ key: '/project', label: '项目管理' }),
      ]),
    });

    expect(menuEntries.map(item => item.key)).not.toEqual(
      expect.arrayContaining(['/owner', '/manager'])
    );
  });

  it('selects flat entries by canonical paths', () => {
    expect(getSelectedKeys('/assets/list')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/contract-groups')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/property-certificates')).toEqual(['/property-certificates']);
    expect(getSelectedKeys('/project')).toEqual(['/project']);

    expect(getOpenKeys('/assets/list')).toEqual(['/assets']);
    expect(getOpenKeys('/contract-groups')).toEqual(['/assets']);
    expect(getOpenKeys('/property-certificates')).toEqual(['/assets']);
    expect(getOpenKeys('/project')).toEqual(['/assets']);
  });

  it('keeps flat parent entries selected for detail routes', () => {
    expect(getSelectedKeys('/assets/asset-1')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/assets/asset-1/edit')).toEqual(['/assets/list']);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/property-certificates/cert-1')).toEqual(['/property-certificates']);
    expect(getSelectedKeys('/project/project-1')).toEqual(['/project']);
    expect(getSelectedKeys('/project/project-1/edit')).toEqual(['/project']);

    expect(getOpenKeys('/assets/asset-1')).toEqual(['/assets']);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual(['/assets']);
    expect(getOpenKeys('/property-certificates/cert-1')).toEqual(['/assets']);
    expect(getOpenKeys('/project/project-1')).toEqual(['/assets']);
  });

  it('keeps contract group navigation highlighted under the flat asset section', () => {
    expect(getSelectedKeys('/contract-groups')).toEqual(['/contract-groups']);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual(['/contract-groups']);
    expect(getOpenKeys('/contract-groups')).toEqual(['/assets']);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual(['/assets']);
  });
});
