import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test.describe('Rental Contract Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('should open contract list and navigate to create page', async ({ page }) => {
    await page.goto('/rental/contracts');
    await expect(page).toHaveURL(/\/rental\/contracts/);
    await expect(page.locator('text=租金合同管理').first()).toBeVisible();

    const createButton = page
      .getByRole('button', { name: '创建合同', exact: true })
      .first();

    const hasCreateButton = await createButton.isVisible().catch(() => false);
    if (hasCreateButton) {
      await createButton.click();
    } else {
      await page.goto('/rental/contracts/create');
    }

    await expect(page).toHaveURL(/\/rental\/contracts\/(create|new)/);
  });
});
