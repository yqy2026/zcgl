import { expect, test, type Page } from '@playwright/test';

import {
  clearAuthState,
  loginAsAdmin,
  loginWithCredential,
  resolveCsrfHeaders,
  resolveRegularCredential,
} from '../helpers/auth';

interface RoleListItem {
  id: string;
  name?: string;
  display_name?: string;
}

interface UserCreateResponse {
  id: string;
  username: string;
}

const normalizeNonEmpty = (value: unknown): string | null => {
  if (value == null) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized !== '' ? normalized : null;
};

const buildPhone = (serial: number): string => {
  const suffix = String(serial % 1000000000).padStart(9, '0');
  return `13${suffix}`;
};

const extractData = <T>(payload: unknown): T => {
  if (
    payload != null &&
    typeof payload === 'object' &&
    'data' in payload &&
    (payload as { data?: unknown }).data !== undefined
  ) {
    return (payload as { data: T }).data;
  }

  return payload as T;
};

const resolveNonAdminRoleId = async (
  page: Page,
  headers?: Record<string, string>
): Promise<string> => {
  const explicitRoleId = normalizeNonEmpty(process.env.E2E_REGULAR_ROLE_ID);
  if (explicitRoleId != null) {
    return explicitRoleId;
  }

  const rolesResponse = await page.request.get('/api/v1/roles?page=1&page_size=100');
  expect(rolesResponse.status()).toBe(200);
  const rolesPayload = (await rolesResponse.json()) as unknown;
  const rolesData = extractData<{ items?: RoleListItem[] }>(rolesPayload);
  const roleItems = Array.isArray(rolesData.items) ? rolesData.items : [];

  const role = roleItems.find(item => {
    const roleName = `${item.name ?? ''} ${item.display_name ?? ''}`.toLowerCase();
    return !roleName.includes('admin') && !roleName.includes('管理员');
  });

  const roleId = normalizeNonEmpty(role?.id);
  if (roleId != null) {
    return roleId;
  }

  if (headers == null || Object.keys(headers).length === 0) {
    throw new Error('No non-admin role is available for access-denied E2E.');
  }

  const suffix = Date.now();
  const createRoleResponse = await page.request.post('/api/v1/roles', {
    headers,
    data: {
      name: `e2e_regular_role_${suffix}`,
      display_name: `E2E Regular Role ${suffix}`,
      description: 'Provisioned by access-denied E2E',
      level: 1,
      scope: 'global',
      permission_ids: [],
    },
  });

  if (createRoleResponse.status() !== 201) {
    const body = await createRoleResponse.text();
    throw new Error(
      `No non-admin role is available for access-denied E2E. role_create_status=${createRoleResponse.status()} body=${body}`
    );
  }

  const createdRolePayload = (await createRoleResponse.json()) as unknown;
  const createdRole = extractData<RoleListItem>(createdRolePayload);
  const createdRoleId = normalizeNonEmpty(createdRole.id);
  if (createdRoleId == null) {
    throw new Error('No non-admin role is available for access-denied E2E.');
  }

  return createdRoleId;
};

const provisionRegularCredential = async (
  page: Page
): Promise<{ credential: { username: string; password: string }; userId: string }> => {
  await clearAuthState(page);
  await loginAsAdmin(page);
  const headers = await resolveCsrfHeaders(page);
  if (Object.keys(headers).length === 0) {
    throw new Error('Unable to provision regular user: csrf_token is missing.');
  }

  const roleId = await resolveNonAdminRoleId(page, headers);
  const suffix = Date.now();
  const password = `Aa!${suffix}`;
  const createUserResponse = await page.request.post('/api/v1/auth/users', {
    headers,
    data: {
      username: `e2e_regular_${suffix}`,
      full_name: `E2E Regular ${suffix}`,
      email: `e2e.regular.${suffix}@example.com`,
      phone: buildPhone(suffix),
      password,
      role_id: roleId,
    },
  });

  if (createUserResponse.status() !== 200) {
    const body = await createUserResponse.text();
    throw new Error(
      `Unable to provision regular user: status=${createUserResponse.status()} body=${body}`
    );
  }

  const payload = (await createUserResponse.json()) as unknown;
  const user = extractData<UserCreateResponse>(payload);
  const userId = normalizeNonEmpty(user.id);
  const username = normalizeNonEmpty(user.username);
  if (userId == null || username == null) {
    throw new Error('Unable to provision regular user: invalid user payload.');
  }

  return {
    credential: {
      username,
      password,
    },
    userId,
  };
};

const cleanupProvisionedUser = async (
  page: Page,
  userId: string
): Promise<void> => {
  try {
    await clearAuthState(page);
    await loginAsAdmin(page);
    const headers = await resolveCsrfHeaders(page);
    if (Object.keys(headers).length === 0) {
      return;
    }
    await page.request.delete(`/api/v1/auth/users/${userId}`, {
      headers,
    });
  } catch {
    // Best-effort cleanup.
  }
};

test.describe('Access Control', () => {
  test('should redirect anonymous users to login', async ({ page }) => {
    await clearAuthState(page);
    await page.goto('/system/users');
    await expect(page).toHaveURL(/\/login/);
  });

  const regularCredential = resolveRegularCredential();

  test('should reject regular user from admin-only API', async ({ page }) => {
    let credential = regularCredential;
    let provisionedUserId: string | null = null;

    try {
      if (credential == null) {
        const provisioned = await provisionRegularCredential(page);
        credential = provisioned.credential;
        provisionedUserId = provisioned.userId;
      }

      await clearAuthState(page);
      const success = await loginWithCredential(page, credential);
      expect(success).toBe(true);

      const response = await page.request.get('/api/v1/system/backup/stats');
      expect([401, 403]).toContain(response.status());
    } finally {
      if (provisionedUserId != null) {
        await cleanupProvisionedUser(page, provisionedUserId);
      }
    }
  });
});
