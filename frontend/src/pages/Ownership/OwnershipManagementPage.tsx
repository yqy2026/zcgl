/**
 * 权属方管理页面
 */

import React, { Suspense } from 'react';
import { Spin } from 'antd';
import PageContainer from '@/components/Common/PageContainer';
import styles from './OwnershipManagementPage.module.css';

// 动态导入权属方列表组件
const OwnershipList = React.lazy(() => import('@/components/Ownership/OwnershipList'));

const OwnershipManagementPage: React.FC = () => {
  return (
    <PageContainer title="权属方管理" subTitle="维护权属主体信息及关联资产关系">
      {/* 权属方列表 */}
      <Suspense
        fallback={
          <div className={styles.loadingFallback}>
            <Spin size="large" />
            <div className={styles.loadingText}>正在加载权属方管理功能...</div>
          </div>
        }
      >
        <OwnershipList />
      </Suspense>
    </PageContainer>
  );
};

export default OwnershipManagementPage;
