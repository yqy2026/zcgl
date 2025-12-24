import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { message } from "antd";
import { apiRequest, API_ENDPOINTS, ApiError, API_BASE_URL } from "@/api/config";

// API返回的资产数据格式
interface AssetApiResponse {
  id: string;
  property_name: string;
  address: string;
  ownership_entity: string;
  management_entity?: string;
  property_nature: string;
  usage_status: string;
  total_area?: number;
  usable_area?: number;
  ownership_status?: string;
  business_category?: string;
  is_litigated?: string | boolean;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

interface AssetFilters {
  propertyNature?: string;
  usageStatus?: string;
  ownershipStatus?: string;
  ownershipEntity?: string;
  occupancyRateRange?: [number, number];
}

interface AssetSummary {
  total: number;
  rented: number;
  vacant: number;
  avgOccupancyRate: number;
}

interface PaginationConfig {
  current: number;
  pageSize: number;
  total: number;
}

// 真实API调用
const fetchAssets = async (params: {
  page: number;
  pageSize: number;
  search?: string;
  filters?: AssetFilters;
}) => {
  try {
    const searchParams = new URLSearchParams({
      page: params.page.toString(),
      limit: params.pageSize.toString(),
    });

    if (params.search) {
      searchParams.append("search", params.search);
    }

    if (params.filters) {
      const { propertyNature, usageStatus, ownershipStatus, ownershipEntity } = params.filters;

      if (propertyNature) {
        searchParams.append("property_nature", propertyNature);
      }
      if (usageStatus) {
        searchParams.append("usage_status", usageStatus);
      }
      if (ownershipStatus) {
        searchParams.append("ownership_status", ownershipStatus);
      }
      if (ownershipEntity) {
        searchParams.append("ownership_entity", ownershipEntity);
      }
    }

    const url = `${API_BASE_URL}${API_ENDPOINTS.assets}/?${searchParams}`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    // 检查响应格式
    if (!result || !result.items) {
      console.error("Invalid API response format:", result);
      throw new Error("Invalid API response format");
    }

    // 转换数据格式以匹配前端期望的格式
    const transformedData = result.items
      .map((item: AssetApiResponse) => {
        // 确保所有必需字段都有有效值
        const transformed = {
          id: item.id || "",
          propertyName: item.property_name || "",
          address: item.address || "",
          ownershipEntity: item.ownership_entity || "",
          managementEntity: item.management_entity || "",
          propertyNature: item.property_nature || "",
          usageStatus: item.usage_status || "",
          actualPropertyArea: Number(item.total_area) || 0,
          rentableArea: Number(item.usable_area) || 0,
          rentedArea: Number(item.usable_area) || 0,
          occupancyRate: item.usage_status === "出租" ? "100" : "0", // 移除%符号，只保留数字
          ownershipStatus: item.ownership_status || "",
          businessCategory: item.business_category || "",
          isLitigated: item.is_litigated || "否",
          notes: item.notes || "",
          createdAt: item.created_at || "",
          updatedAt: item.updated_at || "",
        };

        // 验证关键字段
        if (!transformed.id || !transformed.propertyName) {
          return null;
        }

        return transformed;
      })
      .filter(Boolean); // 过滤掉无效数据

    return {
      data: transformedData,
      total: result.total,
      page: result.page,
      pageSize: result.limit,
    };
  } catch (error) {
    console.error("Error fetching assets:", error);
    // 提供更详细的错误信息
    if (error instanceof Error) {
      throw new Error(`获取资产列表失败: ${error.message}`);
    }
    throw new Error("获取资产列表失败: 未知错误");
  }
};

const fetchAssetSummary = async (): Promise<AssetSummary> => {
  try {
    const result = await apiRequest<{
      total_assets: number;
      usage_status: { rented: number; vacant: number; self_used: number };
    }>(API_ENDPOINTS.statistics.basic);

    // 处理API响应格式
    const data = result.success ? result.data : result;

    const total = data.total_assets || 0;
    const rented = data.usage_status?.rented || 0;
    const vacant = data.usage_status?.vacant || 0;
    const selfUsed = data.usage_status?.self_used || 0;

    // 计算平均出租率
    const rentableAssets = rented + vacant;
    const avgOccupancyRate = rentableAssets > 0 ? (rented / rentableAssets) * 100 : 0;

    return {
      total,
      rented,
      vacant,
      avgOccupancyRate: Math.round(avgOccupancyRate * 100) / 100, // 保留两位小数
    };
  } catch (error) {
    console.error("Error fetching asset summary:", error);
    if (error instanceof ApiError) {
      message.error(`获取统计数据失败: ${error.message}`);
    }
    // 返回默认值
    return {
      total: 0,
      rented: 0,
      vacant: 0,
      avgOccupancyRate: 0,
    };
  }
};

const deleteAssets = async (ids: string[]) => {
  const deletePromises = ids.map(
    (id) =>
      apiRequest(API_ENDPOINTS.assetDetail(id), {
        method: "DELETE",
      }).catch(() => null), // 捕获单个删除失败
  );

  const results = await Promise.all(deletePromises);
  const successCount = results.filter((result) => result !== null).length;

  return { success: successCount === ids.length, deletedCount: successCount };
};

const exportAssets = async (filters?: AssetFilters) => {
  const searchParams = new URLSearchParams();

  if (filters) {
    const { propertyNature, usageStatus, ownershipStatus, ownershipEntity } = filters;

    if (propertyNature) {
      searchParams.append("property_nature", propertyNature);
    }
    if (usageStatus) {
      searchParams.append("usage_status", usageStatus);
    }
    if (ownershipStatus) {
      searchParams.append("ownership_status", ownershipStatus);
    }
    if (ownershipEntity) {
      searchParams.append("ownership_entity", ownershipEntity);
    }
  }

  // 对于文件下载，我们仍然使用原生fetch，因为需要处理blob响应
  const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.excel.export}?${searchParams}`);

  if (!response.ok) {
    throw new Error("Export failed");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `资产清单_${new Date().toISOString().split("T")[0]}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
};

