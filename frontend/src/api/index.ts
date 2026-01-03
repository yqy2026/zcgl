/**
 * API Layer - Centralized API client and configuration
 * @module api
 */

// Export the main API client
export { default as enhancedApiClient } from './client';
export { EnhancedApiClient } from './client';

// Export API configuration
export { API_CONFIG, API_ENDPOINTS, ERROR_CODES, HTTP_STATUS } from './config';

// Export types
export type {
  StandardApiResponse,
  PaginatedApiResponse,
  EnhancedApiClientConfig,
  EnhancedApiError,
  RetryConfig,
  CacheConfig
} from '../types/apiResponse';
