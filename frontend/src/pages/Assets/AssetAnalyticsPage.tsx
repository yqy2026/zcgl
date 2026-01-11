import React, { useState } from "react";
import {
  Card,
  Row,
  Col,
  Spin,
  Alert,
  Empty,
  Typography,
  Space,
  Button,
  Radio,
} from "antd";
import styles from "./AssetAnalyticsPage.module.css";
import { useQuery } from "@tanstack/react-query";
import {
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
} from "@ant-design/icons";
import { analyticsService } from "@/services/analyticsService";
import { exportAnalyticsData } from "@/services/analyticsExportService";
import { AnalyticsStatsGrid, FinancialStatsGrid } from "@/components/Analytics/AnalyticsStatsCard";
import {
  AnalyticsPieChart,
  AnalyticsBarChart,
  AnalyticsLineChart,
  chartDataUtils,
} from "@/components/Analytics/AnalyticsChart";
import AnalyticsFilters from "@/components/Analytics/AnalyticsFilters";
import type { AssetSearchParams } from "@/types/asset";
import type { AnalyticsData, AnalyticsResponse } from "@/types/analytics";
import { createLogger } from "@/utils/logger";
import { MessageManager } from "@/utils/messageManager";
import { COLORS } from '@/styles/colorMap';

const pageLogger = createLogger('AssetAnalytics');

const { Text } = Typography;

// 分析维度类型
type AnalysisDimension = "count" | "area";

