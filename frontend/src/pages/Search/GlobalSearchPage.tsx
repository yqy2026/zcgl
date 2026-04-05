import React, { useMemo, useState } from 'react';
import { Alert, Button, Card, Empty, Input, Radio, Space, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useLocation, useNavigate } from 'react-router-dom';
import PageContainer from '@/components/Common/PageContainer';
import { searchService } from '@/services/searchService';
import type { GlobalSearchResultItem } from '@/types/search';
import { buildQueryScopeKey } from '@/utils/queryScope';
import styles from './GlobalSearchPage.module.css';

const { Text } = Typography;

type SearchViewMode = 'all' | 'grouped';

const GlobalSearchPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [viewMode, setViewMode] = useState<SearchViewMode>('all');

  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const query = searchParams.get('q')?.trim() ?? '';
  const queryScopeKey = buildQueryScopeKey();

  const globalSearchQuery = useQuery({
    queryKey: ['global-search', queryScopeKey, query],
    queryFn: async () => {
      return await searchService.searchGlobal(query);
    },
    enabled: query !== '',
    staleTime: 60 * 1000,
  });

  const handleSearch = (nextQuery: string) => {
    const normalizedQuery = nextQuery.trim();
    if (normalizedQuery === '') {
      navigate(location.pathname);
      return;
    }
    navigate(`${location.pathname}?q=${encodeURIComponent(normalizedQuery)}`);
  };

  const renderResultItem = (item: GlobalSearchResultItem) => (
    <Card key={`${item.object_type}-${item.object_id}`} size="small" className={styles.resultCard}>
      <Space orientation="vertical" size="small" style={{ width: '100%' }}>
        <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
          <Space align="center">
            <Tag color="blue">{item.group_label}</Tag>
            <Text strong>{item.title}</Text>
            {item.subtitle != null && item.subtitle !== '' ? (
              <Text type="secondary">{item.subtitle}</Text>
            ) : null}
          </Space>
          <Button
            type="link"
            aria-label={`查看${item.group_label}${item.title}详情`}
            onClick={() => {
              navigate(item.route_path);
            }}
          >
            查看详情
          </Button>
        </Space>
        {item.summary != null && item.summary !== '' ? <Text type="secondary">{item.summary}</Text> : null}
        {item.keywords.length > 0 ? (
          <div className={styles.keywords}>
            {item.keywords.map(keyword => (
              <Tag key={keyword}>{keyword}</Tag>
            ))}
          </div>
        ) : null}
      </Space>
    </Card>
  );

  const renderGroupedResults = () => {
    const groups = globalSearchQuery.data?.groups ?? [];
    const items = globalSearchQuery.data?.items ?? [];

    return groups.map(group => (
      <Card key={group.object_type} title={`${group.label} (${group.count})`} className={styles.groupCard}>
        <Space orientation="vertical" size="small" style={{ width: '100%' }}>
          {items
            .filter(item => item.object_type === group.object_type)
            .map(item => renderResultItem(item))}
        </Space>
      </Card>
    ));
  };

  return (
    <PageContainer title="全局搜索" subTitle="按当前数据范围跨对象搜索资产、项目、合同、客户和产权证。">
      <div className={styles.page}>
        <Card>
          <div className={styles.toolbar}>
            <Input.Search
              allowClear
              defaultValue={query}
              placeholder="搜索资产、项目、合同组、合同、客户、产权证"
              enterButton="搜索"
              onSearch={handleSearch}
              style={{ maxWidth: 480 }}
            />
            <Radio.Group
              value={viewMode}
              onChange={event => {
                setViewMode(event.target.value as SearchViewMode);
              }}
            >
              <Radio.Button value="all">全部视图</Radio.Button>
              <Radio.Button value="grouped">按对象分组</Radio.Button>
            </Radio.Group>
          </div>
        </Card>

        {globalSearchQuery.isError ? (
          <Alert
            type="error"
            showIcon
            title={globalSearchQuery.error instanceof Error ? globalSearchQuery.error.message : '搜索失败'}
          />
        ) : null}

        {!globalSearchQuery.isLoading && query === '' ? (
          <Card>
            <Empty description="输入关键词后开始搜索" />
          </Card>
        ) : null}

        {!globalSearchQuery.isLoading &&
        query !== '' &&
        (globalSearchQuery.data?.items.length ?? 0) === 0 ? (
          <Card>
            <Empty description="未找到匹配结果" />
          </Card>
        ) : null}

        {(globalSearchQuery.data?.items.length ?? 0) > 0 ? (
          <div className={styles.results}>
            {viewMode === 'all'
              ? (globalSearchQuery.data?.items ?? []).map(item => renderResultItem(item))
              : renderGroupedResults()}
          </div>
        ) : null}
      </div>
    </PageContainer>
  );
};

export default GlobalSearchPage;
