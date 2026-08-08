import React, { useEffect, useState } from 'react';
import { Alert, Descriptions, Modal, Spin, Tag, Typography } from 'antd';
import type { User, UserPartyScopeView } from '@/services/systemService';
import { userService } from '@/services/systemService';
import { MessageManager } from '@/utils/messageManager';

const { Text } = Typography;

interface UserPartyScopeViewModalProps {
  open: boolean;
  user: User | null;
  onClose: () => void;
}

const sourceLabel = (source: UserPartyScopeView['source']): string => {
  const labels: Record<UserPartyScopeView['source'], string> = {
    explicit: '显式绑定',
    organization: '组织默认',
    unrestricted: '不受限',
    none: '无有效范围',
  };
  return labels[source];
};

const modeLabel = (mode: UserPartyScopeView['scope_mode']): string => {
  const labels: Record<UserPartyScopeView['scope_mode'], string> = {
    owner: '产权方',
    manager: '运营方',
    all: '产权方 + 运营方',
    unrestricted: '不受限',
    none: '无',
  };
  return labels[mode];
};

const UserPartyScopeViewModal: React.FC<UserPartyScopeViewModalProps> = ({
  open,
  user,
  onClose,
}) => {
  const [scope, setScope] = useState<UserPartyScopeView | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || user == null) {
      setScope(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    void userService
      .getUserPartyScope(user.id)
      .then(result => {
        if (!cancelled) {
          setScope(result);
        }
      })
      .catch(error => {
        if (!cancelled) {
          MessageManager.error(error instanceof Error ? error.message : '获取用户有效主体范围失败');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, user]);

  return (
    <Modal
      title={user != null ? `有效主体范围 - ${user.full_name}` : '有效主体范围'}
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
    >
      <Spin spinning={loading}>
        {scope != null && (
          <>
            {scope.error_code != null && (
              <Alert
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
                title={`配置异常：${scope.error_code}`}
                description={scope.issues.map(issue => issue.safe_label).join('；')}
              />
            )}
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="范围来源">{sourceLabel(scope.source)}</Descriptions.Item>
              <Descriptions.Item label="范围模式">{modeLabel(scope.scope_mode)}</Descriptions.Item>
              <Descriptions.Item label="产权方主体">
                {scope.owner_party_ids.length > 0 ? scope.owner_party_ids.join('、') : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="运营方主体">
                {scope.manager_party_ids.length > 0 ? scope.manager_party_ids.join('、') : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="所属组织">
                {scope.organization_id ?? '无'}
              </Descriptions.Item>
              <Descriptions.Item label="来源组织">
                {scope.source_organization_id ?? '无'}
              </Descriptions.Item>
              <Descriptions.Item label="下一时间边界">
                {scope.next_transition_at ?? '无'}
              </Descriptions.Item>
            </Descriptions>
            {scope.issues.length > 0 && (
              <div style={{ marginTop: 16 }}>
                {scope.issues.map((issue, index) => (
                  <div key={`${issue.code}-${index}`}>
                    <Text type="warning">
                      {issue.safe_label}
                      {issue.node_ref != null ? `（${issue.node_ref}）` : ''}
                    </Text>
                  </div>
                ))}
              </div>
            )}
            {scope.error_code == null && (
              <div style={{ marginTop: 16 }}>
                <Tag color="green">范围有效</Tag>
              </div>
            )}
          </>
        )}
      </Spin>
    </Modal>
  );
};

export default UserPartyScopeViewModal;
