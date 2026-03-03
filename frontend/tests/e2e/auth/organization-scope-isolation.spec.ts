import { expect, test, type APIResponse, type Page } from '@playwright/test';

import { clearAuthState, ensureAuthenticated, loginWithCredential } from '../helpers/auth';

interface PermissionItem {
  id: string;
  resource: string;
  action: string;
  name?: string;
}

interface UserItem {
  id: string;
  username: string;
  role_id?: string | null;
  is_admin?: boolean;
}

interface AssetItem {
  id: string;
  property_name: string;
  owner_party_id?: string | null;
}

interface RoleListItem {
  id: string;
  name: string;
  display_name?: string;
}

interface RoleDetailItem {
  id: string;
  permissions?: PermissionItem[];
}

interface PartyItem {
  id: string;
}

interface PartyPair {
  partyAId: string;
  partyBId: string;
}

interface AssetListResult {
  total: number;
  items: AssetItem[];
}

const READABLE_ACTIONS = new Set(['read', 'view', 'list', 'query', 'get']);
const FALLBACK_OWNERSHIP_STATUS = '已确权';
const FALLBACK_PROPERTY_NATURE = '经营类';
const FALLBACK_USAGE_STATUS = '自用';

const readNodeEnv = (name: string): string | undefined => {
  const rawValue = process.env[name];
  return typeof rawValue === 'string' && rawValue !== '' ? rawValue : undefined;
};

const normalizeNonEmpty = (value: unknown): string | null => {
  if (value == null) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized !== '' ? normalized : null;
};

