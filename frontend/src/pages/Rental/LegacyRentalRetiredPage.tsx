import React from 'react';
import { Alert, Button, Result, Space, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/Common';
import { CONTRACT_GROUP_ROUTES } from '@/constants/routes';

const LegacyRentalRetiredPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <PageContainer
      title="租赁前端模块已退休"
      subTitle="旧合同前端页面已下线，避免继续调用已经退休的后端接口。"
    >
      <Result
        status="warning"
        title="租赁前端模块已退休"
        subTitle="合同组与台账前端正在切换到新 contract/contract-group 体系。当前旧页面入口已显式关闭。"
        extra={
          <Space>
            <Button type="primary" onClick={() => navigate(CONTRACT_GROUP_ROUTES.LIST)}>
              查看合同组
            </Button>
            <Button onClick={() => navigate(CONTRACT_GROUP_ROUTES.IMPORT)}>PDF导入</Button>
            <Button type="link" onClick={() => navigate('/dashboard')}>
              返回工作台
            </Button>
            <Button type="link" onClick={() => navigate('/assets/list')}>
              查看资产
            </Button>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        title="当前状态"
        description={
          <Typography.Paragraph>
            后端旧合同接口已经退休。这里不再尝试兼容旧前端，而是直接暴露迁移状态。
          </Typography.Paragraph>
        }
      />
    </PageContainer>
  );
};

export default LegacyRentalRetiredPage;
