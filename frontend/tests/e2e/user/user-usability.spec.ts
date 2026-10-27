import { expect, test, type Locator, type Page } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';

interface UsabilityRouteCase {
  path: string;
  urlPattern: RegExp;
  titlePattern: RegExp;
  readySelectors: string[];
}

const CORE_ROUTE_CASES: UsabilityRouteCase[] = [
  {
    path: '/asset-operations/units',
    urlPattern: /\/asset-operations\/units$/,
    titlePattern: /资产单元/,
    readySelectors: ['.ant-table', '.ant-empty', '.ant-alert'],
  },
  {
    path: '/asset-operations/contracts/upstream',
    urlPattern: /\/asset-operations\/contracts\/upstream$/,
    titlePattern: /上游合同/,
    readySelectors: ['.ant-table', '.ant-empty', '.ant-alert'],
  },
  {
    path: '/asset-operations/contracts/terminal',
    urlPattern: /\/asset-operations\/contracts\/terminal$/,
    titlePattern: /终端合同/,
    readySelectors: ['.ant-table', '.ant-empty', '.ant-alert'],
  },
  {
    path: '/asset-operations/contracts/intake',
    urlPattern: /\/asset-operations\/contracts\/intake$/,
    titlePattern: /录入已签合同/,
    readySelectors: ['input[type="file"]', 'button'],
  },
];

const isLocatorVisible = async (locator: Locator): Promise<boolean> =>
  await locator.isVisible().catch(() => false);

const hasVisibleSelector = async (page: Page, selectors: string[]): Promise<boolean> => {
  for (const selector of selectors) {
    const visible = await isLocatorVisible(page.locator(selector).first());
    if (visible) {
      return true;
    }
  }
  return false;
};

const waitForAppShell = async (page: Page): Promise<void> => {
  await page.waitForLoadState('domcontentloaded');
  const shellSelectors = ['[aria-label="主导航侧边栏"]', 'main', '#root'];
  const shellVisible = await hasVisibleSelector(page, shellSelectors);
  if (shellVisible) {
    return;
  }

  await page.waitForTimeout(1_000);
  const shellVisibleAfterWait = await hasVisibleSelector(page, shellSelectors);
  if (shellVisibleAfterWait) {
    return;
  }

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);
};

const assertRouteUsable = async (page: Page, routeCase: UsabilityRouteCase): Promise<void> => {
  await page.goto(routeCase.path);
  await expect(page).toHaveURL(routeCase.urlPattern);
  await waitForAppShell(page);
  await expect
    .poll(
      async () => {
        const headingVisible = await isLocatorVisible(
          page.getByRole('heading', { name: routeCase.titlePattern }).first()
        );
        const contentVisible = await hasVisibleSelector(page, routeCase.readySelectors);
        return headingVisible || contentVisible;
      },
      {
        timeout: 20_000,
        message: `route ${routeCase.path} should have visible heading or core content`,
      }
    )
    .toBe(true);
};

test.describe('@user-usable 用户可用性冒烟', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('authenticated user can access core business routes', async ({ page }) => {
    for (const routeCase of CORE_ROUTE_CASES) {
      await assertRouteUsable(page, routeCase);
    }
  });

  test('authenticated user can reach key creation entries', async ({ page }) => {
    await page.goto('/asset-operations/contracts/intake');
    await expect(page).toHaveURL(/\/asset-operations\/contracts\/intake$/);
    await expect(page.getByRole('heading', { name: '录入已签合同' })).toBeVisible();
    await expect(page.getByRole('button', { name: '终端合同' })).toBeVisible();
    await expect(page.getByLabel('已签扫描件（PDF/图片）')).toBeVisible();
  });
});

test.describe('@user-usable 匿名访问拦截', () => {
  test('anonymous user should be redirected to login for protected routes', async ({ page }) => {
    await clearAuthState(page);

    for (const routeCase of CORE_ROUTE_CASES) {
      await page.goto(routeCase.path);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});
