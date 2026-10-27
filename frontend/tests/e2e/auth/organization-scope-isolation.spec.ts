import { expect, test, type APIResponse, type Page } from '@playwright/test';

import {
  clearAuthState,
  ensureAuthenticated,
  loginWithCredentialRetry,
  resolveCsrfHeaders,
} from '../helpers/auth';

const WALKTHROUGH_OWNER_ID = 'v5-walkthrough-owner';
const WALKTHROUGH_OPERATOR_ID = 'v5-walkthrough-operator';

interface OrganizationItem {
  id: string;
  code?: string;
}

interface PermissionItem {
  action: string;
  resource: string;
}

interface RoleListItem {
  id: string;
  name: string;
}

interface RoleDetailItem {
  permissions?: PermissionItem[];
}

interface UserItem {
  id: string;
  username: string;
}

interface AssetUnitItem {
  id: string;
  owner_party_id: string;
}

interface AssetUnitListResponse {
  items: AssetUnitItem[];
  total: number;
}

const normalizeNonEmpty = (value: unknown): string | null => {
  if (value == null) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized !== '' ? normalized : null;
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

const parsePaginatedItems = <T>(payload: unknown): T[] => {
  const extracted = extractData<unknown>(payload);
  if (Array.isArray(extracted)) {
    return extracted as T[];
  }
  if (
    extracted != null &&
    typeof extracted === 'object' &&
    Array.isArray((extracted as { items?: unknown }).items)
  ) {
    return (extracted as { items: T[] }).items;
  }
  return [];
};

const readResponseSnippet = async (response: APIResponse): Promise<string> => {
  const rawText = await response.text().catch(() => '<unavailable>');
  return rawText.length <= 260 ? rawText : `${rawText.slice(0, 260)}...`;
};

const buildPhone = (serial: number): string => {
  const suffix = String(serial % 1_000_000_000).padStart(9, '0');
  return `13${suffix}`;
};

const requireCsrfHeaders = async (page: Page): Promise<Record<string, string>> => {
  const headers = await resolveCsrfHeaders(page);
  if (Object.keys(headers).length === 0) {
    throw new Error('[org-scope-isolation] authenticated session has no CSRF token');
  }
  return headers;
};

const resolveRegularAssetOpsRoleId = async (page: Page): Promise<string> => {
  const rolesResponse = await page.request.get('/api/v1/roles?page=1&page_size=100');
  expect(rolesResponse.status()).toBe(200);
  const rolesPayload = (await rolesResponse.json()) as unknown;
  const role = parsePaginatedItems<RoleListItem>(rolesPayload).find(item => item.name === 'user');
  if (role == null) {
    throw new Error('[org-scope-isolation] seeded regular role "user" is missing');
  }

  const detailResponse = await page.request.get(`/api/v1/roles/${role.id}`);
  expect(detailResponse.status()).toBe(200);
  const detail = extractData<RoleDetailItem>((await detailResponse.json()) as unknown);
  const canReadAssetOperations = (detail.permissions ?? []).some(
    permission => permission.resource === 'asset_ops' && permission.action === 'read'
  );
  if (!canReadAssetOperations) {
    throw new Error('[org-scope-isolation] regular role lacks asset_ops:read');
  }
  return role.id;
};

const activateCreatedUser = async (
  page: Page,
  userId: string,
  mutationHeaders: Record<string, string>
): Promise<void> => {
  const organizationsResponse = await page.request.get(
    '/api/v1/organizations?page=1&page_size=100'
  );
  expect(organizationsResponse.status()).toBe(200);
  const organizations = parsePaginatedItems<OrganizationItem>(
    (await organizationsResponse.json()) as unknown
  );
  const organization = organizations.find(item => item.code === 'E2E-ORG-ROOT');
  if (organization == null) {
    throw new Error('[org-scope-isolation] seeded organization E2E-ORG-ROOT is missing');
  }

  const previewResponse = await page.request.post(
    `/api/v1/auth/users/${userId}/organization/preview`,
    {
      headers: mutationHeaders,
      data: { organization_id: organization.id },
    }
  );
  expect(previewResponse.status()).toBe(200);
  const preview = extractData<{ preview_token?: string }>(
    (await previewResponse.json()) as unknown
  );
  const previewToken = normalizeNonEmpty(preview.preview_token);
  if (previewToken == null) {
    throw new Error('[org-scope-isolation] organization preview did not return a token');
  }

  const commitResponse = await page.request.put(`/api/v1/auth/users/${userId}/organization`, {
    headers: mutationHeaders,
    data: {
      preview_token: previewToken,
      reason: 'asset operations E2E scope setup',
      idempotency_key: `e2e-org-${userId}`,
    },
  });
  expect(commitResponse.status()).toBe(200);

  const activateResponse = await page.request.post(`/api/v1/auth/users/${userId}/activate`, {
    headers: mutationHeaders,
  });
  expect(activateResponse.status()).toBe(200);
};

const createRegularUser = async ({
  page,
  roleId,
  password,
  suffix,
  label,
  mutationHeaders,
}: {
  page: Page;
  roleId: string;
  password: string;
  suffix: number;
  label: string;
  mutationHeaders: Record<string, string>;
}): Promise<UserItem> => {
  const response = await page.request.post('/api/v1/auth/users', {
    headers: mutationHeaders,
    data: {
      username: `e2e_v5_scope_${label}_${suffix}`,
      full_name: `E2E V5 Scope ${label} ${suffix}`,
      email: `e2e.v5.scope.${label}.${suffix}@example.com`,
      phone: buildPhone(suffix + (label === 'bound' ? 1 : 2)),
      password,
      role_id: roleId,
    },
  });
  if (response.status() !== 200) {
    throw new Error(
      `[org-scope-isolation] user creation failed: ${await readResponseSnippet(response)}`
    );
  }
  const user = extractData<Partial<UserItem>>((await response.json()) as unknown);
  const userId = normalizeNonEmpty(user.id);
  const username = normalizeNonEmpty(user.username);
  if (userId == null || username == null) {
    throw new Error('[org-scope-isolation] user creation returned an invalid payload');
  }
  await activateCreatedUser(page, userId, mutationHeaders);
  return { id: userId, username };
};

const commitOwnerBinding = async ({
  page,
  userId,
  mutationHeaders,
  suffix,
}: {
  page: Page;
  userId: string;
  mutationHeaders: Record<string, string>;
  suffix: number;
}): Promise<void> => {
  const previewResponse = await page.request.post(
    `/api/v1/users/${userId}/party-bindings/preview`,
    {
      headers: mutationHeaders,
      data: {
        operation: 'create',
        party_id: WALKTHROUGH_OWNER_ID,
        relation_type: 'owner',
      },
    }
  );
  if (previewResponse.status() !== 200) {
    throw new Error(
      `[org-scope-isolation] binding preview failed: ${await readResponseSnippet(previewResponse)}`
    );
  }
  const preview = extractData<{ preview_token?: string }>(
    (await previewResponse.json()) as unknown
  );
  const previewToken = normalizeNonEmpty(preview.preview_token);
  if (previewToken == null) {
    throw new Error('[org-scope-isolation] binding preview did not return a token');
  }

  const commitResponse = await page.request.post(`/api/v1/users/${userId}/party-bindings/commit`, {
    headers: mutationHeaders,
    data: {
      preview_token: previewToken,
      reason: 'asset operations E2E scope setup',
      idempotency_key: `e2e-v5-binding-${suffix}`,
    },
  });
  expect(commitResponse.status()).toBe(200);
};

const fetchUnits = async (page: Page, ownerPartyId?: string): Promise<AssetUnitListResponse> => {
  const params = new URLSearchParams({ limit: '100' });
  if (ownerPartyId != null) {
    params.set('owner_party_id', ownerPartyId);
  }
  const response = await page.request.get(`/api/v1/asset-units?${params.toString()}`);
  expect(response.status()).toBe(200);
  return extractData<AssetUnitListResponse>((await response.json()) as unknown);
};

const restoreAdminAndDeleteUsers = async (page: Page, userIds: string[]): Promise<void> => {
  if (userIds.length === 0) {
    return;
  }
  await clearAuthState(page);
  await ensureAuthenticated(page);
  const headers = await requireCsrfHeaders(page);
  for (const userId of userIds) {
    await page.request.delete(`/api/v1/auth/users/${userId}`, { headers });
  }
};

test.describe('@authz-org-scope v5 asset-unit Party scope isolation', () => {
  test('an owner-bound regular user sees only the bound owner asset units', async ({ page }) => {
    await ensureAuthenticated(page);
    const mutationHeaders = await requireCsrfHeaders(page);
    const roleId = await resolveRegularAssetOpsRoleId(page);
    const adminOwnUnits = await fetchUnits(page, WALKTHROUGH_OWNER_ID);
    const adminOtherUnits = await fetchUnits(page, WALKTHROUGH_OPERATOR_ID);
    expect(adminOwnUnits.total).toBeGreaterThanOrEqual(2);
    expect(adminOwnUnits.items).not.toHaveLength(0);
    expect(adminOtherUnits.total).toBeGreaterThanOrEqual(1);
    expect(adminOtherUnits.items).not.toHaveLength(0);
    const otherUnitIds = new Set(adminOtherUnits.items.map(item => item.id));
    const suffix = Date.now();
    const password = `Aa!${suffix}`;
    const createdUserIds: string[] = [];

    try {
      const user = await createRegularUser({
        page,
        roleId,
        password,
        suffix,
        label: 'bound',
        mutationHeaders,
      });
      createdUserIds.push(user.id);
      await commitOwnerBinding({
        page,
        userId: user.id,
        mutationHeaders,
        suffix,
      });

      await clearAuthState(page);
      expect(await loginWithCredentialRetry(page, { username: user.username, password }, 2)).toBe(
        true
      );

      const ownUnits = await fetchUnits(page, WALKTHROUGH_OWNER_ID);
      expect(ownUnits.total).toBeGreaterThanOrEqual(2);
      expect(ownUnits.items).not.toHaveLength(0);
      expect(ownUnits.items.every(item => item.owner_party_id === WALKTHROUGH_OWNER_ID)).toBe(true);

      const otherUnits = await fetchUnits(page, WALKTHROUGH_OPERATOR_ID);
      expect(otherUnits.total).toBe(0);
      expect(otherUnits.items).toHaveLength(0);

      const unfilteredUnits = await fetchUnits(page);
      expect(unfilteredUnits.items).not.toHaveLength(0);
      expect(
        unfilteredUnits.items.every(item => item.owner_party_id === WALKTHROUGH_OWNER_ID)
      ).toBe(true);
      expect(unfilteredUnits.items.some(item => otherUnitIds.has(item.id))).toBe(false);
    } finally {
      await restoreAdminAndDeleteUsers(page, createdUserIds);
    }
  });

  test('a regular user without the explicit owner binding cannot read walkthrough units', async ({
    page,
  }) => {
    await ensureAuthenticated(page);
    const mutationHeaders = await requireCsrfHeaders(page);
    const roleId = await resolveRegularAssetOpsRoleId(page);
    const adminOwnUnits = await fetchUnits(page, WALKTHROUGH_OWNER_ID);
    const adminOtherUnits = await fetchUnits(page, WALKTHROUGH_OPERATOR_ID);
    expect(adminOwnUnits.items).not.toHaveLength(0);
    expect(adminOtherUnits.items).not.toHaveLength(0);
    const suffix = Date.now();
    const password = `Aa!${suffix}`;
    const createdUserIds: string[] = [];

    try {
      const user = await createRegularUser({
        page,
        roleId,
        password,
        suffix,
        label: 'unbound',
        mutationHeaders,
      });
      createdUserIds.push(user.id);

      await clearAuthState(page);
      expect(await loginWithCredentialRetry(page, { username: user.username, password }, 2)).toBe(
        true
      );

      const walkthroughUnits = await fetchUnits(page, WALKTHROUGH_OWNER_ID);
      expect(walkthroughUnits.total).toBe(0);
      expect(walkthroughUnits.items).toHaveLength(0);
    } finally {
      await restoreAdminAndDeleteUsers(page, createdUserIds);
    }
  });
});
