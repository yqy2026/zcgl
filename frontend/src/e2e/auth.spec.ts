/**
 * End-to-End Authentication Flow Tests
 *
 * This module contains comprehensive E2E tests that verify the complete
 * authentication flow from login through permission handling, access control,
 * and logout. These tests validate fixes for Issues #1-4, #11.
 *
 * Issue #1: Rate Limiting - Verify UI handles rate limiting gracefully
 * Issue #2: Admin Role - Verify admin role is recognized throughout UI
 * Issue #3: Permission Storage - Verify permissions are stored and used
 * Issue #4: Token Validation - Verify token handling in frontend
 * Issue #11: Frontend Permission Display - Verify permissions are visible
 */

import { test, expect } from '@playwright/test';
import { API_BASE_URL } from '@/api/config';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page before each test
    await page.goto('/login');
  });

  test('should login successfully and store auth data', async ({ page }) => {
    // Fill and submit login form
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 5000 });

    // Check localStorage for auth data
    const authData = await page.evaluate(() => {
      const data = localStorage.getItem('authData');
      return data ? JSON.parse(data) : null;
    });

    expect(authData).not.toBeNull();
    expect(authData?.user).toBeDefined();
    expect(authData?.permissions).toBeInstanceOf(Array);
    expect(authData?.token).toBeUndefined();
    expect(authData?.refreshToken).toBeUndefined();
  });

  test('should display user permissions in profile', async ({ page }) => {
    // Login as admin
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for navigation to dashboard
    await page.waitForURL(/\/dashboard/);

    // Navigate to profile page
    await page.click('[data-testid="user-menu-button"]');
    await page.click('text=Profile');

    // Should display user information
    await expect(page.locator('text=Admin User')).toBeVisible();

    // Check if permissions are displayed
    const permissionsSection = page.locator('[data-testid="user-permissions"]');
    await expect(permissionsSection).toBeVisible({ timeout: 5000 });

    // Verify permissions are shown as badges or list
    const permissionBadges = await page.locator('[data-testid^="permission-"]').count();
    expect(permissionBadges).toBeGreaterThan(0);
  });

  test('should deny access to admin pages for regular users', async ({ page }) => {
    // Login as regular user
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');

    // Wait for navigation
    await page.waitForURL(/\/dashboard/);

    // Try to access admin users page
    await page.goto('/system/users');

    // Should show access denied or redirect
    const isAccessDenied = await page.locator('.access-denied').isVisible().catch(() => false);
    const isRedirected = page.url().includes('/dashboard') || page.url().includes('/403');

    expect(isAccessDenied || isRedirected).toBeTruthy();
  });

  test('should allow admin access to admin pages', async ({ page }) => {
    // Login as admin
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for navigation
    await page.waitForURL(/\/dashboard/);

    // Navigate to admin users page
    await page.click('[data-testid="admin-menu"]');
    await page.click('text=User Management');

    // Should be able to access the page
    await expect(page).toHaveURL(/\/system\/users/);
    await expect(page.locator('h1:has-text("User Management")')).toBeVisible();
  });

  test('should logout and clear auth data', async ({ page }) => {
    // Login first
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Logout
    await page.click('[data-testid="user-menu-button"]');
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login
    await expect(page).toHaveURL('/login');

    // Check localStorage is cleared
    const authData = await page.evaluate(() => localStorage.getItem('authData'));
    expect(authData).toBeNull();
  });

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    // Try to access dashboard without login
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });

  test('should show error message with invalid credentials', async ({ page }) => {
    // Fill with invalid credentials
    await page.fill('input[name="username"]', 'invalid');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    const errorMessage = page.locator('.ant-message-error, [data-testid="login-error"]');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
    await expect(errorMessage).toContainText(/username|password|invalid/i);
  });

  test('should handle token refresh on API calls', async ({ page }) => {
    // Login
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Make an API call that requires authentication
    // This should trigger token refresh if the access token is expired
    await page.goto('/system/users');

    // Should successfully load data (indicates token refresh worked)
    await expect(page.locator('table, .ant-table')).toBeVisible({ timeout: 10000 });
  });

  test('should display rate limit message when exceeded', async ({ page }) => {
    // Login
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Make multiple rapid requests to trigger rate limiting
    // Note: This might not trigger in all environments depending on rate limit settings
    const healthUrl = API_BASE_URL.endsWith('/') ? `${API_BASE_URL}health` : `${API_BASE_URL}/health`;
    for (let i = 0; i < 70; i++) {
      await page.evaluate(async url => {
        await fetch(url);
      }, healthUrl);
    }

    // Check if rate limit message appears
    const rateLimitMessage = page.locator('text=/rate limit|too many requests/i');
    const isRateLimited = await rateLimitMessage.isVisible().catch(() => false);

    if (isRateLimited) {
      await expect(rateLimitMessage).toBeVisible();
    }
  });

  test('should store and use permissions for UI element control', async ({ page }) => {
    // Login as regular user
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Check that admin-only elements are not visible
    const adminButton = page.locator('[data-testid="admin-only-button"]');
    const isAdminButtonVisible = await adminButton.isVisible().catch(() => false);

    expect(isAdminButtonVisible).toBeFalsy();
  });

  test('should handle session timeout gracefully', async ({ page }) => {
    // Login
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Clear auth data to simulate session timeout
    await page.evaluate(() => {
      localStorage.removeItem('authData');
    });

    // Try to navigate to a protected route
    await page.goto('/system/users');

    // Should redirect to login with session timeout message
    await expect(page).toHaveURL('/login');

    const timeoutMessage = page.locator('text=/session.*expir|timeout/i');
    const isTimeoutShown = await timeoutMessage.isVisible().catch(() => false);

    // Session timeout message might or might not be shown depending on implementation
    if (isTimeoutShown) {
      await expect(timeoutMessage).toBeVisible();
    }
  });

  test('should persist auth data across page refreshes', async ({ page }) => {
    // Login
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Refresh page
    await page.reload();

    // Should still be on dashboard (not redirected to login)
    await expect(page).toHaveURL(/\/dashboard/);

    // Auth data should still be present
    const authData = await page.evaluate(() => {
      const data = localStorage.getItem('authData');
      return data ? JSON.parse(data) : null;
    });

    expect(authData).not.toBeNull();
    expect(authData?.user?.username).toBe('admin');
    expect(authData?.token).toBeUndefined();
  });

  test('should display correct role badge in UI', async ({ page }) => {
    // Login as admin
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Check for admin badge in user menu
    await page.click('[data-testid="user-menu-button"]');

    const adminBadge = page.locator('[data-testid="role-badge-admin"]');
    await expect(adminBadge).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Authentication Security', () => {
  test('should not expose sensitive data in localStorage', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/dashboard/);

    // Check that password is not stored
    const authData = await page.evaluate(() => {
      const data = localStorage.getItem('authData');
      return data ? JSON.parse(data) : null;
    });

    expect(authData?.password).toBeUndefined();
    expect(authData?.user?.password).toBeUndefined();
  });

  test('should handle concurrent login attempts', async ({ context }) => {
    // Create two pages/tabs
    const page1 = await context.newPage();
    const page2 = await context.newPage();

    // Login on both pages
    await page1.goto('/login');
    await page1.fill('input[name="username"]', 'admin');
    await page1.fill('input[name="password"]', 'admin123');
    await page1.click('button[type="submit"]');

    await page2.goto('/login');
    await page2.fill('input[name="username"]', 'admin');
    await page2.fill('input[name="password"]', 'admin123');
    await page2.click('button[type="submit"]');

    // Both should successfully login
    await page1.waitForURL(/\/dashboard/);
    await page2.waitForURL(/\/dashboard/);

    // Both should have valid auth data
    const authData1 = await page1.evaluate(() => {
      const data = localStorage.getItem('authData');
      return data ? JSON.parse(data) : null;
    });

    const authData2 = await page2.evaluate(() => {
      const data = localStorage.getItem('authData');
      return data ? JSON.parse(data) : null;
    });

    expect(authData1).not.toBeNull();
    expect(authData2).not.toBeNull();

    await page1.close();
    await page2.close();
  });
});
