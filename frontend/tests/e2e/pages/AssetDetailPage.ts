import { Page, Locator, expect } from '@playwright/test';

export class AssetDetailPage {
  readonly page: Page;
  readonly pageTitle: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1, .ant-typography-h1, .ant-page-header-heading-title');
  }

  async verifyLoaded() {
    await expect(this.page).toHaveURL(/\/assets\/detail\//);
    // Add specific checks for asset detail content
    // Assuming there are descriptions or tabs
    await expect(this.page.locator('.ant-descriptions')).toBeVisible();
  }
}
