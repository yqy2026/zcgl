import React from 'react';
import { Result, Button, Typography, Space } from 'antd';
import {
  ExclamationCircleOutlined,
  FileSearchOutlined,
  DisconnectOutlined,
  LockOutlined,
  ClockCircleOutlined,
  HomeOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import styles from './ErrorPage.module.css';

const { Paragraph, Text } = Typography;

export type ErrorType = '404' | '403' | '500' | 'network' | 'timeout' | 'maintenance';

interface ErrorPageProps {
  type?: ErrorType;
  title?: string;
  subTitle?: string;
  extra?: React.ReactNode;
  showBackButton?: boolean;
  showHomeButton?: boolean;
  showReloadButton?: boolean;
  onBack?: () => void;
  onHome?: () => void;
  onReload?: () => void;
}

type ErrorTone = 'warning' | 'error' | 'info';

const ErrorPage: React.FC<ErrorPageProps> = ({
  type = '404',
  title,
  subTitle,
  extra,
  showBackButton = true,
  showHomeButton = true,
  showReloadButton = false,
  onBack,
  onHome,
  onReload,
}) => {
  const navigate = useNavigate();
  const iconClassMap: Record<ErrorTone, string> = {
    warning: `${styles.errorIcon} ${styles.errorIconWarning}`,
    error: `${styles.errorIcon} ${styles.errorIconError}`,
    info: `${styles.errorIcon} ${styles.errorIconInfo}`,
  };
  const suggestionConfigMap: Record<ErrorType, { title: string; items: string[] }> = {
    '404': {
      title: '可能的原因：',
      items: ['网址输入错误', '页面已被删除或移动', '链接已过期'],
    },
    '403': {
      title: '您可以尝试：',
      items: ['联系管理员获取访问权限', '使用其他账户登录', '检查您的账户状态'],
    },
    '500': {
      title: '您可以尝试：',
      items: ['刷新页面重试', '稍后再试', '联系技术支持'],
    },
    network: {
      title: '请检查：',
      items: ['网络连接是否正常', '防火墙设置', '代理服务器配置'],
    },
    timeout: {
      title: '建议操作：',
      items: ['检查网络连接速度', '稍后重试', '联系网络管理员'],
    },
    maintenance: {
      title: '维护期间：',
      items: ['系统功能暂时不可用', '数据安全不受影响', '请耐心等待维护完成'],
    },
  };

  // 默认配置
  const errorConfigs = {
    '404': {
      status: '404' as const,
      icon: <FileSearchOutlined className={iconClassMap.warning} aria-hidden />,
      title: '页面不存在',
      subTitle: '抱歉，您访问的页面不存在或已被删除。',
    },
    '403': {
      status: '403' as const,
      icon: <LockOutlined className={iconClassMap.error} aria-hidden />,
      title: '访问被拒绝',
      subTitle: '抱歉，您没有权限访问此页面。',
    },
    '500': {
      status: '500' as const,
      icon: <ExclamationCircleOutlined className={iconClassMap.error} aria-hidden />,
      title: '服务器错误',
      subTitle: '抱歉，服务器出现了一些问题，请稍后重试。',
    },
    network: {
      status: 'error' as const,
      icon: <DisconnectOutlined className={iconClassMap.error} aria-hidden />,
      title: '网络连接失败',
      subTitle: '请检查您的网络连接，然后重试。',
    },
    timeout: {
      status: 'error' as const,
      icon: <ClockCircleOutlined className={iconClassMap.warning} aria-hidden />,
      title: '请求超时',
      subTitle: '服务器响应时间过长，请稍后重试。',
    },
    maintenance: {
      status: 'info' as const,
      icon: <ExclamationCircleOutlined className={iconClassMap.info} aria-hidden />,
      title: '系统维护中',
      subTitle: '系统正在进行维护升级，预计很快恢复正常。',
    },
  };

  const config = errorConfigs[type];

  const handleBack = () => {
    if (onBack !== undefined && onBack !== null) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  const handleHome = () => {
    if (onHome !== undefined && onHome !== null) {
      onHome();
    } else {
      navigate('/');
    }
  };

  const handleReload = () => {
    if (onReload !== undefined && onReload !== null) {
      onReload();
    } else {
      window.location.reload();
    }
  };

  // 根据错误类型生成建议操作
  const getSuggestions = () => {
    const suggestionConfig = suggestionConfigMap[type];
    if (suggestionConfig == null) {
      return null;
    }

    return (
      <div className={styles.suggestions} role="alert" aria-live="polite">
        <Paragraph className={styles.suggestionTitle}>
          <Text type="secondary">{suggestionConfig.title}</Text>
        </Paragraph>
        <ul className={styles.suggestionList}>
          {suggestionConfig.items.map(item => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    );
  };

  // 生成操作按钮
  const getActionButtons = () => {
    const buttons = [];

    if (showBackButton === true) {
      buttons.push(
        <Button key="back" icon={<ArrowLeftOutlined />} onClick={handleBack}>
          返回上页
        </Button>
      );
    }

    if (showHomeButton === true) {
      buttons.push(
        <Button key="home" icon={<HomeOutlined />} onClick={handleHome}>
          返回首页
        </Button>
      );
    }

    if (showReloadButton || type === '500' || type === 'network' || type === 'timeout') {
      buttons.push(
        <Button key="reload" type="primary" icon={<ReloadOutlined />} onClick={handleReload}>
          重新加载
        </Button>
      );
    }

    return buttons;
  };

  return (
    <div className={styles.errorPage}>
      <div className={styles.errorCard}>
        <Result
          status={config.status}
          icon={config.icon}
          title={title ?? config.title}
          subTitle={
            <div className={styles.subTitleBlock}>
              <div>{subTitle ?? config.subTitle}</div>
              {getSuggestions()}
            </div>
          }
          extra={
            extra ?? (
              <Space wrap className={styles.actionButtons}>
                {getActionButtons()}
              </Space>
            )
          }
        />
      </div>
    </div>
  );
};

export default ErrorPage;
