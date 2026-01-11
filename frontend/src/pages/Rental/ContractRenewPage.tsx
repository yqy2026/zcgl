/**
 * 合同续签页面
 *
 * @description 基于原合同创建新合同的续签页面
 * @module pages/Rental
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Button,
  Space,
  Breadcrumb,
  Typography,
  Row,
  Col,
  Spin,
} from 'antd';
import {
  HomeOutlined,
  FileTextOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { MessageManager } from '@/utils/messageManager';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { addDays, differenceInDays, parseISO, formatISO } from 'date-fns';
import { RentContractForm } from '../../components/Forms';
import { RentContractCreate } from '../../types/rentContract';
import { rentContractService } from '../../services/rentContractService';
import RenewalSummarySection from '../../components/Forms/RentContract/RenewalSummarySection';
import { createLogger } from '../../utils/logger';
import { COLORS } from '@/styles/colorMap';

const pageLogger = createLogger('ContractRenewPage');

const { Title, Text } = Typography;

/**
 * 调整租金条款日期到新合同期间
 */
function adjustRentTermsDate(
  originalTerms: any[],
  newStartDate: Date
): any[] {
  if (!originalTerms || originalTerms.length === 0) return [];

  const originalStart = parseISO(originalTerms[0].start_date);
  const originalEnd = parseISO(originalTerms[originalTerms.length - 1].end_date);

  // 计算原合同总天数
  const totalDays = differenceInDays(originalEnd, originalStart);

  // 计算新合同结束日期
  const newEndDate = addDays(newStartDate, totalDays);

  // 调整每个条款的日期
  return originalTerms.map((term, index) => {
    const termStartOffset = differenceInDays(parseISO(term.start_date), originalStart);
    const termEndOffset = differenceInDays(parseISO(term.end_date), originalStart);

    return {
      ...term,
      start_date: formatISO(addDays(newStartDate, termStartOffset), { representation: 'date' }),
      end_date: index === originalTerms.length - 1
        ? formatISO(newEndDate, { representation: 'date' })
        : formatISO(addDays(newStartDate, termEndOffset), { representation: 'date' }),
    };
  });
}

const ContractRenewPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const _queryClient = useQueryClient();

  const [loading, setLoading] = useState(false);
  const [contractCreated, setContractCreated] = useState(false);

  // 获取原合同数据
  const { data: originalContract, isLoading: isLoadingContract } = useQuery({
    queryKey: ['rent-contract', id],
    queryFn: () => rentContractService.getContract(id as string),
    enabled: !!id,
  });

  // 计算新合同的初始数据
  const initialFormData = useMemo(() => {
    if (!originalContract) return undefined;

    // 计算新合同开始日期（原合同结束+1天）
    const newStartDate = addDays(parseISO(originalContract.end_date), 1);

    // 调整租金条款日期
    const adjustedRentTerms = adjustRentTermsDate(
      originalContract.rent_terms || [],
      newStartDate
    );

    return {
      // 继承基本信息
      contract_type: originalContract.contract_type,
      ownership_id: originalContract.ownership_id,
      tenant_name: originalContract.tenant_name,
      tenant_contact: originalContract.tenant_contact,
      tenant_phone: originalContract.tenant_phone,
      tenant_address: originalContract.tenant_address,
      tenant_usage: originalContract.tenant_usage,

      // 新合同开始日期 = 原合同结束+1天
      start_date: formatISO(newStartDate, { representation: 'date' }),
      // 结束日期需用户手动设置
      end_date: '',

      // 继承押金金额（可修改）
      total_deposit: originalContract.total_deposit,

      // 继承资产关联 - 确保始终是数组
      asset_ids: originalContract.assets?.map((a: { id: string }) => a.id) || [],

      // 继承租金条款（日期已调整）
      rent_terms: adjustedRentTerms,

      // 委托运营字段（仅委托合同）
      service_fee_rate: originalContract.service_fee_rate,
    };
  }, [originalContract]);

  // 续签 mutation
  const renewMutation = useMutation({
    mutationFn: (data: RentContractCreate) =>
      rentContractService.renewContract(id!, data, true),
    onSuccess: (newContract) => {
      setContractCreated(true);
      MessageManager.success('合同续签成功！');

      // 3秒后跳转到新合同详情页
      setTimeout(() => {
        navigate(`/rental/contracts/${newContract.id}`);
      }, 3000);

      pageLogger.info('合同续签成功', {
        originalContractId: id,
        newContractId: newContract.id
      });
    },
    onError: (error) => {
      pageLogger.error('续签合同失败:', error as Error);
      MessageManager.error('续签合同失败，请检查网络连接');
    },
  });

  // 处理表单提交
  const handleSubmit = async (contractData: RentContractCreate) => {
    setLoading(true);
    try {
      await renewMutation.mutateAsync(contractData);
    } finally {
      setLoading(false);
    }
  };

  // 取消操作
  const handleCancel = () => {
    navigate(`/rental/contracts/${id}`);
  };

  // 加载状态
  if (isLoadingContract) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载原合同数据中...</div>
      </div>
    );
  }

  // 数据不存在状态
  if (!originalContract) {
    return (
      <div style={{ padding: '24px' }}>
        <Card>
          <Text type="warning">原合同不存在，无法续签</Text>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', background: COLORS.bgTertiary, minHeight: '100vh' }}>
      {/* 页面头部 */}
      <Card style={{ marginBottom: '16px' }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Breadcrumb
              items={[
                {
                  href: '/',
                  title: <HomeOutlined />,
                },
                {
                  href: '/rental/contracts',
                  title: (
                    <span>
                      <FileTextOutlined />
                      <span style={{ marginLeft: '4px' }}>合同管理</span>
                    </span>
                  ),
                },
                {
                  href: `/rental/contracts/${id}`,
                  title: '原合同',
                },
                {
                  title: '续签合同',
                },
              ]}
            />
            <div style={{ marginTop: '16px' }}>
              <Title level={3} style={{ margin: 0 }}>
                <span style={{ marginRight: '8px', color: COLORS.success }}>
                  <CheckCircleOutlined />
                </span>
                合同续签
              </Title>
              <Text type="secondary" style={{ marginTop: '8px', display: 'block' }}>
                基于原合同 {originalContract.contract_number} 创建新合同，自动继承承租方、资产、租金条款等信息
              </Text>
            </div>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={handleCancel}
              >
                返回原合同
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 创建/更新成功提示 */}
      {contractCreated && (
        <Card style={{ marginBottom: '16px', borderColor: COLORS.success, backgroundColor: 'var(--color-success-light, #f6ffed)' }}>
          <Row align="middle">
            <Col>
              <CheckCircleOutlined style={{ fontSize: '24px', color: COLORS.success, marginRight: '12px' }} />
            </Col>
            <Col flex="1">
              <Title level={4} style={{ color: COLORS.success, margin: 0 }}>
                合同续签成功！
              </Title>
              <Text type="secondary">
                新合同已成功创建，原合同状态已变更为"已续签"，即将跳转到新合同详情页...
              </Text>
            </Col>
          </Row>
        </Card>
      )}

      {/* 创建指南 */}
      {!contractCreated && (
        <Card style={{ marginBottom: '16px', backgroundColor: 'var(--color-primary-light, #e6f7ff)' }}>
          <Title level={5} style={{ color: COLORS.primary, marginBottom: '12px' }}>
            <CheckCircleOutlined style={{ marginRight: '6px' }} />
            续签说明
          </Title>
          <Row gutter={16}>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px' }}>
                <FileTextOutlined style={{ fontSize: '24px', color: COLORS.primary }} />
                <div style={{ marginTop: '8px' }}>
                  <Text strong>自动继承</Text>
                  <br />
                  <Text type="secondary">承租方、资产</Text>
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px' }}>
                <FileTextOutlined style={{ fontSize: '24px', color: COLORS.primary }} />
                <div style={{ marginTop: '8px' }}>
                  <Text strong>日期调整</Text>
                  <br />
                  <Text type="secondary">新开始=原结束+1天</Text>
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px' }}>
                <FileTextOutlined style={{ fontSize: '24px', color: COLORS.primary }} />
                <div style={{ marginTop: '8px' }}>
                  <Text strong>条款继承</Text>
                  <br />
                  <Text type="secondary">租金金额保持不变</Text>
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center', padding: '8px' }}>
                <FileTextOutlined style={{ fontSize: '24px', color: COLORS.primary }} />
                <div style={{ marginTop: '8px' }}>
                  <Text strong>押金转移</Text>
                  <br />
                  <Text type="secondary">自动转到新合同</Text>
                </div>
              </div>
            </Col>
          </Row>
          <div style={{ marginTop: '12px' }}>
            <Text type="secondary">
              • 系统已自动预填原合同数据，请根据需要修改<br />
              • 新合同开始日期默认为原合同结束日期+1天<br />
              • 押金将自动从原合同转移到新合同
            </Text>
          </div>
        </Card>
      )}

      {/* 原合同摘要 */}
      <RenewalSummarySection contract={originalContract} />

      {/* 续签表单 */}
      <Card title="新合同信息" loading={loading}>
        <RentContractForm
          mode="create"
          initialData={initialFormData}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
        />
      </Card>
    </div>
  );
};

export default ContractRenewPage;
