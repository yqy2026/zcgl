/**
 * 项目管理页面
 */

import React, { Suspense } from 'react';
import { Spin, Row, Col, Typography } from 'antd';
import { COLORS } from '@/styles/colorMap';

// 动态导入项目列表组件
const ProjectList = React.lazy(() => import('@/components/Project/ProjectList'));
const { Title } = Typography;

const ProjectManagementPage: React.FC = () => {
  return (
    <div className="project-management-page" style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              项目管理
            </Title>
          </Col>
        </Row>
      </div>

      {/* 项目列表 */}
      <Suspense
        fallback={
          <div
            style={{
              padding: '60px',
              textAlign: 'center',
              backgroundColor: COLORS.bgSecondary,
            }}
          >
            <Spin size="large" />
            <div style={{ marginTop: '16' }}>正在加载项目管理功能...</div>
          </div>
        }
      >
        <ProjectList />
      </Suspense>
    </div>
  );
};

export default ProjectManagementPage;
