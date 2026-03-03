import { expect, test } from '@playwright/test';

import { clearAuthState } from '../helpers/auth';

test.describe('@authz-minimal', () => {
  test('allow: anonymous user can access login page', async ({ page }) => {
    await clearAuthState(page);
    await expect(page).toHaveURL(/\/login/);
  });

  test('deny: anonymous user is redirected when accessing admin route', async ({
    page,
  }) => {
    await clearAuthState(page);
    await page.goto('/system/users');
    await expect(page).toHaveURL(/\/login/);
  });
});
