import React, { useMemo } from 'react';
import { Avatar, Button, Popconfirm, Space, Switch, Tag, Tooltip } from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  LockOutlined,
  TagsOutlined,
  UnlockOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { TableWithPagination } from '@/components/Common';
import type { User } from '@/services/systemService';
import type { PaginationState } from '@/components/Common/TableWithPagination';
import type { UserStatus } from '../types';
import styles from '../../UserManagementPage.module.css';

interface UserTableProps {
  users: User[];
  loading: boolean;
  paginationState: PaginationState;
  onPageChange: (next: { current?: number; pageSize?: number }) => void;
  onViewDetail: (user: User) => void;
  onManagePartyBindings: (user: User) => void;
  onEdit: (user: User) => void;
  onToggleLock: (user: User) => void | Promise<void>;
  onToggleStatus: (user: User, status: 'active' | 'inactive') => void | Promise<void>;
  onDelete: (id: string) => void | Promise<void>;
  getStatusTag: (status: UserStatus | string | null | undefined) => React.ReactNode;
}

const UserTable: React.FC<UserTableProps> = ({
  users,
  loading,
  paginationState,
  onPageChange,
  onViewDetail,
  onManagePartyBindings,
  onEdit,
  onToggleLock,
  onToggleStatus,
  onDelete,
  getStatusTag,
}) => {
  const columns: ColumnsType<User> = useMemo(
    () => [
      {
        title: '用户信息',
        key: 'user_info',
        render: (_, record) => (
          <Space className={styles.userCell}>
            <Avatar icon={<UserOutlined />} />
            <div className={styles.userTextGroup}>
              <div className={styles.userNameText}>{record.full_name}</div>
              <div className={styles.secondaryText}>@{record.username}</div>
            </div>
          </Space>
        ),
      },
      {
        title: '联系方式',
        key: 'contact',
        render: (_, record) => (
          <div className={styles.contactCell}>
            <div>{record.email}</div>
            <div className={styles.secondaryText}>{record.phone ?? '未设置'}</div>
          </div>
        ),
      },
      {
        title: '角色',
        dataIndex: 'role_name',
        key: 'role',
        render: (role?: string) => {
          const roleLabel = role ?? '未分配';
          return (
            <Tag className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}>
              {roleLabel}
            </Tag>
          );
        },
      },
      {
        title: '组织',
        dataIndex: 'organization_name',
        key: 'organization',
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (status: UserStatus, record: User) => (
          <Space size={[8, 6]} wrap>
            {getStatusTag(status)}
            {record.is_locked && (
              <Tag className={`${styles.semanticTag} ${styles.lockStateTag} ${styles.toneError}`}>
                已锁定
              </Tag>
            )}
          </Space>
        ),
      },
      {
        title: '最后登录',
        dataIndex: 'last_login',
        key: 'last_login',
        render: date =>
          date !== null && date !== undefined ? dayjs(date).format('YYYY-MM-DD HH:mm') : '从未登录',
      },
      {
        title: '操作',
        key: 'action',
        render: (_, record) => (
          <Space size={4} className={styles.actionGroup}>
            <Tooltip title="查看详情">
              <Button
                type="text"
                icon={<EyeOutlined />}
                className={styles.tableActionButton}
                onClick={() => onViewDetail(record)}
                aria-label={`查看用户${record.username}详情`}
              />
            </Tooltip>
            <Tooltip title="编辑">
              <Button
                type="text"
                icon={<EditOutlined />}
                className={styles.tableActionButton}
                onClick={() => onEdit(record)}
                aria-label={`编辑用户${record.username}`}
              />
            </Tooltip>
            <Tooltip title="主体标签绑定">
              <Button
                type="text"
                icon={<TagsOutlined />}
                className={styles.tableActionButton}
                onClick={() => onManagePartyBindings(record)}
                aria-label={`主体绑定用户${record.username}`}
              />
            </Tooltip>
            <Tooltip title={record.is_locked ? '解锁' : '锁定'}>
              <Button
                type="text"
                icon={record.is_locked ? <UnlockOutlined /> : <LockOutlined />}
                onClick={() => {
                  void onToggleLock(record);
                }}
                className={`${styles.tableActionButton} ${
                  record.is_locked ? styles.unlockActionButton : styles.lockActionButton
                }`}
                aria-label={
                  record.is_locked ? `解锁用户${record.username}` : `锁定用户${record.username}`
                }
              />
            </Tooltip>
            <Tooltip title={record.status === 'active' ? '停用' : '启用'}>
              <Switch
                size="small"
                checked={record.status === 'active'}
                onChange={checked => {
                  void onToggleStatus(record, checked ? 'active' : 'inactive');
                }}
                checkedChildren="启"
                unCheckedChildren="停"
                className={styles.statusSwitch}
                aria-label={
                  record.status === 'active'
                    ? `停用用户${record.username}`
                    : `启用用户${record.username}`
                }
              />
            </Tooltip>
            <Popconfirm
              title="确定要删除这个用户吗？"
              onConfirm={() => {
                void onDelete(record.id);
              }}
              okText="确定"
              cancelText="取消"
              icon={<ExclamationCircleOutlined className={styles.dangerIcon} />}
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  className={styles.tableActionButton}
                  aria-label={`删除用户${record.username}`}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [getStatusTag, onDelete, onEdit, onManagePartyBindings, onToggleLock, onToggleStatus, onViewDetail]
  );

  return (
    <TableWithPagination
      columns={columns}
      dataSource={users}
      rowKey="id"
      loading={loading}
      paginationState={paginationState}
      onPageChange={onPageChange}
      paginationProps={{
        showTotal: (total: number) => `共 ${total} 条记录`,
      }}
    />
  );
};

export default UserTable;
