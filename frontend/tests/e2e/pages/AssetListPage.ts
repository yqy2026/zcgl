import { Page, Locator, expect } from '@playwright/test';

export class AssetListPage {
  readonly page: Page;
  readonly searchInput: Locator;
  readonly searchButton: Locator;
  readonly resetButton: Locator;
  readonly tableRows: Locator;

  constructor(page: Page) {
    this.page = page;
    // Based on AssetSearch.tsx: Form.Item name="search"
    // Antd usually puts id as formName_fieldName if form has name, but in AssetSearch.tsx:
    // const [form] = Form.useForm(); ... <Form form={form}> ... <Form.Item name="search">
    // It doesn't look like the Form has a specific name prop in the snippet I read?
    // Wait, I saw <Form form={form} layout="vertical" ...> in AssetSearch.tsx. No name prop.
    // So inputs might use id="search" if antd decides, or just by name attribute.
    this.searchInput = page.locator('input[id="search"]');
    this.searchButton = page.getByRole('button', { name: '搜索', exact: true });
    this.resetButton = page.getByRole('button', { name: '重置' });
    this.tableRows = page.locator('.ant-table-row');
  }

  async goto() {
    await this.page.goto('/assets/list');
    await this.page.waitForLoadState('networkidle');
  }

  async search(keyword: string) {
    await this.searchInput.fill(keyword);
    await this.searchButton.click();
    // Wait for table to reload - usually a loading spinner or response
    await this.page.waitForLoadState('networkidle');
  }

  async getAssetCount() {
    return await this.tableRows.count();
  }

  async clickFirstAsset() {
    // In AssetList.tsx, the property name column has a button:
    // <Button type="link" onClick={() => onView(record)} ...>
    // We can target that.
    const firstRowNameLink = this.tableRows.first().locator('button.ant-btn-link').first();
    await firstRowNameLink.click();
    await this.page.waitForURL(/\/assets\/detail\//);
  }
}
