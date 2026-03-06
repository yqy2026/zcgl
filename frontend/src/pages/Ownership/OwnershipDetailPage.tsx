/**
 * 权属方详情页面 - V2
 *
 * @description 展示权属方的完整信息，包括基本信息、关联资产、关联合同和财务统计
 * @module pages/Ownership
 */

import React, { useEffect, useMemo } from 'react';
import {
  Typography,
  Button,
  Row,
  Col,
  Alert,
  Card,
  Descriptions,
  Tag,
  Statistic,
  Badge,
  Tabs,
} from 'antd';
import {
  EditOutlined,
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
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { PageContainer } from '@/components/Common';
import styles from './OwnershipDetailPage.module.css';

const { Text } = Typography;

type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';

const getToneClassName = (tone: Tone): string => {
  switch (tone) {
    case 'success':
      return styles.toneSuccess;
    case 'warning':
      return styles.toneWarning;
    case 'error':
      return styles.toneError;
    case 'neutral':
      return styles.toneNeutral;
    default:
      return styles.tonePrimary;
  }
};

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
        owner_party_id: id,
        page: 1,
        page_size: 100,
      }),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 获取关联合同
  const { data: contractsData, isLoading: contractsLoading } = useQuery({
    queryKey: ['ownership-contracts', id],
    queryFn: () =>
      rentContractService.getContracts({
        owner_party_id: id,
        page: 1,
        pageSize: 100,
      }),
    enabled: id !== null && id !== undefined && id.length > 0,
  });

  // 获取财务统计
  const { data: financeStats } = useQuery({
    queryKey: ['ownership-finance', id],
    queryFn: () =>
      rentContractService.getOwnershipStatistics({
        owner_party_ids: [id as string],
      }),
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
          onClick={() => navigate(`/assets/${record.id}`)}
          className={styles.inlineLinkButton}
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
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '可出租面积 (㎡)',
      dataIndex: 'rentable_area',
      key: 'rentable_area',
      align: 'right',
      render: (val?: number) => (val != null ? val.toLocaleString() : '-'),
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
        <Button
          type="link"
          onClick={() => navigate(`/rental/contracts/${record.id}`)}
          className={styles.inlineLinkButton}
        >
          {text}
        </Button>
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
          有效: 'green',
          终止: 'red',
          已续签: 'blue',
          待生效: 'gold',
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
  const assets = useMemo(() => assetsData?.items ?? [], [assetsData?.items]);
  const contracts = useMemo(() => contractsData?.items ?? [], [contractsData?.items]);
  const stats = financeStats?.[0] || {
    total_due_amount: 0,
    total_paid_amount: 0,
    total_overdue_amount: 0,
  };

  const collectionRate =
    stats.total_due_amount > 0
      ? ((stats.total_paid_amount / stats.total_due_amount) * 100).toFixed(1)
      : '0';
  const collectionRateValue = Number(collectionRate);
  const collectionRateTone: Tone =
    collectionRateValue >= 90 ? 'success' : collectionRateValue >= 70 ? 'warning' : 'error';

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

  const {
    data: contractRows,
    loading: contractTableLoading,
    pagination: contractPagination,
    loadList: loadContractList,
    updatePagination: updateContractPagination,
  } = useArrayListData<RentContract, Record<string, never>>({
    items: contracts,
    initialFilters: {},
    initialPageSize: 10,
  });

  useEffect(() => {
    void loadAssetList({ page: 1 });
  }, [assets, loadAssetList]);

  useEffect(() => {
    void loadContractList({ page: 1 });
  }, [contracts, loadContractList]);

  // 错误状态
  if (ownershipError) {
    return (
      <PageContainer title="权属方详情" onBack={() => navigate('/ownership')}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${ownershipError instanceof Error ? ownershipError.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  // 数据不存在
  if (!ownershipLoading && !ownership) {
    return (
      <PageContainer title="权属方详情" onBack={() => navigate('/ownership')}>
        <Alert title="权属方不存在" description="未找到指定的权属方信息" type="warning" showIcon />
      </PageContainer>
    );
  }

  // Tab items
  const tabItems = [
    {
      key: 'assets',
      label: (
        <span className={styles.tabLabel}>
          <HomeOutlined />
          关联资产 ({assets.length})
        </span>
      ),
      children: (
        <TableWithPagination
          columns={assetColumns}
          dataSource={assetRows}
          rowKey="id"
          loading={assetsLoading || assetTableLoading}
          paginationState={assetPagination}
          onPageChange={updateAssetPagination}
          paginationProps={{
            showTotal: (total: number) => `共 ${total} 条`,
          }}
          locale={{ emptyText: '暂无关联资产' }}
          scroll={{ x: 860 }}
        />
      ),
    },
    {
      key: 'contracts',
      label: (
        <span className={styles.tabLabel}>
          <FileTextOutlined />
          关联合同 ({contracts.length})
        </span>
      ),
      children: (
        <TableWithPagination
          columns={contractColumns}
          dataSource={contractRows}
          rowKey="id"
          loading={contractsLoading || contractTableLoading}
          paginationState={contractPagination}
          onPageChange={updateContractPagination}
          paginationProps={{
            showTotal: (total: number) => `共 ${total} 条`,
          }}
          locale={{ emptyText: '暂无关联合同' }}
          scroll={{ x: 960 }}
        />
      ),
    },
  ];

  return (
    <PageContainer
      title={
        <>
          {ownership?.name}
          {ownership?.short_name != null && ownership.short_name.length > 0 && (
            <Text type="secondary" className={styles.shortNameText}>
              ({ownership.short_name})
            </Text>
          )}
          {ownership && (
            <Badge
              status={ownership.is_active ? 'success' : 'error'}
              text={ownership.is_active ? '启用' : '禁用'}
              className={styles.statusBadge}
            />
          )}
        </>
      }
      loading={ownershipLoading}
      onBack={() => navigate('/ownership')}
      extra={
        <Button
          type="primary"
          icon={<EditOutlined />}
          onClick={() => navigate(`/ownership/${id}/edit`)}
        >
          编辑
        </Button>
      }
    >
      <Row gutter={[16, 16]} className={styles.statsRow}>
        <Col xs={24} sm={12} xl={6}>
          <Card className={styles.statsCard}>
            <Statistic
              title="关联资产"
              value={assets.length}
              prefix={<HomeOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className={styles.statsCard}>
            <Statistic
              title="应收总额"
              value={stats.total_due_amount || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className={`${styles.statsCard} ${styles.toneSuccess}`}>
            <Statistic
              title="实收总额"
              value={stats.total_paid_amount || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card className={`${styles.statsCard} ${getToneClassName(collectionRateTone)}`}>
            <Statistic
              title="收缴率"
              value={collectionRate}
              precision={1}
              prefix={<PercentageOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 基本信息 */}
      {ownership && (
        <>
          <Card title="基本信息" className={styles.detailsCard}>
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
                <Tag className={`${styles.countTag} ${styles.tonePrimary}`}>
                  {contracts.length} 个
                </Tag>
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
          <Card className={styles.tabCard}>
            <Tabs items={tabItems} />
          </Card>
        </>
      )}
    </PageContainer>
  );
};

export default OwnershipDetailPage;
