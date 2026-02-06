/**
 * 租金台账相关的API服务 - V2 with 多资产/续签/终止
 *
 * @description 租赁合同管理核心服务，包含合同、条款、台账、统计、续签、终止等完整功能
 * @author Claude Code
 */

import { AxiosError } from 'axios';
import {
  RentContract,
  RentContractCreate,
  RentContractUpdate,
  RentTerm,
  RentTermCreate,
  RentLedger,
  RentLedgerUpdate,
  RentLedgerBatchUpdate,
  GenerateLedgerRequest,
  RentStatisticsQuery,
  RentContractListResponse,
  RentLedgerListResponse,
  RentStatisticsOverview,
  OwnershipRentStatistics,
  AssetRentStatistics,
  MonthlyRentStatistics,
  RentContractQueryParams,
  RentLedgerQueryParams,
  DepositLedger,
  ServiceFeeLedger,
} from '@/types/rentContract';
import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';
import { API_ENDPOINTS } from '@/constants/api';
import { ApiClientError, ApiErrorType } from '@/types/apiResponse';

const logger = createLogger('RentContractService');

const isApiClientError = (error: unknown): error is ApiClientError => {
  return (
    error != null &&
    typeof error === 'object' &&
    'type' in error &&
    'code' in error &&
    'message' in error
  );
};

const shouldRetryOnServerError = (error: unknown): boolean => {
  if (error instanceof AxiosError) {
    const statusCode = error.response?.status;
    if (statusCode != null) {
      return statusCode >= 500;
    }
    return true;
  }

  if (isApiClientError(error)) {
    if (typeof error.statusCode === 'number') {
      return error.statusCode >= 500;
    }

    if (error.type === ApiErrorType.NETWORK_ERROR) {
      return true;
    }

    if (error.type === ApiErrorType.SERVER_ERROR) {
      return true;
    }

    return false;
  }

  if (error != null && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { status?: number } }).response;
    const statusCode = response?.status;
    if (statusCode != null) {
      return statusCode >= 500;
    }
  }

  return false;
};

class RentContractService {
  private baseUrl = API_ENDPOINTS.RENT_CONTRACT.LIST;

  // ==================== 租金合同相关API ====================

