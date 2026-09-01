import type { ReactNode } from 'react';
import {
  ApartmentOutlined,
  BankOutlined,
  FileTextOutlined,
  HomeOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  TeamOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import styles from './AssetOperationsPrototype.module.css';

const primaryNav = [
  { label: '工作台', icon: HomeOutlined },
  { label: '招商租赁', icon: FileTextOutlined },
  { label: '收付催收', icon: BankOutlined },
  { label: '物业作业', icon: ToolOutlined },
  { label: '资产与权属', icon: SafetyCertificateOutlined },
] as const;

const referenceNav = [
  { label: '运营项目', icon: ApartmentOutlined },
  { label: '客户与合作方', icon: TeamOutlined },
] as const;

interface PrototypeShellProps {
  activeNav: string;
  children: ReactNode;
  activityMessage: string | null;
}

export default function PrototypeShell({
  activeNav,
  children,
  activityMessage,
}: PrototypeShellProps) {
  const renderNav = (items: typeof primaryNav | typeof referenceNav) =>
    items.map(item => {
      const Icon = item.icon;
      const isActive = item.label === activeNav;
      return (
        <button
          key={item.label}
          type="button"
          className={isActive ? styles.navItemActive : styles.navItem}
        >
          <Icon aria-hidden="true" />
          <span>{item.label}</span>
        </button>
      );
    });

  return (
    <div className={styles.prototypeRoot}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">
            <ApartmentOutlined />
          </span>
          <strong>资管运营</strong>
        </div>

        <nav className={styles.navigation} aria-label="业务导航">
          <div>{renderNav(primaryNav)}</div>
          <div className={styles.navReference}>{renderNav(referenceNav)}</div>
        </nav>

        <div className={styles.sidebarFoot}>
          <span className={styles.avatar}>张</span>
          <span>
            <strong>张三</strong>
            <small>资产运营部</small>
          </span>
        </div>
      </aside>

      <section className={styles.appColumn}>
        <header className={styles.topbar}>
          <button type="button" className={styles.portfolioButton}>
            全部运营项目 <span>86</span>
          </button>
          <label className={styles.globalSearch}>
            <SearchOutlined aria-hidden="true" />
            <input placeholder="搜索项目、空间、客户" aria-label="全局搜索" />
          </label>
          {activityMessage != null ? (
            <span className={styles.activityMessage} role="status">
              {activityMessage}
            </span>
          ) : (
            <span className={styles.prototypeLabel}>演示数据</span>
          )}
        </header>
        <main className={styles.mainSurface}>{children}</main>
      </section>
    </div>
  );
}
