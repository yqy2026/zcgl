import { expect, test, type Page } from '@playwright/test';
import {
  ensureAuthenticated,
  loginWithCredentialRetry,
  resolveAdminCredentialCandidates,
} from '../helpers/auth';

const CONTRACT_DOCUMENT_REVIEW_PATH = '/contract-center/import';
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

// CI 种子显式创建该项目（E2E_EXTRACTION_PROJECT_NAME，见 ci.yml frontend-e2e seed），
// 不再依赖「e2e-project」关键字模糊命中的巧合（issue #92 / Q14）。
const EXTRACTION_PROJECT_NAME =
  process.env.E2E_EXTRACTION_PROJECT_NAME?.trim() || 'E2E抽取项目';

// 页面支持 ?project_id= 预填锁定（PDFImportPage），比 ProjectSelect 交互稳定：
// 直接查种子项目 id 并带进 URL（issue #92 / Q14 复核：UI 选择在 CI 上偶发超时）。
const resolveExtractionProjectId = async (page: Page): Promise<string> => {
  const response = await page.request.get(
    `/api/v1/projects?page=1&page_size=50&search=${encodeURIComponent(EXTRACTION_PROJECT_NAME)}`
  );
  expect(response.status()).toBe(200);
  const payload = (await response.json()) as {
    data?: { items?: Array<{ id?: string; project_name?: string }> };
  };
  const items = payload.data?.items ?? [];
  const project = items.find(
    item => item.project_name === EXTRACTION_PROJECT_NAME
  );
  if (project?.id == null) {
    throw new Error(
      `[contract-session] seed project '${EXTRACTION_PROJECT_NAME}' missing; run the E2E seed first.`
    );
  }
  return project.id;
};

const completeContractContext = async (page: Page): Promise<void> => {
  await page.getByLabel('合同方向').press('ArrowDown');
  await page.getByLabel('合同方向').press('Enter');
  await page.getByLabel('合同角色').press('ArrowDown');
  await page.getByLabel('合同角色').press('Enter');
};

test.describe('@document-extraction-session contract session creation', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticatedStable(page);
  });

  test('creates a review session for a valid contract PDF', async ({ page }) => {
    const projectId = await resolveExtractionProjectId(page);
    await page.goto(
      `${CONTRACT_DOCUMENT_REVIEW_PATH}?project_id=${encodeURIComponent(projectId)}`
    );
    await expect(page).toHaveURL(/\/contract-center\/import(\?.*)?$/);
    await expect(page.getByRole('heading', { name: '合同文件解析' })).toBeVisible();
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

    await page.getByRole('button', { name: '开始解析' }).click();
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
      page.getByRole('heading', { name: '逐项确认提取的合同字段' })
    ).toBeVisible();

    // antd 对两字按钮自动插入空格（autoInsertSpaceInButton）
    await page.getByRole('button', { name: /取\s*消/, exact: true }).click();
    await expect(page.getByRole('heading', { name: '合同文件解析' })).toBeVisible();
  });
});
