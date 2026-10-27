import { expect, test, type Page, type Request } from '@playwright/test';
import { clearAuthState, ensureAuthenticated } from '../helpers/auth';

type FileInputScope = Page | { locator: Page['locator'] };

const CONTRACT_INTAKE_PATH = '/asset-operations/contracts/intake';
const CONTRACT_INTAKE_ENDPOINT = '/api/v1/contract-intake-sessions';
const CONTRACT_INTAKE_HEADING = '录入已签合同';

const uploadPlainTextFile = async (scope: FileInputScope, filename: string): Promise<void> => {
  const uploadInput = scope.locator('input[type="file"]').first();
  await uploadInput.setInputFiles({
    name: filename,
    mimeType: 'text/plain',
    buffer: Buffer.from('invalid-import-content'),
  });
};

test.describe('@user-usable contract intake validation', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('rejects a non-PDF file without creating an intake session', async ({ page }) => {
    await page.goto(CONTRACT_INTAKE_PATH);
    await expect(page).toHaveURL(/\/asset-operations\/contracts\/intake$/);
    await expect(page.getByRole('heading', { name: CONTRACT_INTAKE_HEADING })).toBeVisible();

    await uploadPlainTextFile(page, 'contract.txt');
    const responsePromise = page.waitForResponse(response => {
      return (
        response.request().method() === 'POST' && response.url().endsWith(CONTRACT_INTAKE_ENDPOINT)
      );
    });
    await page.getByRole('button', { name: '上传并创建会话' }).click();
    expect((await responsePromise).status()).toBe(422);
    await expect(page.getByText(/创建录入会话失败/i)).toBeVisible();
    await expect(
      page.getByRole('heading', { name: '第一步 · 选择类型并上传扫描件' })
    ).toBeVisible();
  });

  test('sends one failed upload request and never advances a rejected file', async ({ page }) => {
    await page.goto(CONTRACT_INTAKE_PATH);
    await expect(page).toHaveURL(/\/asset-operations\/contracts\/intake$/);
    await expect(page.getByRole('heading', { name: CONTRACT_INTAKE_HEADING })).toBeVisible();

    let uploadRequestCount = 0;
    const requestListener = (request: Request) => {
      if (request.method() === 'POST' && request.url().endsWith(CONTRACT_INTAKE_ENDPOINT)) {
        uploadRequestCount += 1;
      }
    };
    page.on('request', requestListener);
    try {
      await uploadPlainTextFile(page, 'contract.txt');
      const responsePromise = page.waitForResponse(response => {
        return (
          response.request().method() === 'POST' &&
          response.url().endsWith(CONTRACT_INTAKE_ENDPOINT)
        );
      });
      await page.getByRole('button', { name: '上传并创建会话' }).click();
      expect((await responsePromise).status()).toBe(422);
      await expect(page.getByText(/创建录入会话失败/i)).toBeVisible();
      await page.waitForTimeout(500);
      expect(uploadRequestCount).toBe(1);
      await expect(page.getByRole('heading', { name: '第二步 · 核对信息' })).toHaveCount(0);
    } finally {
      page.off('request', requestListener);
    }
  });
});

test.describe('@user-usable intake route authentication', () => {
  test('redirects an anonymous user to login for the protected intake route', async ({ page }) => {
    await clearAuthState(page);

    await page.goto(CONTRACT_INTAKE_PATH);
    await expect(page).toHaveURL(/\/login/);
  });
});
