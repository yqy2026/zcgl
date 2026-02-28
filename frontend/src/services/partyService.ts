import { apiClient } from '@/api/client';
import type { ApiClientError } from '@/types/apiResponse';
import type { Party, PartyListParams, PartyType } from '@/types/party';
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