const uniqueNonEmpty = (values: Array<string | null | undefined>): string[] => {
  const result: string[] = [];
  const seen = new Set<string>();

  for (const item of values) {
    const normalized = normalizeNonEmpty(item);
    if (normalized == null || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    result.push(normalized);
  }

  return result;
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

const buildPhone = (serial: number): string => {
  const suffix = String(serial % 1000000000).padStart(9, '0');
  return `13${suffix}`;
};

const resolveCsrfHeaders = async (page: Page): Promise<Record<string, string>> => {
  const csrfToken = await page.evaluate(() => {
    const csrfCookie = document.cookie
      .split('; ')
      .find(item => item.startsWith('csrf_token='));
    if (csrfCookie == null || csrfCookie === '') {
      return null;
    }
    return decodeURIComponent(csrfCookie.split('=').slice(1).join('='));
  });

  if (csrfToken == null || csrfToken === '') {
    return {};
  }
  return { 'X-CSRF-Token': csrfToken };
};

const parsePaginatedItems = <T>(payload: unknown): T[] => {
  const extracted = extractData<{ items?: unknown }>(payload);
  if (
    extracted != null &&
    typeof extracted === 'object' &&
    Array.isArray((extracted as { items?: unknown }).items)
  ) {
    return (extracted as { items: T[] }).items;
  }
  return [];
};

const parsePaginatedTotal = (payload: unknown): number => {
  const extracted = extractData<{ total?: unknown; items?: unknown }>(payload);
  if (extracted != null && typeof extracted === 'object') {
    const maybeTotal = (extracted as { total?: unknown }).total;
    if (typeof maybeTotal === 'number' && Number.isFinite(maybeTotal)) {
      return maybeTotal;
    }
    const maybeItems = (extracted as { items?: unknown }).items;
    if (Array.isArray(maybeItems)) {
      return maybeItems.length;
    }
  }
  return 0;
};

const readResponseSnippet = async (response: APIResponse): Promise<string> => {
  try {
    const rawText = await response.text();
    if (rawText.length <= 260) {
      return rawText;
    }
    return `${rawText.slice(0, 260)}...`;
  } catch {
    return '<unavailable>';
  }
};

const loginWithRetry = async (
  page: Page,
  credential: { username: string; password: string },
  attempts: number = 2
): Promise<boolean> => {
  let lastError: unknown = null;

  for (let index = 0; index < attempts; index += 1) {
    try {
      return await loginWithCredential(page, credential);
    } catch (error) {
      lastError = error;
      if (index + 1 >= attempts) {
        throw error;
      }
      await page.waitForTimeout(300);
    }
  }

  if (lastError instanceof Error) {
    throw lastError;
  }
  return false;
};

const resolveRoleCandidateIds = async (page: Page): Promise<string[]> => {
  const explicitRoleId = normalizeNonEmpty(readNodeEnv('E2E_SCOPE_ROLE_ID'));
  if (explicitRoleId != null) {
    return [explicitRoleId];
  }

  const roleIds: Array<string | null> = [];
  const rolesResponse = await page.request.get('/api/v1/roles?page=1&page_size=100');
  if (rolesResponse.status() === 200) {
    const rolesPayload = (await rolesResponse.json()) as unknown;
    const roleItems = parsePaginatedItems<RoleListItem>(rolesPayload);

    for (const role of roleItems) {
      const roleId = normalizeNonEmpty(role.id);
      if (roleId == null) {
        continue;
      }
      const roleName = `${role.name ?? ''} ${role.display_name ?? ''}`.toLowerCase();
      if (roleName.includes('admin') || roleName.includes('管理员')) {
        continue;
      }

      const roleDetailResponse = await page.request.get(`/api/v1/roles/${roleId}`);
      if (roleDetailResponse.status() !== 200) {
        continue;
      }

      const roleDetailPayload = (await roleDetailResponse.json()) as unknown;
      const roleDetail = extractData<RoleDetailItem>(roleDetailPayload);
      const permissions = Array.isArray(roleDetail.permissions)
        ? roleDetail.permissions
        : [];
      const hasAssetReadPermission = permissions.some(permission => {
        const resource = normalizeNonEmpty(permission.resource);
        const action = normalizeNonEmpty(permission.action)?.toLowerCase() ?? '';
        return resource === 'asset' && READABLE_ACTIONS.has(action);
      });
      if (hasAssetReadPermission) {
        roleIds.push(roleId);
      }
    }
  }

  const usersResponse = await page.request.get('/api/v1/auth/users?page=1&page_size=100');
  if (usersResponse.status() === 200) {
    const usersPayload = (await usersResponse.json()) as unknown;
    const userItems = parsePaginatedItems<UserItem>(usersPayload);

    for (const user of userItems) {
      if (user.is_admin === true) {
        continue;
      }
      roleIds.push(normalizeNonEmpty(user.role_id));
    }
  }

  return uniqueNonEmpty(roleIds);
};

const resolvePartyPair = async (
  page: Page,
  suffix: number,
  mutationHeaders: Record<string, string>
): Promise<PartyPair | null> => {
  const explicitPartyAId = normalizeNonEmpty(readNodeEnv('E2E_SCOPE_PARTY_A_ID'));
  const explicitPartyBId = normalizeNonEmpty(readNodeEnv('E2E_SCOPE_PARTY_B_ID'));

  if (
    explicitPartyAId != null &&
    explicitPartyBId != null &&
    explicitPartyAId === explicitPartyBId
  ) {
    throw new Error('E2E_SCOPE_PARTY_A_ID 与 E2E_SCOPE_PARTY_B_ID 不能相同。');
  }

  if (explicitPartyAId != null && explicitPartyBId != null) {
    return { partyAId: explicitPartyAId, partyBId: explicitPartyBId };
  }

  const candidatePartyIds: Array<string | null> = [explicitPartyAId, explicitPartyBId];
  const partiesResponse = await page.request.get('/api/v1/parties?limit=200');
  if (partiesResponse.status() === 200) {
    const partiesPayload = (await partiesResponse.json()) as unknown;
    const partyItems = extractData<PartyItem[] | unknown>(partiesPayload);
    if (Array.isArray(partyItems)) {
      for (const party of partyItems) {
        candidatePartyIds.push(normalizeNonEmpty((party as PartyItem).id));
      }
    }
  }

  let dedupedPartyIds = uniqueNonEmpty(candidatePartyIds);
  if (dedupedPartyIds.length < 2) {
    const missingCount = 2 - dedupedPartyIds.length;
    for (let i = 0; i < missingCount; i += 1) {
      const createPartyResponse = await page.request.post('/api/v1/parties', {
        headers: mutationHeaders,
        data: {
          party_type: 'organization',
          name: `E2E Scope Party ${suffix}-${i + 1}`,
          code: `E2E_SCOPE_${suffix}_${i + 1}`,
          status: 'active',
        },
      });
      if (createPartyResponse.status() !== 200 && createPartyResponse.status() !== 201) {
        continue;
      }
      const createPartyPayload = (await createPartyResponse.json()) as unknown;
      const createdParty = extractData<PartyItem>(createPartyPayload);
      candidatePartyIds.push(normalizeNonEmpty(createdParty.id));
    }
  }

  dedupedPartyIds = uniqueNonEmpty(candidatePartyIds);
  if (dedupedPartyIds.length < 2) {
    const assetsResponse = await page.request.get('/api/v1/assets?page=1&page_size=200');
    if (assetsResponse.status() === 200) {
      const assetsPayload = (await assetsResponse.json()) as unknown;
      const assetItems = parsePaginatedItems<AssetItem>(assetsPayload);
      for (const asset of assetItems) {
        candidatePartyIds.push(normalizeNonEmpty(asset.owner_party_id));
      }
    }
  }

  dedupedPartyIds = uniqueNonEmpty(candidatePartyIds);
  if (dedupedPartyIds.length < 2) {
    return null;
  }

  if (explicitPartyAId != null) {
    const partyBId = dedupedPartyIds.find(item => item !== explicitPartyAId);
    if (partyBId == null) {
      return null;
    }
    return { partyAId: explicitPartyAId, partyBId };
  }

  if (explicitPartyBId != null) {
    const partyAId = dedupedPartyIds.find(item => item !== explicitPartyBId);
    if (partyAId == null) {
      return null;
    }
    return { partyAId, partyBId: explicitPartyBId };
  }

  return {
    partyAId: dedupedPartyIds[0],
    partyBId: dedupedPartyIds[1],
  };
};

const fetchAssetsByOwnership = async (
  page: Page,
  partyId: string
): Promise<AssetListResult | null> => {
  const response = await page.request.get(
    `/api/v1/assets?page=1&page_size=100&ownership_id=${encodeURIComponent(partyId)}`
  );
  if (response.status() !== 200) {
    return null;
  }

  const payload = (await response.json()) as unknown;
  return {
    total: parsePaginatedTotal(payload),
    items: parsePaginatedItems<AssetItem>(payload),
  };
};

const tryCreateAssetForParty = async (
  page: Page,
  partyId: string,
  suffix: number,
  label: string,
  mutationHeaders: Record<string, string>
): Promise<boolean> => {
  const response = await page.request.post('/api/v1/assets', {
    headers: mutationHeaders,
    data: {
      property_name: `E2E Scope Asset ${label} ${suffix}`,
      address: `E2E Scope Address ${label} ${suffix}`,
      ownership_status: FALLBACK_OWNERSHIP_STATUS,
      property_nature: FALLBACK_PROPERTY_NATURE,
      usage_status: FALLBACK_USAGE_STATUS,
      owner_party_id: partyId,
      manager_party_id: partyId,
    },
  });

  return response.status() === 201;
};

test.describe('@authz-org-scope New User Organization Scope Isolation', () => {
  test('newly created users should only see assets bound to their own party scope', async ({
    page,
  }) => {
    await ensureAuthenticated(page);
    const createdUserIds: string[] = [];

    const suffix = Date.now();
    const sharedPassword = `Aa!${suffix}`;
    const mutationHeaders = await resolveCsrfHeaders(page);
    const explicitRoleId = normalizeNonEmpty(readNodeEnv('E2E_SCOPE_ROLE_ID'));
    const hasExplicitPartyPair =
      normalizeNonEmpty(readNodeEnv('E2E_SCOPE_PARTY_A_ID')) != null &&
      normalizeNonEmpty(readNodeEnv('E2E_SCOPE_PARTY_B_ID')) != null;

    test.skip(
      Object.keys(mutationHeaders).length === 0,
      'Authenticated session has no csrf_token cookie; cannot run mutation setup.'
    );
    if (Object.keys(mutationHeaders).length === 0) {
      return;
    }

    const roleCandidateIds = await resolveRoleCandidateIds(page);
    test.skip(
      roleCandidateIds.length === 0,
      'No available role candidates. Set E2E_SCOPE_ROLE_ID for deterministic run.'
    );
    if (roleCandidateIds.length === 0) {
      return;
    }

    const partyPair = await resolvePartyPair(page, suffix, mutationHeaders);
    test.skip(
      partyPair == null,
      'No available party pair. Set E2E_SCOPE_PARTY_A_ID and E2E_SCOPE_PARTY_B_ID.'
    );
    if (partyPair == null) {
      return;
    }

    let scopedPartyAId = partyPair.partyAId;
    let scopedPartyBId = partyPair.partyBId;

    let adminAssetsForPartyA = await fetchAssetsByOwnership(page, scopedPartyAId);
    let adminAssetsForPartyB = await fetchAssetsByOwnership(page, scopedPartyBId);
    test.skip(
      adminAssetsForPartyA == null || adminAssetsForPartyB == null,
      'Current session cannot read assets list for configured parties.'
    );
    if (adminAssetsForPartyA == null || adminAssetsForPartyB == null) {
      return;
    }

    if (adminAssetsForPartyA.total === 0) {
      await tryCreateAssetForParty(page, scopedPartyAId, suffix, 'A', mutationHeaders);
    }
    if (adminAssetsForPartyB.total === 0) {
      await tryCreateAssetForParty(page, scopedPartyBId, suffix, 'B', mutationHeaders);
    }

    let refreshedAdminAssetsForPartyA = await fetchAssetsByOwnership(page, scopedPartyAId);
    let refreshedAdminAssetsForPartyB = await fetchAssetsByOwnership(page, scopedPartyBId);
    test.skip(
      refreshedAdminAssetsForPartyA == null || refreshedAdminAssetsForPartyB == null,
      'Cannot confirm post-setup asset totals for configured parties.'
    );
    if (refreshedAdminAssetsForPartyA == null || refreshedAdminAssetsForPartyB == null) {
      return;
    }

    if (
      refreshedAdminAssetsForPartyA.total === 0 &&
      refreshedAdminAssetsForPartyB.total === 0
    ) {
      const assetsResponse = await page.request.get('/api/v1/assets?page=1&page_size=200');
      if (assetsResponse.status() === 200) {
        const assetsPayload = (await assetsResponse.json()) as unknown;
        const ownerPartyIds = uniqueNonEmpty(
          parsePaginatedItems<AssetItem>(assetsPayload).map(item =>
            normalizeNonEmpty(item.owner_party_id)
          )
        );
        if (ownerPartyIds.length > 0) {
          const fallbackPartyAId = ownerPartyIds[0];
          const fallbackPartyBId =
            ownerPartyIds.find(item => item !== fallbackPartyAId) ??
            [scopedPartyAId, scopedPartyBId].find(item => item !== fallbackPartyAId) ??
            null;
          if (fallbackPartyBId != null) {
            scopedPartyAId = fallbackPartyAId;
            scopedPartyBId = fallbackPartyBId;

            adminAssetsForPartyA = await fetchAssetsByOwnership(page, scopedPartyAId);
            adminAssetsForPartyB = await fetchAssetsByOwnership(page, scopedPartyBId);
            if (adminAssetsForPartyA != null && adminAssetsForPartyA.total === 0) {
              await tryCreateAssetForParty(
                page,
                scopedPartyAId,
                suffix,
                'A-Fallback',
                mutationHeaders
              );
            }
            if (adminAssetsForPartyB != null && adminAssetsForPartyB.total === 0) {
              await tryCreateAssetForParty(
                page,
                scopedPartyBId,
                suffix,
                'B-Fallback',
                mutationHeaders
              );
            }
            refreshedAdminAssetsForPartyA = await fetchAssetsByOwnership(
              page,
              scopedPartyAId
            );
            refreshedAdminAssetsForPartyB = await fetchAssetsByOwnership(
              page,
              scopedPartyBId
            );
          }
        }
      }
    }

    if (
      refreshedAdminAssetsForPartyA == null ||
      refreshedAdminAssetsForPartyB == null
    ) {
      test.skip(true, 'Cannot confirm post-fallback asset totals for party scopes.');
      return;
    }

    if (
      refreshedAdminAssetsForPartyA.total === 0 &&
      refreshedAdminAssetsForPartyB.total === 0
    ) {
      if (hasExplicitPartyPair) {
        throw new Error(
          [
            `Configured party A (${scopedPartyAId}) total=0, party B (${scopedPartyBId}) total=0.`,
            'Please provide parties that contain assets, or grant asset create permission for test setup.',
          ].join(' ')
        );
      }
      test.skip(
        true,
        'Both party scopes have zero assets and setup cannot seed data in this environment.'
      );
      return;
    }

    try {
      let selectedRoleId: string | null = null;
      let userA: UserItem | null = null;
      const createUserErrors: string[] = [];

      for (const roleId of roleCandidateIds) {
        const createUserAResponse = await page.request.post('/api/v1/auth/users', {
          headers: mutationHeaders,
          data: {
            username: `e2e_scope_a_${suffix}`,
            full_name: `E2E Scope A ${suffix}`,
            email: `e2e.scope.a.${suffix}@example.com`,
            phone: buildPhone(suffix + 1),
            password: sharedPassword,
            role_id: roleId,
          },
        });

        if (createUserAResponse.status() !== 200) {
          const errorSnippet = await readResponseSnippet(createUserAResponse);
          createUserErrors.push(
            `[role_id=${roleId}] status=${createUserAResponse.status()} body=${errorSnippet}`
          );
          continue;
        }

        const userPayload = (await createUserAResponse.json()) as unknown;
        const createdUser = extractData<UserItem>(userPayload);
        const createdUserId = normalizeNonEmpty(createdUser.id);
        const createdUsername = normalizeNonEmpty(createdUser.username);
        if (createdUserId == null || createdUsername == null) {
          createUserErrors.push(`[role_id=${roleId}] status=200 but user payload invalid`);
          continue;
        }

        createdUserIds.push(createdUserId);
        userA = {
          ...createdUser,
          id: createdUserId,
          username: createdUsername,
        };
        selectedRoleId = roleId;
        break;
      }

      if (userA == null || selectedRoleId == null) {
        if (explicitRoleId != null) {
          throw new Error(
            [
              `E2E_SCOPE_ROLE_ID=${explicitRoleId} cannot create scoped user.`,
              `Errors: ${createUserErrors.join(' | ')}`,
            ].join(' ')
          );
        }
        test.skip(
          true,
          `No role candidate can create scoped users. ${createUserErrors.join(' | ')}`
        );
        return;
      }

      const userBResponse = await page.request.post('/api/v1/auth/users', {
        headers: mutationHeaders,
        data: {
          username: `e2e_scope_b_${suffix}`,
          full_name: `E2E Scope B ${suffix}`,
          email: `e2e.scope.b.${suffix}@example.com`,
          phone: buildPhone(suffix + 2),
          password: sharedPassword,
          role_id: selectedRoleId,
        },
      });
      if (userBResponse.status() !== 200) {
        const errorSnippet = await readResponseSnippet(userBResponse);
        throw new Error(
          `Failed to create user B with role ${selectedRoleId}, status=${userBResponse.status()}, body=${errorSnippet}`
        );
      }
      const userBPayload = (await userBResponse.json()) as unknown;
      const userB = extractData<UserItem>(userBPayload);
      const userBId = normalizeNonEmpty(userB.id);
      if (userBId != null) {
        createdUserIds.push(userBId);
      }

      const bindAResponse = await page.request.post(`/api/v1/users/${userA.id}/party-bindings`, {
        headers: mutationHeaders,
        data: {
          party_id: scopedPartyAId,
          relation_type: 'owner',
          is_primary: true,
        },
      });
      if (bindAResponse.status() !== 201) {
        const errorSnippet = await readResponseSnippet(bindAResponse);
        throw new Error(
          `Failed to bind user A, status=${bindAResponse.status()}, body=${errorSnippet}`
        );
      }

      const bindBResponse = await page.request.post(`/api/v1/users/${userB.id}/party-bindings`, {
        headers: mutationHeaders,
        data: {
          party_id: scopedPartyBId,
          relation_type: 'owner',
          is_primary: true,
        },
      });
      if (bindBResponse.status() !== 201) {
        const errorSnippet = await readResponseSnippet(bindBResponse);
        throw new Error(
          `Failed to bind user B, status=${bindBResponse.status()}, body=${errorSnippet}`
        );
      }

      const assertScopedVisibility = async ({
        username,
        ownPartyId,
        otherPartyId,
        expectOwnOwnershipAssets,
      }: {
        username: string;
        ownPartyId: string;
        otherPartyId: string;
        expectOwnOwnershipAssets: boolean;
      }): Promise<void> => {
        await clearAuthState(page);
        const loginOk = await loginWithRetry(
          page,
          {
            username,
            password: sharedPassword,
          },
          2
        );
        expect(loginOk).toBe(true);

        const ownResponse = await page.request.get(
          `/api/v1/assets?page=1&page_size=100&ownership_id=${encodeURIComponent(ownPartyId)}`
        );
        expect(ownResponse.status()).toBe(200);
        const ownPayload = (await ownResponse.json()) as unknown;
        const ownTotal = parsePaginatedTotal(ownPayload);
        if (expectOwnOwnershipAssets) {
          expect(ownTotal).toBeGreaterThan(0);
        } else {
          expect(ownTotal).toBe(0);
        }

        const otherResponse = await page.request.get(
          `/api/v1/assets?page=1&page_size=100&ownership_id=${encodeURIComponent(otherPartyId)}`
        );
        expect(otherResponse.status()).toBe(200);
        const otherPayload = (await otherResponse.json()) as unknown;
        const otherTotal = parsePaginatedTotal(otherPayload);
        expect(otherTotal).toBe(0);
        const otherItems = parsePaginatedItems<AssetItem>(otherPayload);
        expect(otherItems).toHaveLength(0);

        const unfilteredResponse = await page.request.get('/api/v1/assets?page=1&page_size=100');
        expect(unfilteredResponse.status()).toBe(200);
        const unfilteredPayload = (await unfilteredResponse.json()) as unknown;
        const unfilteredItems = parsePaginatedItems<AssetItem>(unfilteredPayload);
        const ownerPartyIds = new Set(
          unfilteredItems
            .map(item => normalizeNonEmpty(item.owner_party_id))
            .filter((item): item is string => item != null)
        );
        expect(ownerPartyIds.has(otherPartyId)).toBe(false);
      };

      await assertScopedVisibility({
        username: userA.username,
        ownPartyId: scopedPartyAId,
        otherPartyId: scopedPartyBId,
        expectOwnOwnershipAssets: refreshedAdminAssetsForPartyA.total > 0,
      });

      await assertScopedVisibility({
        username: userB.username,
        ownPartyId: scopedPartyBId,
        otherPartyId: scopedPartyAId,
        expectOwnOwnershipAssets: refreshedAdminAssetsForPartyB.total > 0,
      });
    } finally {
      if (createdUserIds.length === 0) {
        return;
      }

      try {
        await clearAuthState(page);
        await ensureAuthenticated(page);
        const cleanupHeaders = await resolveCsrfHeaders(page);
        if (Object.keys(cleanupHeaders).length === 0) {
          return;
        }

        const dedupedUserIds = uniqueNonEmpty(createdUserIds);
        for (const userId of dedupedUserIds) {
          await page.request.delete(`/api/v1/auth/users/${userId}`, {
            headers: cleanupHeaders,
          });
        }
      } catch {
        // Best-effort cleanup; assertion results should not be masked by cleanup failure.
      }
    }
  });

  test('newly created users without party bindings should be fail-closed on assets list', async ({
    page,
  }) => {
    await ensureAuthenticated(page);
    const createdUserIds: string[] = [];

    const suffix = Date.now();
    const sharedPassword = `Aa!${suffix}`;
    const mutationHeaders = await resolveCsrfHeaders(page);

    test.skip(
      Object.keys(mutationHeaders).length === 0,
      'Authenticated session has no csrf_token cookie; cannot run mutation setup.'
    );
    if (Object.keys(mutationHeaders).length === 0) {
      return;
    }

    const roleCandidateIds = await resolveRoleCandidateIds(page);
    test.skip(
      roleCandidateIds.length === 0,
      'No available role candidates to create non-admin scoped user.'
    );
    if (roleCandidateIds.length === 0) {
      return;
    }

    try {
      let createdUser: UserItem | null = null;
      const createUserErrors: string[] = [];

      for (const roleId of roleCandidateIds) {
        const createUserResponse = await page.request.post('/api/v1/auth/users', {
          headers: mutationHeaders,
          data: {
            username: `e2e_scope_unbound_${suffix}`,
            full_name: `E2E Scope Unbound ${suffix}`,
            email: `e2e.scope.unbound.${suffix}@example.com`,
            phone: buildPhone(suffix + 3),
            password: sharedPassword,
            role_id: roleId,
          },
        });

        if (createUserResponse.status() !== 200) {
          const errorSnippet = await readResponseSnippet(createUserResponse);
          createUserErrors.push(
            `[role_id=${roleId}] status=${createUserResponse.status()} body=${errorSnippet}`
          );
          continue;
        }

        const payload = (await createUserResponse.json()) as unknown;
        const user = extractData<UserItem>(payload);
        const userId = normalizeNonEmpty(user.id);
        const username = normalizeNonEmpty(user.username);
        if (userId == null || username == null) {
          createUserErrors.push(`[role_id=${roleId}] status=200 but user payload invalid`);
          continue;
        }

        createdUser = {
          ...user,
          id: userId,
          username,
        };
        createdUserIds.push(userId);
        break;
      }

      test.skip(
        createdUser == null,
        `Unable to create unbound non-admin user. ${createUserErrors.join(' | ')}`
      );
      if (createdUser == null) {
        return;
      }

      await clearAuthState(page);
      const loginOk = await loginWithRetry(
        page,
        {
          username: createdUser.username,
          password: sharedPassword,
        },
        2
      );
      expect(loginOk).toBe(true);

      const unfilteredResponse = await page.request.get('/api/v1/assets?page=1&page_size=100');
      expect([200, 403]).toContain(unfilteredResponse.status());
      if (unfilteredResponse.status() === 200) {
        const unfilteredPayload = (await unfilteredResponse.json()) as unknown;
        const unfilteredTotal = parsePaginatedTotal(unfilteredPayload);
        const unfilteredItems = parsePaginatedItems<AssetItem>(unfilteredPayload);
        expect(unfilteredTotal).toBe(0);
        expect(unfilteredItems).toHaveLength(0);
      }

      const partiesResponse = await page.request.get('/api/v1/parties?limit=5');
      if (partiesResponse.status() === 200) {
        const partiesPayload = (await partiesResponse.json()) as unknown;
        const parties = extractData<PartyItem[] | unknown>(partiesPayload);
        const firstPartyId =
          Array.isArray(parties) && parties.length > 0
            ? normalizeNonEmpty((parties[0] as PartyItem).id)
            : null;
        if (firstPartyId != null) {
          const filteredResponse = await page.request.get(
            `/api/v1/assets?page=1&page_size=100&ownership_id=${encodeURIComponent(firstPartyId)}`
          );
          expect([200, 403]).toContain(filteredResponse.status());
          if (filteredResponse.status() === 200) {
            const filteredPayload = (await filteredResponse.json()) as unknown;
            const filteredTotal = parsePaginatedTotal(filteredPayload);
            const filteredItems = parsePaginatedItems<AssetItem>(filteredPayload);
            expect(filteredTotal).toBe(0);
            expect(filteredItems).toHaveLength(0);
          }
        }
      }
    } finally {
      if (createdUserIds.length === 0) {
        return;
      }

      try {
        await clearAuthState(page);
        await ensureAuthenticated(page);
        const cleanupHeaders = await resolveCsrfHeaders(page);
        if (Object.keys(cleanupHeaders).length === 0) {
          return;
        }

        const dedupedUserIds = uniqueNonEmpty(createdUserIds);
        for (const userId of dedupedUserIds) {
          await page.request.delete(`/api/v1/auth/users/${userId}`, {
            headers: cleanupHeaders,
          });
        }
      } catch {
        // Best-effort cleanup; assertion results should not be masked by cleanup failure.
      }
    }
  });
});
