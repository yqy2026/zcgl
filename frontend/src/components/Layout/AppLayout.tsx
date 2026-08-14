import React, { useCallback, useEffect, useState } from 'react';
import { Layout, Typography } from 'antd';

import { PartyScopeBlocked } from '@/components/Common';
import { type UserPartyScopeView, userService } from '@/services/systemService';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';
import MobileLayout from './MobileLayout';
import styles from './Layout.module.css';

const { Content, Footer } = Layout;
const TRANSPARENT_LAYOUT_STYLE = { background: 'transparent' };
const MOBILE_BREAKPOINT = 768;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_BREAKPOINT);
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

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const isScopeBlocked =
    scopeChecked &&
    myScope != null &&
    (myScope.error_code != null || myScope.scope_mode === 'none' || myScope.source === 'none');

  const content = isScopeBlocked ? (
    <PartyScopeBlocked
      scope={myScope}
      onRetry={() => {
        void loadMyScope();
      }}
    />
  ) : (
    children
  );

  if (isMobile) {
    return <MobileLayout>{content}</MobileLayout>;
  }

  return (
    <Layout className={styles.appLayout}>
      <AppSidebar collapsed={collapsed} />

      <Layout style={TRANSPARENT_LAYOUT_STYLE}>
        <AppHeader collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />

        <Content className={styles.content}>{content}</Content>

        <Footer className={styles.footer}>
          <Typography.Text type="secondary">
            土地物业资产运营管理系统 ©2024 Created by Asset Management Team
          </Typography.Text>
        </Footer>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
