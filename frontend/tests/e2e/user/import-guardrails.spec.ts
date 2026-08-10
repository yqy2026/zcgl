import { expect, test, type Page } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';

type FileInputScope = Page | { locator: Page['locator'] };

const CONTRACT_DOCUMENT_REVIEW_PATH = '/contract-center/import';
const CONTRACT_EXTRACTION_ENDPOINT = '/api/v1/extraction-sessions';
const CONTRACT_DOCUMENT_REVIEW_HEADING = '合同文件解析';

const uploadPlainTextFile = async (scope: FileInputScope, filename: string): Promise<void> => {
  const uploadInput = scope.locator('input[type="file"]').first();
  await uploadInput.setInputFiles({
    name: filename,
    mimeType: 'text/plain',
    buffer: Buffer.from('invalid-import-content'),
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
    await expect(page).toHaveURL(/\/contract-center\/import$/);
    await expect(
      page.getByRole('heading', { name: CONTRACT_DOCUMENT_REVIEW_HEADING })
    ).toBeVisible();

    await uploadPlainTextFile(page, 'contract.txt');
    await expectMessageVisible(page, /仅支持 PDF 文件/i);
  });

  test('does not send an extraction request for a rejected file', async ({ page }) => {
    await page.goto(CONTRACT_DOCUMENT_REVIEW_PATH);
    await expect(page).toHaveURL(/\/contract-center\/import$/);
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
      await expectMessageVisible(page, /仅支持 PDF 文件/i);
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
