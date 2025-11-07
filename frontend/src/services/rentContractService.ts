/**
 * 租金台账相关的API服务
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
  RentLedgerQueryParams
} from '../types/rentContract';
import { apiClient } from './api';
import { API_CONFIG, API_ENDPOINTS } from '@/constants/api';

class RentContractService {
  private baseUrl = API_ENDPOINTS.RENT_CONTRACT.LIST;

  // 租金合同相关API
  async getContracts(params?: RentContractQueryParams): Promise<RentContractListResponse> {
    try {
      const response = await apiClient.get(this.baseUrl, { params });

      // 确保响应数据存在且格式正确
      if (!response) {
        throw new Error('API响应数据为空');
      }

      // 确保返回的数据结构符合预期 - 直接使用response，因为apiClient已经解包了数据
      const result = response as RentContractListResponse;
      if (!Array.isArray(result.items)) {
        console.warn('API响应中的items不是数组，使用空数组作为默认值');
        result.items = [];
      }

      return result;
    } catch (error) {
      console.error('获取租金合同列表失败:', error);
      // 返回一个默认的空结果，而不是抛出错误
      return {
        items: [],
        total: 0,
        page: 1,
        limit: 10,
        pages: 0,
      };
    }
  }

  async getContract(id: string): Promise<RentContract> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.DETAIL(id));
    return response as RentContract;
  }

  async createContract(data: RentContractCreate): Promise<RentContract> {
    const response = await apiClient.post(API_ENDPOINTS.RENT_CONTRACT.CREATE, data);
    return response as RentContract;
  }

  async updateContract(id: string, data: RentContractUpdate): Promise<RentContract> {
    const response = await apiClient.put(API_ENDPOINTS.RENT_CONTRACT.UPDATE(id), data);
    return response as RentContract;
  }

  async deleteContract(id: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.RENT_CONTRACT.DELETE(id));
  }

  // 租金条款相关API
  async getContractTerms(contractId: string): Promise<RentTerm[]> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.TERMS(contractId));
    return response as RentTerm[];
  }

  async addRentTerm(contractId: string, data: RentTermCreate): Promise<RentTerm> {
    const response = await apiClient.post(API_ENDPOINTS.RENT_CONTRACT.ADD_TERM(contractId), data);
    return response as RentTerm;
  }

  // 租金台账相关API
  async getRentLedgers(params?: RentLedgerQueryParams): Promise<RentLedgerListResponse> {
    try {
      const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.LEDGER_LIST, { params });

      // 确保响应数据存在且格式正确
      if (!response) {
        throw new Error('API响应数据为空');
      }

      // 确保返回的数据结构符合预期 - 直接使用response，因为apiClient已经解包了数据
      const result = response as RentLedgerListResponse;
      if (!Array.isArray(result.items)) {
        console.warn('API响应中的items不是数组，使用空数组作为默认值');
        result.items = [];
      }

      return result;
    } catch (error) {
      console.error('获取租金台账列表失败:', error);
      // 返回一个默认的空结果，而不是抛出错误
      return {
        items: [],
        total: 0,
        page: 1,
        limit: 10,
        pages: 0,
      };
    }
  }

  async getRentLedger(id: string): Promise<RentLedger> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.LEDGER_DETAIL(id));
    return response as RentLedger;
  }

  async updateRentLedger(id: string, data: RentLedgerUpdate): Promise<RentLedger> {
    const response = await apiClient.put(API_ENDPOINTS.RENT_CONTRACT.LEDGER_UPDATE(id), data);
    return response as RentLedger;
  }

  async batchUpdateRentLedger(data: RentLedgerBatchUpdate): Promise<{ message: string; ledgers: RentLedger[] }> {
    const response = await apiClient.put(API_ENDPOINTS.RENT_CONTRACT.LEDGER_BATCH_UPDATE, data);
    return response as { message: string; ledgers: RentLedger[] };
  }

  async generateMonthlyLedger(data: GenerateLedgerRequest): Promise<{ message: string; ledgers: RentLedger[] }> {
    const response = await apiClient.post(API_ENDPOINTS.RENT_CONTRACT.LEDGER_GENERATE, data);
    return response as { message: string; ledgers: RentLedger[] };
  }

  // 统计相关API
  async getRentStatistics(params?: RentStatisticsQuery): Promise<RentStatisticsOverview> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.STATISTICS_OVERVIEW, { params });
    return response as RentStatisticsOverview;
  }

  async getStatisticsOverview(params?: RentStatisticsQuery): Promise<RentStatisticsOverview> {
    return this.getRentStatistics(params);
  }

  async getOwnershipStatistics(params?: RentStatisticsQuery): Promise<OwnershipRentStatistics[]> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.STATISTICS_OWNERSHIP, { params });
    return response as OwnershipRentStatistics[];
  }

  async getAssetStatistics(params?: RentStatisticsQuery): Promise<AssetRentStatistics[]> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.STATISTICS_ASSET, { params });
    return response as AssetRentStatistics[];
  }

  async getMonthlyStatistics(params?: { year?: number; start_month?: string; end_month?: string }): Promise<MonthlyRentStatistics[]> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.STATISTICS_MONTHLY, { params });
    return response as MonthlyRentStatistics[];
  }

  // 导出统计相关方法
  async exportStatistics(params?: RentStatisticsQuery): Promise<Blob> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.STATISTICS_EXPORT, {
      params,
      responseType: 'blob'
    });
    return response.data;
  }

  // 辅助API
  async getContractLedger(contractId: string): Promise<RentLedger[]> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.LEDGER(contractId));
    return response as RentLedger[];
  }

  async getAssetContracts(assetId: string): Promise<RentContract[]> {
    const response = await apiClient.get(API_ENDPOINTS.ASSET.DETAIL(assetId) + '/contracts');
    return response as RentContract[];
  }

  // 批量操作
  async batchDeleteContracts(contractIds: string[]): Promise<void> {
    await Promise.all(contractIds.map(id => this.deleteContract(id)));
  }

  async batchGenerateLedger(contractIds: string[]): Promise<{ generated: number; errors: string[] }> {
    const results = await Promise.allSettled(
      contractIds.map(id => this.generateMonthlyLedger({ contract_id: id }))
    );

    const generated = results.filter(result => result.status === 'fulfilled').length;
    const errors = results
      .filter(result => result.status === 'rejected')
      .map(result => (result as PromiseRejectedResult).reason.message || '未知错误');

    return { generated, errors };
  }

  // 验证相关方法
  async validateContractNumber(contractNumber: string): Promise<{ exists: boolean }> {
    try {
      const contracts = await this.getContracts({ contract_number: contractNumber, limit: 1 });
      return { exists: contracts.items.length > 0 };
    } catch (error) {
      return { exists: false };
    }
  }

  async validateRentTerms(_contractId: string, terms: RentTermCreate[]): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    // 验证时间范围连续性
    const sortedTerms = [...terms].sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime());

    for (let i = 0; i < sortedTerms.length - 1; i++) {
      const current = sortedTerms[i];
      const next = sortedTerms[i + 1];

      if (new Date(current.end_date).getTime() !== new Date(next.start_date).getTime()) {
        errors.push(`第 ${i + 1} 个条款和第 ${i + 2} 个条款的时间范围不连续`);
      }
    }

    return { valid: errors.length === 0, errors };
  }

  // 计算相关方法
  calculateTotalRentAmount(terms: RentTerm[]): number {
    return terms.reduce((total, term) => total + term.monthly_rent, 0);
  }

  calculateAverageRent(terms: RentTerm[]): number {
    if (terms.length === 0) return 0;
    return this.calculateTotalRentAmount(terms) / terms.length;
  }

  calculateContractDuration(startDate: string, endDate: string): number {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  }

  // 导出相关方法
  async exportContractsToExcel(filters?: Record<string, unknown>): Promise<Blob> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.CONTRACTS_EXPORT, {
      params: filters,
      responseType: 'blob'
    });
    return response as Blob;
  }

  async exportLedgersToExcel(filters?: Record<string, unknown>): Promise<Blob> {
    const response = await apiClient.get(API_ENDPOINTS.RENT_CONTRACT.LEDGER_EXPORT, {
      params: filters,
      responseType: 'blob'
    });
    return response as Blob;
  }

  // 搜索和筛选
  async searchContracts(query: string): Promise<RentContract[]> {
    const response = await this.getContracts({
      tenant_name: query,
      contract_number: query,
      limit: 10
    });
    return response.items;
  }

  async searchLedgers(_query: string): Promise<RentLedger[]> {
    const response = await this.getRentLedgers({
      limit: 10,
      // 可以添加更多搜索条件
    });
    return response.items;
  }

  // 通知和提醒
  async getOverdueLedgers(): Promise<RentLedger[]> {
    const response = await this.getRentLedgers({
      payment_status: '逾期',
      limit: 100
    });
    return response.items;
  }

  async getUpcomingPayments(days: number = 7): Promise<RentLedger[]> {
    const today = new Date();
    const futureDate = new Date(today.getTime() + days * 24 * 60 * 60 * 1000);

    const response = await this.getRentLedgers({
      start_date: today.toISOString().split('T')[0],
      end_date: futureDate.toISOString().split('T')[0],
      payment_status: '未支付',
      limit: 100
    });
    return response.items;
  }

  }

// 创建单例实例
export const rentContractService = new RentContractService();

// 为了向后兼容，也导出类
export { RentContractService };
