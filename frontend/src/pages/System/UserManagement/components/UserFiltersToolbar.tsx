import React from 'react';
import { Button, Input, Select } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { ListToolbar } from '@/components/Common';
import type { OrganizationOption, RoleOption } from '@/services/systemService';
import type { UserFilters, UserStatus } from '../types';
import styles from '../../UserManagementPage.module.css';

const { Option } = Select;
const { Search } = Input;

interface UserFiltersToolbarProps {
  filters: UserFilters;
  roles: RoleOption[];
  organizations: OrganizationOption[];
  statusOptions: Array<{ value: UserStatus; label: string }>;
  isRefreshing: boolean;
  total: number;
  enabledFilterCount: number;
  onSearch: (value: string) => void;
  onStatusFilterChange: (value?: string) => void;
  onRoleFilterChange: (value?: string) => void;
  onOrganizationFilterChange: (value?: string) => void;
  onRefresh: () => void;
  onCreate: () => void;
}

const UserFiltersToolbar: React.FC<UserFiltersToolbarProps> = ({
  filters,
  roles,
  organizations,
  statusOptions,
  isRefreshing,
  total,
  enabledFilterCount,
  onSearch,
  onStatusFilterChange,
  onRoleFilterChange,
  onOrganizationFilterChange,
  onRefresh,
  onCreate,
}) => {
  return (
    <>
      <div className={styles.toolbarSection}>
        <ListToolbar
          variant="plain"
          items={[
            {
              key: 'search',
              col: { xs: 24, sm: 12, md: 10, lg: 8 },
              content: (
                <Search
                  placeholder="搜索用户名、邮箱或姓名"
                  allowClear
                  className={styles.fullWidthControl}
                  onSearch={onSearch}
                  aria-label="搜索用户"
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
                  aria-label="按状态筛选用户"
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
              key: 'role',
              col: { xs: 24, sm: 12, md: 6, lg: 4 },
              content: (
                <Select
                  placeholder="角色筛选"
                  allowClear
                  className={styles.fullWidthControl}
                  value={filters.roleId !== '' ? filters.roleId : undefined}
                  onChange={onRoleFilterChange}
                  aria-label="按角色筛选用户"
                >
                  {roles.map(role => (
                    <Option key={role.id} value={role.id}>
                      {role.name}
                    </Option>
                  ))}
                </Select>
              ),
            },
            {
              key: 'organization',
              col: { xs: 24, sm: 12, md: 6, lg: 4 },
              content: (
                <Select
                  placeholder="组织筛选"
                  allowClear
                  className={styles.fullWidthControl}
                  value={filters.organizationId !== '' ? filters.organizationId : undefined}
                  onChange={onOrganizationFilterChange}
                  aria-label="按组织筛选用户"
                >
                  {organizations.map(org => (
                    <Option key={org.id} value={org.id}>
                      {org.name}
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
                  className={styles.actionButton}
                  loading={isRefreshing}
                  aria-label="刷新用户列表"
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
                  className={styles.actionButton}
                  aria-label="新建系统用户"
                >
                  新建用户
                </Button>
              ),
            },
          ]}
        />
      </div>
      <div className={styles.filterSummary}>
        <span className={styles.summaryText}>总记录：{total}</span>
        <span className={styles.summaryText}>启用筛选：{enabledFilterCount}</span>
      </div>
    </>
  );
};

export default UserFiltersToolbar;
