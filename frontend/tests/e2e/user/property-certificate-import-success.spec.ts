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

test.describe('@property-certificate-import-success 导入成功路径', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('property certificate import page should create certificate and show it in list', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-${Date.now()}`;
    const propertyAddress = `E2E坐落地址-${Date.now()}`;
    const certificateId = `mock-cert-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.93,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: certificateId,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: certificateId,
            certificate_number: certificateNumber,
            property_address: propertyAddress,
          },
        ]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const certificateNumberInput = page.getByLabel('证书编号');
    await expect(certificateNumberInput).toBeVisible();
    await expect(certificateNumberInput).toHaveValue(certificateNumber);

    const propertyAddressInput = page.getByLabel('坐落地址');
    await expect(propertyAddressInput).toHaveValue(propertyAddress);

    await page.getByRole('button', { name: /确认并创建产权证/i }).click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    await expect(page.getByRole('heading', { name: /产权证管理/i })).toBeVisible();
    await expect(page.getByText(certificateNumber)).toBeVisible();
  });

  test('property certificate import should recover after oversized file rejection', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-RECOVER-${Date.now()}`;
    const propertyAddress = `E2E恢复地址-${Date.now()}`;

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `oversized-property-certificate-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: Buffer.alloc((10 * 1024 * 1024) + 1, 0),
    });
    await expectMessageVisible(page, /文件大小不能超过 10MB/);

    let uploadRequestCount = 0;
    await page.route('**/api/v1/property-certificates/upload', async route => {
      uploadRequestCount += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.89,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    await uploadInput.setInputFiles({
      name: `property-certificate-recover-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const certificateNumberInput = page.getByLabel('证书编号');
    await expect(certificateNumberInput).toBeVisible();
    await expect(certificateNumberInput).toHaveValue(certificateNumber);
    expect(uploadRequestCount).toBe(1);
  });

  test('property certificate import should send confirm request once on rapid double click', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-DOUBLE-${Date.now()}`;
    const propertyAddress = `E2E双击地址-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.92,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      await page.waitForTimeout(700);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-double-click-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await expect(confirmButton).toBeVisible();

    await confirmButton.click();
    await confirmButton.click().catch(() => undefined);

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBe(1);
  });

  test('property certificate import should submit existing asset linkage when selecting a matched asset', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-LINK-${Date.now()}`;
    const propertyAddress = `E2E关联地址-${Date.now()}`;
    const matchedAssetId = `asset-match-${Date.now()}`;
    const matchedAssetName = `E2E匹配资产-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.94,
          asset_matches: [
            {
              asset_id: matchedAssetId,
              name: matchedAssetName,
              address: propertyAddress,
              confidence: 0.86,
              match_reasons: ['address'],
            },
          ],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    const confirmPayloads: Array<Record<string, unknown>> = [];
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      confirmPayloads.push((route.request().postDataJSON() ?? {}) as Record<string, unknown>);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-link-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    await page.getByText(matchedAssetName).first().click();

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);

    const confirmPayload = confirmPayloads[0];
    expect(confirmPayload).toBeDefined();
    expect(confirmPayload?.should_create_new_asset).toBe(false);
    expect(confirmPayload?.asset_link_id).toBe(matchedAssetId);

    const assetIds = confirmPayload?.asset_ids;
    expect(Array.isArray(assetIds)).toBe(true);
    expect(assetIds as unknown[]).toContain(matchedAssetId);
  });

  test('property certificate import should submit last selected matched asset linkage', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-LINK-SWITCH-${Date.now()}`;
    const propertyAddress = `E2E切换匹配地址-${Date.now()}`;
    const firstMatchedAssetId = `asset-match-first-${Date.now()}`;
    const secondMatchedAssetId = `asset-match-second-${Date.now()}`;
    const firstMatchedAssetName = `E2E匹配资产A-${Date.now()}`;
    const secondMatchedAssetName = `E2E匹配资产B-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.93,
          asset_matches: [
            {
              asset_id: firstMatchedAssetId,
              name: firstMatchedAssetName,
              address: propertyAddress,
              confidence: 0.85,
              match_reasons: ['address'],
            },
            {
              asset_id: secondMatchedAssetId,
              name: secondMatchedAssetName,
              address: propertyAddress,
              confidence: 0.83,
              match_reasons: ['address'],
            },
          ],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    const confirmPayloads: Array<Record<string, unknown>> = [];
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      confirmPayloads.push((route.request().postDataJSON() ?? {}) as Record<string, unknown>);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-link-switch-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    await page.getByText(firstMatchedAssetName).first().click();
    await page.getByText(secondMatchedAssetName).first().click();

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);

    const confirmPayload = confirmPayloads[0];
    expect(confirmPayload).toBeDefined();
    expect(confirmPayload?.should_create_new_asset).toBe(false);
    expect(confirmPayload?.asset_link_id).toBe(secondMatchedAssetId);

    const assetIds = confirmPayload?.asset_ids;
    expect(Array.isArray(assetIds)).toBe(true);
    expect(assetIds as unknown[]).toContain(secondMatchedAssetId);
    expect(assetIds as unknown[]).not.toContain(firstMatchedAssetId);
  });

  test('property certificate import should submit create-new-asset payload when no matched asset is selected', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-CREATE-NEW-${Date.now()}`;
    const propertyAddress = `E2E新建资产地址-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.9,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    const confirmPayloads: Array<Record<string, unknown>> = [];
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      confirmPayloads.push((route.request().postDataJSON() ?? {}) as Record<string, unknown>);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-create-new-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);

    const confirmPayload = confirmPayloads[0];
    expect(confirmPayload).toBeDefined();
    expect(confirmPayload?.should_create_new_asset).toBe(true);
    expect(confirmPayload?.asset_link_id).toBeNull();

    const assetIds = confirmPayload?.asset_ids;
    expect(Array.isArray(assetIds)).toBe(true);
    expect((assetIds as unknown[]).length).toBe(0);
  });

  test('property certificate import should keep create-new-asset payload when matches exist but user does not select', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-MATCH-NO-SELECT-${Date.now()}`;
    const propertyAddress = `E2E匹配未选择地址-${Date.now()}`;
    const matchedAssetId = `asset-match-no-select-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.91,
          asset_matches: [
            {
              asset_id: matchedAssetId,
              name: `E2E匹配资产未选择-${Date.now()}`,
              address: propertyAddress,
              confidence: 0.82,
              match_reasons: ['address'],
            },
          ],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    const confirmPayloads: Array<Record<string, unknown>> = [];
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      confirmPayloads.push((route.request().postDataJSON() ?? {}) as Record<string, unknown>);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-match-no-select-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);

    const confirmPayload = confirmPayloads[0];
    expect(confirmPayload).toBeDefined();
    expect(confirmPayload?.should_create_new_asset).toBe(true);
    expect(confirmPayload?.asset_link_id).toBeNull();

    const assetIds = confirmPayload?.asset_ids;
    expect(Array.isArray(assetIds)).toBe(true);
    expect((assetIds as unknown[]).length).toBe(0);
  });

  test('property certificate import should normalize mixed date formats before confirm submit', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-DATE-NORMALIZE-${Date.now()}`;
    const propertyAddress = `E2E日期标准化地址-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
            registration_date: '2026/03/04',
            land_use_term_start: '2026年01月01日',
            land_use_term_end: '2026/12/31',
          },
          confidence_score: 0.92,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    const confirmPayloads: Array<Record<string, unknown>> = [];
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      confirmPayloads.push((route.request().postDataJSON() ?? {}) as Record<string, unknown>);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-date-normalize-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);

    const confirmPayload = confirmPayloads[0];
    expect(confirmPayload).toBeDefined();

    const extractedData = (confirmPayload?.extracted_data ?? {}) as Record<string, unknown>;
    expect(extractedData.registration_date).toBe('2026-03-04');
    expect(extractedData.land_use_term_start).toBe('2026-01-01');
    expect(extractedData.land_use_term_end).toBe('2026-12-31');
  });

  test('property certificate import should null invalid date strings before confirm submit', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-DATE-INVALID-${Date.now()}`;
    const propertyAddress = `E2E日期非法地址-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
            registration_date: '2026-13-01',
            land_use_term_start: '无效日期',
            land_use_term_end: '2026/99/40',
          },
          confidence_score: 0.9,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    const confirmPayloads: Array<Record<string, unknown>> = [];
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      confirmPayloads.push((route.request().postDataJSON() ?? {}) as Record<string, unknown>);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.route('**/api/v1/property-certificates/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-date-invalid-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page).toHaveURL(/\/property-certificates$/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);

    const confirmPayload = confirmPayloads[0];
    expect(confirmPayload).toBeDefined();
    const extractedData = (confirmPayload?.extracted_data ?? {}) as Record<string, unknown>;
    expect(extractedData.registration_date).toBeNull();
    expect(extractedData.land_use_term_start).toBeNull();
    expect(extractedData.land_use_term_end).toBeNull();
  });

  test('property certificate import should block confirm request when certificate number is empty', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-REQUIRED-${Date.now()}`;
    const propertyAddress = `E2E必填地址-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.9,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          certificate_id: `mock-cert-${Date.now()}`,
        }),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-required-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const certificateNumberInput = page.getByLabel('证书编号');
    await certificateNumberInput.fill('');

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expect(page.getByText('请输入证书编号')).toBeVisible();
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    expect(confirmRequestCount).toBe(0);
  });

  test('property certificate import should stay on review when confirm returns validation error', async ({
    page,
  }) => {
    const certificateNumber = `E2E-PC-API-VALIDATION-${Date.now()}`;
    const propertyAddress = `E2E后端校验地址-${Date.now()}`;

    await page.route('**/api/v1/property-certificates/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: `session-${Date.now()}`,
          certificate_type: 'property_cert',
          extracted_data: {
            certificate_number: certificateNumber,
            certificate_type: 'other',
            property_address: propertyAddress,
            property_type: '商业',
          },
          confidence_score: 0.91,
          asset_matches: [],
          validation_errors: [],
          warnings: [],
        }),
      });
    });

    let confirmRequestCount = 0;
    await page.route('**/api/v1/property-certificates/confirm-import', async route => {
      confirmRequestCount += 1;
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: '缺少证书编号',
          error: {
            code: 'VALIDATION_ERROR',
            message: '缺少证书编号',
            details: {
              field_errors: {
                certificate_number: ['缺少证书编号'],
              },
            },
          },
        }),
      });
    });

    await page.goto('/property-certificates/import');
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    await expect(page.getByRole('heading', { name: /产权证导入/i })).toBeVisible();

    const uploadInput = page.locator('input[type="file"]').first();
    await uploadInput.setInputFiles({
      name: `property-certificate-api-validation-${Date.now()}.pdf`,
      mimeType: PDF_MIME,
      buffer: MINIMAL_PDF_BUFFER,
    });

    const confirmButton = page.getByRole('button', { name: /确认并创建产权证/i });
    await confirmButton.click();

    await expectMessageVisible(page, /创建失败，请重试/);
    await expect(page).toHaveURL(/\/property-certificates\/import/);
    expect(confirmRequestCount).toBeGreaterThanOrEqual(1);
  });
});
