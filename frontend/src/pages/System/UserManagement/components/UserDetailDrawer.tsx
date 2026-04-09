import React from 'react';
import { Avatar, Button, Descriptions, Drawer, Space, Tag } from 'antd';
import { EditOutlined, LockOutlined, UnlockOutlined, UserOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { User } from '@/services/systemService';
import type { UserStatus } from '../types';
import styles from '../../UserManagementPage.module.css';

interface UserDetailDrawerProps {
  open: boolean;
  user: User | null;
  roleOptions: Array<{ id: string; name: string }>;
  onClose: () => void;
  onEdit: (user: User) => void;
  onToggleLock: (user: User) => void;
  getStatusTag: (status: UserStatus | string | null | undefined) => React.ReactNode;
}

const UserDetailDrawer: React.FC<UserDetailDrawerProps> = ({
  open,
  user,
  roleOptions,
  onClose,
  onEdit,
  onToggleLock,
  getStatusTag,
}) => {
  const roleNameById = new Map(roleOptions.map(role => [role.id, role.name]));
  return (
    <Drawer title="用户详情" placement="right" onClose={onClose} open={open} size={600}>
      {user != null && (
        <div>
          <div className={styles.userProfileHeader}>
            <Avatar size={80} icon={<UserOutlined />} />
            <h3 className={styles.userProfileName}>{user.full_name}</h3>
            <p className={styles.userProfileAccount}>@{user.username}</p>
          </div>

          <Descriptions column={1} bordered>
            <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
            <Descriptions.Item label="手机号">{user.phone ?? '未设置'}</Descriptions.Item>
            <Descriptions.Item label="角色">
              <Space size={[6, 6]} wrap>
                {(user.role_ids?.length ?? 0) > 0
                  ? user.role_ids?.map(roleId => (
                      <Tag
                        key={roleId}
                        className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}
                      >
                        {roleNameById.get(roleId) ?? roleId}
                      </Tag>
                    ))
                  : (user.roles ?? []).length > 0
                    ? user.roles?.map(roleCode => (
                        <Tag
                          key={roleCode}
                          className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}
                        >
                          {roleCode}
                        </Tag>
                      ))
                    : [
                        <Tag
                          key="unassigned"
                          className={`${styles.semanticTag} ${styles.roleTag} ${styles.tonePrimary}`}
                        >
                          未分配
                        </Tag>,
                      ]}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="所属组织">{user.organization_name}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Space size={[8, 6]} wrap>
                {getStatusTag(user.status)}
                {user.is_locked && (
                  <Tag
                    className={`${styles.semanticTag} ${styles.lockStateTag} ${styles.toneError}`}
                  >
                    已锁定
                  </Tag>
                )}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="最后登录">
              {(user.last_login !== null && user.last_login !== undefined) || false
                ? dayjs(user.last_login).format('YYYY-MM-DD HH:mm:ss')
                : '从未登录'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {dayjs(user.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {dayjs(user.updated_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>

          <div className={styles.drawerActions}>
            <Space className={styles.drawerActionsGroup} wrap>
              <Button
                type="primary"
                icon={<EditOutlined />}
                className={styles.actionButton}
                onClick={() => onEdit(user)}
              >
                编辑用户
              </Button>
              <Button
                icon={user.is_locked ? <UnlockOutlined /> : <LockOutlined />}
                className={styles.actionButton}
                onClick={() => onToggleLock(user)}
              >
                {user.is_locked ? '解锁账户' : '锁定账户'}
              </Button>
            </Space>
          </div>
        </div>
      )}
    </Drawer>
  );
};

export default UserDetailDrawer;
