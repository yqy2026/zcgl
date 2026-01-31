/**
 * API Layer - Centralized API client and configuration
 * @module api
 */

// Export the main API client
export { apiClient, ApiClient, createApiClient } from './client';

// Export API configuration
export { API_CONFIG, ERROR_CODES, HTTP_STATUS } from './config';
export { API_ENDPOINTS } from '@/constants/api';

// Export types
export type {
  StandardApiResponse,
  PaginatedApiResponse,
  ApiClientConfig,
  ApiClientError,
  RetryConfig,
  CacheConfig,
} from '@/types/apiResponse';
