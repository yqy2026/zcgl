/**
 * 权属方详情页面 - V2
 *
 * @description 展示权属方的完整信息，包括基本信息、关联资产、关联合同和财务统计
 * @module pages/Ownership
 */

import React from 'react';
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
  Table,
  Tag,
  Statistic,
  Badge,
  Tabs,
} from 'antd';
import {
  EditOutlined,
  ArrowLeftOutlined,
  HomeOutlined,
  DollarOutlined,
  FileTextOutlined,
  PercentageOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ownershipService } from '@/services/ownershipService';
import { assetService } from '@/services/assetService';
import { rentContractService } from '@/services/rentContractService';
import type { ColumnsType } from 'antd/es/table';
import type { Asset } from '@/types/asset';
import type { RentContract } from '@/types/rentContract';
import { COLORS } from '@/styles/colorMap';

const { Title, Text } = Typography;

/**
 * OwnershipDetailPage - 权属方详情页面组件
 *
 * 功能：
 * - 展示权属方基本信息
 * - 展示关联资产列表
 * - 展示关联合同列表
 * - 展示财务统计（应收/实收/收缴率）
 */
const OwnershipDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // 获取权属方详情
  const {
    data: ownership,
    isLoading: ownershipLoading,
    error: ownershipError,
  } = useQuery({
    queryKey: ['ownership', id],
    queryFn: () => ownershipService.getOwnership(id as string),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 获取关联资产
  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ['ownership-assets', id],
    queryFn: () =>
      assetService.getAssets({
        ownership_id: id,
        page: 1,
        limit: 100,
      }),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 获取关联合同
  const { data: contractsData, isLoading: contractsLoading } = useQuery({
    queryKey: ['ownership-contracts', id],
    queryFn: () =>
      rentContractService.getContracts({
        ownership_id: id,
        page: 1,
        limit: 100,
      }),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 获取财务统计
  const { data: financeStats } = useQuery({
    queryKey: ['ownership-finance', id],
    queryFn: () =>
      rentContractService.getOwnershipStatistics({
        ownership_ids: [id as string],
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
        <a onClick={() => navigate(`/assets/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '使用状态',
      dataIndex: 'usage_status',
      key: 'usage_status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          '已出租': 'green',
          '空置': 'orange',
          '自用': 'blue',
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
      title: '所属项目',
      dataIndex: 'project_name',
      key: 'project_name',
      render: (text: string) => text || '-',
    },
  ];

  // 合同表格列定义
  const contractColumns: ColumnsType<RentContract> = [
    {
      title: '合同编号',
      dataIndex: 'contract_number',
      key: 'contract_number',
      render: (text: string, record: RentContract) => (
        <a onClick={() => navigate(`/rental/contracts/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '合同类型',
      dataIndex: 'contract_type',
      key: 'contract_type',
      render: (type: string) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          lease_upstream: { label: '上游租赁', color: 'blue' },
          lease_downstream: { label: '下游租赁', color: 'green' },
          entrusted: { label: '委托运营', color: 'purple' },
        };
        const info = typeMap[type] ?? { label: type, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '承租方',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
    },
    {
      title: '合同状态',
      dataIndex: 'contract_status',
      key: 'contract_status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          '有效': 'green',
          '终止': 'red',
          '已续签': 'blue',
          '待生效': 'gold',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '租期',
      key: 'period',
      render: (_: unknown, record: RentContract) => (
        <span>
          {record.start_date} ~ {record.end_date}
        </span>
      ),
    },
  ];

  // 计算统计数据
  const assets = assetsData?.items || [];
  const contracts = contractsData?.items || [];
  const stats = financeStats?.[0] || {
    total_due_amount: 0,
    total_paid_amount: 0,
    total_overdue_amount: 0,
  };

  const collectionRate =
    stats.total_due_amount > 0
      ? ((stats.total_paid_amount / stats.total_due_amount) * 100).toFixed(1)
      : '0';

  // 加载状态
  if (ownershipLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载权属方详情中...</div>
      </div>
    );
  }

  // 错误状态
  if (ownershipError) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="数据加载失败"
          description={`错误详情: ${ownershipError instanceof Error ? ownershipError.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </div>
    );
  }

  // 数据不存在
  if (!ownership) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="权属方不存在"
          description="未找到指定的权属方信息"
          type="warning"
          showIcon
        />
      </div>
    );
  }

  // Tab items
  const tabItems = [
    {
      key: 'assets',
      label: (
        <span>
          <HomeOutlined />
          关联资产 ({assets.length})
        </span>
      ),
      children: (
        <Table
          columns={assetColumns}
          dataSource={assets}
          rowKey="id"
          loading={assetsLoading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 条`,
          }}
          locale={{ emptyText: '暂无关联资产' }}
        />
      ),
    },
    {
      key: 'contracts',
      label: (
        <span>
          <FileTextOutlined />
          关联合同 ({contracts.length})
        </span>
      ),
      children: (
        <Table
          columns={contractColumns}
          dataSource={contracts}
          rowKey="id"
          loading={contractsLoading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 条`,
          }}
          locale={{ emptyText: '暂无关联合同' }}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate('/ownership')}
              >
                返回列表
              </Button>
              <Title level={2} style={{ margin: 0 }}>
                {ownership.name}
              </Title>
              {(ownership.short_name !== null && ownership.short_name !== undefined && ownership.short_name.length > 0) && (
                <Text type="secondary">({ownership.short_name})</Text>
              )}
              <Badge
                status={ownership.is_active ? 'success' : 'error'}
                text={ownership.is_active ? '启用' : '禁用'}
              />
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => navigate(`/ownership/${id}/edit`)}
            >
              编辑
            </Button>
          </Col>
        </Row>
      </div>

      {/* 财务统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="关联资产"
              value={assets.length}
              prefix={<HomeOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="应收总额"
              value={stats.total_due_amount || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="实收总额"
              value={stats.total_paid_amount || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
              valueStyle={{ color: COLORS.success }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="收缴率"
              value={collectionRate}
              precision={1}
              prefix={<PercentageOutlined />}
              suffix="%"
              valueStyle={{
                color:
                  parseFloat(collectionRate) >= 90
                    ? COLORS.success
                    : parseFloat(collectionRate) >= 70
                      ? COLORS.warning
                      : COLORS.error,
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 基本信息 */}
      <Card title="基本信息" style={{ marginBottom: '24px' }}>
        <Descriptions column={2}>
          <Descriptions.Item label="权属方全称">{ownership.name}</Descriptions.Item>
          <Descriptions.Item label="权属方简称">
            {ownership.short_name ?? '-'}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Badge
              status={ownership.is_active ? 'success' : 'error'}
              text={ownership.is_active ? '启用' : '禁用'}
            />
          </Descriptions.Item>
          <Descriptions.Item label="关联合同数量">
            <Tag color="blue">{contracts.length} 个</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {ownership.created_at
              ? new Date(ownership.created_at).toLocaleString('zh-CN')
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {ownership.updated_at
              ? new Date(ownership.updated_at).toLocaleString('zh-CN')
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 资产和合同列表 */}
      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
};

export default OwnershipDetailPage;
