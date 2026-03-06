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

  const statusMap: Record<string, { color: string; text: string; active: boolean }> = {
    planning: { color: 'default', text: '规划中', active: false },
    active: { color: 'green', text: '进行中', active: true },
    paused: { color: 'orange', text: '已暂停', active: false },
    completed: { color: 'blue', text: '已完成', active: false },
    terminated: { color: 'red', text: '已终止', active: false },
  };
  const statusMeta = statusMap[project.status] ?? {
    color: 'default',
    text: project.status,
    active: false,
  };

  return (
    <div className={styles.projectDetail}>
      {/* 项目基本信息 */}
      <Card>
        <div className={styles.headerRow}>
          <div>
            <Space>
              <h2 className={styles.projectTitle}>{project.project_name}</h2>
              <Badge
                status={statusMeta.active ? 'success' : 'default'}
                text={statusMeta.text}
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
            <Text code>{project.project_code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="业务状态">
            <Tag color={statusMeta.color}>{statusMeta.text}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="项目状态">
            <Tag color={project.data_status === '正常' ? 'green' : 'default'}>{project.data_status}</Tag>
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
