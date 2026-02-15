import React, { useMemo } from 'react';
import { Button, Popconfirm, Space, Switch, Tag, Tooltip } from 'antd';
import { DeleteOutlined, EditOutlined, KeyOutlined, TeamOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { TableWithPagination } from '@/components/Common';
import type { Role } from '@/services/systemService';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import styles from '../../RoleManagementPage.module.css';

interface RoleTableProps {
  roles: Role[];
  loading: boolean;
  paginationState: PaginationState;
  getStatusTag: (status: string) => React.ReactNode;
  onPageChange: (next: { current?: number; pageSize?: number }) => void;
  onEdit: (role: Role) => void;
  onManagePermissions: (role: Role) => void;
  onToggleStatus: (role: Role, newStatus: string) => void | Promise<void>;
  onDelete: (id: string) => void | Promise<void>;
}

const RoleTable: React.FC<RoleTableProps> = ({
  roles,
  loading,
  paginationState,
  getStatusTag,
  onPageChange,
  onEdit,
  onManagePermissions,
  onToggleStatus,
  onDelete,
}) => {
  const columns: ColumnsType<Role> = useMemo(
    () => [
      {
        title: '角色信息',
        key: 'role_info',
        render: (_, record) => (
          <Space size={10} className={styles.roleInfoCell}>
            <TeamOutlined className={styles.roleInfoIcon} />
            <div className={styles.roleMeta}>
              <div className={styles.roleName}>{record.name}</div>
              <div className={styles.roleCodeRow}>
                {record.code}
                {record.is_system && (
                  <Tag className={`${styles.statusTag} ${styles.systemTag} ${styles.toneWarning}`}>
                    系统角色
                  </Tag>
                )}
              </div>
            </div>
          </Space>
        ),
      },
      {
        title: '描述',
        dataIndex: 'description',
        key: 'description',
        ellipsis: true,
      },
      {
        title: '权限数量',
        dataIndex: 'permissions',
        key: 'permissions',
        render: (permissions: string[]) => (
          <span
            className={`${styles.countPill} ${styles.tonePrimary}`}
          >{`${permissions.length} 项`}</span>
        ),
      },
      {
        title: '用户数量',
        dataIndex: 'user_count',
        key: 'user_count',
        render: (count: number) => (
          <span className={`${styles.countPill} ${styles.toneSuccess}`}>{`${count} 人`}</span>
        ),
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => getStatusTag(status),
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
      },
      {
        title: '操作',
        key: 'action',
        render: (_, record) => (
          <Space size={4} className={styles.tableActionGroup}>
            <Tooltip title="编辑">
              <Button
                type="text"
                className={styles.tableActionButton}
                icon={<EditOutlined />}
                onClick={() => onEdit(record)}
                disabled={record.is_system}
                aria-label="编辑"
              />
            </Tooltip>
            <Tooltip title="权限配置">
              <Button
                type="text"
                className={styles.tableActionButton}
                icon={<KeyOutlined />}
                onClick={() => onManagePermissions(record)}
                aria-label="权限配置"
              />
            </Tooltip>
            <Tooltip title={record.status === 'active' ? '停用' : '启用'}>
              <Switch
                checked={record.status === 'active'}
                onChange={checked => {
                  void onToggleStatus(record, checked ? 'active' : 'inactive');
                }}
                disabled={record.is_system}
                checkedChildren="启"
                unCheckedChildren="停"
                className={styles.statusSwitch}
                aria-label={record.status === 'active' ? '停用' : '启用'}
              />
            </Tooltip>
            <Popconfirm
              title="确定要删除这个角色吗？"
              onConfirm={() => {
                void onDelete(record.id);
              }}
              okText="确定"
              cancelText="取消"
              disabled={record.is_system}
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  className={styles.tableActionButton}
                  icon={<DeleteOutlined />}
                  disabled={record.is_system}
                  aria-label="删除"
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [getStatusTag, onDelete, onEdit, onManagePermissions, onToggleStatus]
  );

  return (
    <TableWithPagination
      columns={columns}
      dataSource={roles}
      rowKey="id"
      loading={loading}
      paginationState={paginationState}
      onPageChange={onPageChange}
      scroll={{ x: 1100 }}
      paginationProps={{
        pageSizeOptions: ['10', '20', '50', '100'],
        showTotal: (total: number) => `共 ${total} 条记录`,
      }}
    />
  );
};

export default RoleTable;
