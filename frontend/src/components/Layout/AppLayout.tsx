import React, { useCallback, useEffect, useState } from 'react';
import { Layout, Typography } from 'antd';

import { PartyScopeBlocked } from '@/components/Common';
import {
  type UserPartyScopeView,
  userService,
} from '@/services/systemService';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';
import styles from './Layout.module.css';

const { Content, Footer } = Layout;
const TRANSPARENT_LAYOUT_STYLE = { background: 'transparent' };

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [myScope, setMyScope] = useState<UserPartyScopeView | null>(null);
  const [scopeChecked, setScopeChecked] = useState(false);

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => !prev);
  }, []);

  const loadMyScope = useCallback(async () => {
    try {
      const scope = await userService.getMyPartyScope();
      setMyScope(scope);
    } catch {
      setMyScope(null);
    } finally {
      setScopeChecked(true);
    }
  }, []);

  useEffect(() => {
    void loadMyScope();
  }, [loadMyScope]);

  const isScopeBlocked =
    scopeChecked &&
    myScope != null &&
    (myScope.error_code != null ||
      myScope.scope_mode === 'none' ||
      myScope.source === 'none');

  return (
    <Layout className={styles.appLayout}>
      {/* 侧边栏 */}
      <AppSidebar collapsed={collapsed} />

      <Layout style={TRANSPARENT_LAYOUT_STYLE}>
        {/* 头部 */}
        <AppHeader collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />

        {/* 主内容区 */}
        <Content className={styles.content}>
          {isScopeBlocked ? (
            <PartyScopeBlocked
              scope={myScope}
              onRetry={() => {
                void loadMyScope();
              }}
            />
          ) : (
            children
          )}
        </Content>

        {/* 页脚 */}
        <Footer className={styles.footer}>
          <Typography.Text type="secondary">
            土地房产资产管理系统 ©2024 Created by Asset Management Team
          </Typography.Text>
        </Footer>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
