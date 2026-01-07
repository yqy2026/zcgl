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

  // 默认配置
  const errorConfigs = {
    '404': {
      status: '404' as const,
      icon: <FileSearchOutlined style={{ color: '#faad14' }} />,
      title: '页面不存在',
      subTitle: '抱歉，您访问的页面不存在或已被删除。',
    },
    '403': {
      status: '403' as const,
      icon: <LockOutlined style={{ color: '#ff4d4f' }} />,
      title: '访问被拒绝',
      subTitle: '抱歉，您没有权限访问此页面。',
    },
    '500': {
      status: '500' as const,
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      title: '服务器错误',
      subTitle: '抱歉，服务器出现了一些问题，请稍后重试。',
    },
    network: {
      status: 'error' as const,
      icon: <DisconnectOutlined style={{ color: '#ff4d4f' }} />,
      title: '网络连接失败',
      subTitle: '请检查您的网络连接，然后重试。',
    },
    timeout: {
      status: 'error' as const,
      icon: <ClockCircleOutlined style={{ color: '#faad14' }} />,
      title: '请求超时',
      subTitle: '服务器响应时间过长，请稍后重试。',
    },
    maintenance: {
      status: 'info' as const,
      icon: <ExclamationCircleOutlined style={{ color: '#1890ff' }} />,
      title: '系统维护中',
      subTitle: '系统正在进行维护升级，预计很快恢复正常。',
    },
  };

  const config = errorConfigs[type];

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  const handleHome = () => {
    if (onHome) {
      onHome();
    } else {
      navigate('/');
    }
  };

  const handleReload = () => {
    if (onReload) {
      onReload();
    } else {
      window.location.reload();
    }
  };

  // 根据错误类型生成建议操作
  const getSuggestions = () => {
    switch (type) {
      case '404':
        return (
          <div style={{ marginTop: 16 }}>
            <Paragraph>
              <Text type="secondary">可能的原因：</Text>
            </Paragraph>
            <ul style={{ color: '#8c8c8c', fontSize: '14px' }}>
              <li>网址输入错误</li>
              <li>页面已被删除或移动</li>
              <li>链接已过期</li>
            </ul>
          </div>
        );

      case '403':
        return (
          <div style={{ marginTop: 16 }}>
            <Paragraph>
              <Text type="secondary">您可以尝试：</Text>
            </Paragraph>
            <ul style={{ color: '#8c8c8c', fontSize: '14px' }}>
              <li>联系管理员获取访问权限</li>
              <li>使用其他账户登录</li>
              <li>检查您的账户状态</li>
            </ul>
          </div>
        );

      case '500':
        return (
          <div style={{ marginTop: 16 }}>
            <Paragraph>
              <Text type="secondary">您可以尝试：</Text>
            </Paragraph>
            <ul style={{ color: '#8c8c8c', fontSize: '14px' }}>
              <li>刷新页面重试</li>
              <li>稍后再试</li>
              <li>联系技术支持</li>
            </ul>
          </div>
        );

      case 'network':
        return (
          <div style={{ marginTop: 16 }}>
            <Paragraph>
              <Text type="secondary">请检查：</Text>
            </Paragraph>
            <ul style={{ color: '#8c8c8c', fontSize: '14px' }}>
              <li>网络连接是否正常</li>
              <li>防火墙设置</li>
              <li>代理服务器配置</li>
            </ul>
          </div>
        );

      case 'timeout':
        return (
          <div style={{ marginTop: 16 }}>
            <Paragraph>
              <Text type="secondary">建议操作：</Text>
            </Paragraph>
            <ul style={{ color: '#8c8c8c', fontSize: '14px' }}>
              <li>检查网络连接速度</li>
              <li>稍后重试</li>
              <li>联系网络管理员</li>
            </ul>
          </div>
        );

      case 'maintenance':
        return (
          <div style={{ marginTop: 16 }}>
            <Paragraph>
              <Text type="secondary">维护期间：</Text>
            </Paragraph>
            <ul style={{ color: '#8c8c8c', fontSize: '14px' }}>
              <li>系统功能暂时不可用</li>
              <li>数据安全不受影响</li>
              <li>请耐心等待维护完成</li>
            </ul>
          </div>
        );

      default:
        return null;
    }
  };

  // 生成操作按钮
  const getActionButtons = () => {
    const buttons = [];

    if (showBackButton) {
      buttons.push(
        <Button key="back" icon={<ArrowLeftOutlined />} onClick={handleBack}>
          返回上页
        </Button>
      );
    }

    if (showHomeButton) {
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
    <div
      style={{
        padding: '50px 20px',
        minHeight: '60vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ maxWidth: 500, width: '100%', textAlign: 'center' }}>
        <Result
          status={config.status}
          icon={config.icon}
          title={title ?? config.title}
          subTitle={
            <div>
              <div>{subTitle ?? config.subTitle}</div>
              {getSuggestions()}
            </div>
          }
          extra={extra ?? <Space wrap>{getActionButtons()}</Space>}
        />
      </div>
    </div>
  );
};

export default ErrorPage;
