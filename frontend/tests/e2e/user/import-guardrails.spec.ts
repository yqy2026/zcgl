import { expect, test, type Page, type Request } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';
import { LEGACY_CONTRACT_ROUTES, legacyContractRoutePattern } from '../helpers/legacyContract';

type FileInputScope = Page | { locator: Page['locator'] };

const uploadPlainTextFile = async (scope: FileInputScope, filename: string): Promise<void> => {
  const uploadInput = scope.locator('input[type="file"]').first();
  await uploadInput.setInputFiles({
    name: filename,
    mimeType: 'text/plain',
    buffer: Buffer.from('invalid-import-content'),
  });
};

const uploadOversizedPdfFile = async (scope: FileInputScope, filename: string): Promise<void> => {
  const uploadInput = scope.locator('input[type="file"]').first();
  await uploadInput.setInputFiles({
    name: filename,
    mimeType: 'application/pdf',
    buffer: Buffer.alloc((10 * 1024 * 1024) + 1, 0),
  });
};

const expectMessageVisible = async (page: Page, messagePattern: RegExp): Promise<void> => {
  const messageNotice = page
    .locator('.ant-message-notice-content')
    .filter({ hasText: messagePattern })
    .first();
  await expect(messageNotice).toBeVisible();
};

test.describe('@user-usable 导入入口校验', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('legacy contract list should expose retired state instead of excel import entry', async ({
    page,
  }) => {
    await page.goto(LEGACY_CONTRACT_ROUTES.LIST);
    await expect(page).toHaveURL(legacyContractRoutePattern(LEGACY_CONTRACT_ROUTES.LIST));
    await expect(page.getByRole('heading', { name: /租赁前端模块已退休/i })).toBeVisible();
    await expect(page.getByRole('button', { name: '导入Excel' })).toHaveCount(0);
    await expect(page.locator('input[type="file"]')).toHaveCount(0);
  });

  test('legacy contract list should direct users to active contract-group flows', async ({
    page,
  }) => {
    await page.goto(LEGACY_CONTRACT_ROUTES.LIST);
    await expect(page).toHaveURL(legacyContractRoutePattern(LEGACY_CONTRACT_ROUTES.LIST));
    await expect(page.getByRole('button', { name: '查看合同组' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'PDF导入' })).toBeVisible();
  });

  test('pdf import should reject non-pdf file before request', async ({ page }) => {
    await page.goto(LEGACY_CONTRACT_ROUTES.PDF_IMPORT);
    await expect(page).toHaveURL(legacyContractRoutePattern(LEGACY_CONTRACT_ROUTES.PDF_IMPORT));
    await expect(page.getByRole('heading', { name: /PDF合同智能导入/i })).toBeVisible();

    await uploadPlainTextFile(page, 'contract.txt');
    await expectMessageVisible(page, /只支持PDF文件格式/);
  });

  test('pdf import should not send upload request when file type is rejected', async ({ page }) => {
    await page.goto(LEGACY_CONTRACT_ROUTES.PDF_IMPORT);
    await expect(page).toHaveURL(legacyContractRoutePattern(LEGACY_CONTRACT_ROUTES.PDF_IMPORT));
    await expect(page.getByRole('heading', { name: /PDF合同智能导入/i })).toBeVisible();

    let uploadRequestCount = 0;
    const requestListener = (request: Request) => {
      if (request.method() === 'POST' && request.url().includes('/api/v1/pdf-import/upload')) {
        uploadRequestCount += 1;
      }
    };
    page.on('request', requestListener);
    try {
      await uploadPlainTextFile(page, 'contract.txt');
      await expectMessageVisible(page, /只支持PDF文件格式/);
      await page.waitForTimeout(500);
      expect(uploadRequestCount).toBe(0);
    } finally {
      page.off('request', requestListener);
    }
  });

  test('property certificate import should reject unsupported file type before request', async ({
    page,
  }) => {
    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    await uploadPlainTextFile(page, 'certificate.txt');
    await expectMessageVisible(page, /只支持 PDF、JPG、PNG 格式/);
  });

  test('property certificate import should not send request when file is oversized', async ({
    page,
  }) => {
    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    let uploadRequestCount = 0;
    const requestListener = (request: Request) => {
      if (
        request.method() === 'POST' &&
        request.url().includes('/api/v1/property-certificates/upload')
      ) {
        uploadRequestCount += 1;
      }
    };
    page.on('request', requestListener);
    try {
      await uploadOversizedPdfFile(page, 'oversized-certificate.pdf');
      await expectMessageVisible(page, /文件大小不能超过 10MB/);
      await page.waitForTimeout(500);
      expect(uploadRequestCount).toBe(0);
    } finally {
      page.off('request', requestListener);
    }
  });
});

test.describe('@user-usable 导入路由匿名拦截', () => {
  test('anonymous user should be redirected to login for import routes', async ({ page }) => {
    await clearAuthState(page);

    const protectedImportRoutes = [
      '/assets/import',
      LEGACY_CONTRACT_ROUTES.PDF_IMPORT,
      '/property-certificates/import',
    ];

    for (const route of protectedImportRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});
