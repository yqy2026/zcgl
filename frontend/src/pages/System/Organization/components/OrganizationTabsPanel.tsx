import React, { useMemo } from 'react';
import { Tabs } from 'antd';
import type { DataNode } from 'antd/es/tree';
import OrganizationListTab, { type OrganizationListTabProps } from './OrganizationListTab';
import OrganizationTreeTab from './OrganizationTreeTab';
import styles from '../../OrganizationPage.module.css';

interface OrganizationTabsPanelProps {
  activeTab: string;
  onTabChange: (tabKey: string) => void;
  listTabProps: OrganizationListTabProps;
  treeData: DataNode[];
  isTreeLoading: boolean;
  onTreeRefresh: () => void;
}

const OrganizationTabsPanel: React.FC<OrganizationTabsPanelProps> = ({
  activeTab,
  onTabChange,
  listTabProps,
  treeData,
  isTreeLoading,
  onTreeRefresh,
}) => {
  const tabItems = useMemo(
    () => [
      {
        key: 'list',
        label: '列表视图',
        children: <OrganizationListTab {...listTabProps} />,
      },
      {
        key: 'tree',
        label: '树形视图',
        children: (
          <OrganizationTreeTab
            treeData={treeData}
            loading={isTreeLoading}
            onRefresh={onTreeRefresh}
          />
        ),
      },
    ],
    [isTreeLoading, listTabProps, onTreeRefresh, treeData]
  );

  return (
    <Tabs activeKey={activeTab} onChange={onTabChange} items={tabItems} className={styles.tabs} />
  );
};

export default OrganizationTabsPanel;
