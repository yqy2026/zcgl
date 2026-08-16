import { expect, test, type Page } from '@playwright/test';

import {
  ensureAuthenticated,
  resolveCsrfHeaders,
  resolveSeedPartyId,
} from '../helpers/auth';

// 产权证列表页业务流（issue #92 页面盲区）：API 造数（种子主体 + 资产 + 产权证）
// 后断言列表页真实渲染出该证书，而不是只做空态冒烟。
const CERTIFICATE_LIST_PATH = '/property-certificates';


test.describe('@property-certificate-list certificate list page', () => {
  test('shows an API-created certificate in the list', async ({ page }) => {
    await ensureAuthenticated(page);
    const mutationHeaders = await resolveCsrfHeaders(page);
    expect(Object.keys(mutationHeaders).length).toBeGreaterThan(0);

    const suffix = Date.now();
    const partyId = await resolveSeedPartyId(page);
    const certificateNumber = `E2E-FE-CERT-${suffix}`;

    const assetResponse = await page.request.post('/api/v1/assets', {
      headers: mutationHeaders,
      data: {
        asset_name: `E2E FE 证书资产 ${suffix}`,
        address_detail: `E2E FE 证书地址 ${suffix}`,
        ownership_status: '已确权',
        property_nature: '经营类',
        usage_status: '自用',
        business_category: 'E2E测试业态',
        data_status: '正常',
        owner_party_id: partyId,
        manager_party_id: partyId,
      },
    });
    expect(assetResponse.status()).toBe(201);
    const assetPayload = (await assetResponse.json()) as { id?: string };
    expect(assetPayload.id).toBeTruthy();

    const certificateResponse = await page.request.post(
      '/api/v1/property-certificates',
      {
        headers: mutationHeaders,
        data: {
          certificate_number: certificateNumber,
          certificate_type: 'real_estate',
          registration_date: '2026-01-01',
          property_address: `E2E FE 产权地址 ${suffix}`,
          asset_ids: [assetPayload.id],
          holder_party_ids: [partyId],
        },
      }
    );
    expect(certificateResponse.status()).toBe(200);

    await page.goto(CERTIFICATE_LIST_PATH);
    await expect(page).toHaveURL(/\/property-certificates$/);
    await expect(
      page.getByText(certificateNumber).first()
    ).toBeVisible({ timeout: 15_000 });
  });
});