  /**
   * 获取租金合同列表
   */
  async getContracts(params?: RentContractQueryParams): Promise<RentContractListResponse> {
    try {
      const { pageSize, page_size, ...rest } = params ?? {};
      const result = await apiClient.get<RentContractListResponse>(this.baseUrl, {
        params: { ...rest, page: params?.page ?? 1, page_size: page_size ?? pageSize ?? 10 },
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success) {
        throw new Error(`获取租金合同列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // eslint-disable-next-line no-console
      console.error('获取租金合同列表失败:', enhancedError.message);

      // 返回默认空结果，避免UI崩溃
      return {
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        pages: 0,
      };
    }
  }

  /**
   * 获取合同详情
   */
  async getContract(id: string): Promise<RentContract> {
    try {
      const result = await apiClient.get<RentContract>(
        API_ENDPOINTS.RENT_CONTRACT.DETAIL(id),
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取合同详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建租金合同
   */
  async createContract(data: RentContractCreate): Promise<RentContract> {
    try {
      const result = await apiClient.post<RentContract>(
        API_ENDPOINTS.RENT_CONTRACT.CREATE,
        data,
        {
          retry: {
            maxAttempts: 3,
            delay: 1000,
            backoffMultiplier: 2,
            retryCondition: shouldRetryOnServerError,
          },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`创建租金合同失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新租金合同
   */
  async updateContract(id: string, data: RentContractUpdate): Promise<RentContract> {
    try {
      const result = await apiClient.put<RentContract>(
        API_ENDPOINTS.RENT_CONTRACT.UPDATE(id),
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`更新租金合同失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除租金合同
   */
  async deleteContract(id: string): Promise<void> {
    try {
      const result = await apiClient.delete<void>(API_ENDPOINTS.RENT_CONTRACT.DELETE(id), {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`删除租金合同失败: ${result.error}`);
      }
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 租金条款相关API ====================

  /**
   * 获取合同租金条款
   */
  async getContractTerms(contractId: string): Promise<RentTerm[]> {
    try {
      const result = await apiClient.get<RentTerm[]>(
        API_ENDPOINTS.RENT_CONTRACT.TERMS(contractId),
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取租金条款失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 添加租金条款
   */
  async addRentTerm(contractId: string, data: RentTermCreate): Promise<RentTerm> {
    try {
      const result = await apiClient.post<RentTerm>(
        API_ENDPOINTS.RENT_CONTRACT.ADD_TERM(contractId),
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`添加租金条款失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 租金台账相关API ====================

  /**
   * 获取租金台账列表
   */
  async getRentLedgers(params?: RentLedgerQueryParams): Promise<RentLedgerListResponse> {
    try {
      const { pageSize, page_size, ...rest } = params ?? {};
      const result = await apiClient.get<RentLedgerListResponse>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER_LIST,
        {
          params: { ...rest, page: params?.page ?? 1, page_size: page_size ?? pageSize ?? 10 },
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取租金台账列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // eslint-disable-next-line no-console
      console.error('获取租金台账列表失败:', enhancedError.message);

      // 返回默认空结果，避免UI崩溃
      return {
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        pages: 0,
      };
    }
  }

  /**
   * 获取租金台账详情
   */
  async getRentLedger(id: string): Promise<RentLedger> {
    try {
      const result = await apiClient.get<RentLedger>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER_DETAIL(id),
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取租金台账详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新租金台账
   */
  async updateRentLedger(id: string, data: RentLedgerUpdate): Promise<RentLedger> {
    try {
      const result = await apiClient.put<RentLedger>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER_UPDATE(id),
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`更新租金台账失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量更新租金台账
   */
  async batchUpdateRentLedger(
    data: RentLedgerBatchUpdate
  ): Promise<{ message: string; ledgers: RentLedger[] }> {
    try {
      const result = await apiClient.put<{ message: string; ledgers: RentLedger[] }>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER_BATCH_UPDATE,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`批量更新租金台账失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 生成月度租金台账
   */
  async generateMonthlyLedger(
    data: GenerateLedgerRequest
  ): Promise<{ message: string; ledgers: RentLedger[] }> {
    try {
      const result = await apiClient.post<{ message: string; ledgers: RentLedger[] }>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER_GENERATE,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`生成月度台账失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 统计相关API ====================

  /**
   * 获取租金统计概览
   */
  async getRentStatistics(params?: RentStatisticsQuery): Promise<RentStatisticsOverview> {
    try {
      const result = await apiClient.get<RentStatisticsOverview>(
        API_ENDPOINTS.RENT_CONTRACT.STATISTICS_OVERVIEW,
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取租金统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取租金统计概览 (别名方法)
   */
  async getStatisticsOverview(params?: RentStatisticsQuery): Promise<RentStatisticsOverview> {
    return this.getRentStatistics(params);
  }

  /**
   * 获取权属方租金统�?   */
  async getOwnershipStatistics(params?: RentStatisticsQuery): Promise<OwnershipRentStatistics[]> {
    try {
      const result = await apiClient.get<OwnershipRentStatistics[]>(
        API_ENDPOINTS.RENT_CONTRACT.STATISTICS_OWNERSHIP,
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取权属方租金统计失�? ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取资产租金统计
   */
  async getAssetStatistics(params?: RentStatisticsQuery): Promise<AssetRentStatistics[]> {
    try {
      const result = await apiClient.get<AssetRentStatistics[]>(
        API_ENDPOINTS.RENT_CONTRACT.STATISTICS_ASSET,
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取资产租金统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取月度租金统计
   */
  async getMonthlyStatistics(params?: {
    year?: number;
    start_month?: string;
    end_month?: string;
  }): Promise<MonthlyRentStatistics[]> {
    try {
      const result = await apiClient.get<MonthlyRentStatistics[]>(
        API_ENDPOINTS.RENT_CONTRACT.STATISTICS_MONTHLY,
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取月度租金统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 导出相关API ====================

  /**
   * 导出统计数据
   */
  async exportStatistics(params?: RentStatisticsQuery): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(
        API_ENDPOINTS.RENT_CONTRACT.STATISTICS_EXPORT,
        {
          params,
          responseType: 'blob',
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        }
      );

      if (!result.success) {
        throw new Error(`导出统计数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 导出合同数据到Excel
   */
  async exportContractsToExcel(filters?: Record<string, unknown>): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(
        API_ENDPOINTS.RENT_CONTRACT.CONTRACTS_EXPORT,
        {
          params: filters,
          responseType: 'blob',
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        }
      );

      if (!result.success) {
        throw new Error(`导出合同Excel失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 导出台账数据到Excel
   */
  async exportLedgersToExcel(filters?: Record<string, unknown>): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(API_ENDPOINTS.RENT_CONTRACT.LEDGER_EXPORT, {
        params: filters,
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

      if (!result.success) {
        throw new Error(`导出台账Excel失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 辅助API ====================

  /**
   * 获取合同对应的租金台�?   */
  async getContractLedger(contractId: string): Promise<RentLedger[]> {
    try {
      const result = await apiClient.get<RentLedger[]>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER(contractId),
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取合同台账失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取资产对应的租赁合�?   */
  async getAssetContracts(assetId: string): Promise<RentContract[]> {
    try {
      const result = await apiClient.get<RentContract[]>(
        `${API_ENDPOINTS.ASSET.DETAIL(assetId)}/contracts`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取资产合同失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== V2: 押金台账 ====================

  /**
   * V2: 获取合同押金变动记录
   */
  async getContractDepositLedger(contractId: string): Promise<DepositLedger[]> {
    try {
      const result = await apiClient.get<DepositLedger[]>(
        `${this.baseUrl}/${contractId}/deposit-ledger`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取押金变动记录失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // 返回空数组，避免UI崩溃
      // eslint-disable-next-line no-console
      console.warn('获取押金变动记录失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * V2: 获取合同服务费台账
   */
  async getServiceFeeLedgers(contractId: string): Promise<ServiceFeeLedger[]> {
    try {
      const result = await apiClient.get<ServiceFeeLedger[]>(
        `${this.baseUrl}/${contractId}/service-fee-ledger`,
        {
          cache: true,
          retry: { maxAttempts: 2, delay: 1000, backoffMultiplier: 1 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取服务费台账失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      // eslint-disable-next-line no-console
      console.warn('获取服务费台账失败:', enhancedError.message);
      return [];
    }
  }

  // ==================== 批量操作 ====================

  /**
   * 批量删除合同
   */
  async batchDeleteContracts(
    contractIds: string[]
  ): Promise<{ deleted: number; errors: string[] }> {
    const errors: string[] = [];
    let deleted = 0;

    for (const id of contractIds) {
      try {
        await this.deleteContract(id);
        deleted++;
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        errors.push(`合同 ${id}: ${enhancedError.message}`);
      }
    }

    return { deleted, errors };
  }

  // ==================== V2: 续签和终止 ====================

  /**
   * V2: 合同续签
   * @param originalContractId 原合同ID
   * @param newContractData 新合同数据
   * @param transferDeposit 是否转移押金
   */
  async renewContract(
    originalContractId: string,
    newContractData: RentContractCreate,
    transferDeposit: boolean = true
  ): Promise<RentContract> {
    try {
      const result = await apiClient.post<RentContract>(
        `${this.baseUrl}/${originalContractId}/renew`,
        {
          new_contract_data: newContractData,
          transfer_deposit: transferDeposit,
        },
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`合同续签失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * V2: 合同终止
   * @param contractId 合同ID
   * @param terminationDate 终止日期
   * @param refundDeposit 是否退还押金
   * @param deductionAmount 抵扣金额
   * @param terminationReason 终止原因
   */
  async terminateContract(
    contractId: string,
    terminationDate: string,
    refundDeposit: boolean = true,
    deductionAmount: number = 0,
    terminationReason?: string
  ): Promise<RentContract> {
    try {
      const result = await apiClient.post<RentContract>(
        `${this.baseUrl}/${contractId}/terminate`,
        {
          termination_date: terminationDate,
          refund_deposit: refundDeposit,
          deduction_amount: deductionAmount,
          termination_reason: terminationReason,
        },
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`合同终止失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 批量生成月度台账
   */
  async batchGenerateLedger(
    contractIds: string[]
  ): Promise<{ generated: number; errors: string[] }> {
    const errors: string[] = [];
    let generated = 0;

    for (const id of contractIds) {
      try {
        await this.generateMonthlyLedger({ contract_id: id });
        generated++;
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        errors.push(`合同 ${id}: ${enhancedError.message}`);
      }
    }

    return { generated, errors };
  }

  // ==================== 验证相关方法 ====================

  /**
   * 验证合同编号唯一�?   */
  async validateContractNumber(contractNumber: string): Promise<{ exists: boolean }> {
    try {
      const contracts = await this.getContracts({ contract_number: contractNumber, page_size: 1 });
      return { exists: contracts.items.length > 0 };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('验证合同编号失败', { error: enhancedError.message });
      return { exists: false };
    }
  }

  /**
   * 验证租金条款时间连续性
   */
  async validateRentTerms(
    _contractId: string,
    terms: RentTermCreate[]
  ): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    // 验证时间范围连续性
    const sortedTerms = [...terms].sort(
      (a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime()
    );

    for (let i = 0; i < sortedTerms.length - 1; i++) {
      const current = sortedTerms[i];
      const next = sortedTerms[i + 1];

      if (new Date(current.end_date).getTime() !== new Date(next.start_date).getTime()) {
        errors.push(`第 ${i + 1} 个条款和第 ${i + 2} 个条款的时间范围不连续`);
      }
    }

    return Promise.resolve({ valid: errors.length === 0, errors });
  }

  // ==================== 计算相关方法 ====================

  /**
   * 计算总租金
   */
  calculateTotalRentAmount(terms: RentTerm[]): number {
    return terms.reduce((total, term) => total + term.monthly_rent, 0);
  }

  /**
   * 计算平均租金
   */
  calculateAverageRent(terms: RentTerm[]): number {
    if (terms.length === 0) {
      return 0;
    }
    return this.calculateTotalRentAmount(terms) / terms.length;
  }

  /**
   * 计算合同持续时间（天数）
   */
  calculateContractDuration(startDate: string, endDate: string): number {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  }

  // ==================== 搜索和筛�?====================

  /**
   * 搜索合同
   */
  async searchContracts(query: string): Promise<RentContract[]> {
    try {
      const response = await this.getContracts({
        tenant_name: query,
        contract_number: query,
        page_size: 10,
      });
      return response.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('搜索合同失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 搜索台账
   */
  async searchLedgers(_query: string): Promise<RentLedger[]> {
    try {
      const response = await this.getRentLedgers({
        page_size: 10,
        // 可以添加更多搜索条件
      });
      return response.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('搜索台账失败', { error: enhancedError.message });
      return [];
    }
  }

  // ==================== 通知和提�?====================

  /**
   * 获取逾期台账记录
   */
  async getOverdueLedgers(): Promise<RentLedger[]> {
    try {
      const response = await this.getRentLedgers({
        payment_status: '逾期',
        page_size: 100,
      });
      return response.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取逾期台账失败', { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取即将到期的付款记�?   */
  async getUpcomingPayments(days: number = 7): Promise<RentLedger[]> {
    try {
      const today = new Date();
      const futureDate = new Date(today.getTime() + days * 24 * 60 * 60 * 1000);

      const response = await this.getRentLedgers({
        start_date: today.toISOString().split('T')[0],
        end_date: futureDate.toISOString().split('T')[0],
        payment_status: '未支付',
        page_size: 100,
      });
      return response.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      logger.warn('获取即将到期付款失败', { error: enhancedError.message });
      return [];
    }
  }
}

// 创建单例实例
export const rentContractService = new RentContractService();
export { RentContractService };
