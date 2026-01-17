/**
 * 租赁合同详细信息展示组件
 *
 * @description 展示租赁合同的详细信息，包括基本信息、关联资产、租金条款等
 * @module components/Rental
 */

import React from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Table,
  Row,
  Col,
  Statistic,
  Divider,
} from 'antd';
import {
  FileTextOutlined,
  UserOutlined,
  CalendarOutlined,
  DollarOutlined,
  HomeOutlined,
  BankOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { RentContract, DepositLedger, ServiceFeeLedger } from '@/types/rentContract';
import type { ColumnsType } from 'antd/es/table';
import DepositLedgerHistory from './DepositLedgerHistory';
import ServiceFeeLedgerTable from './ServiceFeeLedgerTable';

interface ContractDetailInfoProps {
  contract: RentContract;
  depositLedgers?: DepositLedger[];
  depositLoading?: boolean;
  serviceFeeLedgers?: ServiceFeeLedger[];
  serviceFeeLoading?: boolean;
}

/**
 * 合同类型映射
 */
const CONTRACT_TYPE_MAP: Record<string, { label: string; color: string }> = {
  lease_upstream: { label: '承租合同（上游）', color: 'blue' },
  lease_downstream: { label: '租赁合同（下游）', color: 'green' },
  entrusted: { label: '委托运营协议', color: 'orange' },
};

/**
 * 付款周期映射
 */
const PAYMENT_CYCLE_MAP: Record<string, string> = {
  monthly: '按月',
  quarterly: '按季度',
  semi_annual: '半年',
  annual: '按年',
};

/**
 * ContractDetailInfo - 合同详细信息组件
 */
const ContractDetailInfo: React.FC<ContractDetailInfoProps> = ({
  contract,
  depositLedgers,
  depositLoading,
  serviceFeeLedgers,
  serviceFeeLoading,
}) => {
  // 租金条款表格列定义
  const rentTermColumns: ColumnsType<any> = [
    {
      title: '序号',
      key: 'index',
      width: 80,
      render: (_: unknown, __: unknown, index: number) => index + 1,
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '结束日期',
      dataIndex: 'end_date',
      key: 'end_date',
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '月租金',
      dataIndex: 'monthly_rent',
      key: 'monthly_rent',
      render: (amount: number) => `¥${amount.toLocaleString()}`,
      align: 'right' as const,
    },
    {
      title: '管理费',
      dataIndex: 'management_fee',
      key: 'management_fee',
      render: (amount: number) => `¥${amount.toLocaleString()}`,
      align: 'right' as const,
    },
    {
      title: '其他费用',
      dataIndex: 'other_fees',
      key: 'other_fees',
      render: (amount: number) => `¥${amount.toLocaleString()}`,
      align: 'right' as const,
    },
    {
      title: '月总金额',
      dataIndex: 'total_monthly_amount',
      key: 'total_monthly_amount',
      render: (amount: number) => (
        <span style={{ color: '#1890ff', fontWeight: 'bold' }}>
          ¥{amount.toLocaleString()}
        </span>
      ),
      align: 'right' as const,
    },
    {
      title: '描述',
      dataIndex: 'rent_description',
      key: 'rent_description',
      render: (text: string) => text || '-',
    },
  ];

  // 计算统计数据
  const calculateStats = () => {
    const totalMonthlyRent = contract.rent_terms?.reduce(
      (sum, term) => sum + (term.total_monthly_amount ?? term.monthly_rent + term.management_fee + term.other_fees),
      0
    ) ?? 0;
    const avgMonthlyRent = (contract.rent_terms?.length ?? 0) > 0 ? totalMonthlyRent / (contract.rent_terms.length ?? 1) : 0;
    const assetCount = contract.assets?.length ?? 0;

    return {
      totalMonthlyRent,
      avgMonthlyRent,
      assetCount,
      termCount: contract.rent_terms?.length ?? 0,
    };
  };

  const stats = calculateStats();

  return (
    <div>
      {/* 基本信息卡片 */}
      <Card
        title={
          <span>
            <InfoCircleOutlined style={{ marginRight: 8 }} />
            基本信息
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions
          bordered
          column={{ xs: 1, sm: 2, md: 3 }}
          styles={{
            label: { width: '130px', fontWeight: 'bold' },
            content: { minWidth: '180px' },
          }}
        >
          <Descriptions.Item
            label={
              <span>
                <FileTextOutlined style={{ marginRight: 4 }} />
                合同编号
              </span>
            }
          >
            <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#1890ff' }}>
              {contract.contract_number || '自动生成'}
            </span>
          </Descriptions.Item>

          <Descriptions.Item
            label={
              <span>
                <BankOutlined style={{ marginRight: 4 }} />
                合同类型
              </span>
            }
          >
            <Tag color={CONTRACT_TYPE_MAP[contract.contract_type]?.color || 'default'}>
              {CONTRACT_TYPE_MAP[contract.contract_type]?.label || contract.contract_type}
            </Tag>
          </Descriptions.Item>

          <Descriptions.Item
            label={
              <span>
                <BankOutlined style={{ marginRight: 4 }} />
                合同状态
              </span>
            }
          >
            <Tag color={contract.contract_status === '有效' ? 'green' : 'red'}>
              {contract.contract_status}
            </Tag>
          </Descriptions.Item>

          <Descriptions.Item
            label={
              <span>
                <UserOutlined style={{ marginRight: 4 }} />
                承租方名称
              </span>
            }
          >
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {contract.tenant_name}
            </span>
          </Descriptions.Item>

          <Descriptions.Item label="联系人">
            {contract.tenant_contact ?? '-'}
          </Descriptions.Item>

          <Descriptions.Item label="联系电话">
            {contract.tenant_phone ?? '-'}
          </Descriptions.Item>

          <Descriptions.Item label="承租方地址" span={2}>
            {contract.tenant_address ?? '-'}
          </Descriptions.Item>

          <Descriptions.Item label="用途说明（下游合同）">
            {contract.tenant_usage ?? '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 租期和金额统计卡片 */}
      <Card
        title={
          <span>
            <CalendarOutlined style={{ marginRight: 8 }} />
            租期与金额
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="签订日期"
              value={new Date(contract.sign_date).toLocaleDateString('zh-CN')}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="租期开始"
              value={new Date(contract.start_date).toLocaleDateString('zh-CN')}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="租期结束"
              value={new Date(contract.end_date).toLocaleDateString('zh-CN')}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="总押金"
              value={contract.total_deposit}
              prefix="¥"
              valueStyle={{ color: '#faad14' }}
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="月均租金"
              value={stats.avgMonthlyRent}
              prefix="¥"
              precision={2}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Statistic
              title="付款周期"
              value={PAYMENT_CYCLE_MAP[contract.payment_cycle || 'monthly'] || contract.payment_cycle || '按月'}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Col>
        </Row>
      </Card>

      {/* V2字段：上游合同和服务费率 */}
      {(contract.upstream_contract_id != null || contract.service_fee_rate != null) && (
        <Card
          title="V2 委托运营信息"
          style={{ marginBottom: 16 }}
        >
          <Descriptions bordered column={{ xs: 1, sm: 2 }} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="上游合同ID">
              {contract.upstream_contract_id ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="服务费率">
              {contract.service_fee_rate !== undefined && contract.service_fee_rate !== null
                ? `${(contract.service_fee_rate * 100).toFixed(2)}%`
                : '-'}
            </Descriptions.Item>
          </Descriptions>

          {/* 服务费台账表格 */}
          {(serviceFeeLoading != null && serviceFeeLoading) || ((serviceFeeLedgers ?? []).length > 0) ? (
            <>
              <Divider titlePlacement="start" style={{ margin: '12px 0' }}>服务费台账</Divider>
              <ServiceFeeLedgerTable ledgers={serviceFeeLedgers ?? []} loading={serviceFeeLoading} />
            </>
          ) : null}
        </Card>
      )}

      {/* 关联资产卡片 */}
      <Card
        title={
          <span>
            <HomeOutlined style={{ marginRight: 8 }} />
            关联资产 ({stats.assetCount})
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        {contract.assets && contract.assets.length > 0 ? (
          <Table
            dataSource={contract.assets}
            rowKey="id"
            pagination={false}
            size="small"
            columns={[
              {
                title: '物业名称',
                dataIndex: 'property_name',
                key: 'property_name',
              },
              {
                title: '地址',
                dataIndex: 'address',
                key: 'address',
                render: (address: string) => address || '-',
              },
              {
                title: '权属方',
                dataIndex: 'ownership_entity',
                key: 'ownership_entity',
              },
            ]}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
            暂无关联资产
          </div>
        )}
      </Card>

      {/* 租金条款表格 */}
      <Card
        title={
          <span>
            <DollarOutlined style={{ marginRight: 8 }} />
            租金条款 ({stats.termCount})
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          dataSource={contract.rent_terms ?? []}
          columns={rentTermColumns}
          rowKey="id"
          pagination={false}
          size="small"
          bordered
        />
      </Card>

      {/* V2: 押金变动记录 */}
      <DepositLedgerHistory
        depositLedgers={depositLedgers}
        loading={depositLoading}
      />

      {/* 其他信息 */}
      {(contract.payment_terms != null || contract.contract_notes != null) && (
        <Card
          title={
            <span>
              <InfoCircleOutlined style={{ marginRight: 8 }} />
              其他信息
            </span>
          }
        >
          <Descriptions bordered column={1}>
            {contract.payment_terms != null && (
              <Descriptions.Item label="支付条款">
                <div style={{ whiteSpace: 'pre-wrap' }}>{contract.payment_terms}</div>
              </Descriptions.Item>
            )}
            {contract.contract_notes != null && (
              <Descriptions.Item label="合同备注">
                <div style={{ whiteSpace: 'pre-wrap' }}>{contract.contract_notes}</div>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}

      {/* 元数据信息 */}
      <Card
        title="元数据"
        style={{ marginTop: 16 }}
      >
        <Descriptions bordered column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="数据状态">
            <Tag color={contract.data_status === '正常' ? 'green' : 'red'}>
              {contract.data_status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="版本号">
            v{contract.version}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(contract.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {new Date(contract.updated_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default ContractDetailInfo;
