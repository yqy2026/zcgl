import React from 'react';
import { Button, Input, Select, Typography } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { ListToolbar } from '@/components/Common';
import type { RoleFilters } from '../types';
import styles from '../../RoleManagementPage.module.css';

const { Option } = Select;
const { Search } = Input;
const { Text } = Typography;

interface RoleFiltersToolbarProps {
  filters: RoleFilters;
  statusOptions: Array<{ value: 'active' | 'inactive'; label: string }>;
  total: number;
  activeFilterCount: number;
  loading: boolean;
  onSearch: (value: string) => void;
  onStatusFilterChange: (value?: string) => void;
  onRefresh: () => void;
  onCreate: () => void;
}

const RoleFiltersToolbar: React.FC<RoleFiltersToolbarProps> = ({
  filters,
  statusOptions,
  total,
  activeFilterCount,
  loading,
  onSearch,
  onStatusFilterChange,
  onRefresh,
  onCreate,
}) => {
  return (
    <div className={styles.filtersSection}>
      <div className={styles.filterSummary} aria-live="polite">
        <Text type="secondary">共 {total} 条角色记录</Text>
        <Text type="secondary">
          {activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项筛选` : '未启用筛选条件'}
        </Text>
      </div>
      <ListToolbar
        variant="plain"
        items={[
          {
            key: 'search',
            col: { xs: 24, sm: 12, md: 10, lg: 8 },
            content: (
              <Search
                placeholder="搜索角色名称或编码"
                allowClear
                className={styles.fullWidthControl}
                value={filters.keyword}
                onSearch={onSearch}
                onChange={event => onSearch(event.target.value)}
              />
            ),
          },
          {
            key: 'status',
            col: { xs: 24, sm: 12, md: 6, lg: 4 },
            content: (
              <Select
                placeholder="状态筛选"
                allowClear
                className={styles.fullWidthControl}
                value={filters.status !== '' ? filters.status : undefined}
                onChange={onStatusFilterChange}
              >
                {statusOptions.map(status => (
                  <Option key={status.value} value={status.value}>
                    {status.label}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'refresh',
            col: { xs: 24, sm: 12, md: 4, lg: 3 },
            content: (
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
                disabled={loading}
                className={styles.toolbarButton}
                aria-label="刷新角色列表"
              >
                刷新
              </Button>
            ),
          },
          {
            key: 'create',
            col: { xs: 24, sm: 12, md: 4, lg: 3 },
            content: (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={onCreate}
                className={styles.toolbarButton}
                aria-label="新建角色"
              >
                新建角色
              </Button>
            ),
          },
        ]}
      />
    </div>
  );
};

export default RoleFiltersToolbar;
