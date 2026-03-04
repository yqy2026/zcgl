import { expect, test, type Page, type Request } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';

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

  test('contract excel import should reject non-excel file before request', async ({ page }) => {
    await page.goto('/rental/contracts');
    await expect(page).toHaveURL(/\/rental\/contracts/);

    await page.getByRole('button', { name: '导入Excel' }).first().click();
    const importModal = page.getByRole('dialog', { name: /导入Excel文件/i });
    await expect(importModal).toBeVisible();

    await uploadPlainTextFile(importModal, 'contracts.txt');
    await expectMessageVisible(page, /请选择Excel文件（\.xlsx或\.xls格式）/);
    await expect(importModal).toBeVisible();
  });

  test('contract excel import should not send request when file type is rejected', async ({
    page,
  }) => {
    await page.goto('/rental/contracts');
    await expect(page).toHaveURL(/\/rental\/contracts/);

    await page.getByRole('button', { name: '导入Excel' }).first().click();
    const importModal = page.getByRole('dialog', { name: /导入Excel文件/i });
    await expect(importModal).toBeVisible();

    let importRequestCount = 0;
    const requestListener = (request: Request) => {
      if (
        request.method() === 'POST' &&
        request.url().includes('/api/v1/rental-contracts/excel/import')
      ) {
        importRequestCount += 1;
      }
    };
    page.on('request', requestListener);
    try {
      await uploadPlainTextFile(importModal, 'contracts.txt');
      await expectMessageVisible(page, /请选择Excel文件（\.xlsx或\.xls格式）/);
      await page.waitForTimeout(500);
      expect(importRequestCount).toBe(0);
    } finally {
      page.off('request', requestListener);
    }
  });

  test('pdf import should reject non-pdf file before request', async ({ page }) => {
    await page.goto('/rental/contracts/pdf-import');
    await expect(page).toHaveURL(/\/rental\/contracts\/pdf-import/);
    await expect(page.getByRole('heading', { name: /PDF合同智能导入/i })).toBeVisible();

    await uploadPlainTextFile(page, 'contract.txt');
    await expectMessageVisible(page, /只支持PDF文件格式/);
  });

  test('pdf import should not send upload request when file type is rejected', async ({ page }) => {
    await page.goto('/rental/contracts/pdf-import');
    await expect(page).toHaveURL(/\/rental\/contracts\/pdf-import/);
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
      '/rental/contracts/pdf-import',
      '/property-certificates/import',
    ];

    for (const route of protectedImportRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});
