/**
 * 项目操作组件 - 弹窗与操作按钮
 * 从 ProjectList.tsx 拆分而来，负责项目的创建/编辑/详情弹窗及删除确认
 */

import React from 'react';
import { Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

import { projectService } from '@/services/projectService';
import { MessageManager } from '@/utils/messageManager';
import type { Project } from '@/types/project';
import { ProjectForm } from '@/components/Forms';
import ProjectDetail from './ProjectDetail';

const { confirm } = Modal;

// --- 操作函数 ---

/**
 * 删除项目（带确认弹窗）
 */
export function confirmDeleteProject(project: Project, onSuccess: () => void): void {
  confirm({
    title: '确认删除',
    icon: <ExclamationCircleOutlined />,
    content: `确定要删除项目 "${project.project_name}" 吗？`,
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      try {
        await projectService.deleteProject(project.id);
        MessageManager.success('项目删除成功');
        onSuccess();
      } catch (error) {
        console.error('删除项目失败:', error);
        MessageManager.error('删除项目失败');
      }
    },
  });
}

/**
 * 切换项目状态
 */
export async function toggleProjectStatus(project: Project, onSuccess: () => void): Promise<void> {
  try {
    await projectService.toggleProjectStatus(project.id);
    MessageManager.success('项目状态切换成功');
    onSuccess();
  } catch (error) {
    console.error('切换项目状态失败:', error);
    MessageManager.error('切换项目状态失败');
  }
}

// --- 弹窗组件 ---

interface ProjectFormModalProps {
  visible: boolean;
  editingProject: Project | null;
  onClose: () => void;
  onSuccess: () => void;
}

/**
 * 项目创建/编辑弹窗
 */
export const ProjectFormModal: React.FC<ProjectFormModalProps> = ({
  visible,
  editingProject,
  onClose,
  onSuccess,
}) => (
  <Modal
    title={editingProject ? '编辑项目' : '新建项目'}
    open={visible}
    onCancel={onClose}
    footer={null}
    width={600}
    destroyOnHidden
  >
    <ProjectForm
      project={editingProject}
      onSuccess={onSuccess}
      onCancel={onClose}
    />
  </Modal>
);

interface ProjectDetailModalProps {
  visible: boolean;
  project: Project | null;
  onClose: () => void;
  onEdit: () => void;
}

/**
 * 项目详情弹窗
 */
export const ProjectDetailModal: React.FC<ProjectDetailModalProps> = ({
  visible,
  project,
  onClose,
  onEdit,
}) => (
  <Modal
    title="项目详情"
    open={visible}
    onCancel={onClose}
    footer={null}
    width={800}
    destroyOnHidden
  >
    {project && <ProjectDetail project={project} onEdit={onEdit} />}
  </Modal>
);
