/**
 * 项目表格列定义组件
 * 从 ProjectList.tsx 拆分而来，负责表格列渲染逻辑
 */

import React from 'react';
import { Button, Space, Tag, Tooltip, Badge, Switch } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { getIconButtonProps } from '@/utils/accessibility';
import type { Project } from '@/types/project';
import styles from './ProjectList.module.css';

// --- 共享常量与工具函数 ---

export const PROJECT_STATUS_MAP: Record<string, { text: string; color: string }> = {
  planning: { text: '规划中', color: 'default' },
  active: { text: '进行中', color: 'green' },
  paused: { text: '已暂停', color: 'orange' },
  completed: { text: '已完成', color: 'blue' },
  terminated: { text: '已终止', color: 'red' },
};

export const isRelationActive = (relation: { is_active?: boolean }): boolean =>
  relation.is_active === true;

export const getProjectAssetCount = (project: Project): number => {
  if (typeof project.asset_count === 'number' && Number.isFinite(project.asset_count)) {
    return project.asset_count;
  }
  return 0;
};

export const isPendingBindingProject = (project: Project): boolean =>
  getProjectAssetCount(project) === 0;

// --- 列定义参数 ---

export interface ProjectColumnHandlers {
  onView: (project: Project) => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
  onSelect: (project: Project) => void;
  onToggleStatus: (project: Project) => void;
  mode: 'list' | 'select';
}

/**
 * 构建项目表格列定义
 */
export function getProjectColumns(handlers: ProjectColumnHandlers): ColumnsType<Project> {
  const { onView, onEdit, onDelete, onSelect, onToggleStatus, mode } = handlers;

  return [
    {
      title: '项目名称',
      dataIndex: 'project_name',
      key: 'project_name',
      render: (text: string, record: Project) => (
        <Button type="link" onClick={() => onView(record)} className={styles.projectNameButton}>
          {text}
        </Button>
      ),
    },
    {
      title: '项目编码',
      dataIndex: 'project_code',
      key: 'project_code',
      width: 120,
    },
    {
      title: '所有方主体',
      dataIndex: 'party_relations',
      key: 'owner_party',
      width: 150,
      render: (_relations: Project['party_relations'], record: Project) => {
        // 优先展示 active 的 party_relations
        if (record.party_relations != null && record.party_relations.length > 0) {
          const activeRelations = record.party_relations.filter(rel => isRelationActive(rel));
          if (activeRelations.length > 0) {
            return (
              <div>
                {activeRelations.slice(0, 2).map((rel, index) => (
                  <Tag
                    key={rel.id ?? `${rel.party_id}-${index}`}
                    color="blue"
                    className={styles.ownershipTag}
                  >
                    {rel.party_name ?? '主体已关联'}
                  </Tag>
                ))}
                {activeRelations.length > 2 && (
                  <Tag color="gray">+{activeRelations.length - 2}</Tag>
                )}
              </div>
            );
          }
        }

        return '-';
      },
    },
    {
      title: '业务状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={PROJECT_STATUS_MAP[status]?.color ?? 'default'}>
          {PROJECT_STATUS_MAP[status]?.text ?? status}
        </Tag>
      ),
    },
    {
      title: '关联资产',
      dataIndex: 'asset_count',
      key: 'asset_count',
      width: 100,
      render: (_count: number, record: Project) => getProjectAssetCount(record),
    },
    {
      title: '面积统计',
      key: 'area_status',
      width: 100,
      render: (_value: unknown, record: Project) =>
        isPendingBindingProject(record) ? <Tag color="default">N/A</Tag> : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status_indicator',
      width: 80,
      render: (status: string, record: Project) => (
        <Space size="small">
          <Badge
            status={status === 'active' ? 'success' : 'default'}
            text={status === 'active' ? '启用' : '非启用'}
          />
          {isPendingBindingProject(record) && <Tag color="warning">待补绑定</Tag>}
        </Space>
      ),
    },
    {
      title: '数据状态',
      dataIndex: 'data_status',
      key: 'data_status',
      width: 100,
      render: (text: string) => {
        let color = 'default';
        switch (text) {
          case '正常':
            color = 'green';
            break;
          case '禁用':
            color = 'red';
            break;
          case '删除':
            color = 'default';
            break;
        }
        return <Tag color={color}>{text ?? '-'}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record: Project) => (
        <Space size="small">
          {mode === 'select' && (
            <Button type="primary" size="small" onClick={() => onSelect(record)}>
              选择
            </Button>
          )}
          {mode === 'list' && (
            <>
              <Tooltip title="查看详情">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => onView(record)}
                  {...getIconButtonProps('view', '项目')}
                />
              </Tooltip>
              <Tooltip title="编辑">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => onEdit(record)}
                  {...getIconButtonProps('edit', '项目')}
                />
              </Tooltip>
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => onDelete(record)}
                  {...getIconButtonProps('delete', '项目')}
                />
              </Tooltip>
            </>
          )}
          <Switch
            size="small"
            checked={record.status === 'active'}
            onChange={() => onToggleStatus(record)}
            checkedChildren="启用"
            unCheckedChildren="禁用"
            aria-label={`${record.status === 'active' ? '停用' : '启用'}项目 ${record.project_name}`}
          />
        </Space>
      ),
    },
  ];
}
