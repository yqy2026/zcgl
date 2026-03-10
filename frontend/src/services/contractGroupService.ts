import { apiClient } from '@/api/client';
import { API_ENDPOINTS } from '@/constants/api';
import type {
  ContractGroupCreate,
  ContractGroupDetail,
  ContractGroupListParams,
  ContractGroupListResponse,
  ContractGroupUpdate,
} from '@/types/contractGroup';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { createLogger } from '@/utils/logger';

const contractGroupLogger = createLogger('ContractGroup');

export class ContractGroupService {
  private readonly baseUrl = API_ENDPOINTS.CONTRACT_GROUP.LIST;

  async getContractGroups(params: ContractGroupListParams = {}): Promise<ContractGroupListResponse> {
    try {
      const requestParams = {
        offset: params.offset ?? 0,
        limit: params.limit ?? 20,
        ...(params.operator_party_id != null && params.operator_party_id.trim() !== ''
          ? { operator_party_id: params.operator_party_id }
          : {}),
        ...(params.owner_party_id != null && params.owner_party_id.trim() !== ''
          ? { owner_party_id: params.owner_party_id }
          : {}),
        ...(params.revenue_mode != null ? { revenue_mode: params.revenue_mode } : {}),
      };

      const result = await apiClient.get<ContractGroupListResponse>(this.baseUrl, {
        params: requestParams,
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取合同组列表失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      contractGroupLogger.error('获取合同组列表失败', error as Error);
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async getContractGroup(id: string): Promise<ContractGroupDetail> {
    try {
      const result = await apiClient.get<ContractGroupDetail>(API_ENDPOINTS.CONTRACT_GROUP.DETAIL(id), {
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取合同组详情失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      contractGroupLogger.error('获取合同组详情失败', error as Error);
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async createContractGroup(payload: ContractGroupCreate): Promise<ContractGroupDetail> {
    try {
      const result = await apiClient.post<ContractGroupDetail>(API_ENDPOINTS.CONTRACT_GROUP.CREATE, payload, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`创建合同组失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      contractGroupLogger.error('创建合同组失败', error as Error);
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async updateContractGroup(id: string, payload: ContractGroupUpdate): Promise<ContractGroupDetail> {
    try {
      const result = await apiClient.put<ContractGroupDetail>(API_ENDPOINTS.CONTRACT_GROUP.UPDATE(id), payload, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`更新合同组失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      contractGroupLogger.error('更新合同组失败', error as Error);
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

export const contractGroupService = new ContractGroupService();
