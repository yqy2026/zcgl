/**
 * 新建/编辑租赁合同页面
 *
 * @description 支持创建和编辑两种模式，通过URL参数id判断
 * @module pages/Rental
 */

import React, { useState } from 'react';
import { Card, Button, Space, Typography, Row, Col, Statistic, Spin } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  FileTextOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { RentContractForm } from '@/components/Forms';
import { RentContractCreate, RentContractUpdate } from '@/types/rentContract';
import { rentContractService } from '@/services/rentContractService';
import { RENTAL_QUERY_KEYS } from '@/constants/queryKeys';
import { useFormat } from '@/utils/format';
import { createLogger } from '@/utils/logger';
import { COLORS } from '@/styles/colorMap';
import { PageContainer } from '@/components/Common';

const pageLogger = createLogger('ContractCreateEdit');

const { Title, Text } = Typography;

const ContractCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const _format = useFormat();
  const queryClient = useQueryClient();

  // 判断当前模式：有id则为编辑模式
  const isEdit = id != null;

  const [contractCreated, setContractCreated] = useState(false);
  const [_createdContractId, _setCreatedContractId] = useState<string | null>(null);

  // 获取合同详情（编辑模式）
  const { data: contract, isLoading: isLoadingContract } = useQuery({
    queryKey: RENTAL_QUERY_KEYS.contract(id),
    queryFn: () => rentContractService.getContract(id!),
    enabled: isEdit,
  });

  // 创建合同时的mutation
  const createMutation = useMutation({
    mutationFn: (data: RentContractCreate) => rentContractService.createContract(data),
    onSuccess: contract => {
      setContractCreated(true);
      _setCreatedContractId(contract.id);
      MessageManager.success('合同创建成功！');

      // 3秒后跳转到合同列表页面
      setTimeout(() => {
        navigate('/rental/contracts');
      }, 3000);
    },
    onError: error => {
      pageLogger.error('创建合同失败:', error);
      const errorMessage =
        error instanceof Error && error.message.trim() !== ''
          ? error.message
          : '创建合同失败，请检查网络连接';
      MessageManager.error(errorMessage);
    },
  });

  // 更新合同时的mutation
  const updateMutation = useMutation({
    mutationFn: (data: RentContractUpdate) => rentContractService.updateContract(id!, data),
    onSuccess: contract => {
      MessageManager.success('合同更新成功！');

      // 使相关查询缓存失效
      void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contractRoot });
      void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contractListRoot });
      void queryClient.invalidateQueries({ queryKey: RENTAL_QUERY_KEYS.contractStatistics });

      // 跳转到详情页
      setTimeout(() => {
        navigate(`/rental/contracts/${contract.id}`);
      }, 1000);
    },
    onError: error => {
      pageLogger.error('更新合同失败:', error);
      MessageManager.error('更新合同失败，请检查网络连接');
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  // 处理表单提交
  const handleSubmit = async (contractData: RentContractCreate) => {
    if (isEdit) {
      // 编辑模式：调用更新API
      await updateMutation.mutateAsync(contractData as RentContractUpdate);
      return;
    }

    // 创建模式：调用创建API
    await createMutation.mutateAsync(contractData);
  };

  // 取消操作
  const handleCancel = () => {
    if (isEdit) {
      // 编辑模式：返回详情页
      navigate(`/rental/contracts/${id}`);
    } else {
      // 创建模式：返回列表页
      navigate('/rental/contracts');
    }
  };

  // 页面标题和描述
  const pageTitle = isEdit ? '编辑租赁合同' : '新建租赁合同';
  const pageDescription = isEdit
    ? '修改现有租赁合同信息和租金条款'
    : '创建新的租赁合同，填写完整的合同信息和租金条款';
  const successTitle = isEdit ? '合同更新成功！' : '合同创建成功！';
  const successMessage = isEdit
    ? '合同已成功更新，即将跳转到合同详情页面...'
    : '合同已成功创建并生成租金台账，即将跳转到合同列表页面...';
  const submitButtonText = isEdit ? '保存修改' : '创建合同';
  const cancelButtonText = isEdit ? '取消编辑' : '取消创建';

  return (
    <PageContainer
      title={pageTitle}
      subTitle={pageDescription}
      onBack={handleCancel}
      loading={isEdit && isLoadingContract}
      contentStyle={{ background: COLORS.bgTertiary }}
    >
      {/* 创建/更新成功提示 */}
      {contractCreated && (
        <Card
          style={{
            marginBottom: '16px',
            borderColor: COLORS.success,
            backgroundColor: 'var(--color-primary-light)',
          }}
        >
          <Row align="middle">
            <Col>
              <InfoCircleOutlined
                style={{ fontSize: '24px', color: COLORS.success, marginRight: '12px' }}
              />
            </Col>
            <Col flex="1">
              <Title level={4} style={{ color: COLORS.success, margin: 0 }}>
                {successTitle}
              </Title>
              <Text type="secondary">{successMessage}</Text>
            </Col>
          </Row>
        </Card>
      )}

      {/* 创建指南 */}
      {!contractCreated && (
        <Card style={{ marginBottom: '16px', backgroundColor: 'var(--color-primary-light)' }}>
          <Title level={5} style={{ color: COLORS.primary, marginBottom: '12px' }}>
            <InfoCircleOutlined style={{ marginRight: '6px' }} />
            创建指南
          </Title>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="步骤 1"
                value="基本信息"
                prefix={<FileTextOutlined />}
                styles={{ content: { fontSize: '16px', color: COLORS.primary } }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 2"
                value="关联资产"
                prefix={<InfoCircleOutlined />}
                styles={{ content: { fontSize: '16px', color: COLORS.primary } }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 3"
                value="承租信息"
                prefix={<InfoCircleOutlined />}
                styles={{ content: { fontSize: '16px', color: COLORS.primary } }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 4"
                value="租金条款"
                prefix={<InfoCircleOutlined />}
                styles={{ content: { fontSize: '16px', color: COLORS.primary } }}
              />
            </Col>
          </Row>
          <div style={{ marginTop: '12px' }}>
            <Text type="secondary">
              • 请确保所有必填字段都已填写完整
              <br />
              • 租金条款可以设置多个时间段的租金
              <br />• 合同创建后将自动生成租金台账
            </Text>
          </div>
        </Card>
      )}

      {/* 合同表单 */}
      <Card title="合同信息" loading={isSubmitting}>
        <RentContractForm
          mode={isEdit ? 'edit' : 'create'}
          initialData={contract ?? undefined}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          isLoading={isSubmitting}
        />
      </Card>

      {/* 底部操作栏 */}
      {!contractCreated && (
        <Card style={{ marginTop: '16px', textAlign: 'center' }}>
          <Space size="large">
            <Button size="large" icon={<ArrowLeftOutlined />} onClick={handleCancel}>
              {cancelButtonText}
            </Button>
            <Button
              type="primary"
              size="large"
              icon={<SaveOutlined />}
              loading={isSubmitting}
              onClick={() => {
                // 触发表单提交
                const form = document.querySelector('form');
                if (form) {
                  const submitButton = form.querySelector('button[type="submit"]');
                  if (submitButton) {
                    (submitButton as HTMLButtonElement).click();
                  }
                }
              }}
            >
              {submitButtonText}
            </Button>
          </Space>
        </Card>
      )}
    </PageContainer>
  );
};

export default ContractCreatePage;
