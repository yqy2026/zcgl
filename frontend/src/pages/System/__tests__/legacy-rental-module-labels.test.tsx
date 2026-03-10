import { describe, expect, it } from 'vitest';
import { rolePermissionModules } from '../RoleManagement/constants';
import { MODULE_OPTIONS } from '../OperationLog/constants';

describe('legacy rental module labels', () => {
  it('uses retired labels for rental module metadata across system pages', () => {
    expect(rolePermissionModules.find(option => option.value === 'rental')?.label).toBe(
      '旧租赁前端已退休'
    );
    expect(MODULE_OPTIONS.find(option => option.value === 'rental')?.label).toBe(
      '旧租赁前端已退休'
    );
  });
});
