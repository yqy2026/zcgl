/**
 * Asset History Service
 * 资产历史记录相关操作
 */

import { enhancedApiClient } from "@/api/client";
import { ApiErrorHandler } from "../../utils/responseExtractor";
import { ASSET_API } from "../../constants/api";
import type {
    AssetHistory,
    PaginatedApiResponse,
    HistoryComparisonResult,
    FieldHistoryRecord,
} from "./types";

/**
 * 资产历史服务类
 * 提供资产变更历史的查询和比较功能
 */
export class AssetHistoryService {
    /**
     * 获取资产变更历史
     */
    async getAssetHistory(
        assetId: string,
        page = 1,
        limit = 20,
        changeType?: string,
    ): Promise<PaginatedApiResponse<AssetHistory>> {
        try {
            const result = await enhancedApiClient.get<PaginatedApiResponse<AssetHistory>>(
                `${ASSET_API.DETAIL(assetId)}/history`,
                {
                    params: { page, limit, change_type: changeType },
                    cache: true,
                    retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                    smartExtract: true
                }
            );

            if (!result.success) {
                throw new Error(`获取资产历史失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取历史记录详情
     */
    async getHistoryDetail(historyId: string): Promise<AssetHistory> {
        try {
            const result = await enhancedApiClient.get<AssetHistory>(`/history/${historyId}`, {
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取历史详情失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 比较历史记录
     */
    async compareHistory(historyId1: string, historyId2: string): Promise<HistoryComparisonResult> {
        try {
            const result = await enhancedApiClient.get<HistoryComparisonResult>(
                `/history/compare/${historyId1}/${historyId2}`,
                {
                    cache: true,
                    retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                    smartExtract: true
                }
            );

            if (!result.success) {
                throw new Error(`比较历史记录失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取字段变更历史
     */
    async getFieldHistory(
        assetId: string,
        fieldName: string,
        limit = 10,
    ): Promise<FieldHistoryRecord[]> {
        try {
            const result = await enhancedApiClient.get<{ history: FieldHistoryRecord[] }>(
                `${ASSET_API.DETAIL(assetId)}/field-history/${fieldName}`,
                {
                    params: { limit },
                    cache: true,
                    retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                    smartExtract: true
                }
            );

            if (!result.success) {
                throw new Error(`获取字段历史失败: ${result.error}`);
            }

            return result.data!.history || [];
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }
}

// 导出服务实例
export const assetHistoryService = new AssetHistoryService();
