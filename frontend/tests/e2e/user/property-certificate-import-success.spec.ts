import { expect, test, type Page } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

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

const expectMessageVisible = async (page: Page, messagePattern: RegExp): Promise<void> => {
  const messageNotice = page
    .locator('.ant-message-notice-content')
    .filter({ hasText: messagePattern })
    .first();
  await expect(messageNotice).toBeVisible();
};

/**
 * 产权证导入走统一 extraction-sessions 流程（上传 → 人工复核 → 确认）。
 * mock 端点：POST /api/v1/extraction-sessions、POST /extraction-sessions/{id}/confirm、
 * GET /property-certificates/。
 */
test.describe('@property-certificate-import-success 产权证导入成功路径', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  const mockExtractionFlow = async (
    page: Page,
    options: { certificateNumber: string; propertyAddress: string }
  ) => {
    const certificateNumber = options.certificateNumber;
    const propertyAddress = options.propertyAddress;
    const sessionId = `session-${Date.now()}`;

    await page.route('**/api/v1/extraction-sessions', async route => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: sessionId,
          target_type: 'property_certificate',
          status: 'ready_for_review',
          candidates: {
            fields: {
              certificate_number: {
                conflict: false,
                candidates: [
                  { value: certificateNumber, value_type: 'string', confidence: 'high', evidence: [] },
                ],
              },
              property_address: {
                conflict: false,
                candidates: [
                  { value: propertyAddress, value_type: 'string', confidence: 'high', evidence: [] },
                ],
              },
            },
          },
          errors: [],
        }),
      });
    });

    await page.route('**/api/v1/extraction-sessions/*/confirm', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ certificate_id: `mock-cert-${Date.now()}` }),
      });
    });

    await page.route('**/api/v1/property-certificates**', async route => {
      if (route.request().method() !== 'GET') {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: `mock-cert-${Date.now()}`, certificate_number: certificateNumber, property_address: propertyAddress },
        ]),
      });
    });

    return sessionId;
  };

  test('导入成功：上传 → 复核 → 保存 → 列表可见证书号', async ({ page }) => {
    const certificateNumber = `E2E-PC-${Date.now()}`;
    const propertyAddress = `E2E坐落地址-${Date.now()}`;
    const sessionId = await mockExtractionFlow(page, { certificateNumber, propertyAddress });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    await page.getByLabel('资产编号').fill('e2e-asset-1');
    await page.locator('input[type="file"]').first().setInputFiles({
      name: `property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const extractionResponse = page.waitForResponse(
      response =>
        response.request().method() === 'POST' &&
        response.url().includes('/api/v1/extraction-sessions')
    );
    await page.getByRole('button', { name: /开始解析/i }).click();
    const uploadResponse = await extractionResponse;
    expect(uploadResponse.status()).toBe(201);

    await expect(page.getByLabel('证书编号')).toBeVisible();
    // 权利人 ID 在解析后才可填（页面 disabled 逻辑）
    await page.getByLabel('权利人编号').fill('e2e-party-1');
    const certificateNumberInput = page.getByLabel('证书编号');
    await expect(certificateNumberInput).toBeVisible();
    await page.getByText(`使用候选：${certificateNumber}`).click();

    const confirmResponse = page.waitForResponse(
      response =>
        response.request().method() === 'POST' &&
        response.url().includes(`/extraction-sessions/${sessionId}/confirm`)
    );
    await page.getByRole('button', { name: /保存产权证/i }).click();
    const confirmResp = await confirmResponse;
    expect(confirmResp.status()).toBe(200);

    await expect(page).toHaveURL(/\/property-certificates$/);
    await expect(page.getByText(certificateNumber)).toBeVisible();
  });

  test('确认请求携带候选动作与资产关联', async ({ page }) => {
    const certificateNumber = `E2E-PC-PAYLOAD-${Date.now()}`;
    const propertyAddress = `E2E载荷地址-${Date.now()}`;
    await mockExtractionFlow(page, { certificateNumber, propertyAddress });

    let confirmPayload: Record<string, unknown> | null = null;
    await page.route('**/api/v1/extraction-sessions/*/confirm', async route => {
      confirmPayload = (route.request().postDataJSON() ?? {}) as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ certificate_id: `mock-cert-${Date.now()}` }),
      });
    });

    await page.goto('/property-certificates/import');
    await page.getByLabel('资产编号').fill('e2e-asset-1');
    await page.locator('input[type="file"]').first().setInputFiles({
      name: `property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });
    await page.getByRole('button', { name: /开始解析/i }).click();

    await expect(page.getByLabel('证书编号')).toBeVisible();
    await page.getByLabel('权利人编号').fill('e2e-party-1');
    await page.getByText(`使用候选：${certificateNumber}`).click();
    await page.getByText(`使用候选：${propertyAddress}`).click();

    await page.getByRole('button', { name: /保存产权证/i }).click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmPayload).not.toBeNull();
    const actions = (confirmPayload?.actions ?? []) as Array<Record<string, unknown>>;
    expect(actions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ field_key: 'certificate_number', action: 'accept_candidate' }),
        expect.objectContaining({ field_key: 'property_address', action: 'accept_candidate' }),
      ])
    );
    expect(confirmPayload?.holder_party_ids).toEqual(['e2e-party-1']);
  });

  test('超大文件被拒绝且不发起解析请求', async ({ page }) => {
    await page.goto('/property-certificates/import');
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    let extractionRequestCount = 0;
    await page.route('**/api/v1/extraction-sessions', async route => {
      if (route.request().method() === 'POST') {
        extractionRequestCount += 1;
      }
      await route.fallback();
    });

    await page.getByLabel('资产编号').fill('e2e-asset-1');
    await page.locator('input[type="file"]').first().setInputFiles({
      name: `oversized-property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: Buffer.alloc(20 * 1024 * 1024 + 1, 0),
    });
    await expectMessageVisible(page, /文件不能超过 20 MiB/);
    await page.waitForTimeout(500);
    expect(extractionRequestCount).toBe(0);
  });

  test('缺失资产 ID 时解析被拦截', async ({ page }) => {
    await page.goto('/property-certificates/import');
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    await page.getByRole('button', { name: /开始解析/i }).click();
    await expect(page.getByText('请输入资产编号')).toBeVisible();
    await expect(page).toHaveURL(/\/property-certificates\/import/);
  });

  test('证书编号为空时保存被拦截，confirm 不发起', async ({ page }) => {
    const certificateNumber = `E2E-PC-REQUIRED-${Date.now()}`;
    const propertyAddress = `E2E必填地址-${Date.now()}`;
    await mockExtractionFlow(page, { certificateNumber, propertyAddress });

    let confirmRequestCount = 0;
    await page.route('**/api/v1/extraction-sessions/*/confirm', async route => {
      confirmRequestCount += 1;
      await route.fallback();
    });

    await page.goto('/property-certificates/import');
    await page.getByLabel('资产编号').fill('e2e-asset-1');
    await page.locator('input[type="file"]').first().setInputFiles({
      name: `property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });
    await page.getByRole('button', { name: /开始解析/i }).click();

    await expect(page.getByLabel('证书编号')).toBeVisible();
    await page.getByLabel('权利人编号').fill('e2e-party-1');
    const certificateNumberInput = page.getByLabel('证书编号');
    await expect(certificateNumberInput).toBeVisible();
    await certificateNumberInput.fill('');

    await page.getByRole('button', { name: /保存产权证/i }).click();
    // 证书编号候选未采纳且为空 → 人工复核拦截（不发 confirm 请求）
    await expect(page.getByText(/证书编号需要人工确认/)).toBeVisible();
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    expect(confirmRequestCount).toBe(0);
  });

  test('confirm 返回校验错误时停留在复核页', async ({ page }) => {
    const certificateNumber = `E2E-PC-API-VALIDATION-${Date.now()}`;
    const propertyAddress = `E2E后端校验地址-${Date.now()}`;
    await mockExtractionFlow(page, { certificateNumber, propertyAddress });

    await page.route('**/api/v1/extraction-sessions/*/confirm', async route => {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: '缺少证书编号',
        }),
      });
    });

    await page.goto('/property-certificates/import');
    await page.getByLabel('资产编号').fill('e2e-asset-1');
    await page.locator('input[type="file"]').first().setInputFiles({
      name: `property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });
    await page.getByRole('button', { name: /开始解析/i }).click();

    await expect(page.getByLabel('证书编号')).toBeVisible();
    await page.getByLabel('权利人编号').fill('e2e-party-1');
    await page.getByText(`使用候选：${certificateNumber}`).click();

    await page.getByRole('button', { name: /保存产权证/i }).click();
    await expectMessageVisible(page, /产权证保存失败，请重试/);
    await expect(page).toHaveURL(/\/property-certificates\/import/);
  });
});
