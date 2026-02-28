import { expect, test } from '@playwright/test';

import {
  clearAuthState,
  loginWithCredential,
  resolveRegularCredential,
} from '../helpers/auth';

test.describe('Access Control', () => {
  test('should redirect anonymous users to login', async ({ page }) => {
    await clearAuthState(page);
    await page.goto('/system/users');
    await expect(page).toHaveURL(/\/login/);
  });

  const regularCredential = resolveRegularCredential();

  test('should reject regular user from admin-only API', async ({ page }) => {
    test.skip(
      regularCredential == null,
      'Set E2E_REGULAR_USERNAME and E2E_REGULAR_PASSWORD to run this test.'
    );

    if (regularCredential == null) {
      return;
    }

    await clearAuthState(page);
    const success = await loginWithCredential(page, regularCredential);
    if (!success) {
      await expect(page).toHaveURL(/\/login/);
      return;
    }

    const response = await page.request.get('/api/v1/system/backup/stats');
    expect([401, 403]).toContain(response.status());
  });
});
