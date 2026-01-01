/**
 * Asset Statistics Service
 * 资产统计相关操作
 */

import { enhancedApiClient } from "@/api/client";
import { ApiErrorHandler } from "../../utils/responseExtractor";
import type {
    AssetSearchParams,
    AssetStats,
    OccupancyRateStats,
    AssetDistributionStats,
    AreaStatistics,
    ComprehensiveStats,
} from "./types";

/**
 * 资产统计服务类
 * 提供各类统计数据的查询功能
 */
export class AssetStatisticsService {
    /**
     * 获取资产统计信息
     */
    async getAssetStats(filters?: AssetSearchParams): Promise<AssetStats> {
        try {
            const result = await enhancedApiClient.get<AssetStats>("/statistics/basic", {
                params: filters,
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取资产统计失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取出租率统计数据
     */
    async getOccupancyRateStats(filters?: AssetSearchParams): Promise<OccupancyRateStats> {
        try {
            const result = await enhancedApiClient.get<OccupancyRateStats>("/statistics/occupancy-rate", {
                params: filters,
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取出租率统计失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取资产分布统计数据
     */
    async getAssetDistributionStats(filters?: AssetSearchParams): Promise<AssetDistributionStats> {
        try {
            const result = await enhancedApiClient.get<AssetDistributionStats>("/statistics/distribution", {
                params: filters,
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取资产分布统计失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取面积统计数据
     */
    async getAreaStatistics(filters?: AssetSearchParams): Promise<AreaStatistics> {
        try {
            const result = await enhancedApiClient.get<AreaStatistics>("/statistics/area", {
                params: filters,
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取面积统计失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }

    /**
     * 获取综合统计数据
     */
    async getComprehensiveStats(filters?: AssetSearchParams): Promise<ComprehensiveStats> {
        try {
            const result = await enhancedApiClient.get<ComprehensiveStats>("/statistics/comprehensive", {
                params: filters,
                cache: true,
                retry: { maxAttempts: 2, delay: 500, backoffMultiplier: 2 },
                smartExtract: true
            });

            if (!result.success) {
                throw new Error(`获取综合统计失败: ${result.error}`);
            }

            return result.data!;
        } catch {
            const enhancedError = ApiErrorHandler.handleError(error);
            throw new Error(enhancedError.message);
        }
    }
}

// 导出服务实例
export const assetStatisticsService = new AssetStatisticsService();
