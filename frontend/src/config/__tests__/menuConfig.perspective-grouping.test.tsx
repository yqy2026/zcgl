import { describe, expect, it } from 'vitest';
import { MENU_ITEMS, getOpenKeys, getSelectedKeys } from '@/config/menuConfig';

interface MenuEntry {
  key?: string;
  label?: string;
  children?: MenuEntry[];
}

const menuEntries = MENU_ITEMS as MenuEntry[];

describe('menuConfig perspective grouping', () => {
  it('uses owner and manager grouped navigation instead of generic asset/project groups', () => {
    const ownerGroup = menuEntries.find(item => item.key === '/owner');
    const managerGroup = menuEntries.find(item => item.key === '/manager');

    expect(ownerGroup).toMatchObject({
      key: '/owner',
      label: '业主视角',
      children: expect.arrayContaining([
        expect.objectContaining({ key: '/owner/assets', label: '业主资产' }),
        expect.objectContaining({ key: '/owner/contract-groups', label: '业主合同组' }),
        expect.objectContaining({ key: '/owner/property-certificates', label: '产权证管理' }),
      ]),
    });

    expect(managerGroup).toMatchObject({
      key: '/manager',
      label: '经营视角',
      children: expect.arrayContaining([
        expect.objectContaining({ key: '/manager/assets', label: '经营资产' }),
        expect.objectContaining({ key: '/manager/contract-groups', label: '经营合同组' }),
        expect.objectContaining({ key: '/manager/projects', label: '经营项目' }),
      ]),
    });

    expect(menuEntries.map(item => item.key)).not.toEqual(
      expect.arrayContaining(['assets', '/project', '/contract-groups'])
    );
  });

  it('selects grouped owner and manager entries by perspective-prefixed paths', () => {
    expect(getSelectedKeys('/owner/assets')).toEqual(['/owner/assets']);
    expect(getSelectedKeys('/owner/contract-groups')).toEqual(['/owner/contract-groups']);
    expect(getSelectedKeys('/owner/property-certificates')).toEqual([
      '/owner/property-certificates',
    ]);
    expect(getSelectedKeys('/manager/assets')).toEqual(['/manager/assets']);
    expect(getSelectedKeys('/manager/contract-groups')).toEqual(['/manager/contract-groups']);
    expect(getSelectedKeys('/manager/projects')).toEqual(['/manager/projects']);

    expect(getOpenKeys('/owner/assets')).toEqual(['/owner']);
    expect(getOpenKeys('/owner/contract-groups')).toEqual(['/owner']);
    expect(getOpenKeys('/owner/property-certificates')).toEqual(['/owner']);
    expect(getOpenKeys('/manager/assets')).toEqual(['/manager']);
    expect(getOpenKeys('/manager/contract-groups')).toEqual(['/manager']);
    expect(getOpenKeys('/manager/projects')).toEqual(['/manager']);
  });

  it('keeps grouped parent entries selected for prefixed detail routes', () => {
    expect(getSelectedKeys('/owner/assets/asset-1')).toEqual(['/owner/assets']);
    expect(getSelectedKeys('/owner/assets/asset-1/edit')).toEqual(['/owner/assets']);
    expect(getSelectedKeys('/owner/contract-groups/group-1')).toEqual(['/owner/contract-groups']);
    expect(getSelectedKeys('/owner/property-certificates/cert-1')).toEqual([
      '/owner/property-certificates',
    ]);
    expect(getSelectedKeys('/manager/assets/asset-2')).toEqual(['/manager/assets']);
    expect(getSelectedKeys('/manager/assets/asset-2/edit')).toEqual(['/manager/assets']);
    expect(getSelectedKeys('/manager/contract-groups/group-1')).toEqual([
      '/manager/contract-groups',
    ]);
    expect(getSelectedKeys('/manager/projects/project-1')).toEqual(['/manager/projects']);
    expect(getSelectedKeys('/manager/projects/project-1/edit')).toEqual(['/manager/projects']);

    expect(getOpenKeys('/owner/assets/asset-1')).toEqual(['/owner']);
    expect(getOpenKeys('/owner/contract-groups/group-1')).toEqual(['/owner']);
    expect(getOpenKeys('/owner/property-certificates/cert-1')).toEqual(['/owner']);
    expect(getOpenKeys('/manager/assets/asset-2')).toEqual(['/manager']);
    expect(getOpenKeys('/manager/contract-groups/group-1')).toEqual(['/manager']);
    expect(getOpenKeys('/manager/projects/project-1')).toEqual(['/manager']);
  });

  it('does not keep shared contract group navigation highlighted after grouping by perspective', () => {
    expect(getSelectedKeys('/contract-groups')).toEqual([]);
    expect(getSelectedKeys('/contract-groups/group-1')).toEqual([]);
    expect(getOpenKeys('/contract-groups')).toEqual([]);
    expect(getOpenKeys('/contract-groups/group-1')).toEqual([]);
  });
});
