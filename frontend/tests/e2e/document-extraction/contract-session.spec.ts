import { expect, test, type Page } from '@playwright/test';
import {
  ensureAuthenticated,
  loginWithCredentialRetry,
  resolveAdminCredentialCandidates,
} from '../helpers/auth';

const CONTRACT_DOCUMENT_REVIEW_PATH = '/contract-groups/import';
const CONTRACT_EXTRACTION_ENDPOINT = '/api/v1/extraction-sessions';
const VALID_CONTRACT_PDF_BUFFER = Buffer.from(
  'JVBERi0xLjcKJcK1wrYKCjEgMCBvYmoKPDwvVHlwZS9DYXRhbG9nL1BhZ2VzIDIgMCBSPj4KZW5kb2JqCgoyIDAgb2JqCjw8L1R5cGUvUGFnZXMvQ291bnQgMS9LaWRzWzQgMCBSXT4+CmVuZG9iagoKMyAwIG9iago8PC9Gb250PDwvaGVsdiA1IDAgUj4+Pj4KZW5kb2JqCgo0IDAgb2JqCjw8L1R5cGUvUGFnZS9NZWRpYUJveFswIDAgNTk1IDg0Ml0vUm90YXRlIDAvUmVzb3VyY2VzIDMgMCBSL1BhcmVudCAyIDAgUi9Db250ZW50c1s2IDAgUl0+PgplbmRvYmoKCjUgMCBvYmoKPDwvVHlwZS9Gb250L1N1YnR5cGUvVHlwZTEvQmFzZUZvbnQvSGVsdmV0aWNhL0VuY29kaW5nL1dpbkFuc2lFbmNvZGluZz4+CmVuZG9iagoKNiAwIG9iago8PC9MZW5ndGggMTMxL0ZpbHRlci9GbGF0ZURlY29kZT4+CnN0cmVhbQp42iXMOwoCQQwG4D6nyAXUvIMgW4g2dsJ0YiHMLhZa2Hh+M2t+EpIiH3zg2ICRKowpmEnY3rB7zq8vMmNb8HYwjSXmtJTg0DShujx6SHiKPoTMVcylK1V4urcLEG7Yt8yG7QRleIzy8R/7rK2UKHGJPgQVHR2rwf+5OucGV/gBR2YlQgplbmRzdHJlYW0KZW5kb2JqCgp4cmVmCjAgNwowMDAwMDAwMDAwIDAwMDAxIGYgCjAwMDAwMDAwMTYgMDAwMDAgbiAKMDAwMDAwMDA2MiAwMDAwMCBuIAowMDAwMDAwMTE0IDAwMDAwIG4gCjAwMDAwMDAxNTUgMDAwMDAgbiAKMDAwMDAwMDI2MiAwMDAwMCBuIAowMDAwMDAwMzUxIDAwMDAwIG4gCgp0cmFpbGVyCjw8L1NpemUgNy9Sb290IDEgMCBSL0lEWzw1Mzc4MkNDMzk0QzI4RUMyQTIyM0MyQUFDMzkwQzM5Qj48QzkxODRBMzg2RjQ5NDM1OUIwODU4Q0U4QjAyOTU0RUE+XT4+CnN0YXJ0eHJlZgo1NTEKJSVFT0YK',
  'base64'
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

  throw new Error('failed to authenticate in contract-session spec');
};

const completeContractContext = async (page: Page): Promise<void> => {
  await page.getByLabel('Project ID').fill('e2e-project');
  await page.getByLabel('Contract direction').click();
  await page.getByRole('option', { name: 'Lessor', exact: true }).click();
  await page.getByLabel('Contract role').click();
  await page.getByRole('option', { name: 'Upstream', exact: true }).click();
};

test.describe('@document-extraction-session contract session creation', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticatedStable(page);
  });

  test('creates a review session for a valid contract PDF', async ({ page }) => {
    await page.goto(CONTRACT_DOCUMENT_REVIEW_PATH);
    await expect(page).toHaveURL(/\/contract-groups\/import$/);
    await expect(page.getByRole('heading', { name: 'Contract document review' })).toBeVisible();
    await completeContractContext(page);

    const uploadResponsePromise = page.waitForResponse(response => {
      return (
        response.request().method() === 'POST' &&
        response.url().includes(CONTRACT_EXTRACTION_ENDPOINT)
      );
    });

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `contract-${Date.now()}.pdf`,
      mimeType: 'application/pdf',
      buffer: VALID_CONTRACT_PDF_BUFFER,
    });

    await page.getByRole('button', { name: 'Extract for review' }).click();
    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.status()).toBe(201);
    const uploadPayload = (await uploadResponse.json()) as {
      session_id?: string;
      status?: string;
      target_type?: string;
    };
    expect(uploadPayload.session_id != null && uploadPayload.session_id !== '').toBe(true);
    expect(uploadPayload.status).toBe('ready_for_review');
    expect(uploadPayload.target_type).toBe('contract');
    await expect(
      page.getByRole('heading', { name: 'Review extracted contract fields' })
    ).toBeVisible();

    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Contract document review' })).toBeVisible();
  });
});
