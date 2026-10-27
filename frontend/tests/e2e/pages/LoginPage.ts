import type { Locator, Page } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.locator('input#login_username'); // Antd Form.Item name="username" usually generates id="login_username" if form name is "login"
    this.passwordInput = page.locator('input#login_password');
    this.loginButton = page.locator('button[type="submit"]');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(username: string, password: string) {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
    // v5 登录后的唯一生产落点是资产单元。
    await this.page.waitForURL('**/asset-operations/units');
  }
}
