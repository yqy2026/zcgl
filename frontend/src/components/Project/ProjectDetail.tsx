/**
 * 项目详情组件 - 精简版本
 */

import React from 'react';
import { Descriptions, Card, Tag, Space, Button, Badge, Typography } from 'antd';
import { EditOutlined } from '@ant-design/icons';

import type { Project } from '@/types/project';
import styles from './ProjectDetail.module.css';

const { Text } = Typography;

interface ProjectDetailProps {
  project: Project;
  onEdit: () => void;
}

const ProjectDetail: React.FC<ProjectDetailProps> = ({ project, onEdit }) => {
  const formatDate = (dateStr?: string | null) => {
    if (dateStr === null || dateStr === undefined || dateStr === '') {
      return '-';
    }
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case '正常':
        return 'green';
      case '禁用':
        return 'red';
      case '删除':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <div className={styles.projectDetail}>
      {/* 项目基本信息 */}
      <Card>
        <div className={styles.headerRow}>
          <div>
            <Space>
              <h2 className={styles.projectTitle}>{project.name}</h2>
              <Badge
                status={project.is_active ? 'success' : 'error'}
                text={project.is_active ? '启用' : '禁用'}
              />
            </Space>
          </div>
          <div>
            <Button type="primary" icon={<EditOutlined />} onClick={onEdit}>
              编辑项目
            </Button>
          </div>
        </div>
      </Card>

      {/* 项目详细信息 */}
      <Card title="项目信息" size="small" className={styles.sectionCard}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="项目编码">
            <Text code>{project.code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="项目状态">
            <Tag color={getStatusColor(project.data_status)}>{project.data_status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="项目描述">
            <Text>
              {project.description !== null &&
              project.description !== undefined &&
              project.description !== ''
                ? project.description
                : '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="关联资产数量">
            <Badge count={project.asset_count ?? 0} />
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 系统信息 */}
      <Card title="系统信息" size="small" className={styles.sectionCard}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="创建时间">{formatDate(project.created_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatDate(project.updated_at)}</Descriptions.Item>
          <Descriptions.Item label="创建人">
            {project.created_by !== null &&
            project.created_by !== undefined &&
            project.created_by !== ''
              ? project.created_by
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新人">
            {project.updated_by !== null &&
            project.updated_by !== undefined &&
            project.updated_by !== ''
              ? project.updated_by
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default ProjectDetail;
