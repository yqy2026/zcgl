import { expect, test, type Page } from '@playwright/test';
import {
  ensureAuthenticated,
  loginWithCredentialRetry,
  resolveAdminCredentialCandidates,
} from '../helpers/auth';
import {
  LEGACY_CONTRACT_ROUTES,
} from '../helpers/legacyContract';

const PDF_MIME = 'application/pdf';
const MINIMAL_PDF_BUFFER = Buffer.from(
  [
    '%PDF-1.4',
    '1 0 obj',
    '<< /Type /Catalog /Pages 2 0 R >>',
    'endobj',
    '2 0 obj',
    '<< /Type /Pages /Count 0 >>',
    'endobj',
    'trailer',
    '<< /Root 1 0 R >>',
    '%%EOF',
  ].join('\n')
);

const ensureAuthenticatedStable = async (page: Page): Promise<void> => {
  try {
    await ensureAuthenticated(page);
    return;
  } catch {
    const candidates = resolveAdminCredentialCandidates();
    for (const credential of candidates) {
      const success = await loginWithCredentialRetry(page, credential, 3);
      if (success) {
        return;
      }
    }
  }

  throw new Error('failed to authenticate in import-success spec');
};
test.describe('@legacy-contract-import-success 导入成功路径', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticatedStable(page);
  });

  test('pdf import should accept minimal valid pdf file', async ({ page }) => {
    await page.goto(LEGACY_CONTRACT_ROUTES.PDF_IMPORT);
    await expect(page).toHaveURL(/\/contract-groups\/import$/);
    await expect(page.getByRole('heading', { name: /PDF合同智能导入/i })).toBeVisible();

    const uploadResponsePromise = page.waitForResponse(response => {
      return (
        response.request().method() === 'POST' && response.url().includes('/api/v1/pdf-import/upload')
      );
    });

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `contract-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.status()).toBe(200);
    const uploadPayload = (await uploadResponse.json()) as {
      success?: boolean;
      session_id?: string;
    };
    expect(uploadPayload.success).toBe(true);
    expect(uploadPayload.session_id != null && uploadPayload.session_id !== '').toBe(true);
  });
});
