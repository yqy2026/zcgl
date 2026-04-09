import React, { useMemo, type ReactNode } from 'react';
import { Badge, Button, Col, Popconfirm, Row, Space, Tag } from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  HistoryOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Input } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { TableWithPagination, type PaginationState } from '@/components/Common/TableWithPagination';
import type { Organization } from '@/types/organization';
import type { OrganizationFilters } from '../types';
import styles from '../../OrganizationPage.module.css';

const { Search } = Input;

export interface OrganizationListTabProps {
  filters: OrganizationFilters;
  total: number;
  activeFilterCount: number;
  loading: boolean;
  isReadOnlyMode: boolean;
  organizations: Organization[];
  paginationState: PaginationState;
  getTypeIcon: (type: string) => ReactNode;
  getTypeLabel: (type: string) => string;
  getStatusTag: (status: string, className?: string) => ReactNode;
  onSearch: (keyword: string) => void;
  onRefresh: () => void;
  onCreate: () => void;
  onPageChange: (next: { current?: number; pageSize?: number }) => void;
  onEdit: (organization: Organization) => void;
  onDelete: (id: string) => Promise<void>;
  onManageBindings: (organization: Organization) => void;
  onViewHistory: (organization: Organization) => void;
}

const OrganizationListTab: React.FC<OrganizationListTabProps> = ({
  filters,
  total,
  activeFilterCount,
  loading,
  isReadOnlyMode,
  organizations,
  paginationState,
  getTypeIcon,
  getTypeLabel,
  getStatusTag,
  onSearch,
  onRefresh,
  onCreate,
  onPageChange,
  onEdit,
  onDelete,
  onManageBindings,
  onViewHistory,
}) => {
  const columns = useMemo<ColumnsType<Organization>>(
    () => [
      {
        title: '组织名称',
        dataIndex: 'name',
        key: 'name',
        render: (text, record) => (
          <Space className={styles.nameCell}>
            {getTypeIcon(record.type)}
            <span className={styles.primaryText}>{text}</span>
            <Tag className={`${styles.codeTag} ${styles.tonePrimary}`}>{record.code}</Tag>
          </Space>
        ),
      },
      {
        title: '类型',
        dataIndex: 'type',
        key: 'type',
        render: type => getTypeLabel(type),
      },
      {
        title: '层级',
        dataIndex: 'level',
        key: 'level',
        render: level => <Badge count={level} color="blue" />,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: status => getStatusTag(status),
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        render: date => new Date(date).toLocaleString(),
      },
      {
        title: '操作',
        key: 'action',
        render: (_, record) => (
          <Space size={4} className={styles.tableActionGroup}>
            {!isReadOnlyMode && (
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => onEdit(record)}
                className={styles.tableActionButton}
                aria-label={`编辑组织 ${record.name}`}
              >
                编辑
              </Button>
            )}
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => onViewHistory(record)}
              className={styles.tableActionButton}
              aria-label={`查看组织 ${record.name} 历史`}
            >
              历史
            </Button>
            {!isReadOnlyMode && (
              <Button
                type="text"
                onClick={() => onManageBindings(record)}
                className={styles.tableActionButton}
                aria-label={`管理组织 ${record.name} 主体绑定`}
              >
                主体绑定
              </Button>
            )}
            {!isReadOnlyMode && (
              <Popconfirm
                title="确定要删除这个组织吗？"
                onConfirm={() => onDelete(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  className={styles.tableActionButton}
                  aria-label={`删除组织 ${record.name}`}
                >
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        ),
      },
    ],
    [
      getStatusTag,
      getTypeIcon,
      getTypeLabel,
      isReadOnlyMode,
      onDelete,
      onEdit,
      onManageBindings,
      onViewHistory,
    ]
  );

  return (
    <>
      <div className={styles.toolbarSection}>
        <div className={styles.filterSummary} aria-live="polite">
          <span className={styles.secondaryText}>共 {total} 条组织记录</span>
          <span className={styles.secondaryText}>
            {activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项筛选` : '未启用筛选条件'}
          </span>
        </div>
        <Row justify="space-between" gutter={[12, 12]}>
          <Col>
            <Space className={styles.toolbarActions} wrap>
              <Search
                placeholder="搜索组织名称、编码或描述"
                allowClear
                className={styles.searchInput}
                onSearch={onSearch}
                value={filters.keyword}
                onChange={event => onSearch(event.target.value)}
              />
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
                disabled={loading}
                className={styles.actionButton}
                aria-label="刷新组织列表"
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={onCreate}
              disabled={isReadOnlyMode}
              title={isReadOnlyMode ? '组织架构已切换为只读模式' : undefined}
              className={styles.actionButton}
              aria-label="新建组织"
            >
              新建组织
            </Button>
          </Col>
        </Row>
      </div>

      <TableWithPagination
        columns={columns}
        dataSource={organizations}
        rowKey="id"
        loading={loading}
        paginationState={paginationState}
        onPageChange={onPageChange}
        paginationProps={{
          showTotal: (value: number) => `共 ${value} 条记录`,
        }}
      />
    </>
  );
};

export default OrganizationListTab;
