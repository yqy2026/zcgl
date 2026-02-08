import React, { useMemo } from 'react';
import { Breadcrumb } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useLocation, Link } from 'react-router-dom';
import { staticBreadcrumbMap, dynamicBreadcrumbMap } from '@/config/breadcrumb';

interface AppBreadcrumbProps {
  customItems?: { title: string; link?: string }[];
}

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

const AppBreadcrumb: React.FC<AppBreadcrumbProps> = ({ customItems }) => {
  const location = useLocation();
  const pathname = location.pathname;

  const breadcrumbItems = useMemo(() => {
    // Always include Home as the first item
    const items = [
      {
        title: (
          <Link to="/">
            <HomeOutlined />
          </Link>
        ),
      },
    ];

    // If custom items are provided, use them
    if (customItems && customItems.length > 0) {
      customItems.forEach((item) => {
        items.push({
          title: item.link ? <Link to={item.link}>{item.title}</Link> : item.title,
        });
      });
      return items;
    }

    // Otherwise generate from path
    const pathSnippets = pathname.split('/').filter((i) => i);

    pathSnippets.forEach((_, index) => {
      const url = `/${pathSnippets.slice(0, index + 1).join('/')}`;
      const name = getBreadcrumbName(url);

      if (name) {
        const isLast = index === pathSnippets.length - 1;
        items.push({
          title: isLast ? (
            <span>{name}</span>
          ) : (
            <Link to={url}>{name}</Link>
          ),
        });
      }
    });

    return items;
  }, [pathname, customItems]);

  return <Breadcrumb items={breadcrumbItems} />;
};

export default AppBreadcrumb;
