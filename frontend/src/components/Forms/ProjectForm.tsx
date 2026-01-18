/**
 * 项目表单组件 - 精简版本
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Button,
  Space,
  Card,
  Select,
  Tag
} from 'antd';
import { MessageManager } from '@/utils/messageManager';

import { ownershipService } from '@/services/ownershipService';
import { projectService } from '@/services/projectService';
import type { Project, ProjectCreate, ProjectUpdate } from '@/types/project';
import type { Ownership } from '@/types/ownership';
import { createLogger } from '@/utils/logger';

const componentLogger = createLogger('ProjectForm');
const { TextArea } = Input;

interface ProjectFormProps {
  project?: Project | null;
  onSuccess: () => void;
  onCancel: () => void;
}

const ProjectForm: React.FC<ProjectFormProps> = ({
  project,
  onSuccess,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedOwnerships, setSelectedOwnerships] = useState<Ownership[]>([]);

  // 获取权属方列表
  useEffect(() => {
    const loadOwnerships = async () => {
      try {
        const response = await ownershipService.getOwnershipOptions(true);
        setOwnerships(response);
      } catch (error) {
        componentLogger.error('获取权属方列表失败:', error as Error);
        MessageManager.error('获取权属方列表失败');
      }
    };
    loadOwnerships();
  }, []);

  const [ownerships, setOwnerships] = useState<Ownership[]>([]);

  useEffect(() => {
    if (project !== undefined && project !== null) {
      // 设置基本信息
      form.setFieldsValue({
        name: project.name,
        description: project.description ?? ''
      });

      // 设置权属方关联
      if (project.ownership_relations && project.ownership_relations.length > 0) {
        const ownershipIds = project.ownership_relations.map(rel => rel.ownership_id);
        const selected = ownerships.filter(ownership =>
          ownershipIds.includes(ownership.id)
        );
        setSelectedOwnerships(selected);
      } else {
        setSelectedOwnerships([]);
      }
    } else {
      form.resetFields();
      setSelectedOwnerships([]);
    }
  }, [project, form, ownerships]);

  // 添加权属方
  const addOwnership = (ownership: Ownership) => {
    if (!selectedOwnerships.find(o => o.id === ownership.id)) {
      const newSelected = [...selectedOwnerships, ownership];
      setSelectedOwnerships(newSelected);
    }
  };

  // 移除权属方
  const removeOwnership = (ownershipId: string) => {
    const newSelected = selectedOwnerships.filter(o => o.id !== ownershipId);
    setSelectedOwnerships(newSelected);
  };

  // 表单提交
  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      // 构建简化的ownership_relations数据
      const ownership_relations = selectedOwnerships.map(ownership => ({
        ownership_id: ownership.id,
        relation_type: '关联'
      }));

      const submitData = {
        ...values,
        ownership_relations
      };

      if (project !== undefined && project !== null) {
        await projectService.updateProject(project.id, submitData as ProjectUpdate);
        MessageManager.success('项目更新成功');
      } else {
        await projectService.createProject(submitData as ProjectCreate);
        MessageManager.success('项目创建成功');
      }
      onSuccess();
    } catch (error: unknown) {
      componentLogger.error('保存项目失败:', error as Error);
      const err = error as { response?: { data?: { detail?: string } } };
      const errorMsg = err.response?.data?.detail ?? '保存项目失败';
      MessageManager.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 表单验证规则接口
  interface FormValidationRule {
    field?: string
    fullField?: string
    type?: string
    validator?: (rule: FormValidationRule, value: unknown) => Promise<void>
  }

  // 验证项目名称
  const validateProjectName = async (rule: FormValidationRule, value: string) => {
    if (value == null) return Promise.reject('请输入项目名称');
    if (value.length < 1) return Promise.reject('项目名称至少1个字符');
    if (value.length > 200) return Promise.reject('项目名称不能超过200个字符');
    return Promise.resolve();
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      autoComplete="off"
    >
      <Card title="项目信息" size="small">
        <Form.Item
          label="项目名称"
          name="name"
          rules={[
            { required: true, validator: validateProjectName as any }
          ]}
        >
          <Input placeholder="请输入项目名称" maxLength={200} />
        </Form.Item>

        <Form.Item
          label="项目描述"
          name="description"
        >
          <TextArea
            placeholder="请输入项目描述"
            rows={3}
            maxLength={1000}
          />
        </Form.Item>
      </Card>

      <Card title="权属方关联" size="small" style={{ marginTop: 16 }}>
        <Form.Item label="选择权属方">
          <Select
            placeholder="选择要关联的权属方"
            style={{ width: '100%' }}
            loading={!ownerships.length}
            optionFilterProp="children"
            filterOption={(input, option) =>
              (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
            }
            onSelect={(value) => {
              const ownership = ownerships.find(o => o.id === value);
              if (ownership !== undefined && ownership !== null) {
                addOwnership(ownership);
              }
            }}
            value={undefined}
          >
            {ownerships
              .filter(ownership => !selectedOwnerships.find(o => o.id === ownership.id))
              .map(ownership => (
                <Select.Option key={ownership.id} value={ownership.id}>
                  {ownership.name}
                </Select.Option>
              ))}
          </Select>
        </Form.Item>

        {selectedOwnerships.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 'bold' }}>已选择的权属方：</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {selectedOwnerships.map(ownership => (
                <Tag
                  key={ownership.id}
                  color="blue"
                  closable
                  onClose={() => removeOwnership(ownership.id)}
                  style={{ padding: '4px 8px', fontSize: '14px' }}
                >
                  {ownership.name}
                </Tag>
              ))}
            </div>
          </div>
        )}

      </Card>

      <div style={{ marginTop: 16 }}>
        <Space style={{ float: 'right' }}>
          <Button onClick={onCancel}>
            取消
          </Button>
          <Button type="primary" htmlType="submit" loading={loading}>
            {project ? '更新' : '创建'}
          </Button>
        </Space>
      </div>
    </Form>
  );
};

export default ProjectForm;
