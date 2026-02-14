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

  test('should block regular user from admin user page', async ({ page }) => {
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

    await page.goto('/system/users');

    const currentPath = new URL(page.url()).pathname;
    const redirectedByPath =
      currentPath.startsWith('/dashboard') ||
      currentPath.startsWith('/login') ||
      currentPath.startsWith('/403');

    const deniedByView = await page
      .locator('text=403, text=无权限, text=Access Denied')
      .first()
      .isVisible()
      .catch(() => false);

    expect(redirectedByPath || deniedByView).toBe(true);
  });
});
