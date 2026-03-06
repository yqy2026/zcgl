/**
 * 项目详情页面 - V2
 *
 * @description 展示项目的完整信息，包括基本信息、关联资产列表和统计数据
 * @module pages/Project
 */

import React, { useEffect, useMemo } from 'react';
import {
  Typography,
  Button,
  Space,
  Row,
  Col,
  Alert,
  Card,
  Descriptions,
  Tag,
  Statistic,
  Badge,
} from 'antd';
import { EditOutlined, HomeOutlined, AreaChartOutlined, TeamOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectService } from '@/services/projectService';
import type { ColumnsType } from 'antd/es/table';
import type { Asset } from '@/types/asset';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { PageContainer } from '@/components/Common';
import styles from './ProjectDetailPage.module.css';

const { Text } = Typography;
const PROJECT_STATUS_MAP: Record<string, { text: string; color: string; active: boolean }> = {
  planning: { text: '规划中', color: 'default', active: false },
  active: { text: '进行中', color: 'green', active: true },
  paused: { text: '已暂停', color: 'orange', active: false },
  completed: { text: '已完成', color: 'blue', active: false },
  terminated: { text: '已终止', color: 'red', active: false },
};

/**
 * ProjectDetailPage - 项目详情页面组件
 *
 * 功能：
 * - 根据URL参数获取项目ID
 * - 展示项目基本信息
 * - 展示关联资产列表
 * - 展示统计卡片（资产数量、总面积、出租率）
 */
const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // 获取项目详情
  const {
    data: project,
    isLoading: projectLoading,
    error: projectError,
  } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectService.getProject(id as string),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 获取项目关联资产
  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ['project-assets', id],
    queryFn: () => projectService.getProjectAssets(id as string),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 资产表格列定义
  const assetColumns: ColumnsType<Asset> = [
    {
      title: '物业名称',
      dataIndex: 'asset_name',
      key: 'asset_name',
      render: (text: string, record: Asset) => (
        <Button
          type="link"
          className={styles.assetLinkButton}
          onClick={() => navigate(`/assets/${record.id}`)}
        >
          {text}
        </Button>
      ),
    },
    {
      title: '使用状态',
      dataIndex: 'usage_status',
      key: 'usage_status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          已出租: 'green',
          空置: 'orange',
          自用: 'blue',
          维修中: 'red',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '可出租面积 (㎡)',
      dataIndex: 'rentable_area',
      key: 'rentable_area',
      align: 'right',
      render: (val?: number | null) => (val != null ? val.toLocaleString() : '-'),
    },
    {
      title: '已出租面积 (㎡)',
      dataIndex: 'rented_area',
      key: 'rented_area',
      align: 'right',
      render: (val?: number | null) => (val != null ? val.toLocaleString() : '-'),
    },
    {
      title: '租户',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      render: (text: string) => text || '-',
    },
  ];

  // 计算统计数据
  const assets = useMemo(() => assetsData?.items ?? [], [assetsData?.items]);
  const summary = assetsData?.summary ?? {
    total_assets: 0,
    total_rentable_area: 0,
    total_rented_area: 0,
    occupancy_rate: 0,
  };
  const totalAssets = summary.total_assets;
  const totalRentableArea = summary.total_rentable_area;
  const totalRentedArea = summary.total_rented_area;
  const occupancyRate = summary.occupancy_rate;
  const occupancyToneClass =
    occupancyRate >= 80
      ? styles.occupancySuccess
      : occupancyRate >= 50
        ? styles.occupancyWarning
        : styles.occupancyError;

  const {
    data: assetRows,
    loading: assetTableLoading,
    pagination: assetPagination,
    loadList: loadAssetList,
    updatePagination: updateAssetPagination,
  } = useArrayListData<Asset, Record<string, never>>({
    items: assets,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadAssetList({ page: 1 });
  }, [assets, loadAssetList]);

  // 错误状态
  if (projectError) {
    return (
      <PageContainer title="项目详情" onBack={() => navigate('/project')}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${projectError instanceof Error ? projectError.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  // 数据不存在状态
  if (!projectLoading && !project) {
    return (
      <PageContainer title="项目详情" onBack={() => navigate('/project')}>
        <Alert title="项目不存在" description="未找到指定的项目信息" type="warning" showIcon />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={
        <span className={styles.projectTitle}>
          <span>{project?.project_name}</span>
          {project && (
            <Badge
              status={(PROJECT_STATUS_MAP[project.status]?.active ?? false) ? 'success' : 'default'}
              text={PROJECT_STATUS_MAP[project.status]?.text ?? project.status}
              className={styles.projectStatus}
            />
          )}
        </span>
      }
      loading={projectLoading}
      onBack={() => navigate('/project')}
      extra={
        <Button
          type="primary"
          icon={<EditOutlined />}
          className={styles.editButton}
          onClick={() => navigate(`/project/${id}/edit`)}
        >
          编辑项目
        </Button>
      }
    >
      <Row gutter={[16, 16]} className={styles.metricsRow}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="关联资产"
              value={totalAssets}
              prefix={<HomeOutlined />}
              suffix="个"
              className={styles.metricPrimary}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="可出租总面积"
              value={totalRentableArea}
              precision={2}
              prefix={<AreaChartOutlined />}
              suffix="㎡"
              className={styles.metricSuccess}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="已出租面积"
              value={totalRentedArea}
              precision={2}
              prefix={<TeamOutlined />}
              suffix="㎡"
              className={styles.metricWarning}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.metricCard}>
            <Statistic
              title="出租率"
              value={occupancyRate}
              precision={1}
              suffix="%"
              className={occupancyToneClass}
            />
          </Card>
        </Col>
      </Row>

      {/* 项目基本信息 */}
      {project && (
        <>
          <Card title="项目信息" className={styles.infoCard}>
            <Descriptions column={2}>
              <Descriptions.Item label="项目编码">
                <Text code>{project.project_code}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="业务状态">
                <Tag color={PROJECT_STATUS_MAP[project.status]?.color ?? 'default'}>
                  {PROJECT_STATUS_MAP[project.status]?.text ?? project.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="项目状态">
                <Tag
                  color={project.data_status === '正常' ? 'green' : 'default'}
                  className={styles.projectDataStatusTag}
                >
                  {project.data_status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {project.created_at ? new Date(project.created_at).toLocaleString('zh-CN') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {project.updated_at ? new Date(project.updated_at).toLocaleString('zh-CN') : '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 关联资产列表 */}
          <Card
            className={styles.assetTableCard}
            title={
              <Space className={styles.assetTableTitle}>
                <span>关联资产</span>
                <Badge count={totalAssets} className={styles.assetCountBadge} />
              </Space>
            }
          >
            <TableWithPagination
              columns={assetColumns}
              dataSource={assetRows}
              rowKey="id"
              loading={assetsLoading || assetTableLoading}
              paginationState={assetPagination}
              onPageChange={updateAssetPagination}
              paginationProps={{
                showSizeChanger: true,
                showTotal: (total: number) => `共 ${total} 条`,
              }}
              locale={{ emptyText: '暂无关联资产' }}
            />
          </Card>
        </>
      )}
    </PageContainer>
  );
};

export default ProjectDetailPage;
