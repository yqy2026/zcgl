/**
 * 权属方管理页面
 */

import React, { Suspense } from 'react';
import { Spin, Row, Col, Typography } from 'antd';

// 动态导入权属方列表组件
const OwnershipList = React.lazy(() => import('@/components/Ownership/OwnershipList'));
const { Title } = Typography;

const OwnershipManagementPage: React.FC = () => {
  return (
    <div className="ownership-management-page" style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              权属方管理
            </Title>
          </Col>
        </Row>
      </div>

      {/* 权属方列表 */}
      <Suspense
        fallback={
          <div
            style={{
              padding: '60px',
              textAlign: 'center',
              backgroundColor: '#fafafa',
            }}
          >
            <Spin size="large" />
            <div style={{ marginTop: '16' }}>正在加载权属方管理功能...</div>
          </div>
        }
      >
        <OwnershipList />
      </Suspense>
    </div>
  );
};

export default OwnershipManagementPage;
