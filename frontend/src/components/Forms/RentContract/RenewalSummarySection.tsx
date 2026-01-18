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
import { RentContract } from '../../../types/rentContract';
import { COLORS } from '@/styles/colorMap';

const { Text } = Typography;

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
    const statusMap: Record<string, { text: string; color: string }> = {
      有效: { text: '有效', color: 'green' },
      已到期: { text: '已到期', color: 'orange' },
      已终止: { text: '已终止', color: 'red' },
      已续签: { text: '已续签', color: 'blue' },
    };
    return statusMap[status] ?? { text: status, color: 'default' };
  };

  const statusInfo = getContractStatusLabel(contract.contract_status || '');

  return (
    <Card
      title={
        <Space>
          <FileTextOutlined style={{ color: COLORS.primary }} />
          原合同信息
        </Space>
      }
      size="small"
      style={{ marginBottom: 16 }}
      headStyle={{ borderBottom: '2px solid ' + COLORS.borderLight }}
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
          <Space direction="vertical" size={0}>
            <Text>
              {contract.start_date} ~ {contract.end_date}
            </Text>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="合同状态">
          <Text type={statusInfo.color as any}>{statusInfo.text}</Text>
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <DollarOutlined /> 押金金额
            </Space>
          }
        >
          <Text strong style={{ color: COLORS.primary }}>
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
            <Text type="secondary" style={{ marginLeft: 8 }}>
              （联系人: {contract.tenant_contact}）
            </Text>
          )}
        </Descriptions.Item>

        {contract.rent_terms != null && contract.rent_terms.length > 0 && (
          <Descriptions.Item label="租金条款" span={2}>
            <Space direction="vertical" size={0}>
              {contract.rent_terms.map((term, index) => (
                <Text key={index}>
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
