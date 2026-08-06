import React from 'react';
import { Alert, Button, Result, Space, Typography } from 'antd';
import { ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import type { UserPartyScopeView } from '@/services/systemService';

const { Text } = Typography;

interface PartyScopeBlockedProps {
  scope: UserPartyScopeView | null;
  onRetry?: () => void;
}

const isScopeBlocked = (scope: UserPartyScopeView | null): boolean =>
  scope != null &&
  (scope.error_code != null ||
    scope.scope_mode === 'none' ||
    scope.source === 'none');

const PartyScopeBlocked: React.FC<PartyScopeBlockedProps> = ({ scope, onRetry }) => {
  if (!isScopeBlocked(scope)) {
    return null;
  }

  const issues = scope?.issues ?? [];
  return (
    <div role="alert" style={{ padding: 24 }}>
      <Result
        icon={<SafetyCertificateOutlined />}
        title="主体范围未配置"
        subTitle={
          scope?.error_code != null
            ? `原因码：${scope.error_code}`
            : '当前账号未获得业务主体范围'
        }
        extra={
          <Space orientation="vertical" align="center">
            {issues.length > 0 && (
              <Alert
                type="warning"
                showIcon
                title="配置异常"
                description={
                  <Space orientation="vertical" size={4}>
                    {issues.map((issue, index) => (
                      <Text key={`${issue.code}-${index}`}>
                        {issue.safe_label}
                        {issue.code !== scope?.error_code
                          ? `（${issue.code}）`
                          : ''}
                      </Text>
                    ))}
                  </Space>
                }
              />
            )}
            {onRetry != null && (
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={onRetry}
              >
                重新检查
              </Button>
            )}
          </Space>
        }
      />
    </div>
  );
};

export default PartyScopeBlocked;
