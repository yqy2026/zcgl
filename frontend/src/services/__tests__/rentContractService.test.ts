/**
 * RentContractService 单元测试
 *
 * 测试租赁合同服务的核心功能
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AxiosError, AxiosResponse } from 'axios';
import { ApiErrorType } from '@/types/apiResponse';
import { RentContractService } from '../rentContractService';

// Mock API client
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock error handler
vi.mock('@/utils/responseExtractor', () => ({
  ApiErrorHandler: {
    handleError: vi.fn(error => ({
      message: error instanceof Error ? error.message : 'Unknown error',
      code: 'UNKNOWN',
    })),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

import { apiClient } from '@/api/client';

describe('RentContractService', () => {
  let service: RentContractService;

  beforeEach(() => {
    service = new RentContractService();
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 合同 CRUD 测试
  // ==========================================================================

  describe('getContracts', () => {
    it('should return contract list on success', async () => {
      const mockResponse = {
        success: true,
        data: {
          items: [
            { id: '1', contract_number: 'HT-001', tenant_name: '租户A' },
            { id: '2', contract_number: 'HT-002', tenant_name: '租户B' },
          ],
          total: 2,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await service.getContracts({ page: 1, page_size: 10 });

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('should use default pagination', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 },
      });

      await service.getContracts();

      expect(apiClient.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ page: 1, page_size: 10 }),
        })
      );
    });

    it('should return empty list on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getContracts();

      expect(result.items).toEqual([]);
      expect(result.total).toBe(0);
    });
  });

  describe('getContract', () => {
    it('should return contract detail', async () => {
      const mockContract = {
        id: '1',
        contract_number: 'HT-001',
        tenant_name: '测试租户',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockContract,
      });

      const result = await service.getContract('1');

      expect(result.contract_number).toBe('HT-001');
      expect(result.tenant_name).toBe('测试租户');
    });

    it('should throw error when contract not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: false,
        error: '合同不存在',
      });

      await expect(service.getContract('999')).rejects.toThrow('获取合同详情失败');
    });
  });

  describe('createContract', () => {
    it('should create contract successfully', async () => {
      const newContract = {
        contract_number: 'HT-003',
        tenant_name: '新租户',
        start_date: '2026-02-01',
        end_date: '2027-01-31',
        asset_ids: ['asset-1'],
      };

      const createdContract = {
        id: '3',
        ...newContract,
        created_at: '2026-01-30T00:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: createdContract,
      });

      const result = await service.createContract(newContract);

      expect(result.id).toBe('3');
      expect(result.contract_number).toBe('HT-003');
    });

    it('should avoid retry on 4xx responses', async () => {
      const newContract = {
        contract_number: 'HT-004',
        tenant_name: '新租户2',
        start_date: '2026-03-01',
        end_date: '2027-02-28',
        asset_ids: ['asset-2'],
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: '4', ...newContract },
      });

      await service.createContract(newContract);

      const config = vi.mocked(apiClient.post).mock.calls[0][2] as {
        retry?: { retryCondition?: (error: unknown) => boolean };
      };
      const retryCondition = config.retry?.retryCondition;

      expect(typeof retryCondition).toBe('function');

      const conflictResponse: AxiosResponse = {
        data: { success: false, message: '资产租金冲突' },
        status: 409,
        statusText: 'Conflict',
        headers: {},
        config: {} as AxiosResponse['config'],
      };
      const conflictError = new AxiosError(
        'Conflict',
        'ERR_BAD_REQUEST',
        conflictResponse.config,
        {},
        conflictResponse
      );

      const serverResponse: AxiosResponse = {
        data: { success: false, message: '服务不可用' },
        status: 503,
        statusText: 'Service Unavailable',
        headers: {},
        config: {} as AxiosResponse['config'],
      };
      const serverError = new AxiosError(
        'Service Unavailable',
        'ERR_BAD_RESPONSE',
        serverResponse.config,
        {},
        serverResponse
      );

      const networkError = new AxiosError('Network Error', 'ERR_NETWORK');

      const clientError = {
        type: ApiErrorType.CLIENT_ERROR,
        code: 'HTTP_409',
        message: '资产租金冲突',
        statusCode: 409,
        timestamp: new Date().toISOString(),
      };
      const serverApiError = {
        type: ApiErrorType.SERVER_ERROR,
        code: 'HTTP_503',
        message: '服务不可用',
        statusCode: 503,
        timestamp: new Date().toISOString(),
      };
      const networkApiError = {
        type: ApiErrorType.NETWORK_ERROR,
        code: 'NETWORK_ERROR',
        message: '网络错误',
        timestamp: new Date().toISOString(),
      };

      expect(retryCondition?.(conflictError)).toBe(false);
      expect(retryCondition?.(serverError)).toBe(true);
      expect(retryCondition?.(networkError)).toBe(true);
      expect(retryCondition?.(clientError)).toBe(false);
      expect(retryCondition?.(serverApiError)).toBe(true);
      expect(retryCondition?.(networkApiError)).toBe(true);
    });

    it('should throw error on creation failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '合同编号重复',
      });

      await expect(
        service.createContract({ contract_number: 'HT-001', tenant_name: '测试' })
      ).rejects.toThrow('创建租金合同失败');
    });
  });

  describe('updateContract', () => {
    it('should update contract successfully', async () => {
      const updateData = { tenant_name: '更新后的租户' };

      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', ...updateData },
      });

      const result = await service.updateContract('1', updateData);

      expect(result.tenant_name).toBe('更新后的租户');
    });
  });

  describe('deleteContract', () => {
    it('should delete contract successfully', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ success: true });

      await expect(service.deleteContract('1')).resolves.toBeUndefined();
    });

    it('should throw error when delete fails', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({
        success: false,
        error: '合同正在使用中',
      });

      await expect(service.deleteContract('1')).rejects.toThrow('删除租金合同失败');
    });
  });

  // ==========================================================================
  // 租金条款测试
  // ==========================================================================

  describe('getContractTerms', () => {
    it('should return rent terms', async () => {
      const mockTerms = [
        { id: '1', monthly_rent: 10000, start_date: '2026-01-01', end_date: '2026-06-30' },
        { id: '2', monthly_rent: 12000, start_date: '2026-07-01', end_date: '2026-12-31' },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockTerms,
      });

      const result = await service.getContractTerms('contract-1');

      expect(result).toHaveLength(2);
      expect(result[0].monthly_rent).toBe(10000);
    });
  });

  describe('addRentTerm', () => {
    it('should add rent term successfully', async () => {
      const newTerm = {
        monthly_rent: 15000,
        start_date: '2027-01-01',
        end_date: '2027-06-30',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: '3', ...newTerm },
      });

      const result = await service.addRentTerm('contract-1', newTerm);

      expect(result.monthly_rent).toBe(15000);
    });
  });

  // ==========================================================================
  // 租金台账测试
  // ==========================================================================

  describe('getRentLedgers', () => {
    it('should return ledger list', async () => {
      const mockLedgers = {
        items: [
          { id: '1', period: '2026-01', amount: 10000, payment_status: '已支付' },
          { id: '2', period: '2026-02', amount: 10000, payment_status: '未支付' },
        ],
        total: 2,
        page: 1,
        page_size: 10,
        pages: 1,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockLedgers,
      });

      const result = await service.getRentLedgers();

      expect(result.items).toHaveLength(2);
    });

    it('should return empty list on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getRentLedgers();

      expect(result.items).toEqual([]);
    });
  });

  describe('updateRentLedger', () => {
    it('should update ledger successfully', async () => {
      const updateData = { payment_status: '已支付', payment_date: '2026-01-15' };

      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: { id: '1', ...updateData },
      });

      const result = await service.updateRentLedger('1', updateData);

      expect(result.payment_status).toBe('已支付');
    });
  });

  describe('batchUpdateRentLedger', () => {
    it('should batch update ledgers', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({
        success: true,
        data: {
          message: '批量更新成功',
          ledgers: [{ id: '1' }, { id: '2' }],
        },
      });

      const result = await service.batchUpdateRentLedger({
        ledger_ids: ['1', '2'],
        payment_status: '已支付',
      });

      expect(result.ledgers).toHaveLength(2);
    });
  });

  describe('generateMonthlyLedger', () => {
    it('should generate monthly ledger', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: {
          message: '生成成功',
          ledgers: [{ id: '1', period: '2026-02' }],
        },
      });

      const result = await service.generateMonthlyLedger({ contract_id: 'c1' });

      expect(result.ledgers).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 统计测试
  // ==========================================================================

  describe('getRentStatistics', () => {
    it('should return statistics overview', async () => {
      const mockStats = {
        total_contracts: 100,
        active_contracts: 80,
        total_rent: 1000000,
        collected_rent: 800000,
      };

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockStats,
      });

      const result = await service.getRentStatistics();

      expect(result.total_contracts).toBe(100);
      expect(result.total_rent).toBe(1000000);
    });
  });

  describe('getMonthlyStatistics', () => {
    it('should return monthly statistics', async () => {
      const mockStats = [
        { month: '2026-01', rent: 100000, collected: 90000 },
        { month: '2026-02', rent: 100000, collected: 85000 },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockStats,
      });

      const result = await service.getMonthlyStatistics({ year: 2026 });

      expect(result).toHaveLength(2);
    });
  });

  // ==========================================================================
  // 续签和终止测试
  // ==========================================================================

  describe('renewContract', () => {
    it('should renew contract successfully', async () => {
      const newContractData = {
        contract_number: 'HT-001-R1',
        tenant_name: '续签租户',
        start_date: '2027-01-01',
        end_date: '2027-12-31',
      };

      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: 'new-1', ...newContractData },
      });

      const result = await service.renewContract('old-1', newContractData, true);

      expect(result.contract_number).toBe('HT-001-R1');
    });

    it('should throw error on renewal failure', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: false,
        error: '原合同未到期',
      });

      await expect(service.renewContract('1', { contract_number: 'HT-002' }, true)).rejects.toThrow(
        '合同续签失败'
      );
    });
  });

  describe('terminateContract', () => {
    it('should terminate contract successfully', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: '1', status: '已终止' },
      });

      const result = await service.terminateContract('1', '2026-06-30', true, 0, '双方协商终止');

      expect(result.status).toBe('已终止');
    });

    it('should handle deduction amount', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        success: true,
        data: { id: '1', status: '已终止' },
      });

      await service.terminateContract('1', '2026-06-30', true, 5000, '违约终止');

      expect(apiClient.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          deduction_amount: 5000,
          termination_reason: '违约终止',
        }),
        expect.any(Object)
      );
    });
  });

  // ==========================================================================
  // 批量操作测试
  // ==========================================================================

  describe('batchDeleteContracts', () => {
    it('should delete multiple contracts', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ success: true });

      const result = await service.batchDeleteContracts(['1', '2', '3']);

      expect(result.deleted).toBe(3);
      expect(result.errors).toHaveLength(0);
    });

    it('should handle partial failures', async () => {
      vi.mocked(apiClient.delete)
        .mockResolvedValueOnce({ success: true })
        .mockResolvedValueOnce({ success: false, error: '删除失败' })
        .mockResolvedValueOnce({ success: true });

      const result = await service.batchDeleteContracts(['1', '2', '3']);

      expect(result.deleted).toBe(2);
      expect(result.errors).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 计算方法测试
  // ==========================================================================

  describe('calculateTotalRentAmount', () => {
    it('should calculate total rent', () => {
      const terms = [{ monthly_rent: 10000 }, { monthly_rent: 12000 }, { monthly_rent: 15000 }];

      const result = service.calculateTotalRentAmount(terms as Array<{ monthly_rent: number }>);

      expect(result).toBe(37000);
    });

    it('should return 0 for empty terms', () => {
      const result = service.calculateTotalRentAmount([]);

      expect(result).toBe(0);
    });
  });

  describe('calculateAverageRent', () => {
    it('should calculate average rent', () => {
      const terms = [{ monthly_rent: 10000 }, { monthly_rent: 12000 }, { monthly_rent: 14000 }];

      const result = service.calculateAverageRent(terms as Array<{ monthly_rent: number }>);

      expect(result).toBe(12000);
    });

    it('should return 0 for empty terms', () => {
      const result = service.calculateAverageRent([]);

      expect(result).toBe(0);
    });
  });

  describe('calculateContractDuration', () => {
    it('should calculate duration in days', () => {
      const result = service.calculateContractDuration('2026-01-01', '2026-12-31');

      expect(result).toBe(364);
    });

    it('should handle same date', () => {
      const result = service.calculateContractDuration('2026-01-01', '2026-01-01');

      expect(result).toBe(0);
    });
  });

  // ==========================================================================
  // 验证方法测试
  // ==========================================================================

  describe('validateContractNumber', () => {
    it('should return exists true when contract exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [{ id: '1' }], total: 1, page: 1, page_size: 1, pages: 1 },
      });

      const result = await service.validateContractNumber('HT-001');

      expect(result.exists).toBe(true);
    });

    it('should return exists false when contract not found', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: { items: [], total: 0, page: 1, page_size: 1, pages: 0 },
      });

      const result = await service.validateContractNumber('HT-999');

      expect(result.exists).toBe(false);
    });
  });

  describe('validateRentTerms', () => {
    it('should validate continuous terms', async () => {
      const terms = [
        { start_date: '2026-01-01', end_date: '2026-06-30', monthly_rent: 10000 },
        { start_date: '2026-06-30', end_date: '2026-12-31', monthly_rent: 12000 },
      ];

      const result = await service.validateRentTerms('1', terms);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect non-continuous terms', async () => {
      const terms = [
        { start_date: '2026-01-01', end_date: '2026-05-31', monthly_rent: 10000 },
        { start_date: '2026-07-01', end_date: '2026-12-31', monthly_rent: 12000 },
      ];

      const result = await service.validateRentTerms('1', terms);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // 搜索和提醒测试
  // ==========================================================================

  describe('searchContracts', () => {
    it('should search contracts by query', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', tenant_name: '测试租户' }],
          total: 1,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      });

      const result = await service.searchContracts('测试');

      expect(result).toHaveLength(1);
    });
  });

  describe('getOverdueLedgers', () => {
    it('should return overdue ledgers', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [
            { id: '1', payment_status: '逾期', amount: 10000 },
            { id: '2', payment_status: '逾期', amount: 12000 },
          ],
          total: 2,
          page: 1,
          page_size: 100,
          pages: 1,
        },
      });

      const result = await service.getOverdueLedgers();

      expect(result).toHaveLength(2);
    });
  });

  describe('getUpcomingPayments', () => {
    it('should return upcoming payments within days', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: {
          items: [{ id: '1', payment_status: '未支付' }],
          total: 1,
          page: 1,
          page_size: 100,
          pages: 1,
        },
      });

      const result = await service.getUpcomingPayments(7);

      expect(result).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 押金和服务费测试
  // ==========================================================================

  describe('getContractDepositLedger', () => {
    it('should return deposit ledger', async () => {
      const mockDeposits = [
        { id: '1', type: '收取', amount: 20000 },
        { id: '2', type: '退还', amount: 20000 },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: mockDeposits,
      });

      const result = await service.getContractDepositLedger('contract-1');

      expect(result).toHaveLength(2);
    });

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      const result = await service.getContractDepositLedger('contract-1');

      expect(result).toEqual([]);
    });
  });

  describe('getServiceFeeLedgers', () => {
    it('should return service fee ledgers', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        success: true,
        data: [{ id: '1', fee_type: '物业费', amount: 5000 }],
      });

      const result = await service.getServiceFeeLedgers('contract-1');

      expect(result).toHaveLength(1);
    });
  });
});
