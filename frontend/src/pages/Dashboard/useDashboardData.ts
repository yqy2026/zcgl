import { useQuery } from '@tanstack/react-query';
import { analyticsService } from '@/services/analyticsService';
import { useDataScopeStore } from '@/stores/dataScopeStore';

const fetchDashboardData = async (viewMode: 'owner' | 'manager' | null) => {
  const response = await analyticsService.getComprehensiveAnalytics(undefined, viewMode);
  const areaSummary = response.data?.area_summary;
  const financialSummary = response.data?.financial_summary;

  return {
    metrics: {
      totalAssets: areaSummary?.total_assets ?? 0,
      totalArea: areaSummary?.total_area ?? 0,
      occupancyRate: areaSummary?.occupancy_rate ?? 0,
      monthlyRevenue: financialSummary?.total_monthly_rent ?? 0,
      rentedAssets: areaSummary?.total_rented_area ?? 0,
      vacantAssets: areaSummary?.total_unrented_area ?? 0,
    },
    todoItems: [],
    chartData: {
      propertyTypes:
        response.data?.property_nature_distribution?.map(item => ({
          name: item.name,
          value: item.count,
          percentage: item.percentage,
        })) ?? [],
      occupancyTrend:
        response.data?.occupancy_trend?.map(item => ({
          month: item.date,
          rate: item.occupancy_rate,
        })) ?? [],
    },
    recentActivities: [],
  };
};

export const useDashboardData = () => {
  const currentViewMode = useDataScopeStore(state => state.getEffectiveViewMode());
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', currentViewMode],
    queryFn: () => fetchDashboardData(currentViewMode),
  });

  return {
    metrics: data?.metrics,
    todoItems: data?.todoItems ?? [],
    chartData: data?.chartData,
    recentActivities: data?.recentActivities ?? [],
    isLoading,
    error,
  };
};
