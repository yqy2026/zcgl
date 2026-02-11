import React from 'react';
import { Row, Col, Card, Space } from 'antd';
import {
  PlusOutlined,
  ImportOutlined,
  ExportOutlined,
  BarChartOutlined,
  FileTextOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { AntdIconProps } from '@ant-design/icons/lib/components/AntdIcon';
import styles from './QuickActions.module.css';

type ActionTone = 'primary' | 'success' | 'warning' | 'info' | 'secondary' | 'neutral';

interface QuickActionItem {
  title: string;
  description: string;
  icon: React.ComponentType<AntdIconProps>;
  tone: ActionTone;
  onClick: () => void;
}

const QuickActions: React.FC = () => {
  const navigate = useNavigate();
  const toneClassMap: Record<ActionTone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    info: styles.toneInfo,
    secondary: styles.toneSecondary,
    neutral: styles.toneNeutral,
  };

  const actions: QuickActionItem[] = [
    {
      title: '新增资产',
      description: '添加新的物业资产',
      icon: PlusOutlined,
      tone: 'primary',
      onClick: () => navigate('/assets/new'),
    },
    {
      title: '批量导入',
      description: '从Excel导入资产数据',
      icon: ImportOutlined,
      tone: 'success',
      onClick: () => navigate('/assets/import'),
    },
    {
      title: '数据导出',
      description: '导出资产清单',
      icon: ExportOutlined,
      tone: 'warning',
      onClick: () => navigate('/assets/list'),
    },
    {
      title: '资产分析',
      description: '查看详细分析报告',
      icon: BarChartOutlined,
      tone: 'info',
      onClick: () => navigate('/assets/analytics'),
    },
    {
      title: '生成报表',
      description: '生成管理报表',
      icon: FileTextOutlined,
      tone: 'secondary',
      onClick: () => navigate('/reports'),
    },
    {
      title: '系统设置',
      description: '配置系统参数',
      icon: SettingOutlined,
      tone: 'neutral',
      onClick: () => navigate('/settings'),
    },
  ];

  return (
    <Row gutter={[16, 16]} className={styles.actionsGrid}>
      {actions.map(action => {
        const IconComponent = action.icon;

        return (
          <Col xs={24} sm={12} md={8} lg={6} xl={4} key={action.title}>
            <Card
              hoverable
              className={styles.actionCard}
              onClick={action.onClick}
              role="button"
              tabIndex={0}
              onKeyDown={event => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  action.onClick();
                }
              }}
            >
              <Space orientation="vertical" size="small" className={styles.actionContent}>
                <IconComponent className={`${styles.actionIcon} ${toneClassMap[action.tone]}`} />
                <div className={styles.actionTextGroup}>
                  <div className={styles.actionTitle}>{action.title}</div>
                  <div className={styles.actionDescription}>{action.description}</div>
                </div>
              </Space>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
};

export default QuickActions;
