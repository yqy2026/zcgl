/**
 * 权属方详情页面 - V2
 *
 * @description 展示权属方的完整信息，包括基本信息、关联资产，以及已退休的旧合同/财务入口提示
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
import { EditOutlined, HomeOutlined, FileTextOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ownershipService } from '@/services/ownershipService';
import { assetService } from '@/services/assetService';
import type { ColumnsType } from 'antd/es/table';
import type { Asset } from '@/types/asset';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import { PageContainer } from '@/components/Common';
import styles from './OwnershipDetailPage.module.css';

const { Text } = Typography;

/**
 * OwnershipDetailPage - 权属方详情页面组件
 *
 * 功能：
 * - 展示权属方基本信息
 * - 展示关联资产列表
 * - 旧合同与财务入口显式标记为迁移中
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

  // 计算统计数据
  const assets = useMemo(() => assetsData?.items ?? [], [assetsData?.items]);

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
          关联合同（迁移中）
        </span>
      ),
      children: (
        <Alert
          title="旧租赁合同与财务汇总入口已退休"
          description="该权属方详情页不再请求旧租赁合同与财务统计接口，请改走新合同流程完成关联与汇总查询。"
          type="info"
          showIcon
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
        <Col xs={24} xl={18}>
          <Card className={styles.statsCard}>
            <Alert
              title="财务汇总迁移中"
              description="旧租赁财务汇总入口已退休，后续将由新合同与台账链路提供。"
              type="info"
              showIcon
            />
          </Card>
        </Col>
      </Row>

      {/* 基本信息 */}
      {ownership && (
        <>
          <Alert
            title="旧租赁合同与财务汇总入口已退休"
            description="该权属方详情页已停止加载旧租赁合同与权属财务接口，请改走新合同流程。"
            type="info"
            showIcon
            className={styles.detailsCard}
          />

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
                <Tag className={`${styles.countTag} ${styles.toneNeutral}`}>迁移中</Tag>
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
