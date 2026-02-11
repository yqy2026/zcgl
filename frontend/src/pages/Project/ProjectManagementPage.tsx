/**
 * 项目管理页面
 */

import React, { Suspense } from 'react';
import { Spin } from 'antd';
import PageContainer from '@/components/Common/PageContainer';
import styles from './ProjectManagementPage.module.css';

// 动态导入项目列表组件
const ProjectList = React.lazy(() => import('@/components/Project/ProjectList'));

const ProjectManagementPage: React.FC = () => {
  return (
    <PageContainer title="项目管理" subTitle="统一管理项目台账与关联权属信息">
      {/* 项目列表 */}
      <Suspense
        fallback={
          <div className={styles.loadingFallback}>
            <Spin size="large" />
            <div className={styles.loadingText}>正在加载项目管理功能...</div>
          </div>
        }
      >
        <ProjectList />
      </Suspense>
    </PageContainer>
  );
};

export default ProjectManagementPage;
