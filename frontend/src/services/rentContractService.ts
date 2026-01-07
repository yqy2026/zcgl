/**
 * 租金台账相关的API服务 - 统一响应处理版本
 *
 * @description 租赁合同管理核心服务，包含合同、条款、台账、统计等完整功能
 * @author Claude Code
 * @updated 2025-11-10
 */

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
} from '../types/rentContract';
import { enhancedApiClient } from '@/api/client';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { createLogger } from '../utils/logger';
import { API_ENDPOINTS } from '@/constants/api';

const logger = createLogger('RentContractService');

class RentContractService {
  private baseUrl = API_ENDPOINTS.RENT_CONTRACT.LIST;

  // ==================== 租金合同相关API ====================

  /**
   * 获取租金合同列表
   */
  async getContracts(params?: RentContractQueryParams): Promise<RentContractListResponse> {
    try {
      const result = await enhancedApiClient.get<RentContractListResponse>(this.baseUrl, {
        params: { ...params, page: params?.page ?? 1, limit: params?.limit ?? 10 },
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
      console.error('获取租金合同列表失败:', enhancedError.message);

      // 返回默认空结果，避免UI崩溃
      return {
        items: [],
        total: 0,
        page: 1,
        limit: 10,
        pages: 0,
      };
    }
  }

  /**
   * 获取合同详情
   */
  async getContract(id: string): Promise<RentContract> {
    try {
      const result = await enhancedApiClient.get<RentContract>(
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
      const result = await enhancedApiClient.post<RentContract>(
        API_ENDPOINTS.RENT_CONTRACT.CREATE,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
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
      const result = await enhancedApiClient.put<RentContract>(
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
      const result = await enhancedApiClient.delete<void>(API_ENDPOINTS.RENT_CONTRACT.DELETE(id), {
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
      const result = await enhancedApiClient.get<RentTerm[]>(
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
      const result = await enhancedApiClient.post<RentTerm>(
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
      const result = await enhancedApiClient.get<RentLedgerListResponse>(
        API_ENDPOINTS.RENT_CONTRACT.LEDGER_LIST,
        {
          params: { ...params, page: params?.page ?? 1, limit: params?.limit ?? 10 },
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
      console.error('获取租金台账列表失败:', enhancedError.message);

      // 返回默认空结果，避免UI崩溃
      return {
        items: [],
        total: 0,
        page: 1,
        limit: 10,
        pages: 0,
      };
    }
  }

  /**
   * 获取租金台账详情
   */
  async getRentLedger(id: string): Promise<RentLedger> {
    try {
      const result = await enhancedApiClient.get<RentLedger>(
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
      const result = await enhancedApiClient.put<RentLedger>(
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
      const result = await enhancedApiClient.put<{ message: string; ledgers: RentLedger[] }>(
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
      const result = await enhancedApiClient.post<{ message: string; ledgers: RentLedger[] }>(
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
      const result = await enhancedApiClient.get<RentStatisticsOverview>(
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
      const result = await enhancedApiClient.get<OwnershipRentStatistics[]>(
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
      const result = await enhancedApiClient.get<AssetRentStatistics[]>(
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
      const result = await enhancedApiClient.get<MonthlyRentStatistics[]>(
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
      const result = await enhancedApiClient.get<Blob>(
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
      const result = await enhancedApiClient.get<Blob>(
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
      const result = await enhancedApiClient.get<Blob>(API_ENDPOINTS.RENT_CONTRACT.LEDGER_EXPORT, {
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
      const result = await enhancedApiClient.get<RentLedger[]>(
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
      const result = await enhancedApiClient.get<RentContract[]>(
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
      const contracts = await this.getContracts({ contract_number: contractNumber, limit: 1 });
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
        limit: 10,
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
        limit: 10,
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
        limit: 100,
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
        limit: 100,
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

// 为了向后兼容，也导出�?export { RentContractService };
