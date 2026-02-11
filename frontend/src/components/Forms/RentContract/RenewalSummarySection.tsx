/**
 * 合同续签 - 原合同摘要信息组件
 *
 * @description 以只读形式展示原合同关键信息，帮助用户核对续签数据
 * @module components/Forms/RentContract
 */

import React from 'react';
import { Card, Descriptions, Typography, Space } from 'antd';
import {
  FileTextOutlined,
  CalendarOutlined,
  DollarOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import {
  RentContract,
  ContractStatus,
  ContractStatusLabels,
  ContractStatusColors,
} from '@/types/rentContract';
import styles from './RenewalSummarySection.module.css';

const { Text } = Typography;

type TextType = 'secondary' | 'success' | 'warning' | 'danger';

interface RenewalSummarySectionProps {
  contract: RentContract;
}

/**
 * 原合同摘要信息组件
 */
const RenewalSummarySection: React.FC<RenewalSummarySectionProps> = ({ contract }) => {
  // 获取合同类型标签
  const getContractTypeLabel = (type: string): string => {
    const typeMap: Record<string, string> = {
      lease_upstream: '承租合同',
      lease_downstream: '租赁合同',
      entrusted: '委托运营协议',
    };
    return typeMap[type] || type;
  };

  // 获取合同状态标签
  const getContractStatusLabel = (status: string): { text: string; color: string } => {
    return {
      text: ContractStatusLabels[status as ContractStatus] || status,
      color: ContractStatusColors[status as ContractStatus] || 'default',
    };
  };

  const statusInfo = getContractStatusLabel(contract.contract_status || '');
  const statusTextType: TextType =
    statusInfo.color === 'success'
      ? 'success'
      : statusInfo.color === 'warning'
        ? 'warning'
        : statusInfo.color === 'error' || statusInfo.color === 'magenta'
          ? 'danger'
          : 'secondary';

  return (
    <Card
      title={
        <Space>
          <FileTextOutlined className={styles.titleIcon} />
          原合同信息
        </Space>
      }
      size="small"
      className={styles.summaryCard}
    >
      <Descriptions column={2} size="small" bordered>
        <Descriptions.Item label="合同编号">
          <Text strong>{contract.contract_number}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="合同类型">
          <Text>{getContractTypeLabel(contract.contract_type)}</Text>
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <CalendarOutlined /> 原租期
            </Space>
          }
        >
          <Space orientation="vertical" size={0}>
            <Text>
              {contract.start_date} ~ {contract.end_date}
            </Text>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="合同状态">
          <Text type={statusTextType}>{statusInfo.text}</Text>
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <DollarOutlined /> 押金金额
            </Space>
          }
        >
          <Text strong className={styles.depositValue}>
            ¥
            {(typeof contract.total_deposit === 'number'
              ? contract.total_deposit
              : (parseFloat(contract.total_deposit as string) ?? 0)
            ).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </Text>
        </Descriptions.Item>
        <Descriptions.Item
          label={
            <Space>
              <HomeOutlined /> 关联资产
            </Space>
          }
        >
          <Text>{contract.assets?.length ?? 0} 个资产</Text>
        </Descriptions.Item>

        <Descriptions.Item label="承租方/委托方" span={2}>
          <Text strong>{contract.tenant_name}</Text>
          {contract.tenant_contact != null && (
            <Text type="secondary" className={styles.contactText}>
              （联系人: {contract.tenant_contact}）
            </Text>
          )}
        </Descriptions.Item>

        {contract.rent_terms != null && contract.rent_terms.length > 0 && (
          <Descriptions.Item label="租金条款" span={2}>
            <Space orientation="vertical" size={0}>
              {contract.rent_terms.map((term, index) => (
                <Text key={`${term.start_date}-${term.end_date}-${term.total_monthly_amount}`}>
                  条款{index + 1}: {term.start_date} ~ {term.end_date}, 月租 ¥
                  {(typeof term.total_monthly_amount === 'number'
                    ? term.total_monthly_amount
                    : (parseFloat(term.total_monthly_amount as string) ?? 0)
                  ).toLocaleString('zh-CN')}
                </Text>
              ))}
            </Space>
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  );
};

export default RenewalSummarySection;
