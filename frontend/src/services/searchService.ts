import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import type { GlobalSearchResponse } from '@/types/search';

export class SearchService {
  async searchGlobal(query: string): Promise<GlobalSearchResponse> {
    try {
      const result = await apiClient.get<GlobalSearchResponse>('/search', {
        params: { q: query.trim() },
        cache: false,
        retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
        smartExtract: true,
      });

      if (!result.success || result.data == null) {
        throw new Error(`全局搜索失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

export const searchService = new SearchService();
