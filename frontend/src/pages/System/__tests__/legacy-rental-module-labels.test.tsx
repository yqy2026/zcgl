import { describe, expect, it } from 'vitest';
import { rolePermissionModules } from '../RoleManagement/constants';
import { MODULE_OPTIONS } from '../OperationLog/constants';

describe('legacy rental module labels', () => {
  it('removes rental module metadata from system pages', () => {
    expect(rolePermissionModules.find(option => option.value === 'rental')).toBeUndefined();
    expect(MODULE_OPTIONS.find(option => option.value === 'rental')).toBeUndefined();
  });
});
