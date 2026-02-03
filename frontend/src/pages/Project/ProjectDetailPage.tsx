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
  Spin,
  Alert,
  Card,
  Descriptions,
  Tag,
  Statistic,
  Badge,
} from 'antd';
import {
  EditOutlined,
  ArrowLeftOutlined,
  HomeOutlined,
  AreaChartOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectService } from '@/services/projectService';
import { assetService } from '@/services/assetService';
import type { ColumnsType } from 'antd/es/table';
import type { Asset } from '@/types/asset';
import { COLORS } from '@/styles/colorMap';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';

const { Title, Text } = Typography;

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
    queryFn: () =>
      assetService.getAssets({
        project_id: id,
        page: 1,
        pageSize: 100,
      }),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 资产表格列定义
  const assetColumns: ColumnsType<Asset> = [
    {
      title: '物业名称',
      dataIndex: 'property_name',
      key: 'property_name',
      render: (text: string, record: Asset) => (
        <Button type="link" onClick={() => navigate(`/assets/${record.id}`)} style={{ padding: 0 }}>
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
      render: (val: number) => val?.toLocaleString() || '-',
    },
    {
      title: '已出租面积 (㎡)',
      dataIndex: 'rented_area',
      key: 'rented_area',
      align: 'right',
      render: (val: number) => val?.toLocaleString() || '-',
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
  const totalAssets = assets.length;
  const totalRentableArea = assets.reduce((sum, a) => sum + (a.rentable_area ?? 0), 0);
  const totalRentedArea = assets.reduce((sum, a) => sum + (a.rented_area ?? 0), 0);
  const occupancyRate =
    totalRentableArea > 0 ? ((totalRentedArea / totalRentableArea) * 100).toFixed(1) : '0';

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

  // 加载状态
  if (projectLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载项目详情中...</div>
      </div>
    );
  }

  // 错误状态
  if (projectError) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${projectError instanceof Error ? projectError.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </div>
    );
  }

  // 数据不存在状态
  if (!project) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert title="项目不存在" description="未找到指定的项目信息" type="warning" showIcon />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/project')}>
                返回列表
              </Button>
              <Title level={2} style={{ margin: 0 }}>
                {project.name}
              </Title>
              <Badge
                status={project.is_active ? 'success' : 'error'}
                text={project.is_active ? '启用' : '禁用'}
              />
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => navigate(`/project/${id}/edit`)}
            >
              编辑项目
            </Button>
          </Col>
        </Row>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic title="关联资产" value={totalAssets} prefix={<HomeOutlined />} suffix="个" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="可出租总面积"
              value={totalRentableArea}
              precision={2}
              prefix={<AreaChartOutlined />}
              suffix="㎡"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已出租面积"
              value={totalRentedArea}
              precision={2}
              prefix={<TeamOutlined />}
              suffix="㎡"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="出租率"
              value={occupancyRate}
              precision={1}
              suffix="%"
              styles={{ content: {
                color:
                  parseFloat(occupancyRate) >= 80
                    ? COLORS.success
                    : parseFloat(occupancyRate) >= 50
                      ? COLORS.warning
                      : COLORS.error,
              } }}
            />
          </Card>
        </Col>
      </Row>

      {/* 项目基本信息 */}
      <Card title="项目信息" style={{ marginBottom: '24px' }}>
        <Descriptions column={2}>
          <Descriptions.Item label="项目编码">
            <Text code>{project.code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="项目状态">
            <Tag color={project.data_status === '正常' ? 'green' : 'default'}>
              {project.data_status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="项目描述" span={2}>
            {project.description ?? '-'}
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
        title={
          <Space>
            <span>关联资产</span>
            <Badge count={totalAssets} style={{ backgroundColor: COLORS.primary }} />
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
    </div>
  );
};

export default ProjectDetailPage;
