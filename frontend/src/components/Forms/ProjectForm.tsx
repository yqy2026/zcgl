/**
 * 项目表单组件 - 精简版本
 */

import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Space, Card, Tag } from 'antd';
import type { RuleObject } from 'antd/es/form';
import { MessageManager } from '@/utils/messageManager';
import PartySelector from '@/components/Common/PartySelector';
import type { PartySelectorSelection } from '@/components/Common/PartySelector';

import { projectService } from '@/services/projectService';
import type { Project, ProjectCreate, ProjectUpdate } from '@/types/project';
import { createLogger } from '@/utils/logger';
import styles from './ProjectForm.module.css';

const componentLogger = createLogger('ProjectForm');
const { TextArea } = Input;

interface ProjectFormProps {
  project?: Project | null;
  onSuccess: () => void;
  onCancel: () => void;
}

const ProjectForm: React.FC<ProjectFormProps> = ({ project, onSuccess, onCancel }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedOwnerParties, setSelectedOwnerParties] = useState<PartySelectorSelection[]>([]);
  const [pendingOwnerPartyId, setPendingOwnerPartyId] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (project !== undefined && project !== null) {
      // 设置基本信息
      form.setFieldsValue({
        name: project.name,
        description: project.description ?? '',
      });

      // 设置主体关联（Phase 3 主链）
      if (project.party_relations != null && project.party_relations.length > 0) {
        const selectedMap = new Map<string, PartySelectorSelection>();
        project.party_relations.forEach(relation => {
          const partyId = relation.party_id.trim();
          if (partyId === '' || selectedMap.has(partyId)) {
            return;
          }
          const partyName = relation.party_name?.trim();
          selectedMap.set(partyId, {
            party_id: partyId,
            party_name: partyName != null && partyName !== '' ? partyName : partyId,
          });
        });
        setSelectedOwnerParties(Array.from(selectedMap.values()));
      } else {
        setSelectedOwnerParties([]);
      }
    } else {
      form.resetFields();
      setSelectedOwnerParties([]);
    }
    setPendingOwnerPartyId(undefined);
  }, [project, form]);

  // 添加所有方主体
  const addOwnerParty = (selection: PartySelectorSelection) => {
    if (selectedOwnerParties.some(item => item.party_id === selection.party_id)) {
      return;
    }
    setSelectedOwnerParties(prev => [...prev, selection]);
  };

  // 移除所有方主体
  const removeOwnerParty = (partyId: string) => {
    setSelectedOwnerParties(prev => prev.filter(item => item.party_id !== partyId));
  };

  // 表单提交
  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      // 构建 party_relations（前端主链）
      const party_relations = selectedOwnerParties.map(selection => ({
        party_id: selection.party_id,
        relation_type: 'owner',
        is_primary: true,
      }));

      const submitData = {
        ...values,
        party_relations,
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

  // 验证项目名称
  const validateProjectName: RuleObject['validator'] = async (_rule, value) => {
    if (value == null || value === '') return Promise.reject('请输入项目名称');
    if (String(value).length < 1) return Promise.reject('项目名称至少1个字符');
    if (String(value).length > 200) return Promise.reject('项目名称不能超过200个字符');
    return Promise.resolve();
  };

  return (
    <Form form={form} layout="vertical" onFinish={handleSubmit} autoComplete="off">
      <Card title="项目信息" size="small">
        <Form.Item
          label="项目名称"
          name="name"
          rules={[{ required: true, validator: validateProjectName }]}
        >
          <Input placeholder="请输入项目名称" maxLength={200} />
        </Form.Item>

        <Form.Item label="项目描述" name="description">
          <TextArea placeholder="请输入项目描述" rows={3} maxLength={1000} />
        </Form.Item>
      </Card>

      <Card title="所有方主体关联" size="small" className={styles.ownershipCard}>
        <Form.Item label="选择所有方主体">
          <div className={styles.ownershipSelectWrapper}>
            <PartySelector
              placeholder="选择要关联的所有方主体"
              value={pendingOwnerPartyId}
              onChange={(value, selection) => {
                setPendingOwnerPartyId(value);
                if (selection != null) {
                  addOwnerParty(selection);
                  setPendingOwnerPartyId(undefined);
                }
              }}
            />
          </div>
        </Form.Item>

        {selectedOwnerParties.length > 0 && (
          <div className={styles.selectedOwnershipsSection}>
            <div className={styles.selectedOwnershipsTitle}>已选择的所有方主体：</div>
            <div className={styles.selectedOwnershipsList}>
              {selectedOwnerParties.map(selection => (
                <Tag
                  key={selection.party_id}
                  color="blue"
                  closable
                  onClose={() => removeOwnerParty(selection.party_id)}
                  className={styles.selectedOwnershipTag}
                >
                  {selection.party_name}
                </Tag>
              ))}
            </div>
          </div>
        )}
      </Card>

      <div className={styles.formActions}>
        <Space>
          <Button onClick={onCancel}>取消</Button>
          <Button type="primary" htmlType="submit" loading={loading}>
            {project ? '更新' : '创建'}
          </Button>
        </Space>
      </div>
    </Form>
  );
};

export default ProjectForm;
