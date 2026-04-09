import React, { useMemo, useState } from 'react';
import { Button, Drawer, Empty, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import type { Organization } from '@/types/organization';
import { type User, userService } from '@/services/systemService';
import UserPartyBindingModal from '@/pages/System/UserManagement/components/UserPartyBindingModal';

interface OrganizationBindingDrawerProps {
  open: boolean;
  organization: Organization | null;
  onClose: () => void;
}

const OrganizationBindingDrawer: React.FC<OrganizationBindingDrawerProps> = ({
  open,
  organization,
  onClose,
}) => {
  const [bindingUser, setBindingUser] = useState<User | null>(null);
  const [bindingModalVisible, setBindingModalVisible] = useState(false);

  const usersQuery = useQuery({
    queryKey: ['organization-binding-users', organization?.id],
    queryFn: async () => {
      if (organization == null) {
        return [];
      }
      const result = await userService.getUsers({
        default_organization_id: organization.id,
        page_size: 200,
      });
      return result.items ?? [];
    },
    enabled: open && organization != null,
  });

  const columns = useMemo<ColumnsType<User>>(
    () => [
      {
        title: '用户',
        key: 'user',
        render: (_, record) => (
          <div>
            <Typography.Text strong>{record.full_name}</Typography.Text>
            <div>{record.username}</div>
          </div>
        ),
      },
      {
        title: '角色',
        key: 'roles',
        render: (_, record) => {
          const roleLabels = record.roles ?? [];
          if (roleLabels.length === 0) {
            return <Tag>未分配</Tag>;
          }
          return (
            <Space size={[4, 4]} wrap>
              {roleLabels.map(roleLabel => (
                <Tag key={roleLabel}>{roleLabel}</Tag>
              ))}
            </Space>
          );
        },
      },
      {
        title: '操作',
        key: 'actions',
        render: (_, record) => (
          <Button
            type="link"
            onClick={() => {
              setBindingUser(record);
              setBindingModalVisible(true);
            }}
            aria-label={`管理 ${record.full_name} 主体绑定`}
          >
            管理主体绑定
          </Button>
        ),
      },
    ],
    []
  );

  const users = usersQuery.data ?? [];

  return (
    <>
      <Drawer
        title={organization != null ? `${organization.name} · 用户主体绑定` : '用户主体绑定'}
        placement="right"
        size="large"
        open={open}
        onClose={onClose}
      >
        {users.length === 0 && !usersQuery.isLoading ? (
          <Empty description="该组织下暂无用户" />
        ) : (
          <Table<User>
            rowKey="id"
            loading={usersQuery.isLoading}
            columns={columns}
            dataSource={users}
            pagination={false}
          />
        )}
      </Drawer>

      <UserPartyBindingModal
        open={bindingModalVisible}
        user={bindingUser}
        onClose={() => {
          setBindingModalVisible(false);
          setBindingUser(null);
        }}
        onChanged={async () => {
          await usersQuery.refetch();
        }}
      />
    </>
  );
};

export default OrganizationBindingDrawer;
