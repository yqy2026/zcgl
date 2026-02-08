/**
 * 租赁合同详情页面
 *
 * @description 显示租赁合同的详细信息，包括基本信息、关联资产、租金条款等
 * @module pages/Rental
 */

import React, { useState } from 'react';
import { Button, Space, Alert } from 'antd';
import { EditOutlined, StopOutlined, SyncOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { rentContractService } from '@/services/rentContractService';
import { RENTAL_QUERY_KEYS } from '@/constants/queryKeys';
import ContractDetailInfo from '@/components/Rental/ContractDetailInfo';
import ContractTerminateModal from '@/components/Rental/ContractTerminateModal';
import { ContractStatus } from '@/types/rentContract';

/**
 * ContractDetailPage - 租赁合同详情页面组件
 *
 * 功能：
 * - 根据URL参数获取合同ID
 * - 使用React Query获取合同详情
 * - 显示合同基本信息、关联资产、租金条款
 * - 提供编辑和返回按钮
 */
const ContractDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [terminateModalVisible, setTerminateModalVisible] = useState(false);

  // 使用React Query获取合同详情
  const {
    data: contract,
    isLoading,
    error,
  } = useQuery({
    queryKey: RENTAL_QUERY_KEYS.contract(id),
    queryFn: () => rentContractService.getContract(id as string),
    enabled: id !== null && id !== undefined && id !== '',
  });

  // V2: 获取押金变动记录
  const { data: depositLedgers, isLoading: depositLoading } = useQuery({
    queryKey: RENTAL_QUERY_KEYS.contractDepositLedger(id),
    queryFn: () => rentContractService.getContractDepositLedger(id as string),
    enabled: id !== null && id !== undefined && id !== '',
  });

  // V2: 获取服务费台账
  const { data: serviceFeeLedgers, isLoading: serviceFeeLoading } = useQuery({
    queryKey: RENTAL_QUERY_KEYS.contractServiceFeeLedger(id),
    queryFn: () => rentContractService.getServiceFeeLedgers(id as string),
    enabled: id !== null && id !== undefined && id !== '',
  });

  // 获取合同标题
  const getContractTitle = () => {
    if (contract?.contract_number) {
      return `${contract.contract_number} - ${contract.tenant_name}`;
    }
    return contract?.tenant_name ?? '合同详情';
  };

  // 错误状态
  if (error) {
    return (
      <PageContainer title="合同详情" onBack={() => navigate('/rental/contracts')}>
        <Alert
          title="数据加载失败"
          description={`错误详情: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  // 数据不存在状态
  if (!isLoading && !contract) {
    return (
      <PageContainer title="合同详情" onBack={() => navigate('/rental/contracts')}>
        <Alert title="合同不存在" description="未找到指定的合同信息" type="warning" showIcon />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={getContractTitle()}
      loading={isLoading}
      onBack={() => navigate('/rental/contracts')}
      extra={
        <Space>
          {/* 只有合同状态为"有效"时才显示续签和终止按钮 */}
          {contract?.contract_status === ContractStatus.ACTIVE && (
            <>
              <Button
                type="default"
                icon={<SyncOutlined />}
                onClick={() => navigate(`/rental/contracts/${id}/renew`)}
              >
                续签合同
              </Button>
              <Button
                type="primary"
                danger
                icon={<StopOutlined />}
                onClick={() => setTerminateModalVisible(true)}
              >
                终止合同
              </Button>
            </>
          )}
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={() => navigate(`/rental/contracts/${id}/edit`)}
          >
            编辑合同
          </Button>
        </Space>
      }
    >
      {/* 合同详细信息 */}
      {contract && (
        <ContractDetailInfo
          contract={contract}
          depositLedgers={depositLedgers}
          depositLoading={depositLoading}
          serviceFeeLedgers={serviceFeeLedgers}
          serviceFeeLoading={serviceFeeLoading}
        />
      )}

      {/* 终止合同模态框 */}
      {contract && (
        <ContractTerminateModal
          visible={terminateModalVisible}
          contract={contract}
          onCancel={() => setTerminateModalVisible(false)}
          onSuccess={() => {
            setTerminateModalVisible(false);
            // 刷新合同详情数据
            queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contract(id) });
          }}
        />
      )}
    </PageContainer>
  );
};

export default ContractDetailPage;
