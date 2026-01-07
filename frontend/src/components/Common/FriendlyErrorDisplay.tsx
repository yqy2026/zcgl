import React from 'react';
import { Alert, Result, Button, Space, Typography } from 'antd';
import {
  ExclamationCircleOutlined,
  ReloadOutlined,
  HomeOutlined,
  ApiOutlined,
  DatabaseOutlined,
  WifiOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

interface FriendlyErrorDisplayProps {
  error?: {
    message?: string;
    status?: number;
    code?: string;
    details?: unknown;
  };
  type?: 'network' | 'data' | 'server' | 'permission' | 'not-found';
  onRetry?: () => void;
  onGoHome?: () => void;
  showDetails?: boolean;
}

const FriendlyErrorDisplay: React.FC<FriendlyErrorDisplayProps> = ({
  error,
  type = 'network',
  onRetry,
  onGoHome,
  showDetails = false,
}) => {
  const getErrorConfig = () => {
    const configs = {
      network: {
        title: '网络连接问题',
        subtitle: '无法连接到服务器，请检查网络连接后重试',
        icon: <WifiOutlined style={{ color: '#ff4d4f', fontSize: 48 }} />,
        color: '#ff4d4f',
      },
      data: {
        title: '数据加载失败',
        subtitle: '获取数据时出现问题，数据可能正在处理中',
        icon: <DatabaseOutlined style={{ color: '#fa8c16', fontSize: 48 }} />,
        color: '#fa8c16',
      },
      server: {
        title: '服务器错误',
        subtitle: '服务器暂时无法处理请求，请稍后重试',
        icon: <ApiOutlined style={{ color: '#722ed1', fontSize: 48 }} />,
        color: '#722ed1',
      },
      permission: {
        title: '权限不足',
        subtitle: '您没有访问此功能的权限，请联系管理员',
        icon: <ExclamationCircleOutlined style={{ color: '#cf1322', fontSize: 48 }} />,
        color: '#cf1322',
      },
      'not-found': {
        title: '未找到数据',
        subtitle: '请求的资源不存在或已被删除',
        icon: <ExclamationCircleOutlined style={{ color: '#d9d9d9', fontSize: 48 }} />,
        color: '#d9d9d9',
      },
    };

    return configs[type] ?? configs.network;
  };

  const config = getErrorConfig();

  const getErrorSuggestions = () => {
    const suggestions = {
      network: [
        '检查网络连接是否正常',
        '确认服务器是否正在运行',
        '尝试刷新页面重新加载',
        '检查防火墙设置',
      ],
      data: ['确认数据是否存在', '检查数据格式是否正确', '稍等片刻后重试', '联系技术支持'],
      server: [
        '服务器可能正在维护',
        '请稍后再次尝试',
        '如果问题持续存在，请联系技术支持',
        '查看系统状态页面',
      ],
      permission: [
        '联系系统管理员申请权限',
        '确认您的账户状态是否正常',
        '检查是否需要重新登录',
        '查看用户权限说明',
      ],
      'not-found': [
        '确认资源地址是否正确',
        '检查资源是否已被删除或移动',
        '返回上一页面重试',
        '从首页重新导航',
      ],
    };

    return suggestions[type] ?? suggestions.network;
  };

  if ((error === null || error === undefined) && !showDetails) {
    return null;
  }

  return (
    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
      <Result
        icon={config.icon}
        title={config.title}
        subTitle={config.subtitle}
        extra={
          <Space direction="vertical" size="middle">
            <Space wrap>
              {onRetry && (
                <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
                  重试
                </Button>
              )}
              {onGoHome && (
                <Button icon={<HomeOutlined />} onClick={onGoHome}>
                  返回首页
                </Button>
              )}
            </Space>

            {showDetails && (
              <Alert
                message="详细错误信息"
                description={
                  <div style={{ textAlign: 'left', marginTop: '16px' }}>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      {error?.status !== null && error?.status !== undefined && (
                        <div>
                          <Text strong>状态码:</Text> {error.status}
                        </div>
                      )}
                      {error?.code !== null && error?.code !== undefined && (
                        <div>
                          <Text strong>错误代码:</Text> {error.code}
                        </div>
                      )}
                      {error?.message !== null && error?.message !== undefined && (
                        <div>
                          <Text strong>错误信息:</Text> {error.message}
                        </div>
                      )}
                      {error?.details !== null && error?.details !== undefined && (
                        <div>
                          <Text strong>详细信息:</Text>
                          <pre
                            style={{
                              background: '#f5f5f5',
                              padding: '8px',
                              borderRadius: '4px',
                              fontSize: '12px',
                              overflow: 'auto',
                              maxHeight: '200px',
                            }}
                          >
                            {JSON.stringify(error.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </Space>
                  </div>
                }
                type="warning"
                showIcon
              />
            )}

            <div
              style={{
                background: '#fafafa',
                padding: '16px',
                borderRadius: '8px',
                textAlign: 'left',
                maxWidth: '600px',
                margin: '0 auto',
              }}
            >
              <Title level={5} style={{ margin: '0 0 12px 0', color: '#666' }}>
                💡 建议解决方案
              </Title>
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                {getErrorSuggestions().map((suggestion, index) => (
                  <li key={index} style={{ marginBottom: '4px', color: '#666' }}>
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          </Space>
        }
      />
    </div>
  );
};

export default FriendlyErrorDisplay;
