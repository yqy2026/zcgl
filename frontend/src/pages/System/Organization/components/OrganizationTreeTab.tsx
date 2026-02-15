import React from 'react';
import { Button, Tree } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import styles from '../../OrganizationPage.module.css';

interface OrganizationTreeTabProps {
  treeData: DataNode[];
  loading: boolean;
  onRefresh: () => void;
}

const OrganizationTreeTab: React.FC<OrganizationTreeTabProps> = ({
  treeData,
  loading,
  onRefresh,
}) => {
  return (
    <>
      <div className={styles.toolbarSection}>
        <Button
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          loading={loading}
          disabled={loading}
          className={styles.actionButton}
          aria-label="刷新组织树结构"
        >
          刷新树形结构
        </Button>
      </div>

      <Tree
        treeData={treeData}
        showLine={{ showLeafIcon: false }}
        defaultExpandAll
        className={styles.treePanel}
      />
    </>
  );
};

export default OrganizationTreeTab;
