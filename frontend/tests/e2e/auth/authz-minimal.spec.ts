import { test, expect } from '@playwright/test';

test.describe('@authz-minimal', () => {
  test('skeleton: capability guard wiring baseline', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\//);
  });
});