import React from 'react';
import dayjs from 'dayjs';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, fireEvent, waitFor } from '@/test/utils/test-helpers';
import RentContractForm from '../RentContractForm';

let mockValidateFields: ReturnType<typeof vi.fn>;

vi.mock('@/services/assetService', () => ({
  assetService: {
    getAssets: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

vi.mock('@/services/ownershipService', () => ({
  ownershipService: {
    getOwnerships: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock('antd', () => {
  const Form = Object.assign(
    ({ children, onFinish }: { children: React.ReactNode; onFinish?: () => void }) => (
      <form
        onSubmit={event => {
          event.preventDefault();
          onFinish?.();
        }}
      >
        {children}
      </form>
    ),
    {
      useForm: () => [
        {
          validateFields: mockValidateFields,
          setFieldsValue: vi.fn(),
        },
        {},
      ],
    }
  );

  return { Form };
});

vi.mock('../RentContract', async () => {
  const context = await vi.importActual<typeof import('../RentContract/RentContractFormContext')>(
    '../RentContract/RentContractFormContext'
  );
  return {
    RentContractFormProvider: context.RentContractFormProvider,
    useRentContractFormContext: context.useRentContractFormContext,
    BasicInfoSection: () => null,
    RelationInfoSection: () => null,
    TenantInfoSection: () => null,
    ContractPeriodSection: () => null,
    RentTermsSection: () => null,
    OtherInfoSection: () => null,
    RentTermModal: () => null,
    FormActionsSection: () => <button type="submit">提交</button>,
  };
});

describe('RentContractForm', () => {
  beforeEach(() => {
    mockValidateFields = vi.fn().mockResolvedValue({
      contract_number: 'HT-TEST-001',
      asset_ids: ['asset-1'],
      ownership_id: 'owner-1',
      tenant_name: '测试租户',
      start_date: dayjs('2026-02-01'),
      end_date: dayjs('2026-12-31'),
    });
  });

  it('submits when form is submitted', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWithProviders(
      <RentContractForm
        mode="edit"
        initialData={{
          contract_number: 'HT-INIT',
          asset_ids: ['asset-1'],
          ownership_id: 'owner-1',
          tenant_name: '测试租户',
          start_date: '2026-02-01',
          end_date: '2026-12-31',
          rent_terms: [
            {
              start_date: '2026-02-01',
              end_date: '2026-12-31',
              monthly_rent: 1000,
            },
          ],
        }}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '提交' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
  });
});