const AssetAnalyticsPage: React.FC = () => {
  const [filters, setFilters] = useState<AssetSearchParams>({});
  const [dimension, setDimension] = useState<AnalysisDimension>("area");
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 获取分析数据
  const {
    data: analyticsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["asset-analytics", filters],
    queryFn: async () => {
      const result = await analyticsService.getComprehensiveAnalytics(filters);
      pageLogger.debug('Analytics API Result:', result as unknown as Record<string, unknown>);
      return result;
    },
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    refetchOnWindowFocus: false,
  });

  // React Query 返回 AnalyticsResponse，从中提取 AnalyticsData
  // analyticsService 已经处理了数据适配，这里直接使用
  let analyticsData: AnalyticsData | null = null;
  if (analyticsResponse) {
    if ('success' in analyticsResponse && 'data' in analyticsResponse) {
      analyticsData = analyticsResponse.data;
    } else if ('area_summary' in analyticsResponse) {
      // 兼容直接返回 AnalyticsData 的情况
      analyticsData = analyticsResponse as unknown as AnalyticsData;
    } else {
      pageLogger.warn('Unexpected analytics response format:', analyticsResponse as unknown as Record<string, unknown>);
    }
  }

  // 处理筛选条件变化
  const handleFilterChange = (newFilters: AssetSearchParams) => {
    setFilters(newFilters);
  };

  // 处理筛选条件重置
  const handleFilterReset = () => {
    setFilters({});
  };

  // 处理维度切换
  const handleDimensionChange = (newDimension: AnalysisDimension) => {
    setDimension(newDimension);
  };

  // 处理导出数据
  const handleExport = async () => {
    if (!analyticsData) return;

    try {
      MessageManager.loading("正在导出数据...", 0);

      const exportData = {
        summary: {
          total_assets: analyticsData.area_summary.total_assets,
          total_area: analyticsData.area_summary.total_area,
          total_rentable_area: analyticsData.area_summary.total_rentable_area,
          occupancy_rate: analyticsData.area_summary.occupancy_rate,
          total_annual_income: analyticsData.financial_summary.total_annual_income,
          total_annual_expense: analyticsData.financial_summary.total_annual_expense,
          total_net_income: analyticsData.financial_summary.total_net_income,
          total_monthly_rent: analyticsData.financial_summary.total_monthly_rent,
        },
        property_nature_distribution: analyticsData.property_nature_distribution ?? [],
        ownership_status_distribution: analyticsData.ownership_status_distribution ?? [],
        usage_status_distribution: analyticsData.usage_status_distribution ?? [],
        business_category_distribution: (analyticsData.business_category_distribution ?? []).map(item => ({
          category: item.category,
          count: item.count,
          occupancy_rate: item.occupancy_rate ?? 0
        })),
        occupancy_trend: (analyticsData.occupancy_trend ?? []).map(item => ({
          date: item.date,
          occupancy_rate: item.occupancy_rate,
          total_rented_area: 0,
          total_rentable_area: 0
        })),
        // 面积维度数据
        property_nature_area_distribution: analyticsData.property_nature_area_distribution,
        ownership_status_area_distribution: analyticsData.ownership_status_area_distribution,
        usage_status_area_distribution: analyticsData.usage_status_area_distribution,
        business_category_area_distribution: analyticsData.business_category_area_distribution,
      };

      await exportAnalyticsData(exportData, "excel");
      MessageManager.success("数据导出成功！");
    } catch (error) {
      pageLogger.error("导出失败:", error as Error);
      MessageManager.error("导出失败，请重试");
    } finally {
      MessageManager.destroy();
    }
  };

  // 处理全屏切换
  const handleToggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        // 进入全屏
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
        MessageManager.success("已进入全屏模式");
      } else {
        // 退出全屏
        await document.exitFullscreen();
        setIsFullscreen(false);
        MessageManager.success("已退出全屏模式");
      }
    } catch (error) {
      pageLogger.error("全屏切换失败:", error as Error);
      MessageManager.error("全屏切换失败，请检查浏览器权限设置");
    }
  };

  // 监听全屏状态变化
  React.useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  if (isLoading) {
    return (
      <div style={{ padding: "24px", textAlign: "center" }}>
        <Spin size="large" />
        <div style={{ marginTop: "16px" }}>加载分析数据中...</div>
      </div>
    );
  }

  if (error) {
    // 调试 - 显示错误详情
    pageLogger.error("Analytics Error:", error as Error);
    return (
      <div style={{ padding: "24px" }}>
        <Alert
          message="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : "未知错误"}`}
          type="error"
          showIcon
        />
      </div>
    );
  }

  const hasData =
    analyticsData && analyticsData.area_summary && Number(analyticsData.area_summary.total_assets) > 0;

  return (
    <div className={styles.analyticsContainer}>
      {/* 页面标题和操作栏 */}
      <Card style={{ marginBottom: "24px" }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <Typography.Title level={3} style={{ margin: 0 }}>
              资产分析
            </Typography.Title>
          </Col>
          <Col xs={24} sm={12}>
            <Space wrap className={styles.headerActions}>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => refetch()}
                loading={isLoading}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>刷新</span>
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={!hasData}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>导出</span>
              </Button>
              <Button
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={handleToggleFullscreen}
                size="small"
                className="no-print"
              >
                <span className={styles.btnText}>{isFullscreen ? "退出全屏" : "全屏"}</span>
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 筛选条件 */}
      <AnalyticsFilters
        filters={filters}
        onFiltersChange={handleFilterChange}
        onResetFilters={handleFilterReset}
        loading={isLoading}
      />

      {/* 维度切换 */}
      <Card style={{ marginBottom: "24px" }}>
        <Space align="center">
          <Text strong>分析维度：</Text>
          <Radio.Group
            value={dimension}
            onChange={(e) => handleDimensionChange(e.target.value as AnalysisDimension)}
            buttonStyle="solid"
          >
            <Radio.Button value="count">数量维度</Radio.Button>
            <Radio.Button value="area">面积维度</Radio.Button>
          </Radio.Group>
          <Text type="secondary">
            {dimension === "count" ? "基于资产个数进行分析" : "基于资产面积进行分析"}
          </Text>
        </Space>
      </Card>

      {!hasData || !analyticsData ? (
        <Card>
          <Empty description="暂无数据" style={{ padding: "60px 0" }}>
            <p>数据库中还没有资产数据，请先录入资产信息</p>
          </Empty>
        </Card>
      ) : (
        <>
          {/* 概览统计卡片 */}
          <Card title="概览统计" style={{ marginBottom: "24px" }}>
            <AnalyticsStatsGrid
              data={{
                total_assets: analyticsData.area_summary.total_assets,
                total_area: analyticsData.area_summary.total_area,
                total_rentable_area: analyticsData.area_summary.total_rentable_area,
                occupancy_rate: analyticsData.area_summary.occupancy_rate,
                total_annual_income: analyticsData.financial_summary.total_annual_income,
                total_net_income: analyticsData.financial_summary.total_net_income,
                total_monthly_rent: analyticsData.financial_summary.total_monthly_rent,
              }}
              loading={isLoading}
            />
          </Card>

          {/* 分布图表 */}
          <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
            {/* 物业性质分布饼图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsPieChart
                title={`物业性质分布 (${dimension === "count" ? "数量" : "面积"})`}
                data={
                  dimension === "count"
                    ? chartDataUtils.toPieData(analyticsData.property_nature_distribution ?? [])
                    : chartDataUtils.toAreaData(analyticsData.property_nature_area_distribution ?? [])
                }
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 确权状态分布饼图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsPieChart
                title={`确权状态分布 (${dimension === "count" ? "数量" : "面积"})`}
                data={
                  dimension === "count"
                    ? chartDataUtils.toPieData(
                      (analyticsData.ownership_status_distribution ?? []).map((item) => ({
                        name: item.status,
                        count: item.count,
                        percentage: item.percentage,
                      })),
                    )
                    : chartDataUtils.toAreaData(
                      (analyticsData.ownership_status_area_distribution as any)?.map((item: any) => ({
                        name: item.status,
                        total_area: item.total_area,
                        area_percentage: item.area_percentage ?? item.percentage ?? 0,
                        average_area: item.average_area,
                      })) ?? [],
                    )
                }
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 使用状态分布柱状图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsBarChart
                title={`使用状态分布 (${dimension === "count" ? "数量" : "面积"})`}
                data={
                  dimension === "count"
                    ? (analyticsData.usage_status_distribution ?? []).map((item) => ({
                      name: item.status,
                      value: item.count,
                    }))
                    : chartDataUtils.toAreaBarData(
                      (analyticsData.usage_status_area_distribution as any)?.map((item: any) => ({
                        name: item.status,
                        total_area: item.total_area,
                        count: item.count,
                        average_area: item.average_area,
                      })) ?? [],
                    )
                }
                xAxisKey="name"
                barKey="value"
                loading={isLoading}
                height={280}
              />
            </Col>

            {/* 业态类别分布柱状图 */}
            <Col xs={24} sm={12} xl={6}>
              <AnalyticsBarChart
                title={`业态类别分布 (${dimension === "count" ? "数量" : "面积"})`}
                data={
                  dimension === "count"
                    ? chartDataUtils.toBusinessCategoryData(
                      analyticsData.business_category_distribution ?? [],
                    )
                    : chartDataUtils.toBusinessCategoryAreaData(
                      analyticsData.business_category_area_distribution ?? [],
                    )
                }
                xAxisKey="name"
                barKey="value"
                loading={isLoading}
                height={280}
              />
            </Col>
          </Row>

          {/* 财务指标 */}
          <Card title="财务指标" style={{ marginBottom: "24px" }}>
            <FinancialStatsGrid data={analyticsData.financial_summary} loading={isLoading} />
          </Card>

          {/* 出租率趋势 */}
          {analyticsData.occupancy_trend && analyticsData.occupancy_trend.length > 0 && (
            <Card title="出租率趋势" style={{ marginBottom: "24px" }}>
              <AnalyticsLineChart
                title="出租率趋势"
                data={chartDataUtils.toTrendData(analyticsData.occupancy_trend)}
                lines={[
                  {
                    key: "occupancy_rate",
                    name: "出租率 (%)",
                    color: COLORS.primary,
                  },
                ]}
                xAxisKey="date"
                loading={isLoading}
                height={400}
              />
            </Card>
          )}

          {/* 详细数据表格 */}
          <Row gutter={[16, 16]}>
            <Col xs={24}>
              <Card title="分布详情">
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      物业性质分布 ({dimension === "count" ? "数量" : "面积"})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === "count"
                        ? analyticsData.property_nature_distribution ?? []
                        : analyticsData.property_nature_area_distribution ?? []
                      ).map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === "count" ? item.name : item.name}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === "count"
                              ? `${(item as { count: number; percentage: number }).count} (${(item as { percentage: number }).percentage}%)`
                              : `${(item as { total_area?: number }).total_area?.toFixed(0)}㎡ (${(item as { area_percentage?: number }).area_percentage ?? 0}%)`}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      确权状态分布 ({dimension === "count" ? "数量" : "面积"})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === "count"
                        ? analyticsData.ownership_status_distribution ?? []
                        : analyticsData.ownership_status_area_distribution ?? []
                      ).map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === "count" ? (item as { status: string }).status : (item as { status: string }).status}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === "count"
                              ? `${(item as { count: number }).count} (${(item as { percentage: number }).percentage}%)`
                              : `${(item as { total_area?: number }).total_area?.toFixed(0)}㎡ (${(item as { area_percentage?: number; percentage?: number }).area_percentage || (item as { area_percentage?: number; percentage?: number }).percentage}%)`}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      使用状态分布 ({dimension === "count" ? "数量" : "面积"})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === "count"
                        ? analyticsData.usage_status_distribution ?? []
                        : analyticsData.usage_status_area_distribution ?? []
                      ).map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === "count" ? (item as { status: string }).status : (item as { status: string }).status}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === "count"
                              ? `${(item as { count: number }).count} (${(item as { percentage: number }).percentage}%)`
                              : `${(item as { total_area?: number }).total_area?.toFixed(0)}㎡ (${(item as { area_percentage?: number }).area_percentage}%)`}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>

                  <Col xs={24} sm={12} lg={6}>
                    <Typography.Title level={5}>
                      业态类别分布 ({dimension === "count" ? "数量" : "面积"})
                    </Typography.Title>
                    <div className={styles.distributionList}>
                      {(dimension === "count"
                        ? analyticsData.business_category_distribution ?? []
                        : analyticsData.business_category_area_distribution ?? []
                      ).map((item, index) => (
                        <div key={index} className={styles.distributionItem}>
                          <span className={styles.itemName}>
                            {dimension === "count" ? (item as { category: string }).category : (item as { category: string }).category}
                          </span>
                          <span className={styles.itemStats}>
                            {dimension === "count"
                              ? `${(item as any).count}个 (占比${(item as any).percentage}%)`
                              : `${(item as any).total_area?.toFixed(0)}㎡ (占比${(item as any).area_percentage}%)`}
                            {dimension === "count" && Number((item as any).occupancy_rate) > 0 && (
                              <span className={styles.occupancyRate}>
                                ，出租率{Number((item as any).occupancy_rate).toFixed(2)}%
                              </span>
                            )}
                            {dimension === "area" &&
                              (item as any).occupancy_rate &&
                              Number((item as any).occupancy_rate) > 0 && (
                                <span className={styles.occupancyRate}>
                                  ，出租率{Number((item as any).occupancy_rate).toFixed(2)}%
                                </span>
                              )}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default AssetAnalyticsPage;
