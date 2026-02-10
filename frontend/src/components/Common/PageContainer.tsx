import React from 'react';
import { Typography, Button, Space, Row, Col, Spin, theme } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import AppBreadcrumb from '@/components/Layout/AppBreadcrumb';

const { Title, Text } = Typography;
const { useToken } = theme;

export interface PageContainerProps {
  title?: React.ReactNode;
  subTitle?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  extra?: React.ReactNode;
  onBack?: (() => void) | boolean;
  loading?: boolean;
  className?: string;
  children: React.ReactNode;
  contentStyle?: React.CSSProperties;
}

const PageContainer: React.FC<PageContainerProps> = ({
  title,
  subTitle,
  breadcrumb,
  extra,
  onBack,
  loading = false,
  className,
  children,
  contentStyle,
}) => {
  const navigate = useNavigate();
  const { token } = useToken();

  const handleBack = () => {
    if (typeof onBack === 'function') {
      onBack();
    } else {
      navigate(-1);
    }
  };

  return (
    <div
      className={className}
      style={{
        padding: '24px',
        minHeight: '100%',
        backgroundColor: token.colorBgLayout,
        ...contentStyle,
      }}
    >
      <div style={{ marginBottom: '24px' }}>
        {/* Breadcrumb */}
        <div style={{ marginBottom: '16px' }}>
          {breadcrumb ?? <AppBreadcrumb />}
        </div>

        {/* Header */}
        {(title != null || extra != null || onBack != null) && (
          <Row justify="space-between" align="middle" gutter={[16, 16]}>
            <Col flex="1">
              <Space align="center" size={16}>
                {(onBack === true || typeof onBack === 'function') && (
                  <Button
                    type="text"
                    icon={<ArrowLeftOutlined />}
                    onClick={handleBack}
                    aria-label="返回"
                    style={{ fontSize: '16px', width: 32, height: 32, padding: 0 }}
                  />
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {typeof title === 'string' ? (
                      <Title level={2} style={{ margin: 0 }}>
                        {title}
                      </Title>
                    ) : (
                      title
                    )}
                  </div>
                  {subTitle != null && (
                    <Text type="secondary" style={{ marginTop: '4px' }}>
                      {subTitle}
                    </Text>
                  )}
                </div>
              </Space>
            </Col>
            {extra != null && <Col>{extra}</Col>}
          </Row>
        )}
      </div>

      {/* Content */}
      <Spin spinning={loading} size="large">
        {children}
      </Spin>
    </div>
  );
};

export default PageContainer;
