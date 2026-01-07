/**
 * 新建租赁合同页面
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
  message,
} from 'antd';
import {
  HomeOutlined,
  FileTextOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  PlusOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { RentContractForm } from '../../components/Forms';
import { RentContractCreate } from '../../types/rentContract';
import { rentContractService } from '../../services/rentContractService';
import { useFormat } from '../../utils/format';
import { createLogger } from '../../utils/logger';

const pageLogger = createLogger('ContractCreate');

const { Title, Text } = Typography;

const ContractCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const _format = useFormat();
  const [loading, setLoading] = useState(false);
  const [contractCreated, setContractCreated] = useState(false);
  const [_createdContractId, _setCreatedContractId] = useState<string | null>(null);

  // 处理合同创建
  const handleCreateContract = async (contractData: RentContractCreate) => {
    setLoading(true);
    try {
      const contract = await rentContractService.createContract(contractData);

      setContractCreated(true);
      _setCreatedContractId(contract.id);
      message.success('合同创建成功！');

      // 3秒后跳转到合同列表页面
      setTimeout(() => {
        navigate('/rental/contracts');
      }, 3000);
    } catch (error) {
      pageLogger.error('创建合同失败:', error as Error);
      message.error('创建合同失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  // 取消创建
  const handleCancel = () => {
    navigate('/rental/contracts');
  };

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
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
                  title: '新建合同',
                },
              ]}
            />
            <div style={{ marginTop: '16px' }}>
              <Title level={3} style={{ margin: 0 }}>
                <PlusOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
                新建租赁合同
              </Title>
              <Text type="secondary" style={{ marginTop: '8px', display: 'block' }}>
                创建新的租赁合同，填写完整的合同信息和租金条款
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

      {/* 创建成功提示 */}
      {contractCreated && (
        <Card style={{ marginBottom: '16px', borderColor: '#52c41a', backgroundColor: '#f6ffed' }}>
          <Row align="middle">
            <Col>
              <InfoCircleOutlined style={{ fontSize: '24px', color: '#52c41a', marginRight: '12px' }} />
            </Col>
            <Col flex="1">
              <Title level={4} style={{ color: '#52c41a', margin: 0 }}>
                合同创建成功！
              </Title>
              <Text type="secondary">
                合同已成功创建并生成租金台账，即将跳转到合同列表页面...
              </Text>
            </Col>
          </Row>
        </Card>
      )}

      {/* 创建指南 */}
      {!contractCreated && (
        <Card style={{ marginBottom: '16px', backgroundColor: '#e6f7ff' }}>
          <Title level={5} style={{ color: '#1890ff', marginBottom: '12px' }}>
            <InfoCircleOutlined style={{ marginRight: '6px' }} />
            创建指南
          </Title>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="步骤 1"
                value="基本信息"
                prefix={<FileTextOutlined />}
                valueStyle={{ fontSize: '16px', color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 2"
                value="关联资产"
                prefix={<InfoCircleOutlined />}
                valueStyle={{ fontSize: '16px', color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 3"
                value="承租信息"
                prefix={<InfoCircleOutlined />}
                valueStyle={{ fontSize: '16px', color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="步骤 4"
                value="租金条款"
                prefix={<InfoCircleOutlined />}
                valueStyle={{ fontSize: '16px', color: '#1890ff' }}
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
          mode="create"
          onSubmit={handleCreateContract}
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
              取消创建
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
              创建合同
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default ContractCreatePage;
