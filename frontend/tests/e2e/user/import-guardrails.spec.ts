import { expect, test, type Page, type Request } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';

type FileInputScope = Page | { locator: Page['locator'] };

const CONTRACT_DOCUMENT_REVIEW_PATH = '/contract-groups/import';
const CONTRACT_EXTRACTION_ENDPOINT = '/api/v1/extraction-sessions';
const CONTRACT_DOCUMENT_REVIEW_HEADING = 'Contract document review';

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
    buffer: Buffer.alloc(10 * 1024 * 1024 + 1, 0),
  });
};

const expectMessageVisible = async (page: Page, messagePattern: RegExp): Promise<void> => {
  const messageNotice = page
    .locator('.ant-message-notice-content')
    .filter({ hasText: messagePattern })
    .first();
  await expect(messageNotice).toBeVisible();
};

test.describe('@user-usable contract document review validation', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('rejects a non-PDF file before creating an extraction session', async ({ page }) => {
    await page.goto(CONTRACT_DOCUMENT_REVIEW_PATH);
    await expect(page).toHaveURL(/\/contract-groups\/import$/);
    await expect(
      page.getByRole('heading', { name: CONTRACT_DOCUMENT_REVIEW_HEADING })
    ).toBeVisible();

    await uploadPlainTextFile(page, 'contract.txt');
    await expectMessageVisible(page, /Only PDF files are supported/i);
  });

  test('does not send an extraction request for a rejected file', async ({ page }) => {
    await page.goto(CONTRACT_DOCUMENT_REVIEW_PATH);
    await expect(page).toHaveURL(/\/contract-groups\/import$/);
    await expect(
      page.getByRole('heading', { name: CONTRACT_DOCUMENT_REVIEW_HEADING })
    ).toBeVisible();

    let uploadRequestCount = 0;
    const requestListener = (request: Request) => {
      if (request.method() === 'POST' && request.url().includes(CONTRACT_EXTRACTION_ENDPOINT)) {
        uploadRequestCount += 1;
      }
    };
    page.on('request', requestListener);
    try {
      await uploadPlainTextFile(page, 'contract.txt');
      await expectMessageVisible(page, /Only PDF files are supported/i);
      await page.waitForTimeout(500);
      expect(uploadRequestCount).toBe(0);
    } finally {
      page.off('request', requestListener);
    }
  });

  test.skip('property certificate import should reject unsupported file type before request', async ({
    page,
  }) => {
    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    await uploadPlainTextFile(page, 'certificate.txt');
    await expectMessageVisible(page, /只支持 PDF、JPG、PNG 格式/);
  });

  test.skip('property certificate import should not send request when file is oversized', async ({
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

test.describe('@user-usable import route authentication', () => {
  test('redirects an anonymous user to login for protected import routes', async ({ page }) => {
    await clearAuthState(page);

    const protectedImportRoutes = ['/assets/import', CONTRACT_DOCUMENT_REVIEW_PATH];

    for (const route of protectedImportRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});
