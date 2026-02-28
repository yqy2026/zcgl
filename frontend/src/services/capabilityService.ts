import { apiClient } from '@/api/client';
import type { CapabilitiesResponse, CapabilityItem } from '@/types/capability';
import { ApiErrorHandler } from '@/utils/responseExtractor';

const CAPABILITIES_ENDPOINT = '/auth/me/capabilities';
const CAPABILITIES_CACHE_TTL_MS = 10 * 60 * 1000;

interface CapabilitiesCache {
  cachedAt: number;
  value: CapabilitiesResponse;
}

const normalizeCapabilityItem = (item: CapabilityItem): CapabilityItem => {
  return {
    resource: item.resource,
    actions: Array.isArray(item.actions) ? item.actions : [],
    perspectives: Array.isArray(item.perspectives) ? item.perspectives : [],
    data_scope: {
      owner_party_ids: Array.isArray(item.data_scope?.owner_party_ids)
        ? item.data_scope.owner_party_ids
        : [],
      manager_party_ids: Array.isArray(item.data_scope?.manager_party_ids)
        ? item.data_scope.manager_party_ids
        : [],
    },
  };
};

const normalizeCapabilitiesResponse = (
  payload: Partial<CapabilitiesResponse> | null | undefined
): CapabilitiesResponse => {
  const normalizedCapabilities = Array.isArray(payload?.capabilities)
    ? payload.capabilities.map(item => normalizeCapabilityItem(item))
    : [];

  return {
    version: typeof payload?.version === 'string' ? payload.version : 'v1',
    generated_at:
      typeof payload?.generated_at === 'string' && payload.generated_at !== ''
        ? payload.generated_at
        : new Date().toISOString(),
    capabilities: normalizedCapabilities,
  };
};

export class CapabilityService {
  private cache: CapabilitiesCache | null = null;
  private inFlightRequest: Promise<CapabilitiesResponse> | null = null;
  private generation = 0;
  private requestToken = 0;

  private isCacheFresh(cache: CapabilitiesCache): boolean {
    return Date.now() - cache.cachedAt < CAPABILITIES_CACHE_TTL_MS;
  }

  private async requestCapabilities(): Promise<CapabilitiesResponse> {
    const result = await apiClient.get<CapabilitiesResponse>(CAPABILITIES_ENDPOINT, {
      cache: false,
      retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
      smartExtract: true,
    });

    if (!result.success) {
      throw new Error(`获取能力清单失败: ${result.error}`);
    }

    return normalizeCapabilitiesResponse(result.data);
  }

  getCachedCapabilities(): CapabilitiesResponse | null {
    if (this.cache == null || this.isCacheFresh(this.cache) === false) {
      return null;
    }
    return this.cache.value;
  }

  setCachedCapabilities(value: CapabilitiesResponse, cachedAt: number = Date.now()): void {
    this.cache = {
      value: normalizeCapabilitiesResponse(value),
      cachedAt,
    };
  }

  clearCache(): void {
    this.generation += 1;
    this.cache = null;
    this.inFlightRequest = null;
  }

  async fetchCapabilities(options: { forceRefresh?: boolean } = {}): Promise<CapabilitiesResponse> {
    const forceRefresh = options.forceRefresh === true;
    const generation = this.generation;

    if (!forceRefresh) {
      const cached = this.getCachedCapabilities();
      if (cached != null) {
        return cached;
      }
      if (this.inFlightRequest != null) {
        return this.inFlightRequest;
      }
    }

    const token = ++this.requestToken;
    this.inFlightRequest = this.requestCapabilities()
      .then(response => {
        if (this.generation === generation && this.requestToken === token) {
          this.setCachedCapabilities(response);
        }
        return response;
      })
      .finally(() => {
        if (this.requestToken === token) {
          this.inFlightRequest = null;
        }
      });

    return this.inFlightRequest;
  }

  async getCapabilities(options: { forceRefresh?: boolean } = {}): Promise<CapabilitiesResponse> {
    try {
      return await this.fetchCapabilities(options);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

export const capabilityService = new CapabilityService();
