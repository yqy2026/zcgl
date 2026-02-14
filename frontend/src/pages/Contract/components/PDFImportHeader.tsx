/**
 * PDF导入页面头部组件
 *
 * 显示页面标题、描述和操作按钮
 */

import React from 'react';
import { Card, Button, Space, Row, Col, Typography } from 'antd';
import { UploadOutlined, QuestionCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import styles from './PDFImportHeader.module.css';

const { Title, Text } = Typography;

interface PDFImportHeaderProps {
  onShowHelp: () => void;
  onReload: () => void;
  loading: boolean;
}

export const PDFImportHeader: React.FC<PDFImportHeaderProps> = ({
  onShowHelp,
  onReload,
  loading,
}) => {
  return (
    <Card className={styles.headerCard}>
      <Row justify="space-between" align="middle">
        <Col>
          <Space size="large">
            <div className={styles.uploadIconWrapper}>
              <UploadOutlined className={styles.uploadIcon} />
            </div>
            <div>
              <Title level={3} className={styles.headerTitle}>
                PDF合同智能导入
              </Title>
              <Text type="secondary">上传PDF文件,自动提取合同信息并导入系统</Text>
            </div>
          </Space>
        </Col>
        <Col>
          <Space>
            <Button icon={<QuestionCircleOutlined />} onClick={onShowHelp}>
              使用帮助
            </Button>
            <Button icon={<ReloadOutlined />} onClick={onReload} loading={loading}>
              刷新
            </Button>
          </Space>
        </Col>
      </Row>
    </Card>
  );
};
