/**
 * 权属方详情组件
 */

import React from 'react';
import { Descriptions, Card, Tag, Space, Button, Badge, Typography, Table } from 'antd';
import { EditOutlined, ProjectOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import type { Ownership } from '@/types/ownership';

const { Text } = Typography;

interface OwnershipDetailProps {
  ownership: Ownership;
  onEdit: () => void;
}

const OwnershipDetail: React.FC<OwnershipDetailProps> = ({ ownership, onEdit }) => {
  const formatDate = (dateStr?: string) => {
    if (dateStr === null || dateStr === undefined || dateStr === '') {
      return '-';
    }
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  // 关联项目的简化类型
  interface RelatedProject {
    id: string;
    name: string;
    code: string;
    relation_type: string;
    start_date?: string;
    end_date?: string;
  }

  // 关联项目表格列定义
  const projectColumns: ColumnsType<RelatedProject> = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <ProjectOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: '项目编码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '关系类型',
      dataIndex: 'relation_type',
      key: 'relation_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === '合作' ? 'blue' : type === '投资' ? 'green' : 'orange'}>{type}</Tag>
      ),
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      render: (date: string) => formatDate(date),
    },
    {
      title: '结束日期',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      render: (date: string) => formatDate(date),
    },
  ];

  return (
    <div>
      {/* 头部信息 */}
      <Card>
        <Space size="large" align="start">
          <div>
            <Text strong style={{ fontSize: 20 }}>
              {ownership.name}
            </Text>
            {ownership.short_name !== null &&
              ownership.short_name !== undefined &&
              ownership.short_name !== '' && (
                <div style={{ marginTop: 8, color: '#666' }}>简称：{ownership.short_name}</div>
              )}
          </div>
          <Badge
            status={ownership.is_active ? 'success' : 'error'}
            text={ownership.is_active ? '启用' : '禁用'}
          />
          <Button type="primary" icon={<EditOutlined />} onClick={onEdit}>
            编辑
          </Button>
        </Space>
      </Card>

      {/* 基本信息 */}
      <Card title="基本信息" style={{ marginTop: 16 }}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="权属方全称">{ownership.name}</Descriptions.Item>
          <Descriptions.Item label="权属方简称">
            {ownership.short_name !== null &&
              ownership.short_name !== undefined &&
              ownership.short_name !== ''
              ? ownership.short_name
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Badge
              status={ownership.is_active ? 'success' : 'error'}
              text={ownership.is_active ? '启用' : '禁用'}
            />
          </Descriptions.Item>
          <Descriptions.Item label="关联资产数量">
            <Tag color="blue">{ownership.asset_count ?? 0} 个</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="关联项目数量">
            <Tag color="green">{ownership.project_count ?? 0} 个</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 关联项目信息 */}
      {ownership.related_projects && ownership.related_projects.length > 0 && (
        <Card title="关联项目" style={{ marginTop: 16 }}>
          <Table
            columns={projectColumns}
            dataSource={ownership.related_projects}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* 系统信息 */}
      <Card title="系统信息" style={{ marginTop: 16 }}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="创建时间">{formatDate(ownership.created_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatDate(ownership.updated_at)}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default OwnershipDetail;
