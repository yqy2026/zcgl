/**
 * 新建/编辑租赁合同页面
 *
 * @description 支持创建和编辑两种模式，通过URL参数id判断
 * @module pages/Rental
 */

import React, { useState } from 'react';
import {
  Card,
  Button,
  Space,
  Breadcrumb,
  Typography,
  Row,
  Col,
  Statistic,
  Spin,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  HomeOutlined,
  FileTextOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  PlusOutlined,
  EditOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { RentContractForm } from '../../components/Forms';
import { RentContractCreate, RentContractUpdate } from '../../types/rentContract';
import { rentContractService } from '../../services/rentContractService';
import { useFormat } from '../../utils/format';
import { createLogger } from '../../utils/logger';
import { COLORS } from '@/styles/colorMap';

const pageLogger = createLogger('ContractCreateEdit');

const { Title, Text } = Typography;

const ContractCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const _format = useFormat();
  const queryClient = useQueryClient();

  // 判断当前模式：有id则为编辑模式
  const isEdit = !!id;

  const [loading, setLoading] = useState(false);
  const [contractCreated, setContractCreated] = useState(false);
  const [_createdContractId, _setCreatedContractId] = useState<string | null>(null);

  // 获取合同详情（编辑模式）
  const { data: contract, isLoading: isLoadingContract } = useQuery({
    queryKey: ['rent-contract', id],
    queryFn: () => rentContractService.getContract(id!),
    enabled: isEdit,
  });

  // 创建合同时的mutation
  const createMutation = useMutation({
    mutationFn: (data: RentContractCreate) => rentContractService.createContract(data),
    onSuccess: (contract) => {
      setContractCreated(true);
      _setCreatedContractId(contract.id);
      MessageManager.success('合同创建成功！');

      // 3秒后跳转到合同列表页面
      setTimeout(() => {
        navigate('/rental/contracts');
      }, 3000);
    },
    onError: (error) => {
      pageLogger.error('创建合同失败:', error as Error);
      MessageManager.error('创建合同失败，请检查网络连接');
    },
  });

  // 更新合同时的mutation
  const updateMutation = useMutation({
    mutationFn: (data: RentContractUpdate) => rentContractService.updateContract(id!, data),
    onSuccess: (contract) => {
      MessageManager.success('合同更新成功！');

      // 使相关查询缓存失效
      queryClient.invalidateQueries({ queryKey: ['rent-contract'] });
      queryClient.invalidateQueries({ queryKey: ['rent-contracts'] });

      // 跳转到详情页
      setTimeout(() => {
        navigate(`/rental/contracts/${contract.id}`);
      }, 1000);
    },
    onError: (error) => {
      pageLogger.error('更新合同失败:', error as Error);
      MessageManager.error('更新合同失败，请检查网络连接');
    },
  });

  // 处理表单提交
  const handleSubmit = async (contractData: RentContractCreate) => {
    setLoading(true);
    try {
      if (isEdit) {
        // 编辑模式：调用更新API
        await updateMutation.mutateAsync(contractData as RentContractUpdate);
      } else {
        // 创建模式：调用创建API
        await createMutation.mutateAsync(contractData);
      }
    } finally {
      setLoading(false);
    }
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

  // 加载状态（编辑模式下正在获取数据）
  if (isEdit && isLoadingContract) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>加载合同数据中...</div>
      </div>
    );
  }

  // 页面标题和描述
  const pageTitle = isEdit ? '编辑租赁合同' : '新建租赁合同';
  const pageDescription = isEdit
    ? '修改现有租赁合同信息和租金条款'
    : '创建新的租赁合同，填写完整的合同信息和租金条款';
  const pageIcon = isEdit ? <EditOutlined /> : <PlusOutlined />;
  const breadcrumbTitle = isEdit ? '编辑合同' : '新建合同';
  const successTitle = isEdit ? '合同更新成功！' : '合同创建成功！';
  const successMessage = isEdit
    ? '合同已成功更新，即将跳转到合同详情页面...'
    : '合同已成功创建并生成租金台账，即将跳转到合同列表页面...';
  const submitButtonText = isEdit ? '保存修改' : '创建合同';
  const cancelButtonText = isEdit ? '取消编辑' : '取消创建';

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
                  title: breadcrumbTitle,
                },
              ]}
            />
            <div style={{ marginTop: '16px' }}>
              <Title level={3} style={{ margin: 0 }}>
                <span style={{ marginRight: '8px', color: COLORS.primary }}>
                  {pageIcon}
                </span>
                {pageTitle}
              </Title>
              <Text type="secondary" style={{ marginTop: '8px', display: 'block' }}>
                {pageDescription}
              </Text>
            </div>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={handleCancel}
              >
                返回列表
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 创建/更新成功提示 */}
      {contractCreated && (
        <Card style={{ marginBottom: '16px', borderColor: COLORS.success, backgroundColor: 'var(--color-primary-light)' }}>
          <Row align="middle">
            <Col>
              <InfoCircleOutlined style={{ fontSize: '24px', color: COLORS.success, marginRight: '12px' }} />
            </Col>
            <Col flex="1">
              <Title level={4} style={{ color: COLORS.success, margin: 0 }}>
                {successTitle}
              </Title>
              <Text type="secondary">
                {successMessage}
              </Text>
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
                valueStyle={{ fontSize: '16px', color: COLORS.primary }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 2"
                value="关联资产"
                prefix={<InfoCircleOutlined />}
                valueStyle={{ fontSize: '16px', color: COLORS.primary }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 3"
                value="承租信息"
                prefix={<InfoCircleOutlined />}
                valueStyle={{ fontSize: '16px', color: COLORS.primary }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 4"
                value="租金条款"
                prefix={<InfoCircleOutlined />}
                valueStyle={{ fontSize: '16px', color: COLORS.primary }}
              />
            </Col>
          </Row>
          <div style={{ marginTop: '12px' }}>
            <Text type="secondary">
              • 请确保所有必填字段都已填写完整<br />
              • 租金条款可以设置多个时间段的租金<br />
              • 合同创建后将自动生成租金台账
            </Text>
          </div>
        </Card>
      )}

      {/* 合同表单 */}
      <Card title="合同信息" loading={loading}>
        <RentContractForm
          mode={isEdit ? 'edit' : 'create'}
          initialData={contract}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={loading}
        />
      </Card>

      {/* 底部操作栏 */}
      {!contractCreated && (
        <Card style={{ marginTop: '16px', textAlign: 'center' }}>
          <Space size="large">
            <Button
              size="large"
              icon={<ArrowLeftOutlined />}
              onClick={handleCancel}
            >
              {cancelButtonText}
            </Button>
            <Button
              type="primary"
              size="large"
              icon={<SaveOutlined />}
              loading={loading}
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
    </div>
  );
};

export default ContractCreatePage;
