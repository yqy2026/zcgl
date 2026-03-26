import React, { useMemo } from 'react';
import { Breadcrumb } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useLocation, Link } from 'react-router-dom';
import { staticBreadcrumbMap, dynamicBreadcrumbMap } from '@/config/breadcrumb';
import { MANAGER_ROUTES, OWNER_ROUTES } from '@/constants/routes';
import styles from './AppBreadcrumb.module.css';

interface AppBreadcrumbProps {
  customItems?: { title: string; link?: string }[];
}

type BreadcrumbItems = NonNullable<React.ComponentProps<typeof Breadcrumb>['items']>;

const getBreadcrumbName = (path: string): string | null => {
  // 1. Static match
  if (staticBreadcrumbMap[path]) {
    return staticBreadcrumbMap[path];
  }

  // 2. Dynamic match
  for (const [pattern, name] of Object.entries(dynamicBreadcrumbMap)) {
    // Simple regex for :id -> [^/]+
    const regexPattern = pattern.replace(/:[^/]+/g, '([^/]+)');
    const regex = new RegExp(`^${regexPattern}$`);
    if (regex.test(path)) {
      return name;
    }
  }
  return null;
};

const renderCrumbLink = (to: string, label: React.ReactNode) => (
  <Link to={to} className={styles.breadcrumbLink}>
    {label}
  </Link>
);

const renderCrumbLabel = (label: React.ReactNode) => (
  <span className={styles.currentLabel}>{label}</span>
);

const resolveBreadcrumbLink = (pathname: string, url: string): string => {
  if (pathname.startsWith('/project/') && url === '/project') {
    return MANAGER_ROUTES.PROJECTS;
  }

  if (pathname.startsWith('/property-certificates/') && url === '/property-certificates') {
    return OWNER_ROUTES.PROPERTY_CERTIFICATES;
  }

  return url;
};

const AppBreadcrumb: React.FC<AppBreadcrumbProps> = ({ customItems }) => {
  const location = useLocation();
  const pathname = location.pathname;

  const breadcrumbItems = useMemo(() => {
    // Always include Home as the first item
    const items: BreadcrumbItems = [
      {
        key: 'home',
        title: (
          <Link to="/" aria-label="返回首页" className={styles.homeLink}>
            <HomeOutlined />
            <span className={styles.homeText}>首页</span>
          </Link>
        ),
      },
    ];

    // If custom items are provided, use them
    if (customItems && customItems.length > 0) {
      customItems.forEach((item, index) => {
        items.push({
          key: item.link ?? `custom-${index}`,
          title: item.link ? renderCrumbLink(item.link, item.title) : renderCrumbLabel(item.title),
        });
      });
      return items;
    }

    // Otherwise generate from path
    const pathSnippets = pathname.split('/').filter(i => i);

    pathSnippets.forEach((_, index) => {
      const url = `/${pathSnippets.slice(0, index + 1).join('/')}`;
      const name = getBreadcrumbName(url);

      if (name) {
        const isLast = index === pathSnippets.length - 1;
        items.push({
          key: url,
          title: isLast
            ? renderCrumbLabel(name)
            : renderCrumbLink(resolveBreadcrumbLink(pathname, url), name),
        });
      }
    });

    return items;
  }, [pathname, customItems]);

  return (
    <nav aria-label="页面路径" className={styles.breadcrumbWrapper}>
      <Breadcrumb className={styles.breadcrumb} items={breadcrumbItems} />
    </nav>
  );
};

export default AppBreadcrumb;
