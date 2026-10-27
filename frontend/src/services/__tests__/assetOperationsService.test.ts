import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn((error: unknown) => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'INVALID_RESPONSE_DATA',
    })),
  },
}));

import { apiClient } from '@/api/client';

import { assetOperationsService } from '../assetOperationsService';

describe('assetOperationsService Decimal normalization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('rejects malformed Decimal data instead of silently replacing it with zero', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            id: 'unit-1',
            unit_code: 'AU-001',
            name: '测试单元',
            project_id: 'project-1',
            owner_party_id: 'party-1',
            address: '测试地址',
            usage_type: 'office',
            acquisition_mode: 'owned',
            is_operating: true,
            land_area: 'not-a-decimal',
            building_area: '80.00',
            rentable_area: '60.00',
            managed_from: '2026-01-01',
            managed_to: null,
            vacancy_reason: null,
            expected_lease_start: null,
            predecessor_unit_ids: [],
            version: 1,
            rental_status: 'vacant',
            rented_area: '0.00',
            occupancy_rate: '0.00',
            warnings: [],
            terminal_contract_ids: [],
          },
        ],
        total: 1,
      },
    });

    await expect(assetOperationsService.listAssetUnits()).rejects.toThrow(
      'Invalid Decimal field: land_area'
    );
  });

  it('serializes v5 Decimal payload fields through the shared conversion entry point', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { id: 'upstream-1', contract_number: 'UP-001', idempotent: false },
    });

    await assetOperationsService.confirmUpstreamIntake(
      'session-1',
      {
        contract_number: 'UP-001',
        name: '上游合同',
        owner_party_id: 'owner-1',
        operator_party_id: 'operator-1',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        management_fee_rate: 0.035,
        deposit_amount: 12000,
        asset_unit_ids: ['unit-1'],
        rent_schedules: [
          {
            stage_start: '2026-01-01',
            stage_end: '2026-12-31',
            base_monthly_rent: 8000,
            increase_rate: 0.05,
            free_rent_months: 1.5,
            discount_amount: 100,
            actual_monthly_rent: 7900,
            payment_cycle: 'monthly',
            due_day: 5,
          },
        ],
      },
      'idem-1'
    );

    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/v1/contract-intake-sessions/session-1/confirm-upstream',
      expect.objectContaining({
        management_fee_rate: '0.035',
        deposit_amount: '12000',
        rent_schedules: [
          expect.objectContaining({
            base_monthly_rent: '8000',
            increase_rate: '0.05',
            free_rent_months: '1.5',
            discount_amount: '100',
            actual_monthly_rent: '7900',
          }),
        ],
      }),
      expect.any(Object)
    );
  });
});
