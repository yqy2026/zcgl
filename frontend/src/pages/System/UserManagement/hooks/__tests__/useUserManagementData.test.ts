import { describe, expect, it } from 'vitest';
import type { User } from '@/services/systemService';
import { attachOrganizationNames } from '../useUserManagementData';

const user: User = {
  id: 'user-1',
  username: 'admin',
  email: 'admin@example.com',
  full_name: 'Development Administrator',
  phone: '13800000000',
  status: 'active',
  roles: ['system_admin'],
  role_ids: ['role-admin'],
  account_type: 'human',
  organization_id: 'org-1',
  last_login: null,
  created_at: '2026-08-01T08:00:00Z',
  updated_at: '2026-08-04T08:00:00Z',
  is_locked: false,
  login_attempts: 0,
};

describe('attachOrganizationNames', () => {
  it('resolves the direct organization name without inventing a fallback association', () => {
    expect(
      attachOrganizationNames([user], [{ id: 'org-1', name: '广州国有资产管理集团有限公司' }])
    ).toEqual([
      expect.objectContaining({
        organization_id: 'org-1',
        organization_name: '广州国有资产管理集团有限公司',
      }),
    ]);
  });
});
