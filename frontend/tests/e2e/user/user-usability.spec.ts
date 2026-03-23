import { expect, test, type Locator, type Page } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';
import {
  LEGACY_CONTRACT_ROUTES,
  legacyContractRoutePattern,
} from '../helpers/legacyContract';

interface UsabilityRouteCase {
  path: string;
  urlPattern: RegExp;
  titlePattern: RegExp;
  readySelectors: string[];
}

const LEGACY_CONTRACT_RETIRED_TITLE_PATTERN = /租赁前端模块已退休/i;
const LEGACY_CONTRACT_RETIRED_READY_SELECTORS = ['.ant-result', '.ant-alert'];

const CORE_ROUTE_CASES: UsabilityRouteCase[] = [
  {
    path: '/dashboard',
    urlPattern: /\/dashboard/,
    titlePattern: /资产管理看板|工作台|仪表盘/i,
    readySelectors: ['.dashboardContainer', '.ant-card', '.errorContainer'],
  },
  {
    path: '/owner/assets',
    urlPattern: /\/owner\/assets$/,
    titlePattern: /资产列表|资产管理/i,
    readySelectors: ['.ant-table', '.ant-empty'],
  },
  {
    path: LEGACY_CONTRACT_ROUTES.LIST,
    urlPattern: legacyContractRoutePattern(LEGACY_CONTRACT_ROUTES.LIST),
    titlePattern: LEGACY_CONTRACT_RETIRED_TITLE_PATTERN,
    readySelectors: LEGACY_CONTRACT_RETIRED_READY_SELECTORS,
  },
  {
    path: '/manager/projects',
    urlPattern: /\/manager\/projects$/,
    titlePattern: /项目管理/i,
    readySelectors: ['.ant-table', '.ant-empty'],
  },
  {
    path: '/owner/property-certificates',
    urlPattern: /\/owner\/property-certificates$/,
    titlePattern: /产权证管理/i,
    readySelectors: ['.ant-table', '.ant-empty'],
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

  test('authenticated user can reach key creation entries and see retired contract entry state', async ({
    page,
  }) => {
    await page.goto('/owner/assets');
    await expect(page).toHaveURL(/\/owner\/assets$/);
    const createAssetButton = page.getByRole('button', { name: /新增资产/ }).first();
    if (await isLocatorVisible(createAssetButton)) {
      await createAssetButton.click();
    } else {
      await page.goto('/assets/new');
    }
    await expect(page).toHaveURL(/\/assets\/new/);
    await expect(page.getByRole('heading', { name: /新增资产|编辑资产/i })).toBeVisible();

    await page.goto(LEGACY_CONTRACT_ROUTES.LIST);
    await expect(page).toHaveURL(legacyContractRoutePattern(LEGACY_CONTRACT_ROUTES.LIST));
    await expect(page.getByText(/租赁前端模块已退休/i).first()).toBeVisible();
    await expect(page.getByText(/旧合同前端页面已下线/i).first()).toBeVisible();

    await page.goto('/manager/projects');
    await expect(page).toHaveURL(/\/manager\/projects$/);
    const createProjectButton = page.getByRole('button', { name: /新建项目/ }).first();
    await expect(createProjectButton).toBeVisible();
    await createProjectButton.click();
    await expect(page.getByRole('dialog', { name: /新建项目|编辑项目/i })).toBeVisible();

    await page.goto('/owner/property-certificates');
    await expect(page).toHaveURL(/\/owner\/property-certificates$/);
    const createCertificateButton = page.getByRole('button', { name: /新建产权证/ }).first();
    if (await isLocatorVisible(createCertificateButton)) {
      await createCertificateButton.click();
    } else {
      await page.goto('/property-certificates/import');
    }
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();
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
