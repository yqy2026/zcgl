import React from 'react';
import { Typography, Button, Space, Row, Col, Spin } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import AppBreadcrumb from '@/components/Layout/AppBreadcrumb';
import styles from './PageContainer.module.css';

const { Title, Text } = Typography;

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
  const hasBackAction = onBack === true || typeof onBack === 'function';
  const hasHeader = title != null || extra != null || hasBackAction;
  const pageClassName = [styles.pageContainer, className]
    .filter((currentClassName): currentClassName is string => {
      return currentClassName != null && currentClassName !== '';
    })
    .join(' ');

  const handleBack = () => {
    if (typeof onBack === 'function') {
      onBack();
    } else {
      navigate(-1);
    }
  };

  return (
    <div className={pageClassName} style={contentStyle}>
      <div className={styles.headerSection}>
        {/* Breadcrumb */}
        <div className={styles.breadcrumbSection}>
          {breadcrumb ?? <AppBreadcrumb />}
        </div>

        {/* Header */}
        {hasHeader && (
          <Row justify="space-between" align="middle" gutter={[16, 16]} className={styles.headerRow}>
            <Col flex="auto">
              <Space align="center" size={16} className={styles.headerTitleGroup}>
                {hasBackAction && (
                  <Button
                    type="text"
                    icon={<ArrowLeftOutlined />}
                    onClick={handleBack}
                    aria-label="返回"
                    className={styles.backButton}
                  />
                )}
                <div className={styles.titleBlock}>
                  <div className={styles.titleRow}>
                    {typeof title === 'string' ? (
                      <Title level={2} className={styles.title}>
                        {title}
                      </Title>
                    ) : (
                      title
                    )}
                  </div>
                  {subTitle != null && (
                    <Text type="secondary" className={styles.subTitle}>
                      {subTitle}
                    </Text>
                  )}
                </div>
              </Space>
            </Col>
            {extra != null && <Col className={styles.extraSection}>{extra}</Col>}
          </Row>
        )}
      </div>

      {/* Content */}
      <Spin spinning={loading} size="large" className={styles.contentSpin}>
        {children}
      </Spin>
    </div>
  );
};

export default PageContainer;
