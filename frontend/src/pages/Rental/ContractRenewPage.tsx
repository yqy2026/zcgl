/**
 * 合同续签页面
 *
 * @description 基于原合同创建新合同的续签页面
 * @module pages/Rental
 */

import React, { useState, useMemo } from 'react';
import { Card, Typography, Row, Col } from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { MessageManager } from '@/utils/messageManager';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { RentContractForm } from '@/components/Forms';
import type { RentTermData } from '@/components/Forms/RentContract';
import type { RentContractCreate, RentTerm } from '@/types/rentContract';
import { rentContractService } from '@/services/rentContractService';
import { RENTAL_QUERY_KEYS } from '@/constants/queryKeys';
import RenewalSummarySection from '@/components/Forms/RentContract/RenewalSummarySection';
import { createLogger } from '@/utils/logger';
import { PageContainer } from '@/components/Common';
import styles from './ContractRenewPage.module.css';

const pageLogger = createLogger('ContractRenewPage');

const { Title, Text } = Typography;

/**
 * 调整租金条款日期到新合同期间
 */
function adjustRentTermsDate(originalTerms: RentTerm[], newStartDate: dayjs.Dayjs): RentTermData[] {
  if (originalTerms == null || originalTerms.length === 0) return [];

  const originalStart = dayjs(originalTerms[0].start_date);
  const originalEnd = dayjs(originalTerms[originalTerms.length - 1].end_date);

  // 计算原合同总天数
  const totalDays = originalEnd.diff(originalStart, 'day');

  // 计算新合同结束日期
  const newEndDate = newStartDate.add(totalDays, 'day');

  // 调整每个条款的日期
  return originalTerms.map((term, index) => {
    const termStartOffset = dayjs(term.start_date).diff(originalStart, 'day');
    const termEndOffset = dayjs(term.end_date).diff(originalStart, 'day');

    return {
      monthly_rent: term.monthly_rent,
      rent_description: term.rent_description,
      management_fee: term.management_fee,
      other_fees: term.other_fees,
      start_date: newStartDate.add(termStartOffset, 'day').format('YYYY-MM-DD'),
      end_date:
        index === originalTerms.length - 1
          ? newEndDate.format('YYYY-MM-DD')
          : newStartDate.add(termEndOffset, 'day').format('YYYY-MM-DD'),
    };
  });
}

const ContractRenewPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [contractCreated, setContractCreated] = useState(false);

  // 获取原合同数据
  const { data: originalContract, isLoading: isLoadingContract } = useQuery({
    queryKey: RENTAL_QUERY_KEYS.contract(id),
    queryFn: () => rentContractService.getContract(id as string),
    enabled: id != null,
  });

  // 计算新合同的初始数据
  const initialFormData = useMemo(() => {
    if (!originalContract) return undefined;

    // 计算新合同开始日期（原合同结束+1天）
    const newStartDate = dayjs(originalContract.end_date).add(1, 'day');

    // 调整租金条款日期
    const adjustedRentTerms = adjustRentTermsDate(originalContract.rent_terms ?? [], newStartDate);

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
      start_date: newStartDate.format('YYYY-MM-DD'),
      // 结束日期需用户手动设置
      end_date: '',

      // 继承押金金额（可修改）
      total_deposit: originalContract.total_deposit,

      // 继承资产关联 - 确保始终是数组
      asset_ids: originalContract.assets?.map((a: { id: string }) => a.id) ?? [],

      // 继承租金条款（日期已调整）
      rent_terms: adjustedRentTerms,

      // 委托运营字段（仅委托合同）
      service_fee_rate: originalContract.service_fee_rate,
    };
  }, [originalContract]);

  // 续签 mutation
  const renewMutation = useMutation({
    mutationFn: (data: RentContractCreate) => rentContractService.renewContract(id!, data, true),
    onSuccess: newContract => {
      setContractCreated(true);
      MessageManager.success('合同续签成功！');

      // 3秒后跳转到新合同详情页
      setTimeout(() => {
        navigate(`/rental/contracts/${newContract.id}`);
      }, 3000);

      void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contractRoot });
      void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contractListRoot });
      void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contractStatistics });

      pageLogger.info('合同续签成功', {
        originalContractId: id,
        newContractId: newContract.id,
      });
    },
    onError: error => {
      pageLogger.error('续签合同失败:', error);
      MessageManager.error('续签合同失败，请检查网络连接');
    },
  });

  const isSubmitting = renewMutation.isPending;

  // 处理表单提交
  const handleSubmit = async (contractData: RentContractCreate) => {
    await renewMutation.mutateAsync(contractData);
  };

  // 取消操作
  const handleCancel = () => {
    navigate(`/rental/contracts/${id}`);
  };

  // 数据不存在状态
  if (!isLoadingContract && !originalContract) {
    return (
      <PageContainer title="合同续签" onBack={handleCancel}>
        <Card>
          <Text type="warning">原合同不存在，无法续签</Text>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      className={styles.pageContainer}
      title={
        <>
          <span className={styles.titleIcon}>
            <CheckCircleOutlined />
          </span>
          合同续签
        </>
      }
      subTitle={
        originalContract ? (
          <>
            基于原合同 {originalContract.contract_number}{' '}
            创建新合同，自动继承承租方、资产、租金条款等信息
          </>
        ) : undefined
      }
      onBack={handleCancel}
      loading={isLoadingContract}
    >
      {/* 创建/更新成功提示 */}
      {contractCreated && (
        <Card className={styles.successCard}>
          <Row align="middle">
            <Col>
              <CheckCircleOutlined className={styles.successIcon} />
            </Col>
            <Col flex="1">
              <Title level={4} className={styles.successTitle}>
                合同续签成功！
              </Title>
              <Text type="secondary">
                新合同已成功创建，原合同状态已变更为&quot;已续签&quot;，即将跳转到新合同详情页...
              </Text>
            </Col>
          </Row>
        </Card>
      )}

      {/* 创建指南 */}
      {!contractCreated && (
        <Card className={styles.guideCard}>
          <Title level={5} className={styles.guideTitle}>
            <CheckCircleOutlined className={styles.guideTitleIcon} />
            续签说明
          </Title>
          <Row gutter={16}>
            <Col span={6}>
              <div className={styles.guideStep}>
                <FileTextOutlined className={styles.guideStepIcon} />
                <div className={styles.guideStepText}>
                  <Text strong>自动继承</Text>
                  <br />
                  <Text type="secondary">承租方、资产</Text>
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div className={styles.guideStep}>
                <FileTextOutlined className={styles.guideStepIcon} />
                <div className={styles.guideStepText}>
                  <Text strong>日期调整</Text>
                  <br />
                  <Text type="secondary">新开始=原结束+1天</Text>
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div className={styles.guideStep}>
                <FileTextOutlined className={styles.guideStepIcon} />
                <div className={styles.guideStepText}>
                  <Text strong>条款继承</Text>
                  <br />
                  <Text type="secondary">租金金额保持不变</Text>
                </div>
              </div>
            </Col>
            <Col span={6}>
              <div className={styles.guideStep}>
                <FileTextOutlined className={styles.guideStepIcon} />
                <div className={styles.guideStepText}>
                  <Text strong>押金转移</Text>
                  <br />
                  <Text type="secondary">自动转到新合同</Text>
                </div>
              </div>
            </Col>
          </Row>
          <div className={styles.guideNotes}>
            <Text type="secondary">
              • 系统已自动预填原合同数据，请根据需要修改
              <br />
              • 新合同开始日期默认为原合同结束日期+1天
              <br />• 押金将自动从原合同转移到新合同
            </Text>
          </div>
        </Card>
      )}

      {/* 原合同摘要 */}
      {originalContract && <RenewalSummarySection contract={originalContract} />}

      {/* 续签表单 */}
      <Card title="新合同信息" loading={isSubmitting}>
        <RentContractForm
          mode="create"
          initialData={initialFormData}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          isLoading={isSubmitting}
        />
      </Card>
    </PageContainer>
  );
};

export default ContractRenewPage;