export const useAssetList = () => {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<AssetFilters>({});
  const [pagination, setPagination] = useState<PaginationConfig>({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  const queryClient = useQueryClient();

  // 获取资产列表
  const assetsQuery = useQuery({
    queryKey: [
      "assets",
      {
        page: pagination.current,
        pageSize: pagination.pageSize,
        search: search || undefined,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
      },
    ],
    queryFn: () =>
      fetchAssets({
        page: pagination.current,
        pageSize: pagination.pageSize,
        search,
        filters,
      }),
    retry: 2,
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    refetchOnMount: "always",
    refetchOnWindowFocus: false,
    enabled: true, // 确保查询启用
  });

  // 获取资产汇总信息
  const summaryQuery = useQuery({
    queryKey: ["asset-summary"],
    queryFn: fetchAssetSummary,
  });

  // 删除资产
  const deleteMutation = useMutation({
    mutationFn: deleteAssets,
    onSuccess: (data) => {
      message.success(`成功删除 ${data.deletedCount} 个资产`);
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
    },
    onError: () => {
      message.error("删除失败，请重试");
    },
  });

  // 导出资产
  const exportMutation = useMutation({
    mutationFn: exportAssets,
    onSuccess: () => {
      message.success("导出成功");
    },
    onError: () => {
      message.error("导出失败，请重试");
    },
  });

  // 更新分页信息
  useEffect(() => {
    if (assetsQuery.data) {
      setPagination((prev) => ({
        ...prev,
        total: assetsQuery.data.total,
      }));
    }
  }, [assetsQuery.data]);

  const handleSearch = (value: string) => {
    setSearch(value);
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const handleFilter = (newFilters: AssetFilters) => {
    setFilters(newFilters);
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const handlePaginationChange = (page: number, pageSize: number) => {
    setPagination((prev) => ({
      ...prev,
      current: page,
      pageSize,
    }));
  };

  const handleBatchDelete = (ids: string[]) => {
    deleteMutation.mutate(ids);
  };

  const handleExport = () => {
    exportMutation.mutate(filters);
  };

  // 调试信息
  // Debug information
  console.log("useAssetList Debug Info:", {
    isLoading: assetsQuery.isLoading,
    isError: assetsQuery.isError,
    error: assetsQuery.error,
    data: assetsQuery.data,
    assets: assetsQuery.data?.data,
    assetsLength: assetsQuery.data?.data?.length,
  });

  return {
    assets: assetsQuery.data?.data || [],
    loading: assetsQuery.isLoading,
    error: assetsQuery.error,
    pagination,
    filters,
    summary: summaryQuery.data,
    handleSearch,
    handleFilter,
    handlePaginationChange,
    handleBatchDelete,
    handleExport,
    isDeleting: deleteMutation.isPending,
    isExporting: exportMutation.isPending,
  };
};
