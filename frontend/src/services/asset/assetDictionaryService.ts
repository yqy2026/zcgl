/**
 * Asset Dictionary Service
 * 系统字典管理相关操作
 */

import { enhancedApiClient } from "@/api/client";
import { ApiErrorHandler } from "../../utils/responseExtractor";
import type { SystemDictionary } from "./types";

/**
 * 资产字典服务类
 * 提供系统字典的管理功能
 */
export class AssetDictionaryService {
    /**
     * 获取系统字典列表
     */
    async getSystemDictionaries(dict_type?: string): Promise<SystemDictionary[]> {
        try {
            const result = await enhancedApiClient.get<SystemDictionary[]>("/system-dictionaries", {
                params: dict_type ? { dict_type } : undefined,
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取系统字典失败: ${result.error}`);
            }

            return result.data || [];
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取单个系统字典
     */
    async getSystemDictionary(id: string): Promise<SystemDictionary> {
        try {
            const result = await enhancedApiClient.get<SystemDictionary>(`/system-dictionaries/${id}`, {
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取系统字典详情失败: ${result.error}`);
            }

            return result.data!;
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 创建系统字典
     */
    async createSystemDictionary(
        data: Omit<SystemDictionary, "id" | "created_at" | "updated_at">,
    ): Promise<SystemDictionary> {
        try {
            const result = await enhancedApiClient.post<SystemDictionary>("/system-dictionaries", data, {
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`创建系统字典失败: ${result.error}`);
            }

            return result.data!;
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 更新系统字典
     */
    async updateSystemDictionary(
        id: string,
        data: Partial<SystemDictionary>,
    ): Promise<SystemDictionary> {
        try {
            const result = await enhancedApiClient.put<SystemDictionary>(`/system-dictionaries/${id}`, data, {
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`更新系统字典失败: ${result.error}`);
            }

            return result.data!;
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 删除系统字典
     */
    async deleteSystemDictionary(id: string): Promise<void> {
        try {
            const result = await enhancedApiClient.delete<void>(`/system-dictionaries/${id}`, {
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`删除系统字典失败: ${result.error}`);
            }
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 批量更新系统字典
     */
    async batchUpdateSystemDictionaries(
        updates: Array<{ id: string; data: Partial<SystemDictionary> }>,
    ): Promise<SystemDictionary[]> {
        try {
            const result = await enhancedApiClient.post<SystemDictionary[]>("/system-dictionaries/batch-update", { updates }, {
                retry: false,
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`批量更新系统字典失败: ${result.error}`);
            }

            return result.data || [];
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取字典类型列表
     */
    async getDictionaryTypes(): Promise<{ types: string[] }> {
        try {
            const result = await enhancedApiClient.get<{ types: string[] }>("/system-dictionaries/types/list", {
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取字典类型列表失败: ${result.error}`);
            }

            return result.data || { types: [] };
        } catch (error) {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    // ===== 便捷方法：获取特定类型字典 =====

    /**
     * 获取权属方字典
     */
    async getOwnershipEntitiesFromDict(): Promise<SystemDictionary[]> {
        return this.getSystemDictionaries("ownership_entity");
    }

    /**
     * 获取管理方字典
     */
    async getManagementEntitiesFromDict(): Promise<SystemDictionary[]> {
        return this.getSystemDictionaries("management_entity");
    }

    /**
     * 获取业态类别字典
     */
    async getBusinessCategoriesFromDict(): Promise<SystemDictionary[]> {
        return this.getSystemDictionaries("business_category");
    }

    /**
     * 获取资产状态字典
     */
    async getAssetStatusFromDict(): Promise<SystemDictionary[]> {
        return this.getSystemDictionaries("asset_status");
    }

    /**
     * 获取权属性质字典
     */
    async getOwnershipNatureFromDict(): Promise<SystemDictionary[]> {
        return this.getSystemDictionaries("ownership_nature");
    }

    /**
     * 获取租赁状态字典
     */
    async getLeaseStatusFromDict(): Promise<SystemDictionary[]> {
        return this.getSystemDictionaries("lease_status");
    }
}

// 导出服务实例
export const assetDictionaryService = new AssetDictionaryService();
