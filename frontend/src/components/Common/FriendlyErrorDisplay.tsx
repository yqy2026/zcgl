import React from 'react';
import { Alert, Result, Button, Space, Typography } from 'antd';
import {
  ExclamationCircleOutlined,
  ReloadOutlined,
  HomeOutlined,
  ApiOutlined,
  DatabaseOutlined,
  WifiOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import styles from './FriendlyErrorDisplay.module.css';

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
        icon: <WifiOutlined className={styles.networkIcon} />,
      },
      data: {
        title: '数据加载失败',
        subtitle: '获取数据时出现问题，数据可能正在处理中',
        icon: <DatabaseOutlined className={styles.dataIcon} />,
      },
      server: {
        title: '服务器错误',
        subtitle: '服务器暂时无法处理请求，请稍后重试',
        icon: <ApiOutlined className={styles.serverIcon} />,
      },
      permission: {
        title: '权限不足',
        subtitle: '您没有访问此功能的权限，请联系管理员',
        icon: <ExclamationCircleOutlined className={styles.permissionIcon} />,
      },
      'not-found': {
        title: '未找到数据',
        subtitle: '请求的资源不存在或已被删除',
        icon: <ExclamationCircleOutlined className={styles.notFoundIcon} />,
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
    <div className={styles.container}>
      <Result
        icon={config.icon}
        title={config.title}
        subTitle={config.subtitle}
        extra={
          <Space orientation="vertical" size="middle">
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
                title="详细错误信息"
                description={
                  <div className={styles.detailsContainer}>
                    <Space orientation="vertical" size="small" className={styles.detailsSpace}>
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
                          <pre className={styles.errorDetailsPre}>
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

            <div className={styles.suggestionsPanel}>
              <Title level={5} className={styles.suggestionsTitle}>
                <BulbOutlined className={styles.suggestionsTitleIcon} />
                建议解决方案
              </Title>
              <ul className={styles.suggestionsList}>
                {getErrorSuggestions().map(suggestion => (
                  <li key={suggestion} className={styles.suggestionItem}>
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
