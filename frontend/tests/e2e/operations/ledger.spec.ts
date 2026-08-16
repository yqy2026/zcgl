import { expect, test, type Page } from '@playwright/test';

import {
  ensureAuthenticated,
  resolveCsrfHeaders,
  resolveSeedPartyId,
} from '../helpers/auth';

// 经营台账页面业务流（issue #92 页面盲区）：此前该页面只有冒烟渲染断言。
// 这里通过 API 造出「项目 → 合同组 → 下游合同（12 期台账）」链路，断言页面
// 真正渲染出该合同组的数据，而不是只看标题。
const OPERATIONS_LEDGER_PATH = '/operations/ledger';

interface GroupResponse {
  contract_group_id?: string;
  group_code?: string;
}


test.describe('@operations-ledger operations ledger page', () => {
  test('renders the ledger of an API-created downstream contract', async ({
    page,
  }) => {
    await ensureAuthenticated(page);
    const mutationHeaders = await resolveCsrfHeaders(page);
    expect(Object.keys(mutationHeaders).length).toBeGreaterThan(0);

    const suffix = Date.now();
    const partyId = await resolveSeedPartyId(page);

    const projectResponse = await page.request.post('/api/v1/projects', {
      headers: mutationHeaders,
      data: {
        project_name: `E2E FE 台账项目 ${suffix}`,
        status: 'planning',
        manager_party_id: partyId,
        data_status: '正常',
      },
    });
    expect(projectResponse.status()).toBe(200);
    const projectId = (await projectResponse.json()) as { id?: string };

    const groupResponse = await page.request.post('/api/v1/contract-groups', {
      headers: mutationHeaders,
      data: {
        project_id: projectId.id,
        revenue_mode: 'lease',
        operator_party_id: partyId,
        owner_party_id: partyId,
        effective_from: '2026-01-01',
        settlement_rule: {
          version: 'v1',
          cycle: '月付',
          settlement_mode: '固定',
          amount_rule: { base: 5000 },
          payment_rule: { due_day: 10 },
        },
      },
    });
    expect(groupResponse.status()).toBe(201);
    const group = (await groupResponse.json()) as GroupResponse;
    expect(group.group_code).toMatch(/^GRP-/);

    const contractResponse = await page.request.post(
      `/api/v1/contract-groups/${group.contract_group_id}/contracts`,
      {
        headers: mutationHeaders,
        data: {
          contract_group_id: group.contract_group_id,
          contract_number: `E2E-FE-HT-${suffix}`,
          contract_direction: '出租',
          group_relation_type: '下游',
          lessor_party_id: partyId,
          lessee_party_id: partyId,
          sign_date: '2026-01-01',
          effective_from: '2026-01-01',
          effective_to: '2026-12-31',
          payment_cycle: '月付',
          lease_detail: {
            total_deposit: 10000,
            rent_amount: 5000,
            monthly_rent_base: 5000,
            payment_cycle: '月付',
            tenant_name: `E2E FE 租户 ${suffix}`,
          },
          rent_terms: [
            {
              sort_order: 1,
              start_date: '2026-01-01',
              end_date: '2026-12-31',
              monthly_rent: 5000,
            },
          ],
        },
      }
    );
    expect(contractResponse.status()).toBe(201);

    const contractId = (await contractResponse.json()) as { contract_id?: string };
    expect(contractId.contract_id).toBeTruthy();

    await page.goto(OPERATIONS_LEDGER_PATH);
    await expect(page).toHaveURL(/\/operations\/ledger$/);
    // 默认视图（终端租户收缴）表格的「合同/协议」列渲染完整 contract_id，
    // 用唯一 UUID 断言业务链路打通（group_code 只在服务费视图的选择器出现）。
    await expect(
      page.getByText(contractId.contract_id as string).first()
    ).toBeVisible({ timeout: 15_000 });
  });
});
