import React from 'react';
import { Button, DatePicker, Input, Select, Typography } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { ListToolbar } from '@/components/Common';
import { ACTION_OPTIONS, MODULE_OPTIONS, STATUS_OPTIONS } from '../constants';
import type { LogFilters } from '../types';
import styles from '../../OperationLogPage.module.css';

const { RangePicker } = DatePicker;
const { Search } = Input;
const { Option } = Select;
const { Text } = Typography;

interface OperationLogFiltersToolbarProps {
  filters: LogFilters;
  total: number;
  activeFilterCount: number;
  loading: boolean;
  onSearch: (value: string) => void;
  onModuleChange: (value?: string) => void;
  onActionChange: (value?: string) => void;
  onStatusChange: (value?: string) => void;
  onDateRangeChange: (dates: [Dayjs, Dayjs] | null) => void;
  onRefresh: () => void;
}

const OperationLogFiltersToolbar: React.FC<OperationLogFiltersToolbarProps> = ({
  filters,
  total,
  activeFilterCount,
  loading,
  onSearch,
  onModuleChange,
  onActionChange,
  onStatusChange,
  onDateRangeChange,
  onRefresh,
}) => {
  return (
    <div className={styles.filtersSection}>
      <div className={styles.filterSummary} aria-live="polite">
        <Text type="secondary">共 {total} 条记录</Text>
        <Text type="secondary">
          {activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项筛选` : '未启用筛选条件'}
        </Text>
      </div>
      <ListToolbar
        variant="plain"
        gutter={[16, 16]}
        items={[
          {
            key: 'search',
            col: { xs: 24, sm: 12, md: 6 },
            content: (
              <Search
                placeholder="搜索用户名、资源或操作"
                allowClear
                className={styles.fullWidthControl}
                onSearch={onSearch}
                value={filters.searchText}
                onChange={event => onSearch(event.target.value)}
                prefix={<SearchOutlined />}
              />
            ),
          },
          {
            key: 'module',
            col: { xs: 24, sm: 12, md: 4 },
            content: (
              <Select
                placeholder="模块筛选"
                allowClear
                className={styles.fullWidthControl}
                value={filters.module === '' ? undefined : filters.module}
                onChange={onModuleChange}
              >
                {MODULE_OPTIONS.map(module => (
                  <Option key={module.value} value={module.value}>
                    {module.label}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'action',
            col: { xs: 24, sm: 12, md: 4 },
            content: (
              <Select
                placeholder="操作筛选"
                allowClear
                className={styles.fullWidthControl}
                value={filters.action === '' ? undefined : filters.action}
                onChange={onActionChange}
              >
                {ACTION_OPTIONS.map(action => (
                  <Option key={action.value} value={action.value}>
                    {action.label}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'status',
            col: { xs: 24, sm: 12, md: 4 },
            content: (
              <Select
                placeholder="状态筛选"
                allowClear
                className={styles.fullWidthControl}
                value={filters.status === '' ? undefined : filters.status}
                onChange={onStatusChange}
              >
                {STATUS_OPTIONS.map(status => (
                  <Option key={status.value} value={status.value}>
                    {status.label}
                  </Option>
                ))}
              </Select>
            ),
          },
          {
            key: 'range',
            col: { xs: 24, sm: 12, md: 6 },
            content: (
              <RangePicker
                className={styles.fullWidthControl}
                value={filters.dateRange}
                onChange={dates => {
                  if (dates != null && dates[0] != null && dates[1] != null) {
                    onDateRangeChange([dates[0], dates[1]]);
                    return;
                  }
                  onDateRangeChange(null);
                }}
                placeholder={['开始日期', '结束日期']}
              />
            ),
          },
          {
            key: 'refresh',
            col: { xs: 24, sm: 12, md: 4 },
            content: (
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
                disabled={loading}
                className={styles.toolbarButton}
                aria-label="刷新操作日志列表"
              >
                刷新
              </Button>
            ),
          },
        ]}
      />
    </div>
  );
};

export default OperationLogFiltersToolbar;
