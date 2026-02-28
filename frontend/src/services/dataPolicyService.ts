import { apiClient } from '@/api/client';
import type {
  DataPolicyTemplateItem,
  DataPolicyTemplatesResponse,
  RoleDataPoliciesResponse,
  RoleDataPoliciesUpdateRequest,
} from '@/types/dataPolicy';
import { ApiErrorHandler } from '@/utils/responseExtractor';

const ROLE_DATA_POLICIES_ENDPOINT = (roleId: string) => `/auth/roles/${roleId}/data-policies`;
const DATA_POLICY_TEMPLATES_ENDPOINT = '/auth/data-policies/templates';

export class DataPolicyService {
  async getRoleDataPolicies(roleId: string): Promise<RoleDataPoliciesResponse> {
    try {
      const result = await apiClient.get<RoleDataPoliciesResponse>(
        ROLE_DATA_POLICIES_ENDPOINT(roleId),
        {
          cache: false,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`获取角色数据策略失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async updateRoleDataPolicies(
    roleId: string,
    payload: RoleDataPoliciesUpdateRequest
  ): Promise<RoleDataPoliciesResponse> {
    try {
      const result = await apiClient.put<RoleDataPoliciesResponse>(
        ROLE_DATA_POLICIES_ENDPOINT(roleId),
        payload,
        {
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`更新角色数据策略失败: ${result.error}`);
      }

      return result.data;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  async getDataPolicyTemplates(): Promise<DataPolicyTemplateItem[]> {
    try {
      const result = await apiClient.get<DataPolicyTemplatesResponse>(
        DATA_POLICY_TEMPLATES_ENDPOINT,
        {
          cache: true,
          retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success || result.data == null) {
        throw new Error(`获取策略模板失败: ${result.error}`);
      }

      return Object.entries(result.data).map(([code, template]) => ({
        code,
        name: template.name,
        description: template.description,
      }));
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }
}

export const dataPolicyService = new DataPolicyService();
