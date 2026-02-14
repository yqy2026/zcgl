import { expect, test } from '@playwright/test';
import {
  clearAuthState,
  loginAsAdmin,
  loginWithCredential,
  resolveLogoutCredential,
} from '../helpers/auth';

test.describe('Authentication Flow', () => {
  const logoutCredential = resolveLogoutCredential();

  test.beforeEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should login and redirect to dashboard', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should keep login page for invalid credentials', async ({ page }) => {
    const success = await loginWithCredential(page, {
      username: 'invalid-user',
      password: 'invalid-password',
    });

    expect(success).toBe(false);
    await expect(page).toHaveURL(/\/login/);
  });

  test('should persist session after page refresh', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page).toHaveURL(/\/dashboard/);

    await page.reload();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should revoke session after logout endpoint call', async ({ page }) => {
    test.skip(
      logoutCredential == null,
      'Set E2E_LOGOUT_USERNAME and E2E_LOGOUT_PASSWORD to isolate logout revocation test.'
    );

    if (logoutCredential == null) {
      return;
    }

    const loginSuccess = await loginWithCredential(page, logoutCredential);
    expect(loginSuccess).toBe(true);
    await expect(page).toHaveURL(/\/dashboard/);

    const csrfToken = await page.evaluate(() => {
      const csrfCookie = document.cookie
        .split('; ')
        .find(item => item.startsWith('csrf_token='));
      if (csrfCookie == null || csrfCookie === '') {
        return null;
      }
      return decodeURIComponent(csrfCookie.split('=').slice(1).join('='));
    });

    const headers: Record<string, string> = {};
    if (csrfToken != null && csrfToken !== '') {
      headers['X-CSRF-Token'] = csrfToken;
    }

    const response = await page.request.post('/api/v1/auth/logout', { headers });
    expect(response.ok()).toBe(true);

    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
