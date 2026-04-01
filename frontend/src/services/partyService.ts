import { apiClient } from '@/api/client';
import type { ApiClientError } from '@/types/apiResponse';
import type { CustomerProfile, Party, PartyListParams, PartyType } from '@/types/party';
import { ApiErrorHandler } from '@/utils/responseExtractor';

const DEFAULT_SEARCH_LIMIT = 20;
const PARTY_BASE_URL = '/parties';

type PartyListRawResponse =
  | Party[]
  | {
      items?: Party[];
      total?: number;
      skip?: number;
      limit?: number;
    };

export interface PartyListResult {
  items: Party[];
  total?: number;
  skip: number;
  limit: number;
  isTruncated: boolean;
}

export interface PartyCreatePayload {
  party_type: PartyType;
  name: string;
  code: string;
  external_ref?: string | null;
  status?: string;
  metadata?: Record<string, unknown>;
}

export type PartyUpdatePayload = Partial<PartyCreatePayload>;

export interface PartyReviewRejectPayload {
  reason: string;
}

export interface PartyImportPayload {
  items: PartyCreatePayload[];
}

export interface PartyImportResult {
  created_count: number;
  error_count: number;
  items: Array<{
    index: number;
    status: string;
    party_id: string | null;
    message: string | null;
  }>;
}

export interface PartyReviewLog {
  id: string;
  party_id: string;
  action: string;
  from_status: string;
  to_status: string;
  operator?: string | null;
  reason?: string | null;
  created_at: string;
}

const normalizePartyList = (
  responseData: PartyListRawResponse,
  request: { skip: number; limit: number }
): PartyListResult => {
  if (Array.isArray(responseData)) {
    return {
      items: responseData,
      total: undefined,
      skip: request.skip,
      limit: request.limit,
      isTruncated: responseData.length >= request.limit,
    };
  }

  const items = Array.isArray(responseData.items) ? responseData.items : [];
  const skip = responseData.skip ?? request.skip;
  const limit = responseData.limit ?? request.limit;
  const total = responseData.total;

  return {
    items,
    total,
    skip,
    limit,
    isTruncated: typeof total === 'number' ? skip + items.length < total : items.length >= limit,
  };
};

const toServiceError = (enhancedError: ApiClientError): Error => {
  const serviceError = new Error(enhancedError.message);
  Object.assign(serviceError, {
    code: enhancedError.code,
    statusCode: enhancedError.statusCode,
    type: enhancedError.type,
    requestId: enhancedError.requestId,
    details: enhancedError.details,
    originalError: enhancedError.originalError,
  });
  return serviceError;
};

export class PartyService {
  async getParties(params: PartyListParams = {}): Promise<PartyListResult> {
    try {
      const requestParams = {
        party_type: params.party_type,
        status: params.status,
        search: params.search,
        skip: params.skip ?? 0,
        limit: params.limit ?? 100,
      };

      const result = await apiClient.get<PartyListRawResponse>(PARTY_BASE_URL, {
        params: requestParams,
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取主体列表失败: ${result.error}`);
      }

      return normalizePartyList(result.data, {
        skip: requestParams.skip,
        limit: requestParams.limit,
      });
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async searchParties(
    query: string,
    params: Omit<PartyListParams, 'search'> = {}
  ): Promise<PartyListResult> {
    const normalizedQuery = query.trim();
    return this.getParties({
      ...params,
      search: normalizedQuery !== '' ? normalizedQuery : undefined,
      limit: params.limit ?? DEFAULT_SEARCH_LIMIT,
    });
  }

  async getPartyById(id: string): Promise<Party> {
    try {
      const result = await apiClient.get<Party>(`${PARTY_BASE_URL}/${id}`, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取主体详情失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async getCustomerProfile(id: string): Promise<CustomerProfile> {
    try {
      const result = await apiClient.get<CustomerProfile>(`/customers/${id}`, {
        cache: true,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取客户档案失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async createParty(payload: PartyCreatePayload): Promise<Party> {
    try {
      const result = await apiClient.post<Party>(PARTY_BASE_URL, payload, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`创建主体失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async updateParty(id: string, payload: PartyUpdatePayload): Promise<Party> {
    try {
      const result = await apiClient.put<Party>(`${PARTY_BASE_URL}/${id}`, payload, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`更新主体失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async submitReview(id: string): Promise<Party> {
    try {
      const result = await apiClient.post<Party>(
        `${PARTY_BASE_URL}/${id}/submit-review`,
        undefined,
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`提交主体审核失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async approveReview(id: string): Promise<Party> {
    try {
      const result = await apiClient.post<Party>(
        `${PARTY_BASE_URL}/${id}/approve-review`,
        undefined,
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`审核通过主体失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async rejectReview(id: string, payload: PartyReviewRejectPayload): Promise<Party> {
    try {
      const result = await apiClient.post<Party>(`${PARTY_BASE_URL}/${id}/reject-review`, payload, {
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`驳回主体审核失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async importParties(payload: PartyImportPayload): Promise<PartyImportResult> {
    try {
      const result = await apiClient.post<PartyImportResult>(`${PARTY_BASE_URL}/import`, payload, {
        retry: { maxAttempts: 1, delay: 0, backoffMultiplier: 1 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`批量导入主体失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async getReviewLogs(id: string): Promise<PartyReviewLog[]> {
    try {
      const result = await apiClient.get<PartyReviewLog[]>(`${PARTY_BASE_URL}/${id}/review-logs`, {
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取主体日志失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }

  async getPartyHierarchy(partyId: string, includeSelf: boolean = false): Promise<string[]> {
    try {
      const result = await apiClient.get<string[]>(`${PARTY_BASE_URL}/${partyId}/hierarchy`, {
        params: includeSelf === true ? { include_self: true } : undefined,
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`获取主体层级失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw toServiceError(enhancedError);
    }
  }
}

export const partyService = new PartyService();
